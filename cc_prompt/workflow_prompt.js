export const meta = {
  name: 'codeclash-prompt-evolution',
  description: 'PURE PROMPT EVOLUTION (GEPA vs CORE). Genotype = one bot-generation prompt; cheapest harness = 1 Haiku call -> one bot; a prompt is evaluated by the MEAN ladder win-rate over R replicate generations (Haiku variance). Verified gate = two-sample bootstrap over child-prompt vs parent-prompt bot distributions. One workflow, optimizer in {gepa, core}; baseline = best gen-0 seed prompt. Ends after Evolve; final headline via cc_prompt.control_prompt final-compare. Reuses cc_decomp scoring + cc_core bank.',
  phases: [
    { title: 'Init', detail: 'config + ladder (weak/moderate/strong) + 8 diverse seed prompts (+ empty bank for CORE)' },
    { title: 'Gen0', detail: 'evaluate every seed prompt = R single-shot bots -> mean ladder fitness' },
    { title: 'Evolve', detail: 'OUTER_GENERATIONS: select -> [CORE: contrastive reflection winner/loser prompts -> bank] -> mutate prompt -> R-replicate eval -> TWO-SAMPLE verified gate -> refill' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = (A && A.ccroot) || '/ABSOLUTE/PATH/TO/evolving-agent-harnesses'
const OPT = (A.optimizer === 'core') ? 'core' : 'gepa'
const OUT = A.out || (CCROOT + '/cc_prompt_evo_' + OPT)
const SEED = A.seed ?? 0
const GEN = A.generations ?? 4
const POP = A.pop ?? 8
const SURVIVORS = A.survivors ?? 4
const R = A.R ?? 5                 // replicate generations per prompt (variance control)
const SIMS_EVAL = A.sims_eval ?? 120
const SIMS_FINAL = A.sims_final ?? 1500
const PAIRS = A.pairs ?? SURVIVORS
const TOPK = A.topk ?? 3
const MAX_LESSONS = A.max_lessons ?? 4
const HALT_TOKENS = A.halt_tokens ?? 9_000_000
const MAXW = A.maxw ?? 16   // native-sim concurrency; lower (e.g. 6-8) when running two workflows in PARALLEL
const spent = () => { try { return budget && budget.spent ? budget.spent() : 0 } catch (e) { return 0 } }
const _spentStart = spent(); const runSpent = () => Math.max(0, spent() - _spentStart)
const CODER = 'haiku'      // the bot-writing call (the cheapest harness)
const REFLECT = 'sonnet'   // outer optimizer (mutation / contrastive reflection)
const py = `cd ${CCROOT} && CC_MAXW=${MAXW} python3 -m cc_prompt.control_prompt`
const pad2 = n => String(n).padStart(2, '0')

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, optimizer: { type: 'string' }, R: { type: 'number' }, seed_ids: { type: 'array', items: { type: 'string' } } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, exists: { type: 'boolean' }, R: { type: 'number' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, R_valid: { type: 'number' }, per_rung: { type: 'object' } }, required: ['ok'] }
const SCORE_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok'] }
const SEL_S = { type: 'object', properties: { ok: { type: 'boolean' }, survivors: { type: 'array', items: { type: 'string' } }, champion: { type: ['string', 'null'] } }, required: ['ok'] }
const BREED_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, survivors: { type: 'array' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const ADMIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, admitted: { type: 'boolean' }, delta: { type: ['number', 'null'] }, ci_low: { type: ['number', 'null'] }, ci_high: { type: ['number', 'null'] }, child_fit: { type: ['number', 'null'] }, parent_fit: { type: ['number', 'null'] } }, required: ['ok'] }
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
  for (let i = 0; i < 3; i++) {
    r = await agent(prompt, { label: i ? `${label}~r${i}` : label, phase, schema, model })
    if (r && r.ok !== false) return r
    log(`py-step ${label}: attempt ${i + 1} ok:false — retry`)
  }
  return r || { ok: false }
}

const gdir = (gen, aid) => `${OUT}/gen_${pad2(gen)}/genotypes/agent_${aid}`

function draftPrompt(gen, aid, r) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake CODER (model=HAIKU), independent attempt #${r}. Read the contract ` +
    `${OUT}/contracts/simple_bot_contract.txt and the STRATEGY PROMPT ${d}/prompt.md . Follow the strategy ` +
    `prompt's guidance to write the strongest complete single-file bot you can, as raw Python (NO markdown ` +
    `fences) with the Write tool to ${d}/candidates/bot_${r}.py (define info/start/end/move; pure; never raises; ` +
    `stdlib only; fast). ${r > 0 ? 'Vary your implementation from other attempts. ' : ''}Return one line.`
}

const LENS_GUIDE = {
  strategy: 'Reframe the overall STRATEGY and priorities for stronger play — make clear what to optimize and in what order. Keep it a coherent generation prompt.',
  concept: 'Add exactly ONE missing tactical CONCEPT (e.g. head-to-head pressure, trap/dead-end avoidance, length-race, endgame stalling, edge/hazard safety), woven into the strategy.',
  specificity: 'Make the instructions more CONCRETE and actionable (explicit per-move rules, thresholds, what to compute, what to never do) WITHOUT changing the core strategy.',
  fix: 'Look at the per-rung win-rates in metrics.json; the bots lose most to one rung — add specific guidance to beat THAT opponent.',
}

function gepaMutatePrompt(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are an OUTER-OPTIMIZER reflection lens = "${off.lens}" (model=SONNET) evolving a BattleSnake bot-` +
    `GENERATION PROMPT (the prompt instructs a small model to write a complete bot). PARENT prompt: ${pd}/prompt.md . ` +
    `PARENT performance: ${pd}/metrics.json (mean ladder win-rate over ${R} bots + per-rung — diagnose where the bots lose).\n` +
    `THROUGH YOUR LENS, make ONE focused improvement: ${LENS_GUIDE[off.lens]}\n` +
    `Write the FULL improved prompt with the Write tool to ${cd}/prompt.md (a complete generation prompt, not a diff; ` +
    `keep what already works). ALSO update ${cd}/lineage.json: set "changed_components" and "diff" (one line on the change). ` +
    `Return one line.`
}

function coreReflectPrompt(p) {
  return `You are a CONTRASTIVE-REFLECTION analyst (model=SONNET) studying how to PROMPT a small model to write a ` +
    `strong BattleSnake bot. Two GENERATION PROMPTS were each used to write ${R} bots and scored on the SAME ladder:\n` +
    `[WINNER] (mean win-rate ${p.winner_fitness}) — prompt ${p.winner_dir}/prompt.md , metrics ${p.winner_dir}/metrics.json\n` +
    `[LOSER]  (mean win-rate ${p.loser_fitness}) — prompt ${p.loser_dir}/prompt.md , metrics ${p.loser_dir}/metrics.json\n` +
    `The LOSER's profile: ${p.weakness}\n\nRead both prompts + metrics. Think step by step: what does the WINNER prompt ` +
    `say or emphasise (strategy, specific tactics, concreteness) that the LOSER prompt lacks, and which difference most ` +
    `plausibly produced better bots? Distil EXACTLY ${MAX_LESSONS} short INSIGHTS about how to write a bot-generation ` +
    `prompt (e.g. "spell out the flood-fill space metric explicitly", "always instruct head-to-head veto rules", ` +
    `"concrete thresholds beat vague guidance"). Write a JSON array of ${MAX_LESSONS} objects, each {"lesson": ` +
    `"<imperative; <=30 words; generalizable prompt-writing insight>", "label": "specific" or "meta"}. Write ONLY that ` +
    `JSON array with the Write tool to ${p.lessons_path} (valid JSON, no prose, no fences). Return one line.`
}

function coreMutatePrompt(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are a CORE MUTATION operator (model=SONNET) evolving a BattleSnake bot-GENERATION PROMPT. PARENT prompt: ` +
    `${pd}/prompt.md ; performance ${pd}/metrics.json .\nRETRIEVED INSIGHTS about prompt-writing (distilled from past ` +
    `winner-vs-loser prompts, ranked by relevance + verified track record): read ${cd}/breed_context.json .\n` +
    `Make ONE focused improvement to the prompt that APPLIES the most relevant insight(s) to produce stronger bots. Write ` +
    `the FULL improved prompt with the Write tool to ${cd}/prompt.md (a complete generation prompt, not a diff; keep what ` +
    `works). ALSO update ${cd}/lineage.json: set "changed_components" and "diff" (the change + which insight id(s) it ` +
    `applied); keep the existing "lessons_used" field. Return one line.`
}

async function runEval(gen, aid, phase) {
  const plan = await runPy(`eval-plan --out ${OUT} --gen ${gen} --agent ${aid} --R ${R}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`eval CACHED [g${gen}/${aid}]`); return }
  await parallel(Array.from({ length: R }, (_, r) => () => agent(draftPrompt(gen, aid, r), { label: `bot:${aid}:${r}`, phase, model: CODER })))
  const ev = await runPy(`eval-score --out ${OUT} --gen ${gen} --agent ${aid} --R ${R} --sims-eval ${SIMS_EVAL} --seed ${SEED}`, EVAL_S, `eval:${aid}`, phase)
  log(`eval [g${gen}/${aid}] fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'} (R_valid=${ev.R_valid})`)
}

// =================================================================== RUN
phase('Init')
const init = await runPy(`init --out ${OUT} --optimizer ${OPT} --seed ${SEED} --generations ${GEN} --pop ${POP} ` +
  `--survivors ${SURVIVORS} --R ${R} --sims-eval ${SIMS_EVAL} --sims-final ${SIMS_FINAL}`, INIT_S, 'init', 'Init')
const SEEDS = init.seed_ids || []
log(`init ok. optimizer=${OPT} R=${R}. ${SEEDS.length} seed prompts: ${SEEDS.join(',')}`)

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
    await parallel(pairs.map(p => () => agent(coreReflectPrompt(p), { label: `reflect:g${gen}:${p.winner_id}>${p.loser_id}`, phase: 'Evolve', model: REFLECT })))
    const ing = await runPy(`core-ingest --out ${OUT} --gen ${gen} --max-lessons ${MAX_LESSONS}`, INGEST_S, `ingest:g${gen}`, 'Evolve')
    log(`gen ${gen}: reflected on ${pairs.length} prompt pairs -> +${ing.added}/${ing.merged}m insights; bank=${ing.bank_size}`)
  }

  const br = await runPy(`${OPT === 'core' ? 'core-breed-plan' : 'breed-plan-gepa'} --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}${OPT === 'core' ? ` --topk ${TOPK}` : ''}`, BREED_S, `breed:g${gen}`, 'Evolve')
  const plan = br.plan || []
  await pipeline(plan,
    async (off) => {
      if (!off.exists) await agent(OPT === 'core' ? coreMutatePrompt(gen, off) : gepaMutatePrompt(gen, off),
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
log(`EVOLVE COMPLETE [${OPT}]. champion curve: ${JSON.stringify(championCurve.map(c => [c.gen, c.fitness != null ? +c.fitness.toFixed(3) : null]))}. Run cc_prompt.control_prompt final-compare for the clean headline.`)

return {
  output_dir: OUT, optimizer: OPT, R, generations: GEN,
  champion_curve: championCurve, bank_final: bankFinal,
  next_step: `python3 -m cc_prompt.control_prompt final-compare --out ${OUT} --sims ${SIMS_FINAL} --seed ${SEED}`,
}
