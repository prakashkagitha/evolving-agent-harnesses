export const meta = {
  name: 'cc-pipe-evolve-decoupled',
  description: 'Evolve a typed self-correction pipeline (GEPA or CORE) with a DECOUPLED admit gate that fixes the R=3 optimizer-curse inflation: explore offspring cheaply at R=3, then re-evaluate only parent-beaters at R=8 FRESH and admit on the robust R=8 two-sample bootstrap vs the parent. gen0 seeds are scored at R_GEN0 so survivor/contrast fitnesses are reliable. A self-limiting agent-budget guard finalizes early if it nears the workflow agent cap. Runs ONE optimizer alone (launch GEPA, then CORE).',
  phases: [
    { title: 'Init', detail: 'config + ladder + contracts + seeds (+ empty bank for CORE)' },
    { title: 'Gen0', detail: 'score every seed at R_GEN0 (reliable baseline)' },
    { title: 'Evolve', detail: 'select -> [CORE reflect] -> mutate -> explore R=3 -> prefilter -> top-up parent-beaters to R=8 -> robust admit' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OPT = (A.optimizer === 'core') ? 'core' : 'gepa'
const OUT = A.out || (CCROOT + '/cc_pipe_dec_' + OPT)
const N = A.N ?? 4
const SEED = A.seed ?? 0
const GEN = A.generations ?? 4
const POP = A.pop ?? 6
const SURV = A.survivors ?? 3
const R_GEN0 = A.r_gen0 ?? 4         // seeds scored at this R (reliable ranking/contrast; seeds aren't selection-inflated)
const R_EXPLORE = A.r_explore ?? 3   // cheap offspring exploration
const R_ADMIT = A.r_admit ?? 8       // robust re-eval of parent-beaters before admission
const MARGIN = A.margin ?? 0.02      // promote to R=8 admit if child R=3 fit >= parent fit - MARGIN
const SIMS_EVAL = A.sims_eval ?? 100
const SIMS_CAND = A.sims_cand ?? 60
const PAIRS = A.pairs ?? SURV
const TOPK = A.topk ?? 3
const MAX_LESSONS = A.max_lessons ?? 4
const MAXW = A.maxw ?? 8
const AGENT_BUDGET = A.agent_budget ?? 850   // self-limit well under the 1000 workflow cap
const REFLECT = 'sonnet'
const py = `cd ${CCROOT} && CC_MAXW=${MAXW} python3 -m cc_pipe.control_pipe`
const pad2 = n => String(n).padStart(2, '0')

let nAgents = 0
const bumped = () => { nAgents += 1 }

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, seed_ids: { type: 'array', items: { type: 'string' } }, seed_labels: { type: 'object' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' }, label: { type: 'string' }, exists: { type: 'boolean' } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, R_valid: { type: 'number' } }, required: ['ok'] }
const SCORE_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok'] }
const SEL_S = { type: 'object', properties: { ok: { type: 'boolean' }, survivors: { type: 'array', items: { type: 'string' } }, champion: { type: ['string', 'null'] } }, required: ['ok'] }
const BREED_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const ADMIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, admitted: { type: 'boolean' }, delta: { type: ['number', 'null'] }, ci_low: { type: ['number', 'null'] }, ci_high: { type: ['number', 'null'] } }, required: ['ok'] }
const FIN_S = { type: 'object', properties: { ok: { type: 'boolean' }, ids: { type: 'array', items: { type: 'string' } }, n_admitted: { type: 'number' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok', 'ids'] }
const REFLECT_S = { type: 'object', properties: { ok: { type: 'boolean' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const INGEST_S = { type: 'object', properties: { ok: { type: 'boolean' }, added: { type: 'number' }, bank_size: { type: 'number' } }, required: ['ok'] }
const CREDIT_S = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }

async function runPy(cmd, schema, label, phase, model = 'haiku') {
  const prompt = `Run EXACTLY this shell command and report its result:\n\`\`\`\n${py} ${cmd}\n\`\`\`\n` +
    `It prints a single JSON object on its last stdout line. Return THAT JSON object via structured output. ` +
    `If it exits non-zero, run it once more; if it still fails, return {"ok": false, "error": "<stderr tail>"}.`
  let r = null
  for (let i = 0; i < 4; i++) {
    bumped()
    try { r = await agent(prompt, { label: i ? `${label}~r${i}` : label, phase, schema, model }); if (r && r.ok !== false) return r }
    catch (e) { log(`py ${label}: attempt ${i + 1} threw — retry`); r = { ok: false } }
  }
  return r || { ok: false }
}

// retry-wrap an LLM agent() call so a transient throw doesn't crash the whole run (mirrors runPy)
async function agentR(promptStr, opts, tries = 4) {
  for (let i = 0; i < tries; i++) {
    bumped()
    try { return await agent(promptStr, { ...opts, label: i ? `${opts.label}~r${i}` : opts.label }) }
    catch (e) { log(`agent ${opts.label}: attempt ${i + 1} threw — retry`) }
  }
  log(`agent ${opts.label}: gave up after ${tries} (downstream score will treat as invalid)`); return null
}

const gdir = (gen, aid) => `${OUT}/gen_${pad2(gen)}/genotypes/agent_${aid}`
function draftPrompt(gen, aid, r, idx, model) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake CODER (model=${model.toUpperCase()}), replicate ${r} attempt ${idx}. Read the contract ` +
    `${OUT}/contracts/simple_bot_contract.txt and the strategy ${d}/prompts/draft.md . Write the strongest complete ` +
    `single-file bot you can as raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py (info/start/end/move; pure; never raises; stdlib only; fast). Return one line.`
}
function critiquePrompt(gen, aid, r) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake bot REVIEWER (model=HAIKU). Read the current best bot ${d}/repl_${r}/best.py , the engine ` +
    `feedback ${d}/repl_${r}/feedback.json , and the critique guidance ${d}/prompts/critique.md . Name the SINGLE biggest ` +
    `concrete weakness and exactly what to change; write it with the Write tool to ${d}/repl_${r}/note.txt . Return one line.`
}
function fixPrompt(gen, aid, r, idx) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake IMPROVER (model=HAIKU), replicate ${r}. Read the current best bot ${d}/repl_${r}/best.py , the ` +
    `engine feedback ${d}/repl_${r}/feedback.json , the critique note ${d}/repl_${r}/note.txt (if present), and the fix guidance ` +
    `${d}/prompts/fix.md . Apply the critique and fix the failures to produce an IMPROVED complete single-file bot (keep info/start/end/move; pure; never raises; stdlib only). Write raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py . Return one line.`
}

const GENO_DESC = `The genotype is a budget-${N} self-correction PIPELINE: roles.json = {"roles": [${N} steps, each ` +
  `"draft"|"critique"|"fix"; step 0 must be "draft"], "draft_model": "haiku"} + a free-text prompt per role at ` +
  `prompts/draft.md, prompts/critique.md, prompts/fix.md. The child already CONTAINS the parent's roles.json + prompts (a clone) — edit in place.`
const LENSES = ['draft', 'critique', 'fix', 'structure']
function gepaMutate(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  if (off.lens === 'structure') {
    return `You are an OUTER-OPTIMIZER STRUCTURE lens (model=SONNET) evolving a budget-${N} BattleSnake self-correction ` +
      `pipeline. ${GENO_DESC}\nPARENT performance: ${pd}/metrics.json . Make ONE structural change to ${cd}/roles.json: retype ` +
      `or reorder a single step (keep exactly ${N} steps, step 0 = "draft", no trailing "critique"). Write the new ` +
      `${cd}/roles.json. ALSO update ${cd}/lineage.json "diff". Return one line.`
  }
  const role = off.lens
  return `You are an OUTER-OPTIMIZER lens = "${role}" (model=SONNET) evolving a budget-${N} BattleSnake self-correction ` +
    `pipeline. ${GENO_DESC}\nPARENT performance: ${pd}/metrics.json . Rewrite ONLY the "${role}" role prompt to improve where ` +
    `the bots lose (note blind refinement HURTS, so keep fixes targeted/conservative). Write the full improved prompt with the ` +
    `Write tool to ${cd}/prompts/${role}.md (keep the other files untouched). ALSO update ${cd}/lineage.json "diff". Return one line.`
}
function coreReflect(p) {
  return `You are a CONTRASTIVE-REFLECTION analyst (model=SONNET) studying how to design a budget-${N} BattleSnake ` +
    `self-correction pipeline. Two pipelines were each scored on the SAME ladder:\n[WINNER] (win-rate ${p.winner_fitness}, ` +
    `shape ${p.winner_label}) — ${p.winner_dir}/\n[LOSER] (win-rate ${p.loser_fitness}, shape ${p.loser_label}) — ${p.loser_dir}/\n` +
    `LOSER profile: ${p.weakness}\n\nRead both pipelines' roles.json + prompts/*.md + metrics. Which difference (role SHAPE or a ` +
    `role PROMPT) most plausibly caused the gap? Distil EXACTLY ${MAX_LESSONS} short INSIGHTS about pipeline design/prompts. Write ` +
    `a JSON array of ${MAX_LESSONS} objects {"lesson":"<=30 words","label":"specific"|"meta"} with the Write tool to ` +
    `${p.lessons_path} (valid JSON, no fences). Return one line.`
}
function coreMutate(gen, off) {
  const cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are a CORE MUTATION operator (model=SONNET) evolving a budget-${N} BattleSnake self-correction pipeline. ` +
    `${GENO_DESC}\nRETRIEVED INSIGHTS (read ${cd}/breed_context.json) come from past winner-vs-loser pipelines ranked by relevance ` +
    `+ verified track record. Apply the most relevant insight(s) by editing the child in place: change ${cd}/roles.json (keep ${N} ` +
    `steps, step0="draft", no trailing critique) AND/OR rewrite one role prompt at ${cd}/prompts/<role>.md — a focused, coherent ` +
    `change. ALSO update ${cd}/lineage.json "changed_components" + "diff" (+ which insight ids); keep "lessons_used". Return one line.`
}

// run replicates [startR, endR) of agent `aid` at generation `gen`
async function runChain(gen, aid, roles, model, startR, endR, phase) {
  for (let r = startR; r < endR; r++) {
    let cand = 0
    for (const role of roles) {
      if (role === 'draft') {
        await agentR(draftPrompt(gen, aid, r, cand, model), { label: `draft:${aid}:r${r}:${cand}`, phase, model })
        await runPy(`pipe-score-cand --out ${OUT} --gen ${gen} --agent ${aid} --repl ${r} --cand ${cand} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SC_S, `score:${aid}:r${r}:${cand}`, phase)
        cand++
      } else if (role === 'critique') {
        await runPy(`pipe-feedback --out ${OUT} --gen ${gen} --agent ${aid} --repl ${r}`, FB_S, `fb:${aid}:r${r}`, phase)
        await agentR(critiquePrompt(gen, aid, r), { label: `crit:${aid}:r${r}`, phase, model: 'haiku' })
      } else {
        await runPy(`pipe-feedback --out ${OUT} --gen ${gen} --agent ${aid} --repl ${r}`, FB_S, `fb:${aid}:r${r}:${cand}`, phase)
        await agentR(fixPrompt(gen, aid, r, cand), { label: `fix:${aid}:r${r}:${cand}`, phase, model: 'haiku' })
        await runPy(`pipe-score-cand --out ${OUT} --gen ${gen} --agent ${aid} --repl ${r} --cand ${cand} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SC_S, `score:${aid}:r${r}:${cand}`, phase)
        cand++
      }
    }
  }
}

// =================================================================== RUN
phase('Init')
const init = await runPy(`init --out ${OUT} --N ${N} --R ${R_ADMIT} --pop ${POP} --survivors ${SURV} --sims-eval ${SIMS_EVAL} --sims-cand ${SIMS_CAND} --seed ${SEED} --optimizer ${OPT}`, INIT_S, 'init', 'Init')
const SEEDS = init.seed_ids || []
log(`init ok. optimizer=${OPT} N=${N}. decoupled gate: gen0 R=${R_GEN0}, explore R=${R_EXPLORE}, admit R=${R_ADMIT}. seeds: ${JSON.stringify(init.seed_labels)}`)

phase('Gen0')
await parallel(SEEDS.map(aid => () => (async () => {
  const plan = await runPy(`pipe-plan --out ${OUT} --gen 0 --agent ${aid} --N ${N}`, PLAN_S, `plan:${aid}`, 'Gen0')
  if (plan.exists) { log(`seed CACHED [${aid}]`); return }
  await runChain(0, aid, plan.roles || ['draft'], plan.draft_model || 'haiku', 0, R_GEN0, 'Gen0')
  const ev = await runPy(`pipe-eval-score --out ${OUT} --gen 0 --agent ${aid} --R ${R_GEN0} --sims-cand ${SIMS_CAND} --seed ${SEED}`, EVAL_S, `eval:${aid}`, 'Gen0')
  log(`seed [${aid}] ${plan.label}: R${R_GEN0} fit=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'}`)
})()))
const sc0 = await runPy(`score-pop --out ${OUT} --gen 0`, SCORE_S, 'score:g0', 'Gen0')
await runPy(`population-summary --out ${OUT} --gen 0`, OK, 'popsum:g0', 'Gen0')
log(`gen 0 scored. champion=${sc0.champion} fitness=${sc0.champion_fitness && sc0.champion_fitness.toFixed(3)}`)

phase('Evolve')
let curve = [{ gen: 0, champion: sc0.champion, fitness: sc0.champion_fitness }]
for (let gen = 0; gen < GEN; gen++) {
  if (nAgents > AGENT_BUDGET) { log(`AGENT-BUDGET GUARD: ${nAgents}>${AGENT_BUDGET}, stopping evolve at gen ${gen}.`); break }
  log(`--- gen ${gen} (agents so far: ${nAgents}/${AGENT_BUDGET}) ---`)
  const sel = await runPy(`select --out ${OUT} --gen ${gen} --survivors ${SURV}`, SEL_S, `select:g${gen}`, 'Evolve')
  log(`gen ${gen}: survivors=${(sel.survivors || []).join(',')} champion=${sel.champion}`)
  if (OPT === 'core') {
    const rp = await runPy(`core-reflect-plan --out ${OUT} --gen ${gen} --pairs ${PAIRS}`, REFLECT_S, `reflect:g${gen}`, 'Evolve')
    const pairs = rp.plan || []
    await parallel(pairs.map(p => () => agentR(coreReflect(p), { label: `reflect:g${gen}:${p.winner_id}>${p.loser_id}`, phase: 'Evolve', model: REFLECT })))
    const ing = await runPy(`core-ingest --out ${OUT} --gen ${gen} --max-lessons ${MAX_LESSONS}`, INGEST_S, `ingest:g${gen}`, 'Evolve')
    log(`gen ${gen}: reflected ${pairs.length} pairs -> +${ing.added}; bank=${ing.bank_size}`)
  }
  const br = await runPy(`${OPT === 'core' ? 'core-breed-plan' : 'breed-plan-gepa'} --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURV}${OPT === 'core' ? ` --topk ${TOPK}` : ''}`, BREED_S, `breed:g${gen}`, 'Evolve')
  const plan = br.plan || []
  // process offspring sequentially (clean scoring, predictable agent count)
  for (const off of plan) {
    if (!off.exists) { await agentR(OPT === 'core' ? coreMutate(gen, off) : gepaMutate(gen, off), { label: `mutate:${off.new_id}:${off.lens}`, phase: 'Evolve', model: REFLECT }) }
    const pl = await runPy(`pipe-plan --out ${OUT} --gen ${gen + 1} --agent ${off.new_id} --N ${N}`, PLAN_S, `plan:${off.new_id}`, 'Evolve')
    if (pl.exists) { log(`  ${off.new_id} CACHED`); continue }
    // explore at R_EXPLORE
    await runChain(gen + 1, off.new_id, pl.roles || ['draft'], pl.draft_model || 'haiku', 0, R_EXPLORE, 'Evolve')
    const e3 = await runPy(`pipe-eval-score --out ${OUT} --gen ${gen + 1} --agent ${off.new_id} --R ${R_EXPLORE} --sims-cand ${SIMS_CAND} --seed ${SEED}`, EVAL_S, `eval3:${off.new_id}`, 'Evolve')
    const childFit = e3.fitness ?? 0, parentFit = off.parent_fit ?? 0
    const promote = childFit >= parentFit - MARGIN
    log(`  ${off.new_id} [${off.lens}] explore R${R_EXPLORE}=${childFit.toFixed(3)} vs parent ${parentFit.toFixed(3)} -> ${promote ? 'PROMOTE to R' + R_ADMIT : 'prefilter-reject'}`)
    if (promote) {
      await runChain(gen + 1, off.new_id, pl.roles || ['draft'], pl.draft_model || 'haiku', R_EXPLORE, R_ADMIT, 'Evolve')
      await runPy(`pipe-eval-score --out ${OUT} --gen ${gen + 1} --agent ${off.new_id} --R ${R_ADMIT} --sims-cand ${SIMS_CAND} --seed ${SEED}`, EVAL_S, `eval8:${off.new_id}`, 'Evolve')
    }
    const ad = await runPy(`admit --out ${OUT} --gen ${gen + 1} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id}`, ADMIT_S, `admit:${off.new_id}`, 'Evolve')
    log(`    ${off.new_id} admit: d=${ad.delta != null ? ad.delta.toFixed(3) : '?'} CI=[${ad.ci_low != null ? ad.ci_low.toFixed(3) : '?'},${ad.ci_high != null ? ad.ci_high.toFixed(3) : '?'}] -> ${ad.admitted ? 'ADMITTED' : 'rejected'}`)
  }
  if (OPT === 'core') await runPy(`core-credit --out ${OUT} --gen ${gen}`, CREDIT_S, `credit:g${gen}`, 'Evolve')
  const fin = await runPy(`finalize-gen --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURV}`, FIN_S, `finalize:g${gen}`, 'Evolve')
  curve.push({ gen: gen + 1, champion: fin.champion, fitness: fin.champion_fitness })
  log(`gen ${gen} -> ${gen + 1}: ${fin.n_admitted} admitted. champion=${fin.champion} fitness=${fin.champion_fitness && fin.champion_fitness.toFixed(3)} (R${R_ADMIT}-verified)`)
}
log(`EVOLVE COMPLETE [${OPT}] decoupled. agents=${nAgents}. curve: ${JSON.stringify(curve.map(c => [c.gen, c.fitness != null ? +c.fitness.toFixed(3) : null]))}`)
return { output_dir: OUT, optimizer: OPT, N, decoupled: true, r_gen0: R_GEN0, r_explore: R_EXPLORE, r_admit: R_ADMIT, agents: nAgents, champion_curve: curve,
  next_step: `python3 -m cc_pipe.control_pipe final-compare --out ${OUT}` }
