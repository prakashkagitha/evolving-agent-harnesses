export const meta = {
  name: 'codeclash-core-evolution-v2',
  description: 'CORE-v2: contrastive-reflection evolution of the SAME harness as cc_decomp/GEPA, PLUS a FRONTIER reflection each generation that reframes the champion\'s OWN losses (to the strong/sonnet rungs) as the negative trace — so the bank also accrues lessons that can target the frontier harness, which ordinary winner-vs-loser pairs never reach (the champion is always the winner). Population contrastive reflection + champion-frontier reflection -> one bank -> lesson-conditioned mutation -> identical verified-acceptance gate. Ends after Evolve; the SIMS_FINAL headline + analysis are produced by cc_core.reeval (contention-safe).',
  phases: [
    { title: 'Init', detail: 'config + 12 seed genotypes + ladder rungs 0-2 + empty lesson bank (deterministic)' },
    { title: 'Ladder', detail: 'produce the frozen Sonnet rung (simple-refinement) + 4-rung sanity' },
    { title: 'Gate', detail: 'verification gate on the richest gen-0 harness (shared with cc_decomp)' },
    { title: 'Ablations', detail: 'simple-refinement bot + best-of-N bot (Haiku) — the baselines to beat' },
    { title: 'Gen0', detail: 'run all 12 seed harnesses (Haiku nested pipeline) + score vs ladder' },
    { title: 'Evolve', detail: 'OUTER_GENERATIONS: population contrastive reflection (winner/loser pairs) + FRONTIER reflection (champion vs the rungs it loses) -> ingest into one bank -> retrieve top-K per parent -> lesson-conditioned mutation -> VERIFIED-acceptance gate (paired 95% CI) -> credit -> refill' },
  ],
}

// ----------------------------------------------------------------- knobs (?? so explicit 0 is honored)
let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = (A && A.ccroot) || '/ABSOLUTE/PATH/TO/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_core_evo')
const SEED = A.seed ?? 0
const GEN = A.generations ?? 6
const POP = A.pop ?? 12
const SURVIVORS = A.survivors ?? 4
const REFINE = A.refine_rounds ?? 4
const SIMS_EVOLVE = A.sims_evolve ?? 120
const SIMS_ADMIT = A.sims_admit ?? 200
const SIMS_FINAL = A.sims_final ?? 1500
const SIMS_REFINE = A.sims_refine ?? 36
const SIMS_LADDER_SANITY = A.sims_sanity ?? 120
const BEST_OF_N = A.best_of_n ?? 8
const PAIRS = A.pairs ?? SURVIVORS        // contrastive pairs reflected on per generation
const TOPK = A.topk ?? 3                  // lessons retrieved to condition each mutation
const MAX_LESSONS = A.max_lessons ?? 4    // lessons distilled per contrastive pair
const HALT_TOKENS = A.halt_tokens ?? 9_000_000
const spent = () => { try { return budget && budget.spent ? budget.spent() : 0 } catch (e) { return 0 } }
const _spentStart = spent()
const runSpent = () => Math.max(0, spent() - _spentStart)
const CODER = 'haiku'      // ALL harness execution (planner/specialists/referee/debugger)
const REFLECT = 'sonnet'   // outer evolution (contrastive reflection + lesson-conditioned mutation) + the Sonnet rung
const py = `cd ${CCROOT} && python3 -m cc_core.control`
const pad2 = n => String(n).padStart(2, '0')

// ----------------------------------------------------------------- schemas
const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, seed_ids: { type: 'array', items: { type: 'string' } }, battlesnake_commit: { type: 'string' }, bank_initialized: { type: 'boolean' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, specialists: { type: 'array', items: { type: 'string' } }, referee_policy: { type: 'string' }, tester: { type: 'boolean' }, refine_rounds: { type: 'number' }, exists: { type: 'boolean' } }, required: ['ok'] }
const REFI_S = { type: 'object', properties: { ok: { type: 'boolean' }, baseline_score: { type: 'number' }, valid: { type: 'boolean' }, winrate_vs_moderate: { type: ['number', 'null'] }, refine_rounds: { type: 'number' } }, required: ['ok'] }
const KEEP_S = { type: 'object', properties: { ok: { type: 'boolean' }, kept: { type: 'boolean' }, valid: { type: 'boolean' }, new_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const SCORE_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] }, ranking: { type: 'array' } }, required: ['ok'] }
const SEL_S = { type: 'object', properties: { ok: { type: 'boolean' }, survivors: { type: 'array', items: { type: 'string' } }, champion: { type: ['string', 'null'] } }, required: ['ok'] }
const ADMIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, admitted: { type: 'boolean' }, delta: { type: ['number', 'null'] }, ci_low: { type: ['number', 'null'] }, ci_high: { type: ['number', 'null'] }, child_fit: { type: ['number', 'null'] }, parent_fit: { type: ['number', 'null'] } }, required: ['ok'] }
const FIN_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, ids: { type: 'array', items: { type: 'string' } }, new_ids: { type: 'array', items: { type: 'string' } }, carried: { type: 'array', items: { type: 'string' } }, n_admitted: { type: 'number' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok', 'ids'] }
const SAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, order_ok: { type: 'boolean' }, sonnet_competitive: { type: ['boolean', 'null'] }, fitness: { type: 'object' } }, required: ['ok'] }
const GATE_S = { type: 'object', properties: { ok: { type: 'boolean' }, pass: { type: 'boolean' }, specialists_spawned: { type: 'boolean' }, bot_reflects_genotype: { type: 'boolean' }, ladder_ranks_sane: { type: 'boolean' }, paired_ci_computed: { type: 'boolean' }, fitness_from_sims: { type: 'boolean' }, details: { type: 'object' } }, required: ['ok', 'pass'] }
const STAT_S = { type: 'object', properties: { ok: { type: 'boolean' }, exists: { type: 'boolean' } }, required: ['ok'] }
const BON_S = { type: 'object', properties: { ok: { type: 'boolean' }, best_run: { type: ['number', 'null'] }, best_fitness: { type: 'number' } }, required: ['ok'] }
const FINAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, headline: { type: 'object' }, champion_vs_ablations: { type: 'object' } }, required: ['ok'] }
// CORE-specific
const REFLECT_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_pairs: { type: 'number' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const INGEST_S = { type: 'object', properties: { ok: { type: 'boolean' }, added: { type: 'number' }, merged: { type: 'number' }, parsed: { type: 'number' }, bank_size: { type: 'number' }, n_meta: { type: 'number' } }, required: ['ok'] }
const COREBREED_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, survivors: { type: 'array' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const CREDIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_credited: { type: 'number' }, bank_size: { type: 'number' }, credited: { type: 'array' } }, required: ['ok'] }
const BANK_S = { type: 'object', properties: { ok: { type: 'boolean' }, bank_size: { type: 'number' }, n_meta: { type: 'number' }, total_wins: { type: 'number' }, top: { type: 'array' } }, required: ['ok'] }
const FRONT_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] }, losing_rungs: { type: 'array' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const BOLD = (A.bold_champion ?? 0)   // frontier-fallback tweak: allow a bolder/multi-aspect champion edit

// ----------------------------------------------------------------- py-step helper (retry busts resume cache)
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

// ----------------------------------------------------------------- agent prompts
const gdir = (gen, aid) => `${OUT}/gen_${pad2(gen)}/genotypes/agent_${aid}`

function plannerPrompt(gen, aid, specs) {
  const d = gdir(gen, aid)
  return `You are the PLANNER (model=HAIKU) of a nested multi-agent BattleSnake coding harness. Read the ` +
    `strategy framing ${d}/planner_prompt.md . The ACTIVE specialists are: ${specs.join(', ')}. For EACH active ` +
    `specialist, write a 1-3 sentence BRIEF telling that specialist what to implement for THIS strategy (its ` +
    `sub-goal, priorities, what to veto). Write a single JSON object {${specs.map(s => `"${s}":"..."`).join(', ')}} ` +
    `(exactly one key per active specialist) with the Write tool to ${d}/briefs.json (valid JSON only). Return one line.`
}

function specialistPrompt(gen, aid, name) {
  const d = gdir(gen, aid)
  return `You are the SPECIALIST CODER "${name}" (model=HAIKU) in a BattleSnake harness. Read: the contract ` +
    `${OUT}/contracts/specialist_contract.txt , your CONCERN (the "${name}" entry in ` +
    `${OUT}/contracts/specialist_concerns.json), your BRIEF (the "${name}" entry in ${d}/briefs.json), and the ` +
    `strategy ${d}/planner_prompt.md . Implement \`def score(game_state) -> dict\` EXACTLY per the contract and your ` +
    `concern (return {"up","down","left","right"} floats; -1e9 = hard veto; pure; never raises; stdlib only). ` +
    `Write ONLY raw Python (NO markdown fences) with the Write tool to ${d}/specialists/${name}.py . Return one line.`
}

function refereePrompt(gen, aid, specs) {
  const d = gdir(gen, aid)
  return `You are the REFEREE / INTEGRATOR (model=HAIKU). Read ${OUT}/contracts/referee_contract.txt , the strategy ` +
    `${d}/planner_prompt.md and the briefs ${d}/briefs.json . The active specialists are ${specs.join(', ')}. ` +
    `Implement \`def referee(scores, game_state, legal) -> str\` that integrates the specialists per the strategy ` +
    `(drop vetoed moves <= -5e8, then weigh per the plan; pure; never raises; return a move in \`legal\`). ` +
    `Write ONLY raw Python (NO fences) with the Write tool to ${d}/specialists/_referee.py . Return one line.`
}

function debuggerPrompt(gen, aid, specs) {
  const d = gdir(gen, aid)
  return `You are the DEBUGGER (model=HAIKU) in a VERIFIED refine loop for a BattleSnake harness. Read the latest ` +
    `feedback ${d}/produced_bot/feedback.json (win-rate vs the moderate opponent, crashes, causes_of_death, and ` +
    `adversarial-board failures) and the current specialist code in ${d}/specialists/ (active: ${specs.join(', ')}). ` +
    `Diagnose the SINGLE biggest weakness shown in the feedback and FIX it by editing the most relevant specialist ` +
    `file(s) with the Write tool (raw Python, keep the \`def score(game_state)->dict\` contract; pure; never raises). ` +
    `Make a real behavioral improvement and keep what already works. Edit ONLY files in ${d}/specialists/ . ` +
    `Your edit is kept ONLY if it does not regress fitness (verified automatically), so make it count. Return one line.`
}

function simpleCoderPrompt(dir, persona, model) {
  return `You are a BattleSnake CODER (model=${model.toUpperCase()}). Read the contract ` +
    `${OUT}/contracts/simple_bot_contract.txt . Directive: ${persona} Write the STRONGEST complete single-file bot ` +
    `you can (flood-fill space control + head-to-head safety/opportunism + measured food/health), as raw Python ` +
    `(NO fences) with the Write tool to ${dir}/produced_bot/main.py (define info/start/end/move). Return one line.`
}

function simpleDebuggerPrompt(dir, model) {
  return `You are the DEBUGGER (model=${model.toUpperCase()}) in a VERIFIED refine loop. Read the feedback ` +
    `${dir}/produced_bot/feedback.json (win-rate vs the moderate opponent, crashes, causes_of_death, adversarial ` +
    `failures) and the current bot ${dir}/produced_bot/main.py . Fix the SINGLE biggest weakness by editing main.py ` +
    `with the Write tool (raw Python, keep info/start/end/move, pure, never raises). Your edit is kept only if it ` +
    `does not regress fitness (verified automatically). Return one line.`
}

// ---- CORE: contrastive reflection (winner vs loser harness) -> lessons -----
function reflectPrompt(p) {
  return `You are a CONTRASTIVE-REFLECTION analyst (model=SONNET) in an evolutionary tournament of BattleSnake ` +
    `coding HARNESSES. A harness has two evolvable components: planner_prompt.md (strategy framing + how the planner ` +
    `briefs/decomposes for specialists) and decomposition.json {specialists: subset of [space_control,combat,food,` +
    `endgame,hazard], referee_policy in [priority_order,weighted_vote,planner_merge], tester: bool, refine_rounds: int}.\n\n` +
    `You are given two harnesses that played the SAME fixed opponent ladder:\n` +
    `[WINNER] (ladder win-rate ${p.winner_fitness}) — genotype: ${p.winner_dir}/planner_prompt.md , ` +
    `${p.winner_dir}/decomposition.json ; per-rung win-rates: ${p.winner_dir}/metrics.json\n` +
    `[LOSER]  (ladder win-rate ${p.loser_fitness}) — genotype: ${p.loser_dir}/planner_prompt.md , ` +
    `${p.loser_dir}/decomposition.json ; per-rung win-rates: ${p.loser_dir}/metrics.json\n` +
    `The LOSER's salient weakness: ${p.weakness}\n\n` +
    `Read all six files. Think step by step: (1) what does the WINNER's genotype do — in strategy framing AND in ` +
    `decomposition structure — that the LOSER does not, especially anything that addresses the loser's weak rungs? ` +
    `(2) what mistake or omission in the LOSER's genotype most plausibly cost it win-rate? (3) what generalizable ` +
    `harness-design principle follows?\n` +
    `Distil EXACTLY ${MAX_LESSONS} short LESSONS that would most improve a weak harness. Write a JSON array of ` +
    `${MAX_LESSONS} objects, each {"lesson": "<imperative; <=30 words; about harness strategy or decomposition ` +
    `structure, NOT this specific matchup>", "label": "specific" or "meta"} ("specific" = BattleSnake-strategy/` +
    `decomposition know-how; "meta" = broadly-applicable harness-design principle). Write ONLY that JSON array with ` +
    `the Write tool to ${p.lessons_path} (valid JSON, no prose, no fences). Return one line.`
}

// ---- CORE: lesson-conditioned mutation -------------------------------------
function coreMutatePrompt(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id)
  const cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are a CORE MUTATION operator (model=SONNET). You evolve a HARNESS genotype with TWO components: ` +
    `planner_prompt.md (strategy framing + how the planner briefs/decomposes for specialists) and decomposition.json ` +
    `{specialists: subset of [space_control,combat,food,endgame,hazard], referee_policy in [priority_order,` +
    `weighted_vote,planner_merge], tester: bool, refine_rounds: int}.\n` +
    `PARENT genotype: ${pd}/planner_prompt.md and ${pd}/decomposition.json . PARENT performance: ${pd}/metrics.json ` +
    `(ladder_fitness + per_rung win-rates — note where it is weak).\n` +
    `RETRIEVED LESSONS (distilled by contrastive reflection on past winner-vs-loser harnesses, ranked by relevance ` +
    `to this parent's weakness and by their verified track record): read ${cd}/breed_context.json — it holds the ` +
    `parent's weakness profile and the top lessons to apply.\n` +
    `Make ONE incremental, single-aspect edit to the genotype that APPLIES the most relevant retrieved lesson(s) to ` +
    `fix the parent's weakness — either sharpen/extend planner_prompt.md OR make exactly one structural change to ` +
    `decomposition.json (add/remove one specialist, change referee_policy, toggle tester, or adjust refine_rounds), ` +
    `not both. Keep the change SMALL and plausible.\n` +
    `Write the CHILD's TWO files with the Write tool: ${cd}/planner_prompt.md and ${cd}/decomposition.json (copy the ` +
    `UNCHANGED component verbatim from the parent; decomposition.json must be valid JSON with those four keys). ALSO ` +
    `update ${cd}/lineage.json: set "changed_components" (list) and "diff" (one line: the change + which lesson id(s) ` +
    `it applied). Do NOT remove the existing "lessons_used" field. Return one line.`
}

// ----------------------------------------------------------------- one nested harness run (Haiku)
// FRONTIER reflection: contrast the CHAMPION against the opponents that beat it -> lessons to improve IT.
function frontierReflectPrompt(t) {
  const oppLines = (t.losing_rungs || []).map(r => `  - ${r} rung (champion win-rate ${t.per_rung[r]}): ${t.opponents[r]}`).join('\n')
  const boldLine = BOLD
    ? `You MAY propose a BOLDER restructuring than a single tweak (e.g. switch referee_policy AND drop a diluting specialist) when the evidence supports it — the champion is already complete, so incremental prompt edits have repeatedly failed; a decisive structural change is preferred. `
    : ''
  return `You are a FRONTIER CONTRASTIVE-REFLECTION analyst (model=SONNET). Unlike ordinary contrastive ` +
    `reflection (which compares two population harnesses), here you must improve the CURRENT CHAMPION harness — the ` +
    `best harness in the tournament, which no weaker harness can teach. A harness has two evolvable components: ` +
    `planner_prompt.md (strategy framing + how the planner briefs/decomposes) and decomposition.json {specialists: ` +
    `subset of [space_control,combat,food,endgame,hazard], referee_policy in [priority_order,weighted_vote,` +
    `planner_merge], tester: bool, refine_rounds: int}.\n\n` +
    `CHAMPION genotype: ${t.champion_dir}/planner_prompt.md , ${t.champion_dir}/decomposition.json ; per-rung ` +
    `win-rates: ${t.champion_dir}/metrics.json (ladder_fitness ${t.champion_fitness}).\n` +
    `It DOMINATES the easy rungs but LOSES to the opponents it cannot beat:\n${oppLines}\n\n` +
    `Read the champion's two genotype files + metrics. Think step by step: (1) does its planner_merge/weighting ` +
    `DILUTE the decisive concern (head-to-head combat or space denial) that these strong opponents punish? (2) would ` +
    `a sharper planner framing, a different referee_policy, dropping a distracting specialist, or deeper refine ` +
    `rounds plausibly close the gap on the strong/sonnet rungs? (3) what does a flood-fill + head-to-head opponent do ` +
    `that the champion fails to counter? ${boldLine}\n` +
    `Distil EXACTLY ${MAX_LESSONS} short LESSONS that would most improve THIS champion against the rungs it loses ` +
    `(not generic advice for weak harnesses). Write a JSON array of ${MAX_LESSONS} objects, each {"lesson": ` +
    `"<imperative; <=30 words; about sharpening or restructuring an ALREADY-COMPLETE harness to beat strong ` +
    `head-to-head/space opponents>", "label": "specific" or "meta"}. Write ONLY that JSON array with the Write tool ` +
    `to ${t.lessons_path} (valid JSON, no prose, no fences). Return one line.`
}

async function runHarness(gen, aid, phase) {
  const plan = await runPy(`harness-plan --out ${OUT} --gen ${gen} --agent ${aid}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`harness CACHED [g${gen}/${aid}]`); return { cached: true } }
  const specs = plan.specialists || []
  await agent(plannerPrompt(gen, aid, specs), { label: `plan-brief:${aid}`, phase, model: CODER })
  await parallel(specs.map(s => () => agent(specialistPrompt(gen, aid, s), { label: `spec:${aid}:${s}`, phase, model: CODER })))
  if (plan.referee_policy === 'planner_merge') {
    await agent(refereePrompt(gen, aid, specs), { label: `ref:${aid}`, phase, model: CODER })
  }
  await runPy(`assemble --out ${OUT} --gen ${gen} --agent ${aid}`, OK, `asm:${aid}`, phase)
  await runPy(`refine-init --out ${OUT} --gen ${gen} --agent ${aid} --sims ${SIMS_REFINE} --seed ${SEED}`, REFI_S, `refi:${aid}`, phase)
  const rounds = plan.refine_rounds || REFINE
  for (let r = 1; r <= rounds; r++) {
    await agent(debuggerPrompt(gen, aid, specs), { label: `debug:${aid}:r${r}`, phase, model: CODER })
    await runPy(`refine-keep --out ${OUT} --gen ${gen} --agent ${aid} --round ${r} --sims ${SIMS_REFINE} --seed ${SEED}`, KEEP_S, `keep:${aid}:r${r}`, phase)
  }
  log(`harness done [g${gen}/${aid}] specs=[${specs.join(',')}] policy=${plan.referee_policy} tester=${plan.tester} rounds=${rounds}`)
  return { cached: false }
}

// ----------------------------------------------------------------- simple-refinement run (ablation / sonnet rung)
async function runSimple(dir, persona, model, tester, rounds, phase, label) {
  const st = await runPy(`status --out ${OUT} --path ${dir} --rounds ${rounds}`, STAT_S, `stat:${label}`, phase)
  if (st.exists) { log(`simple CACHED [${label}]`); return { cached: true } }
  await agent(simpleCoderPrompt(dir, persona, model), { label: `code:${label}`, phase, model })
  await runPy(`refine-init --out ${OUT} --simple ${dir} --sims ${SIMS_REFINE} --seed ${SEED + 1} --tester ${tester}`, REFI_S, `refi:${label}`, phase, model)
  for (let r = 1; r <= rounds; r++) {
    await agent(simpleDebuggerPrompt(dir, model), { label: `debug:${label}:r${r}`, phase, model })
    await runPy(`refine-keep --out ${OUT} --simple ${dir} --round ${r} --sims ${SIMS_REFINE} --seed ${SEED + 1} --tester ${tester}`, KEEP_S, `keep:${label}:r${r}`, phase, model)
  }
  log(`simple done [${label}] rounds=${rounds}`)
  return { cached: false }
}

// =================================================================== RUN
phase('Init')
const init = await runPy(`init --out ${OUT} --seed ${SEED} --generations ${GEN} --pop ${POP} --survivors ${SURVIVORS} ` +
  `--refine-rounds ${REFINE} --crossovers 0 --sims-evolve ${SIMS_EVOLVE} --sims-admit ${SIMS_ADMIT} --sims-final ${SIMS_FINAL}`,
  INIT_S, 'init', 'Init')
const SEEDS = init.seed_ids || []
log(`init ok. ${SEEDS.length} seeds=${SEEDS.join(',')} bank=${init.bank_initialized} battlesnake=${init.battlesnake_commit}`)

phase('Ladder')
const SONNET_RUNG = `${OUT}/ladder_build/sonnet_rung`
await runSimple(SONNET_RUNG, 'You are producing the aspirational TOP ladder rung — a strong reference bot.', REFLECT, 1, REFINE, 'Ladder', 'sonnet_rung')
await runPy(`install-sonnet-rung --out ${OUT} --path ${SONNET_RUNG}/produced_bot/main.py`, OK, 'install-sonnet', 'Ladder')
const san = await runPy(`ladder-sanity --out ${OUT} --sims ${SIMS_LADDER_SANITY} --seed 4242`, SAN_S, 'ladder-sanity', 'Ladder')
log(`ladder sanity: order_ok=${san.order_ok} sonnet_competitive=${san.sonnet_competitive} fitness=${JSON.stringify(san.fitness)}`)
if (!san.order_ok) log('WARNING: ladder ranking not strictly weak<moderate<strong — continuing.')

phase('Gate')
const GATE_AGENT = ['generalist', 'tactician', 'balanced'].find(s => SEEDS.includes(s)) || SEEDS[0]
await runHarness(0, GATE_AGENT, 'Gate')
const gate = await runPy(`gate --out ${OUT} --gen 0 --agent ${GATE_AGENT}`, GATE_S, 'gate-check', 'Gate')
log(`GATE [${GATE_AGENT}]: pass=${gate.pass} (specialists=${gate.specialists_spawned} reflects=${gate.bot_reflects_genotype} ladder=${gate.ladder_ranks_sane} pairedCI=${gate.paired_ci_computed} simsfit=${gate.fitness_from_sims})`)
if (!gate.pass) { log('VERIFICATION GATE FAILED — halting before the expensive run.'); return { halted: 'gate_failed', gate } }

phase('Ablations')
await runSimple(`${OUT}/ablations/simple_refine`, 'A plain iterative-refinement Haiku bot (no decomposition) — the primary baseline.', CODER, 1, REFINE, 'Ablations', 'simple_refine')
await parallel(Array.from({ length: BEST_OF_N }, (_, k) => () =>
  runSimple(`${OUT}/ablations/best_of_n/run_${k}`, `Independent simple-refinement attempt #${k} (vary your approach).`, CODER, 0, Math.max(1, REFINE - 1), 'Ablations', `bon${k}`)))
const bon = await runPy(`pick-best-of-n --out ${OUT} --dir ${OUT}/ablations/best_of_n --n ${BEST_OF_N} --sims ${SIMS_EVOLVE} --seed ${SEED}`, BON_S, 'pick-bon', 'Ablations')
log(`ablations done. best-of-${BEST_OF_N}: run ${bon.best_run} (ladder_fitness=${bon.best_fitness && bon.best_fitness.toFixed(3)})`)

phase('Gen0')
const rest = SEEDS.filter(s => s !== GATE_AGENT)
await parallel(rest.map(aid => () => runHarness(0, aid, 'Gen0')))
const sc0 = await runPy(`score-pop --out ${OUT} --gen 0 --sims ${SIMS_EVOLVE} --seed ${SEED}`, SCORE_S, 'score:g0', 'Gen0')
await runPy(`population-summary --out ${OUT} --gen 0`, OK, 'popsum:g0', 'Gen0')
log(`gen 0 scored. champion=${sc0.champion} ladder_fitness=${sc0.champion_fitness && sc0.champion_fitness.toFixed(3)}`)

// ---- Evolve (CORE) ----------------------------------------------------------
phase('Evolve')
let championCurve = [{ gen: 0, champion: sc0.champion, fitness: sc0.champion_fitness }]
let bankCurve = []
for (let gen = 0; gen < GEN; gen++) {
  log(`--- entering generation ${gen} (this-run output tokens: ${Math.round(runSpent() / 1000)}k) ---`)
  if (runSpent() > HALT_TOKENS) { log(`HALT: token backstop (${Math.round(runSpent() / 1000)}k) at gen ${gen}. Finalizing.`); break }
  const sel = await runPy(`select --out ${OUT} --gen ${gen} --survivors ${SURVIVORS}`, SEL_S, `select:g${gen}`, 'Evolve')
  log(`gen ${gen}: survivors=${(sel.survivors || []).join(',')} champion=${sel.champion}`)

  // 1. CONTRASTIVE REFLECTION on winner/loser pairs from this scored generation -> lessons -> bank
  const rp = await runPy(`core-reflect-plan --out ${OUT} --gen ${gen} --pairs ${PAIRS}`, REFLECT_S, `reflect-plan:g${gen}`, 'Evolve')
  const pairs = rp.plan || []
  await parallel(pairs.map(p => () => agent(reflectPrompt(p), { label: `reflect:g${gen}:${p.winner_id}>${p.loser_id}`, phase: 'Evolve', model: REFLECT })))
  const ing = await runPy(`core-ingest --out ${OUT} --gen ${gen} --max-lessons ${MAX_LESSONS}`, INGEST_S, `ingest:g${gen}`, 'Evolve')
  log(`gen ${gen}: reflected on ${pairs.length} pairs -> +${ing.added} new / ${ing.merged} merged lessons; bank=${ing.bank_size} (${ing.n_meta} meta)`)

  // 1b. FRONTIER reflection: reframe the CHAMPION's own losses (to the rungs it can't beat) as the
  // negative trace, so the bank also gets lessons that can target the frontier harness. These are
  // keyed to the champion's weakness, so the champion's own offspring retrieve them when breeding.
  const fp = await runPy(`core-frontier-plan --out ${OUT} --gen ${gen}`, FRONT_S, `frontier-plan:g${gen}`, 'Evolve', REFLECT)
  const ft = (fp.plan || [])[0]
  if (ft) {
    await agent(frontierReflectPrompt(ft), { label: `frontier-reflect:g${gen}:${fp.champion}`, phase: 'Evolve', model: REFLECT })
    const fing = await runPy(`core-ingest --out ${OUT} --gen ${gen} --max-lessons ${MAX_LESSONS} --plan ${OUT}/core_bank/reflections/gen_${pad2(gen)}/frontier_plan.json`, INGEST_S, `frontier-ingest:g${gen}`, 'Evolve')
    log(`gen ${gen}: frontier reflection on champion ${fp.champion} (loses to [${(fp.losing_rungs || []).join(',')}]) -> +${fing.added} new / ${fing.merged} merged; bank=${fing.bank_size}`)
  }

  // 2. retrieve top-K lessons per parent, then lesson-conditioned mutation
  const br = await runPy(`core-breed-plan --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS} --topk ${TOPK}`, COREBREED_S, `breed:g${gen}`, 'Evolve')
  const plan = br.plan || []
  await pipeline(plan,
    async (off) => {       // 1. Sonnet writes the child genotype applying retrieved lessons (skip if bred — disk-resume)
      if (!off.exists) {
        await agent(coreMutatePrompt(gen, off), { label: `mutate:${off.new_id}:L${off.n_lessons}`, phase: 'Evolve', model: REFLECT })
      }
      return off
    },
    async (off) => {       // 2. run the child's nested harness (Haiku) + 3. score vs ladder
      await runHarness(gen + 1, off.new_id, 'Evolve')
      await runPy(`score-pop --out ${OUT} --gen ${gen + 1} --agent ${off.new_id} --sims ${SIMS_EVOLVE} --seed ${SEED}`, SCORE_S, `score:${off.new_id}`, 'Evolve')
      return off
    },
    async (off) => {       // 4. VERIFIED-acceptance gate: paired common-seed 95% CI vs PARENT (identical to GEPA)
      const ad = await runPy(`admit --out ${OUT} --gen ${gen + 1} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id} --sims ${SIMS_ADMIT} --seed ${SEED}`, ADMIT_S, `admit:${off.new_id}`, 'Evolve')
      log(`  offspring ${off.new_id} [core L=${off.n_lessons}] vs parent ${off.parent_id}: delta=${ad.delta != null ? ad.delta.toFixed(3) : '?'} CI=[${ad.ci_low != null ? ad.ci_low.toFixed(3) : '?'},${ad.ci_high != null ? ad.ci_high.toFixed(3) : '?'}] -> ${ad.admitted ? 'ADMITTED' : 'rejected'}`)
      return off
    })

  // 3. CREDIT the lessons used by each offspring (admitted -> win) — drives UCB retrieval next gen
  const cr = await runPy(`core-credit --out ${OUT} --gen ${gen}`, CREDIT_S, `credit:g${gen}`, 'Evolve')
  const bs = await runPy(`bank-status --out ${OUT}`, BANK_S, `bank:g${gen}`, 'Evolve')
  bankCurve.push({ gen: gen + 1, bank_size: bs.bank_size, n_meta: bs.n_meta, total_wins: bs.total_wins })
  log(`gen ${gen}: credited ${cr.n_credited} offspring. bank=${bs.bank_size} wins=${bs.total_wins}`)

  const fin = await runPy(`finalize-gen --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}`, FIN_S, `finalize:g${gen}`, 'Evolve')
  championCurve.push({ gen: gen + 1, champion: fin.champion, fitness: fin.champion_fitness })
  log(`gen ${gen} -> ${gen + 1}: ${fin.n_admitted} admitted. pop=${(fin.ids || []).join(',')} | champion=${fin.champion} fitness=${fin.champion_fitness && fin.champion_fitness.toFixed(3)}`)
}

// NOTE: the SIMS_FINAL headline + analysis are produced OUT-OF-BAND by cc_core.reeval (sequential,
// contention-safe) — wrapping the multi-minute 1500-sim final-eval in a subagent is what killed the
// v1 run's tail. End here after Evolve; run `python3 -m cc_core.reeval --out <OUT>` afterward.
const bankFinal = await runPy(`bank-status --out ${OUT}`, BANK_S, 'bank-final', 'Evolve')
log(`EVOLVE COMPLETE. bank=${bankFinal.bank_size} lessons (${bankFinal.n_meta} meta), ${bankFinal.total_wins} verified wins. Run cc_core.reeval for the contention-safe headline.`)

return {
  output_dir: OUT,
  optimizer: BOLD ? 'CORE-v2-frontier-bold' : 'CORE-v2-frontier',
  generations: GEN,
  knobs: { POP, SURVIVORS, REFINE, SIMS_EVOLVE, SIMS_ADMIT, SIMS_FINAL, BEST_OF_N, PAIRS, TOPK, MAX_LESSONS, BOLD },
  champion_curve: championCurve,
  bank_curve: bankCurve,
  bank_final: bankFinal,
  next_step: `python3 -m cc_core.reeval --out ${OUT} --sims-evolve 150 --sims-admit 240 --sims-final 1500`,
}
