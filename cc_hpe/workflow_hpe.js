export const meta = {
  name: 'codeclash-harness-prompt-evolution',
  description: 'HARNESS-PROMPT EVOLUTION (GEPA vs CORE). Genotype = FOUR role-prompts of a decomposition harness (a brief per specialist {space_control,combat,food} + a referee/integration prompt). A genotype is realized R times (Haiku codes each specialist from its evolving brief + the referee from its prompt; the cc_decomp scaffold assembles one bot); fitness = mean ladder win-rate over the R bots. Two-sample bootstrap gate. One workflow, optimizer in {gepa,core}; GEPA edits one role-prompt per lens, CORE reflects contrastively over prompt-SETS into an insight bank. Ends after Evolve; headline via control_hpe final-compare (capped sims). Reuses cc_prompt gate + cc_alloc assembly + cc_decomp scoring + cc_core bank.',
  phases: [
    { title: 'Init', detail: 'config + ladder + contracts + 8 seed prompt-sets (4 prompts each) (+ empty bank for CORE)' },
    { title: 'Gen0', detail: 'realize every seed prompt-set R times (specialists+referee -> assembled bot) + clean ladder scoring' },
    { title: 'Evolve', detail: 'OUTER_GENERATIONS: select -> [CORE: contrastive reflection over prompt-sets -> bank] -> mutate role-prompt(s) -> R-replicate eval -> two-sample verified gate -> refill' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = (A && A.ccroot) || '/ABSOLUTE/PATH/TO/evolving-agent-harnesses'
const OPT = (A.optimizer === 'core') ? 'core' : 'gepa'
const OUT = A.out || (CCROOT + '/cc_hpe_evo_' + OPT)
const SEED = A.seed ?? 0
const GEN = A.generations ?? 6
const POP = A.pop ?? 8
const SURVIVORS = A.survivors ?? 4
const R = A.R ?? 3
const SIMS_EVAL = A.sims_eval ?? 100
const PAIRS = A.pairs ?? SURVIVORS
const TOPK = A.topk ?? 3
const MAX_LESSONS = A.max_lessons ?? 4
const MAXW = A.maxw ?? 16
const HALT_TOKENS = A.halt_tokens ?? 12_000_000
const spent = () => { try { return budget && budget.spent ? budget.spent() : 0 } catch (e) { return 0 } }
const _spentStart = spent(); const runSpent = () => Math.max(0, spent() - _spentStart)
const CODER = 'haiku'; const REFLECT = 'sonnet'
const py = `cd ${CCROOT} && CC_MAXW=${MAXW} python3 -m cc_hpe.control_hpe`
const pad2 = n => String(n).padStart(2, '0')
const CONCERNS = ['space_control', 'combat', 'food']
const ROLES = [...CONCERNS, 'referee']

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, optimizer: { type: 'string' }, R: { type: 'number' }, seed_ids: { type: 'array', items: { type: 'string' } }, concerns: { type: 'array' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, exists: { type: 'boolean' }, R: { type: 'number' }, concerns: { type: 'array', items: { type: 'string' } } }, required: ['ok'] }
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

async function runPy(cmd, schema, label, phase, model = CODER) {
  const prompt = `Run EXACTLY this shell command and report its result:\n\`\`\`\n${py} ${cmd}\n\`\`\`\n` +
    `It prints a single JSON object on its last stdout line. Return THAT JSON object via structured output. ` +
    `If it exits non-zero, run it once more; if it still fails, return {"ok": false, "error": "<stderr tail>"}.`
  let r = null
  for (let i = 0; i < 4; i++) {
    try {
      r = await agent(prompt, { label: i ? `${label}~r${i}` : label, phase, schema, model })
      if (r && r.ok !== false) return r
    } catch (e) {
      // a StructuredOutput nudge-failure THROWS; catch it so a transient flake becomes a retry
      // instead of killing the whole workflow.
      log(`py-step ${label}: attempt ${i + 1} threw (${String(e && e.message || e).slice(0, 70)}) — retry`)
      r = { ok: false }
    }
    log(`py-step ${label}: attempt ${i + 1} not-ok — retry`)
  }
  return r || { ok: false }
}

const gdir = (gen, aid) => `${OUT}/gen_${pad2(gen)}/genotypes/agent_${aid}`

function specCoder(gen, aid, r, concern) {
  const d = gdir(gen, aid)
  return `You are the SPECIALIST CODER "${concern}" (model=HAIKU), replicate #${r}. Read: the contract ` +
    `${OUT}/contracts/specialist_contract.txt , your fixed CONCERN (the "${concern}" entry in ` +
    `${OUT}/contracts/specialist_concerns.json), and your BRIEF (the evolving strategy for this specialist) at ` +
    `${d}/prompts/${concern}.md . Implement \`def score(game_state) -> dict\` EXACTLY per the contract and concern, ` +
    `following your brief ({"up","down","left","right"} floats; -1e9 = hard veto; pure; never raises; stdlib only). ` +
    `Write ONLY raw Python (NO fences) with the Write tool to ${d}/repl_${r}/specialists/${concern}.py . Return one line.`
}
function refCoder(gen, aid, r) {
  const d = gdir(gen, aid)
  return `You are the REFEREE / INTEGRATOR CODER (model=HAIKU), replicate #${r}. Read the contract ` +
    `${OUT}/contracts/referee_contract.txt and the evolving INTEGRATION STRATEGY at ${d}/prompts/referee.md . ` +
    `Implement \`def referee(scores, game_state, legal) -> str\` that integrates the specialists ${CONCERNS.join(', ')} ` +
    `per that strategy (scores[name][move]; a value <= -5e8 is a veto; return a move in legal; pure; never raises). ` +
    `Write ONLY raw Python (NO fences) with the Write tool to ${d}/repl_${r}/specialists/_referee.py . Return one line.`
}

function gepaMutate(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  const role = off.lens
  const what = role === 'referee'
    ? 'the REFEREE/INTEGRATION strategy (how the three specialists are combined into one move)'
    : `the "${role}" specialist's BRIEF (its strategy / what to compute / what to veto)`
  return `You are an OUTER-OPTIMIZER lens = "${role}" (model=SONNET) evolving a multi-agent BattleSnake harness whose ` +
    `genotype is FOUR role-prompts: briefs for ${CONCERNS.join(', ')} + a referee prompt. The child ${cd}/prompts/ ` +
    `already CONTAINS the parent's four prompts (a clone). PARENT performance: ${pd}/metrics.json (mean ladder win-rate ` +
    `over ${R} assembled bots + per-rung — diagnose where the bots lose). For comparison the parent's prompt is ` +
    `${pd}/prompts/${role}.md .\nYOUR JOB: rewrite ONLY ${what} to improve where the bots lose. Write the full improved ` +
    `prompt with the Write tool to ${cd}/prompts/${role}.md (keep the other three role-prompts untouched). ALSO update ` +
    `${cd}/lineage.json: set "diff" (one line on the change). Return one line.`
}
function coreReflect(p) {
  return `You are a CONTRASTIVE-REFLECTION analyst (model=SONNET) studying how to write the role-prompts of a ` +
    `multi-agent BattleSnake harness (briefs for ${CONCERNS.join(', ')} specialists + a referee/integration prompt). ` +
    `Two prompt-SETS were each realized into ${R} bots and scored on the SAME ladder:\n` +
    `[WINNER] (mean win-rate ${p.winner_fitness}) — prompts in ${p.winner_dir}/prompts/ , metrics ${p.winner_dir}/metrics.json\n` +
    `[LOSER]  (mean win-rate ${p.loser_fitness}) — prompts in ${p.loser_dir}/prompts/ , metrics ${p.loser_dir}/metrics.json\n` +
    `The LOSER's profile: ${p.weakness}\n\nRead all four role-prompts of each set + metrics. Think step by step: which ` +
    `brief or the referee differs in a way that most plausibly produced better bots (more concrete spec? a veto rule? ` +
    `a sharper integration policy?). Distil EXACTLY ${MAX_LESSONS} short INSIGHTS about writing harness role-prompts ` +
    `(e.g. "give the space brief an explicit flood-fill cell-count + self-trap veto", "the referee must drop vetoed moves ` +
    `before weighting", "name concrete head-to-head rules in the combat brief"). Write a JSON array of ${MAX_LESSONS} ` +
    `objects, each {"lesson": "<imperative; <=30 words; generalizable role-prompt insight>", "label": "specific" or ` +
    `"meta"}. Write ONLY that JSON array with the Write tool to ${p.lessons_path} (valid JSON, no prose, no fences). Return one line.`
}
function coreMutate(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are a CORE MUTATION operator (model=SONNET) evolving a multi-agent BattleSnake harness's FOUR role-prompts ` +
    `(briefs for ${CONCERNS.join(', ')} + referee). The child ${cd}/prompts/ already CONTAINS the parent's four prompts ` +
    `(a clone). PARENT performance: ${pd}/metrics.json . RETRIEVED INSIGHTS about role-prompt writing (from past ` +
    `winner-vs-loser prompt-sets, ranked by relevance + verified track record): read ${cd}/breed_context.json .\n` +
    `Apply the most relevant insight(s) by rewriting ONE OR TWO of the four role-prompts (${ROLES.join(', ')}) in place ` +
    `at ${cd}/prompts/<role>.md — a focused, coherent change; leave the rest untouched. ALSO update ${cd}/lineage.json: ` +
    `set "changed_components" (which role-prompts) and "diff" (the change + which insight id(s) it applied); keep the ` +
    `existing "lessons_used" field. Return one line.`
}

async function runEval(gen, aid, phase) {
  const plan = await runPy(`eval-plan --out ${OUT} --gen ${gen} --agent ${aid} --R ${R}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`eval CACHED [g${gen}/${aid}]`); return }
  // realize R replicates: each = 3 specialist coders + 1 referee coder (all parallel across replicates)
  const jobs = []
  for (let r = 0; r < R; r++) {
    for (const c of CONCERNS) jobs.push(() => agent(specCoder(gen, aid, r, c), { label: `spec:${aid}:r${r}:${c}`, phase, model: CODER }))
    jobs.push(() => agent(refCoder(gen, aid, r), { label: `ref:${aid}:r${r}`, phase, model: CODER }))
  }
  await parallel(jobs)
  const ev = await runPy(`eval-score --out ${OUT} --gen ${gen} --agent ${aid} --R ${R} --sims-eval ${SIMS_EVAL} --seed ${SEED}`, EVAL_S, `eval:${aid}`, phase)
  log(`eval [g${gen}/${aid}] fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'} (R_valid=${ev.R_valid})`)
}

// =================================================================== RUN
phase('Init')
const init = await runPy(`init --out ${OUT} --optimizer ${OPT} --seed ${SEED} --generations ${GEN} --pop ${POP} ` +
  `--survivors ${SURVIVORS} --R ${R} --sims-eval ${SIMS_EVAL}`, INIT_S, 'init', 'Init')
const SEEDS = init.seed_ids || []
log(`init ok. optimizer=${OPT} R=${R} concerns=${(init.concerns || []).join(',')}. ${SEEDS.length} seed prompt-sets`)

phase('Gen0')
await parallel(SEEDS.map(aid => () => runEval(0, aid, 'Gen0')))
const sc0 = await runPy(`score-pop --out ${OUT} --gen 0`, SCORE_S, 'score:g0', 'Gen0')
await runPy(`population-summary --out ${OUT} --gen 0`, OK, 'popsum:g0', 'Gen0')
log(`gen 0 scored. champion=${sc0.champion} fitness=${sc0.champion_fitness && sc0.champion_fitness.toFixed(3)}`)

phase('Evolve')
let championCurve = [{ gen: 0, champion: sc0.champion, fitness: sc0.champion_fitness }]
for (let gen = 0; gen < GEN; gen++) {
  log(`--- generation ${gen} (this-run output tokens: ${Math.round(runSpent() / 1000)}k) ---`)
  if (runSpent() > HALT_TOKENS) { log(`HALT: token backstop at gen ${gen}.`); break }
  const sel = await runPy(`select --out ${OUT} --gen ${gen} --survivors ${SURVIVORS}`, SEL_S, `select:g${gen}`, 'Evolve')
  log(`gen ${gen}: survivors=${(sel.survivors || []).join(',')} champion=${sel.champion}`)

  if (OPT === 'core') {
    const rp = await runPy(`core-reflect-plan --out ${OUT} --gen ${gen} --pairs ${PAIRS}`, REFLECT_S, `reflect:g${gen}`, 'Evolve')
    const pairs = rp.plan || []
    await parallel(pairs.map(p => () => agent(coreReflect(p), { label: `reflect:g${gen}:${p.winner_id}>${p.loser_id}`, phase: 'Evolve', model: REFLECT })))
    const ing = await runPy(`core-ingest --out ${OUT} --gen ${gen} --max-lessons ${MAX_LESSONS}`, INGEST_S, `ingest:g${gen}`, 'Evolve')
    log(`gen ${gen}: reflected on ${pairs.length} prompt-set pairs -> +${ing.added}/${ing.merged}m insights; bank=${ing.bank_size}`)
  }

  const br = await runPy(`${OPT === 'core' ? 'core-breed-plan' : 'breed-plan-gepa'} --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}${OPT === 'core' ? ` --topk ${TOPK}` : ''}`, BREED_S, `breed:g${gen}`, 'Evolve')
  const plan = br.plan || []
  await pipeline(plan,
    async (off) => {
      if (!off.exists) await agent(OPT === 'core' ? coreMutate(gen, off) : gepaMutate(gen, off),
        { label: `mutate:${off.new_id}:${off.lens}`, phase: 'Evolve', model: REFLECT })
      return off
    },
    async (off) => { await runEval(gen + 1, off.new_id, 'Evolve'); return off },
    async (off) => {
      const ad = await runPy(`admit --out ${OUT} --gen ${gen + 1} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id}`, ADMIT_S, `admit:${off.new_id}`, 'Evolve')
      log(`  offspring ${off.new_id} [${off.lens}] vs parent ${off.parent_id}: delta=${ad.delta != null ? ad.delta.toFixed(3) : '?'} CI=[${ad.ci_low != null ? ad.ci_low.toFixed(3) : '?'},${ad.ci_high != null ? ad.ci_high.toFixed(3) : '?'}] -> ${ad.admitted ? 'ADMITTED' : 'rejected'}`)
      return off
    })

  if (OPT === 'core') await runPy(`core-credit --out ${OUT} --gen ${gen}`, CREDIT_S, `credit:g${gen}`, 'Evolve')
  const fin = await runPy(`finalize-gen --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}`, FIN_S, `finalize:g${gen}`, 'Evolve')
  championCurve.push({ gen: gen + 1, champion: fin.champion, fitness: fin.champion_fitness })
  log(`gen ${gen} -> ${gen + 1}: ${fin.n_admitted} admitted. champion=${fin.champion} fitness=${fin.champion_fitness && fin.champion_fitness.toFixed(3)}`)
}

let bankFinal = null
if (OPT === 'core') bankFinal = await runPy(`bank-status --out ${OUT}`, BANK_S, 'bank-final', 'Evolve')
log(`EVOLVE COMPLETE [${OPT}]. champion curve: ${JSON.stringify(championCurve.map(c => [c.gen, c.fitness != null ? +c.fitness.toFixed(3) : null]))}.`)

return {
  output_dir: OUT, optimizer: OPT, R, generations: GEN,
  champion_curve: championCurve, bank_final: bankFinal,
  next_step: `python3 -m cc_hpe.control_hpe final-compare --out ${OUT} --sims 300 --seed ${SEED}`,
}
