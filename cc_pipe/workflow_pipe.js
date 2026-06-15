export const meta = {
  name: 'cc-pipe-evolve',
  description: 'Evolve a TYPED SELF-CORRECTION PIPELINE (the harness) with GEPA or CORE: genotype = role sequence in {draft,critique,fix} (step0=draft) + a free-text prompt per role; BOTH structure and prompts evolve. Execution = keep-best chain with in-process engine feedback (adversarial-board rule checks) feeding critique/fix. Fitness = mean ladder win-rate of the per-replicate best over R replicates; two-sample verified gate. The Haiku->Sonnet PoC: does an evolved Haiku pipeline beat best-of-N/refine-N at equal budget and approach single-shot Sonnet? Ends after Evolve; compare via final-compare.',
  phases: [
    { title: 'Init', detail: 'config + ladder + contracts + seed pipelines (+ empty bank for CORE)' },
    { title: 'Gen0', detail: 'execute every seed pipeline (R replicates, keep-best chain) + clean ladder scoring' },
    { title: 'Evolve', detail: 'OUTER_GENERATIONS: select -> [CORE: contrastive reflection over pipelines -> bank] -> mutate structure/prompt -> R-replicate eval -> two-sample gate -> refill' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = (A && A.ccroot) || '/ABSOLUTE/PATH/TO/evolving-agent-harnesses'
const OPT = (A.optimizer === 'core') ? 'core' : 'gepa'
const OUT = A.out || (CCROOT + '/cc_pipe_evo_' + OPT)
const N = A.N ?? 4
const R = A.R ?? 3
const SEED = A.seed ?? 0
const GEN = A.generations ?? 5
const POP = A.pop ?? 6
const SURVIVORS = A.survivors ?? 3
const SIMS_EVAL = A.sims_eval ?? 100
const SIMS_CAND = A.sims_cand ?? 60
const PAIRS = A.pairs ?? SURVIVORS
const TOPK = A.topk ?? 3
const MAX_LESSONS = A.max_lessons ?? 4
const MAXW = A.maxw ?? 8
const HALT = A.halt_tokens ?? 12_000_000
const spent = () => { try { return budget && budget.spent ? budget.spent() : 0 } catch (e) { return 0 } }
const _s0 = spent(); const runSpent = () => Math.max(0, spent() - _s0)
const REFLECT = 'sonnet'
const py = `cd ${CCROOT} && CC_MAXW=${MAXW} python3 -m cc_pipe.control_pipe`
const pad2 = n => String(n).padStart(2, '0')
const ROLES = ['draft', 'critique', 'fix']

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, optimizer: { type: 'string' }, seed_ids: { type: 'array', items: { type: 'string' } }, seed_labels: { type: 'object' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' }, label: { type: 'string' }, exists: { type: 'boolean' } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, cand_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_fail: { type: 'number' }, summary: { type: 'string' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, R_valid: { type: 'number' }, per_rung: { type: 'object' } }, required: ['ok'] }
const SCORE_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok'] }
const SEL_S = { type: 'object', properties: { ok: { type: 'boolean' }, survivors: { type: 'array', items: { type: 'string' } }, champion: { type: ['string', 'null'] } }, required: ['ok'] }
const BREED_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, survivors: { type: 'array' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const ADMIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, admitted: { type: 'boolean' }, delta: { type: ['number', 'null'] }, ci_low: { type: ['number', 'null'] }, ci_high: { type: ['number', 'null'] } }, required: ['ok'] }
const FIN_S = { type: 'object', properties: { ok: { type: 'boolean' }, ids: { type: 'array', items: { type: 'string' } }, n_admitted: { type: 'number' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok', 'ids'] }
const REFLECT_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_pairs: { type: 'number' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const INGEST_S = { type: 'object', properties: { ok: { type: 'boolean' }, added: { type: 'number' }, merged: { type: 'number' }, bank_size: { type: 'number' } }, required: ['ok'] }
const CREDIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_credited: { type: 'number' }, bank_size: { type: 'number' } }, required: ['ok'] }
const BANK_S = { type: 'object', properties: { ok: { type: 'boolean' }, bank_size: { type: 'number' }, total_wins: { type: 'number' } }, required: ['ok'] }

async function runPy(cmd, schema, label, phase, model = 'haiku') {
  const prompt = `Run EXACTLY this shell command and report its result:\n\`\`\`\n${py} ${cmd}\n\`\`\`\n` +
    `It prints a single JSON object on its last stdout line. Return THAT JSON object via structured output. ` +
    `If it exits non-zero, run it once more; if it still fails, return {"ok": false, "error": "<stderr tail>"}.`
  let r = null
  for (let i = 0; i < 4; i++) {
    try { r = await agent(prompt, { label: i ? `${label}~r${i}` : label, phase, schema, model }); if (r && r.ok !== false) return r }
    catch (e) { log(`py ${label}: attempt ${i + 1} threw — retry`); r = { ok: false } }
  }
  return r || { ok: false }
}

const gdir = (gen, aid) => `${OUT}/gen_${pad2(gen)}/genotypes/agent_${aid}`

function draftPrompt(gen, aid, r, idx, model) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake CODER (model=${model.toUpperCase()}), replicate ${r} attempt ${idx}. Read the contract ` +
    `${OUT}/contracts/simple_bot_contract.txt and the strategy ${d}/prompts/draft.md . Write the strongest complete ` +
    `single-file bot you can as raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py (info/start/end/move; ` +
    `pure; never raises; stdlib only; fast). Return one line.`
}
function critiquePrompt(gen, aid, r) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake bot REVIEWER (model=HAIKU). Read the current best bot ${d}/repl_${r}/best.py , the engine ` +
    `feedback ${d}/repl_${r}/feedback.json (failed adversarial boards), and the critique guidance ${d}/prompts/critique.md . ` +
    `Name the SINGLE biggest concrete weakness and exactly what to change; write it with the Write tool to ${d}/repl_${r}/note.txt . Return one line.`
}
function fixPrompt(gen, aid, r, idx) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake IMPROVER (model=HAIKU), replicate ${r}. Read the current best bot ${d}/repl_${r}/best.py , the ` +
    `engine feedback ${d}/repl_${r}/feedback.json , the critique note ${d}/repl_${r}/note.txt (if present), and the fix guidance ` +
    `${d}/prompts/fix.md . Apply the critique and fix the specific failures to produce an IMPROVED complete single-file bot ` +
    `(keep info/start/end/move; pure; never raises; stdlib only). Write raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py . Return one line.`
}

// ---- mutation agents ----
const GENO_DESC = `The genotype is a budget-${N} self-correction PIPELINE: roles.json = {"roles": [${N} steps, each ` +
  `"draft"|"critique"|"fix"; step 0 must be "draft"], "draft_model": "haiku"} + a free-text prompt per role at ` +
  `prompts/draft.md, prompts/critique.md, prompts/fix.md. Execution is a keep-best chain: draft/fix make a bot (scored), ` +
  `critique reads the best bot + engine feedback and writes a diagnosis the next fix uses. The child already CONTAINS the ` +
  `parent's roles.json + prompts (a clone) — edit in place.`

function gepaMutate(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  if (off.lens === 'structure') {
    return `You are an OUTER-OPTIMIZER STRUCTURE lens (model=SONNET) evolving a budget-${N} BattleSnake self-correction ` +
      `pipeline. ${GENO_DESC}\nPARENT performance: ${pd}/metrics.json (mean ladder win-rate over ${R} runs + per-rung). ` +
      `Make ONE structural change to ${cd}/roles.json: retype or reorder a single step (keep exactly ${N} steps, step 0 = ` +
      `"draft", no trailing "critique"). E.g. turn a blind "fix" into a "critique" then "fix", or add an extra "draft" for ` +
      `diversity. Write the new ${cd}/roles.json (valid JSON: {"roles": [...], "draft_model": "haiku"}). ALSO update ` +
      `${cd}/lineage.json "diff" (one line). Return one line.`
  }
  const role = off.lens
  return `You are an OUTER-OPTIMIZER lens = "${role}" (model=SONNET) evolving a budget-${N} BattleSnake self-correction ` +
    `pipeline. ${GENO_DESC}\nPARENT performance: ${pd}/metrics.json . Rewrite ONLY the "${role}" role prompt to improve where ` +
    `the bots lose (for "draft": a stronger first bot; "critique": sharper diagnosis from engine feedback; "fix": apply the ` +
    `critique without regressing — note blind refinement currently HURTS, so make the fix targeted and conservative). Write ` +
    `the full improved prompt with the Write tool to ${cd}/prompts/${role}.md (keep the other files untouched). ALSO update ` +
    `${cd}/lineage.json "diff". Return one line.`
}
function coreReflect(p) {
  return `You are a CONTRASTIVE-REFLECTION analyst (model=SONNET) studying how to design a budget-${N} BattleSnake ` +
    `self-correction pipeline (role sequence in {draft,critique,fix} + a prompt per role). Two pipelines were each run ${R} ` +
    `times and scored on the SAME ladder:\n[WINNER] (win-rate ${p.winner_fitness}, shape ${p.winner_label}) — roles+prompts in ` +
    `${p.winner_dir}/ , metrics ${p.winner_dir}/metrics.json\n[LOSER] (win-rate ${p.loser_fitness}, shape ${p.loser_label}) — ` +
    `${p.loser_dir}/ , metrics ${p.loser_dir}/metrics.json\nLOSER profile: ${p.weakness}\n\nRead both pipelines' roles.json + ` +
    `prompts/*.md + metrics. Which difference — the role SHAPE (e.g. critique-before-fix vs blind fix, more drafts) or a role ` +
    `PROMPT — most plausibly caused the gap? Distil EXACTLY ${MAX_LESSONS} short INSIGHTS about pipeline design/prompts (e.g. ` +
    `"insert a critique before each fix so the fix is targeted", "blind fixes regress — make fix prompts conservative", "spend ` +
    `an extra draft when the first bot is weak"). Write a JSON array of ${MAX_LESSONS} objects {"lesson":"<=30 words","label":` +
    `"specific"|"meta"}. Write ONLY that JSON array with the Write tool to ${p.lessons_path} (valid JSON, no fences). Return one line.`
}
function coreMutate(gen, off) {
  const cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are a CORE MUTATION operator (model=SONNET) evolving a budget-${N} BattleSnake self-correction pipeline. ` +
    `${GENO_DESC}\nRETRIEVED INSIGHTS about pipeline design (from past winner-vs-loser pipelines, ranked by relevance + ` +
    `verified track record): read ${cd}/breed_context.json . Apply the most relevant insight(s) by editing the child in place: ` +
    `change ${cd}/roles.json (the shape — keep ${N} steps, step0="draft", no trailing critique) AND/OR rewrite one role prompt ` +
    `at ${cd}/prompts/<role>.md — a focused, coherent change. ALSO update ${cd}/lineage.json "changed_components" + "diff" (+ ` +
    `which insight ids); keep the existing "lessons_used" field. Return one line.`
}

async function runPipe(gen, aid, phase) {
  const plan = await runPy(`pipe-plan --out ${OUT} --gen ${gen} --agent ${aid} --N ${N}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`pipe CACHED [g${gen}/${aid}]`); return }
  const roles = plan.roles || ['draft']; const model = plan.draft_model || 'haiku'
  for (let r = 0; r < R; r++) {
    let cand = 0
    for (const role of roles) {
      if (role === 'draft') {
        await agent(draftPrompt(gen, aid, r, cand, model), { label: `draft:${aid}:r${r}:${cand}`, phase, model })
        await runPy(`pipe-score-cand --out ${OUT} --gen ${gen} --agent ${aid} --repl ${r} --cand ${cand} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SC_S, `score:${aid}:r${r}:${cand}`, phase)
        cand++
      } else if (role === 'critique') {
        await runPy(`pipe-feedback --out ${OUT} --gen ${gen} --agent ${aid} --repl ${r}`, FB_S, `fb:${aid}:r${r}`, phase)
        await agent(critiquePrompt(gen, aid, r), { label: `crit:${aid}:r${r}`, phase, model: 'haiku' })
      } else {
        await runPy(`pipe-feedback --out ${OUT} --gen ${gen} --agent ${aid} --repl ${r}`, FB_S, `fb:${aid}:r${r}:${cand}`, phase)
        await agent(fixPrompt(gen, aid, r, cand), { label: `fix:${aid}:r${r}:${cand}`, phase, model: 'haiku' })
        await runPy(`pipe-score-cand --out ${OUT} --gen ${gen} --agent ${aid} --repl ${r} --cand ${cand} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SC_S, `score:${aid}:r${r}:${cand}`, phase)
        cand++
      }
    }
  }
  const ev = await runPy(`pipe-eval-score --out ${OUT} --gen ${gen} --agent ${aid} --R ${R} --sims-cand ${SIMS_CAND} --seed ${SEED}`, EVAL_S, `eval:${aid}`, phase)
  log(`pipe [g${gen}/${aid}] ${plan.label} fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'} (R_valid=${ev.R_valid})`)
}

// =================================================================== RUN
phase('Init')
const init = await runPy(`init --out ${OUT} --N ${N} --R ${R} --pop ${POP} --survivors ${SURVIVORS} --sims-eval ${SIMS_EVAL} --sims-cand ${SIMS_CAND} --seed ${SEED} --optimizer ${OPT}`, INIT_S, 'init', 'Init')
const SEEDS = init.seed_ids || []
log(`init ok. optimizer=${OPT} N=${N}. seeds: ${JSON.stringify(init.seed_labels)}`)

phase('Gen0')
await parallel(SEEDS.map(aid => () => runPipe(0, aid, 'Gen0')))
const sc0 = await runPy(`score-pop --out ${OUT} --gen 0`, SCORE_S, 'score:g0', 'Gen0')
await runPy(`population-summary --out ${OUT} --gen 0`, OK, 'popsum:g0', 'Gen0')
log(`gen 0 scored. champion=${sc0.champion} fitness=${sc0.champion_fitness && sc0.champion_fitness.toFixed(3)}`)

phase('Evolve')
let curve = [{ gen: 0, champion: sc0.champion, fitness: sc0.champion_fitness }]
for (let gen = 0; gen < GEN; gen++) {
  log(`--- gen ${gen} (this-run tokens: ${Math.round(runSpent() / 1000)}k) ---`)
  if (runSpent() > HALT) { log(`HALT: token backstop at gen ${gen}.`); break }
  const sel = await runPy(`select --out ${OUT} --gen ${gen} --survivors ${SURVIVORS}`, SEL_S, `select:g${gen}`, 'Evolve')
  log(`gen ${gen}: survivors=${(sel.survivors || []).join(',')} champion=${sel.champion}`)
  if (OPT === 'core') {
    const rp = await runPy(`core-reflect-plan --out ${OUT} --gen ${gen} --pairs ${PAIRS}`, REFLECT_S, `reflect:g${gen}`, 'Evolve')
    const pairs = rp.plan || []
    await parallel(pairs.map(p => () => agent(coreReflect(p), { label: `reflect:g${gen}:${p.winner_id}>${p.loser_id}`, phase: 'Evolve', model: REFLECT })))
    const ing = await runPy(`core-ingest --out ${OUT} --gen ${gen} --max-lessons ${MAX_LESSONS}`, INGEST_S, `ingest:g${gen}`, 'Evolve')
    log(`gen ${gen}: reflected ${pairs.length} pairs -> +${ing.added}/${ing.merged}m insights; bank=${ing.bank_size}`)
  }
  const br = await runPy(`${OPT === 'core' ? 'core-breed-plan' : 'breed-plan-gepa'} --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}${OPT === 'core' ? ` --topk ${TOPK}` : ''}`, BREED_S, `breed:g${gen}`, 'Evolve')
  const plan = br.plan || []
  await pipeline(plan,
    async (off) => { if (!off.exists) await agent(OPT === 'core' ? coreMutate(gen, off) : gepaMutate(gen, off), { label: `mutate:${off.new_id}:${off.lens}`, phase: 'Evolve', model: REFLECT }); return off },
    async (off) => { await runPipe(gen + 1, off.new_id, 'Evolve'); return off },
    async (off) => {
      const ad = await runPy(`admit --out ${OUT} --gen ${gen + 1} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id}`, ADMIT_S, `admit:${off.new_id}`, 'Evolve')
      log(`  ${off.new_id} [${off.lens}] vs ${off.parent_id}: d=${ad.delta != null ? ad.delta.toFixed(3) : '?'} CI=[${ad.ci_low != null ? ad.ci_low.toFixed(3) : '?'},${ad.ci_high != null ? ad.ci_high.toFixed(3) : '?'}] -> ${ad.admitted ? 'ADMITTED' : 'rejected'}`)
      return off
    })
  if (OPT === 'core') await runPy(`core-credit --out ${OUT} --gen ${gen}`, CREDIT_S, `credit:g${gen}`, 'Evolve')
  const fin = await runPy(`finalize-gen --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}`, FIN_S, `finalize:g${gen}`, 'Evolve')
  curve.push({ gen: gen + 1, champion: fin.champion, fitness: fin.champion_fitness })
  log(`gen ${gen} -> ${gen + 1}: ${fin.n_admitted} admitted. champion=${fin.champion} fitness=${fin.champion_fitness && fin.champion_fitness.toFixed(3)}`)
}

let bank = null
if (OPT === 'core') bank = await runPy(`bank-status --out ${OUT}`, BANK_S, 'bank-final', 'Evolve')
log(`EVOLVE COMPLETE [${OPT}]. curve: ${JSON.stringify(curve.map(c => [c.gen, c.fitness != null ? +c.fitness.toFixed(3) : null]))}`)
return { output_dir: OUT, optimizer: OPT, N, R, champion_curve: curve, bank_final: bank,
  next_step: `python3 -m cc_pipe.control_pipe final-compare --out ${OUT}` }
