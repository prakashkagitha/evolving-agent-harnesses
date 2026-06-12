export const meta = {
  name: 'codeclash-alloc-search',
  description: 'Budget-constrained allocation search: EVOLVE the best way to spend a fixed budget of B LLM calls to write one BattleSnake bot. The genotype is a budget-B allocation (n_draft monolithic drafts / n_spec specialists + optional merge / n_revise revisions) + the generator prompt; best-of-B, revision chains, decomposition, and hybrids are all reachable points. One workflow, optimizer in {gepa, core}, searches the space; naive best-of-B is the baseline. Clean low-concurrency scoring; verified-acceptance gate. Reuses cc_decomp scoring/gate + cc_core bank.',
  phases: [
    { title: 'Init', detail: 'config + ladder rungs (weak/moderate/strong) + 8 seed recipes spanning the allocation space (+ empty bank for CORE)' },
    { title: 'Gen0', detail: 'execute every seed recipe (its B LLM calls -> one bot) + clean ladder scoring' },
    { title: 'Evolve', detail: 'OUTER_GENERATIONS: select -> [CORE: contrastive reflection on winner/loser recipes -> bank] -> breed B-preserving recipe mutations -> execute -> VERIFIED gate (paired 95% CI) vs parent recipe -> refill. Ends after Evolve; final compare is offline (cc_alloc.control_alloc final-compare).' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = (A && A.ccroot) || '/ABSOLUTE/PATH/TO/evolving-agent-harnesses'
const OPT = (A.optimizer === 'core') ? 'core' : 'gepa'
const OUT = A.out || (CCROOT + '/cc_alloc_evo_' + OPT)
const B = A.B ?? 8
const SEED = A.seed ?? 0
const GEN = A.generations ?? 4
const POP = A.pop ?? 8
const SURVIVORS = A.survivors ?? 4
const SIMS_CAND = A.sims_cand ?? 60
const SIMS_EVOLVE = A.sims_evolve ?? 120
const SIMS_ADMIT = A.sims_admit ?? 200
const SIMS_FINAL = A.sims_final ?? 1500
const PAIRS = A.pairs ?? SURVIVORS
const TOPK = A.topk ?? 3
const MAX_LESSONS = A.max_lessons ?? 4
const HALT_TOKENS = A.halt_tokens ?? 9_000_000
const spent = () => { try { return budget && budget.spent ? budget.spent() : 0 } catch (e) { return 0 } }
const _spentStart = spent(); const runSpent = () => Math.max(0, spent() - _spentStart)
const CODER = 'haiku'      // ALL bot-writing calls (drafts/specialists/merge/revise) — the budget is spent here
const REFLECT = 'sonnet'   // outer optimizer (mutation / contrastive reflection)
const py = `cd ${CCROOT} && python3 -m cc_alloc.control_alloc`
const pad2 = n => String(n).padStart(2, '0')

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, B: { type: 'number' }, optimizer: { type: 'string' }, seed_ids: { type: 'array', items: { type: 'string' } }, seed_allocs: { type: 'object' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, exists: { type: 'boolean' }, n_draft: { type: 'number' }, n_spec: { type: 'number' }, do_merge: { type: 'number' }, n_revise: { type: 'number' }, concerns: { type: 'array', items: { type: 'string' } }, alloc_label: { type: 'string' } }, required: ['ok'] }
const BASE_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_candidates: { type: 'number' }, best: { type: ['string', 'null'] }, best_score: { type: 'number' }, has_revise: { type: 'boolean' } }, required: ['ok'] }
const KEEP_S = { type: 'object', properties: { ok: { type: 'boolean' }, kept: { type: 'boolean' }, new_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const FINI_S = { type: 'object', properties: { ok: { type: 'boolean' }, valid: { type: 'boolean' } }, required: ['ok'] }
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
  for (let i = 0; i < 3; i++) {
    r = await agent(prompt, { label: i ? `${label}~r${i}` : label, phase, schema, model })
    if (r && r.ok !== false) return r
    log(`py-step ${label}: attempt ${i + 1} ok:false — retry`)
  }
  return r || { ok: false }
}

const gdir = (gen, aid) => `${OUT}/gen_${pad2(gen)}/genotypes/agent_${aid}`

// ---- the B-call bot-writing agents (this is where the budget is spent) ----
function draftPrompt(gen, aid, k) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake CODER (model=HAIKU), independent draft #${k}. Read the contract ` +
    `${OUT}/contracts/simple_bot_contract.txt and the strategy ${d}/draft_prompt.md . Write the STRONGEST complete ` +
    `single-file bot you can (flood-fill space control + head-to-head safety/opportunism + measured food/health), ` +
    `as raw Python (NO fences) with the Write tool to ${d}/candidates/draft_${k}.py (define info/start/end/move). ` +
    `${k > 0 ? 'Vary your approach from other drafts. ' : ''}Return one line.`
}
function specPrompt(gen, aid, name) {
  const d = gdir(gen, aid)
  return `You are the SPECIALIST CODER "${name}" (model=HAIKU). Read the contract ${OUT}/contracts/specialist_contract.txt , ` +
    `your CONCERN (the "${name}" entry in ${OUT}/contracts/specialist_concerns.json), and the strategy ${d}/draft_prompt.md . ` +
    `Implement \`def score(game_state) -> dict\` EXACTLY per the contract and your concern ({"up","down","left","right"} ` +
    `floats; -1e9 = hard veto; pure; never raises; stdlib only). Write ONLY raw Python (NO fences) with the Write tool ` +
    `to ${d}/specialists/${name}.py . Return one line.`
}
function mergePrompt(gen, aid, concerns) {
  const d = gdir(gen, aid)
  return `You are the REFEREE / INTEGRATOR (model=HAIKU). Read ${OUT}/contracts/referee_contract.txt and the strategy ` +
    `${d}/draft_prompt.md . The active specialists are ${concerns.join(', ')}. Implement \`def referee(scores, game_state, legal) -> str\` ` +
    `that integrates them per the strategy (drop vetoed moves <= -5e8, then weigh; pure; never raises; return a move in legal). ` +
    `Write ONLY raw Python (NO fences) with the Write tool to ${d}/specialists/_referee.py . Return one line.`
}
function revisePrompt(gen, aid, r) {
  const d = gdir(gen, aid)
  return `You are a BattleSnake REVISER (model=HAIKU), revision #${r}. Read the current best bot ${d}/produced_bot/best.py ` +
    `and its feedback ${d}/produced_bot/feedback.json (win-rate vs the moderate opponent, crashes, causes_of_death, ` +
    `adversarial-board failures). Diagnose the SINGLE biggest weakness and rewrite an IMPROVED complete single-file bot ` +
    `(keep info/start/end/move; pure; never raises; stdlib only). Write ONLY raw Python (NO fences) with the Write tool to ` +
    `${d}/candidates/revise_${r}.py . Your revision is kept only if it does not regress (verified). Return one line.`
}

// ---- outer optimizer agents (mutate the recipe) ----
const GENO_DESC = `A recipe genotype is JSON {"alloc": {"n_draft": int, "n_spec": int (0-5), "do_merge": 0|1, "n_revise": int}, ` +
  `"concerns": [subset of space_control,combat,food,endgame,hazard], "draft_prompt": "<generator prompt>"}. ` +
  `CONSTRAINT: n_draft + n_spec + do_merge + n_revise == ${B} (the call budget). It encodes how to spend ${B} LLM calls: ` +
  `n_draft independent monolithic drafts, then n_spec specialist coders (+1 merge if do_merge) assembled into one bot, ` +
  `then n_revise sequential revisions on the best-so-far; the best candidate is kept. do_merge=1 needs n_spec>=1; there ` +
  `must be a base producer (n_draft>=1 OR n_spec>=1 with do_merge). An over-budget recipe is auto-repaired, but aim for exactly ${B}.`

const LENS_GUIDE = {
  alloc: `Change the ALLOCATION counts: move one call between buckets (e.g. n_draft<->n_revise, or +/-1 specialist, or toggle do_merge) to better spend the ${B}-call budget. Keep the sum == ${B}.`,
  concerns: `Keep the alloc counts; change WHICH specialists — swap one concern for a more useful one from the menu (or reorder by importance).`,
  prompt: `Keep alloc + concerns; SHARPEN the draft_prompt so the bot writer produces a stronger bot (clearer tactics/priorities).`,
  mix: `Rebalance exploration vs refinement: shift the split between drafts (breadth), specialists (decomposition), and revisions (depth) for better return on ${B} calls. One coherent change.`,
}

function gepaMutatePrompt(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are an OUTER-OPTIMIZER reflection lens = "${off.lens}" (model=SONNET) searching the space of budget-${B} ` +
    `allocations for writing a BattleSnake bot. ${GENO_DESC}\n` +
    `PARENT recipe: ${pd}/recipe.json . PARENT performance: ${pd}/metrics.json (ladder_fitness + per-rung win-rates — ` +
    `diagnose where its produced bot is weak and whether the budget is mis-allocated).\n` +
    `THROUGH YOUR LENS make ONE incremental, budget-preserving edit: ${LENS_GUIDE[off.lens]}\n` +
    `Write the CHILD recipe with the Write tool to ${cd}/recipe.json (valid JSON, sum == ${B}). ALSO update ${cd}/lineage.json: ` +
    `set "changed_components" and "diff" (one line describing the single change). Make the smallest change that plausibly ` +
    `raises win-rate per fixed budget. Return one line.`
}
function coreReflectPrompt(p) {
  return `You are a CONTRASTIVE-REFLECTION analyst (model=SONNET) studying how to best spend a budget of ${B} LLM calls to ` +
    `write a BattleSnake bot. ${GENO_DESC}\n\nTwo recipes were given the SAME ${B}-call budget and the SAME fixed opponent ladder:\n` +
    `[WINNER] (ladder win-rate ${p.winner_fitness}, allocation ${p.winner_alloc}) — ${p.winner_dir}/recipe.json , metrics ${p.winner_dir}/metrics.json\n` +
    `[LOSER]  (ladder win-rate ${p.loser_fitness}, allocation ${p.loser_alloc}) — ${p.loser_dir}/recipe.json , metrics ${p.loser_dir}/metrics.json\n` +
    `The LOSER's profile: ${p.weakness}\n\nRead all four files. Think step by step: how did the WINNER spend its ${B} calls ` +
    `differently (more drafts? more revisions? decomposition? a sharper prompt?), and which difference most plausibly caused ` +
    `the win-rate gap? Distil EXACTLY ${MAX_LESSONS} short LESSONS about HOW TO ALLOCATE a fixed LLM-call budget for this task ` +
    `(e.g. "spend most of the budget on revisions, not parallel drafts", "decomposition beats best-of-N only when >=3 ` +
    `specialists", "a sharper prompt is worth more than an extra draft"). Write a JSON array of ${MAX_LESSONS} objects, each ` +
    `{"lesson": "<imperative; <=30 words; about budget allocation / prompt, generalizable>", "label": "specific" or "meta"}. ` +
    `Write ONLY that JSON array with the Write tool to ${p.lessons_path} (valid JSON, no prose, no fences). Return one line.`
}
function coreMutatePrompt(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are a CORE MUTATION operator (model=SONNET) searching the space of budget-${B} allocations. ${GENO_DESC}\n` +
    `PARENT recipe: ${pd}/recipe.json ; performance ${pd}/metrics.json .\n` +
    `RETRIEVED LESSONS about budget allocation (distilled from past winner-vs-loser recipes, ranked by relevance + verified ` +
    `track record): read ${cd}/breed_context.json (the parent's profile + the top lessons to apply).\n` +
    `Make ONE incremental, budget-preserving edit to the recipe that APPLIES the most relevant lesson(s) to spend the ${B} ` +
    `calls better (reallocate calls, change concerns, or sharpen the draft_prompt — one coherent change). Write the CHILD recipe ` +
    `to ${cd}/recipe.json (valid JSON, sum == ${B}). ALSO update ${cd}/lineage.json: set "changed_components" and "diff" (the ` +
    `change + which lesson id(s) it applied); keep the existing "lessons_used" field. Return one line.`
}

// ---- execute one recipe: spend its B calls -> one produced bot ----
async function runRecipe(gen, aid, phase) {
  const plan = await runPy(`recipe-plan --out ${OUT} --gen ${gen} --agent ${aid} --B ${B}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`recipe CACHED [g${gen}/${aid}]`); return }
  const concerns = (plan.concerns || []).slice(0, plan.n_spec || 0)
  // drafts (parallel)
  if ((plan.n_draft || 0) > 0) {
    await parallel(Array.from({ length: plan.n_draft }, (_, k) => () => agent(draftPrompt(gen, aid, k), { label: `draft:${aid}:${k}`, phase, model: CODER })))
  }
  // specialists (parallel) + merge
  if ((plan.n_spec || 0) > 0) {
    await parallel(concerns.map(c => () => agent(specPrompt(gen, aid, c), { label: `spec:${aid}:${c}`, phase, model: CODER })))
    if (plan.do_merge) await agent(mergePrompt(gen, aid, concerns), { label: `merge:${aid}`, phase, model: CODER })
  }
  await runPy(`recipe-build-base --out ${OUT} --gen ${gen} --agent ${aid} --B ${B} --sims-cand ${SIMS_CAND} --seed ${SEED}`, BASE_S, `base:${aid}`, phase)
  // revisions (sequential)
  for (let r = 1; r <= (plan.n_revise || 0); r++) {
    await agent(revisePrompt(gen, aid, r), { label: `revise:${aid}:r${r}`, phase, model: CODER })
    await runPy(`recipe-revise-keep --out ${OUT} --gen ${gen} --agent ${aid} --round ${r} --sims-cand ${SIMS_CAND} --seed ${SEED}`, KEEP_S, `keep:${aid}:r${r}`, phase)
  }
  await runPy(`recipe-finalize --out ${OUT} --gen ${gen} --agent ${aid} --B ${B}`, FINI_S, `fin:${aid}`, phase)
  log(`recipe done [g${gen}/${aid}] alloc=${plan.alloc_label}`)
}

// =================================================================== RUN
phase('Init')
const init = await runPy(`init --out ${OUT} --B ${B} --optimizer ${OPT} --seed ${SEED} --generations ${GEN} --pop ${POP} ` +
  `--survivors ${SURVIVORS} --sims-cand ${SIMS_CAND} --sims-evolve ${SIMS_EVOLVE} --sims-admit ${SIMS_ADMIT} --sims-final ${SIMS_FINAL}`,
  INIT_S, 'init', 'Init')
const SEEDS = init.seed_ids || []
log(`init ok. optimizer=${OPT} B=${B}. ${SEEDS.length} seed recipes: ${JSON.stringify(init.seed_allocs)}`)

phase('Gen0')
await parallel(SEEDS.map(aid => () => runRecipe(0, aid, 'Gen0')))
const sc0 = await runPy(`score-pop --out ${OUT} --gen 0 --sims ${SIMS_EVOLVE} --seed ${SEED}`, SCORE_S, 'score:g0', 'Gen0')
await runPy(`population-summary --out ${OUT} --gen 0`, OK, 'popsum:g0', 'Gen0')
log(`gen 0 scored. champion=${sc0.champion} ladder_fitness=${sc0.champion_fitness && sc0.champion_fitness.toFixed(3)}`)

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
    log(`gen ${gen}: reflected on ${pairs.length} recipe pairs -> +${ing.added}/${ing.merged}m lessons; bank=${ing.bank_size}`)
  }

  const br = await runPy(`${OPT === 'core' ? 'core-breed-plan' : 'breed-plan-gepa'} --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}${OPT === 'core' ? ` --topk ${TOPK}` : ''}`, BREED_S, `breed:g${gen}`, 'Evolve')
  const plan = br.plan || []
  await pipeline(plan,
    async (off) => {
      if (!off.exists) await agent(OPT === 'core' ? coreMutatePrompt(gen, off) : gepaMutatePrompt(gen, off),
        { label: `mutate:${off.new_id}:${off.lens}`, phase: 'Evolve', model: REFLECT })
      return off
    },
    async (off) => {
      await runRecipe(gen + 1, off.new_id, 'Evolve')
      await runPy(`score-pop --out ${OUT} --gen ${gen + 1} --agent ${off.new_id} --sims ${SIMS_EVOLVE} --seed ${SEED}`, SCORE_S, `score:${off.new_id}`, 'Evolve')
      return off
    },
    async (off) => {
      const ad = await runPy(`admit --out ${OUT} --gen ${gen + 1} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id} --sims ${SIMS_ADMIT} --seed ${SEED}`, ADMIT_S, `admit:${off.new_id}`, 'Evolve')
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
log(`EVOLVE COMPLETE [${OPT}]. champion curve: ${JSON.stringify(championCurve.map(c => [c.gen, c.fitness != null ? +c.fitness.toFixed(3) : null]))}. Run cc_alloc.control_alloc final-compare for the clean headline.`)

return {
  output_dir: OUT, optimizer: OPT, B, generations: GEN,
  champion_curve: championCurve, bank_final: bankFinal,
  next_step: `python3 -m cc_alloc.control_alloc final-compare --out ${OUT} --sims ${SIMS_FINAL} --seed ${SEED}`,
}
