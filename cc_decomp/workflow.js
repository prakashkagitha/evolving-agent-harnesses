export const meta = {
  name: 'codeclash-decomp-evolution',
  description: 'Single-level evolution of a NESTED multi-agent BattleSnake harness (planner->parallel specialists->referee->verified refine loop, all Haiku); Sonnet evolves the harness genotype; ladder-anchored fitness + verified acceptance. Reuses CodeClash BattleSnake sims.',
  phases: [
    { title: 'Init', detail: 'config + 12 seed genotypes + fixed ladder rungs 0-2 (deterministic)' },
    { title: 'Ladder', detail: 'produce the frozen Sonnet rung (simple-refinement) + 4-rung sanity' },
    { title: 'Gate', detail: 'verification gate on the richest gen-0 harness (specialists spawn, bot reflects genotype, ladder ranks, paired CI computes)' },
    { title: 'Ablations', detail: 'simple-refinement bot + best-of-N bot (Haiku) — the baselines to beat' },
    { title: 'Gen0', detail: 'run all 12 seed harnesses (Haiku nested pipeline) + score vs ladder' },
    { title: 'Evolve', detail: 'OUTER_GENERATIONS: select -> Sonnet breeds ~8 offspring (all 4 lenses) -> harness run -> VERIFIED-acceptance gate (paired 95% CI) -> refill' },
    { title: 'Final', detail: 'SIMS_FINAL headline: champion + both ablations vs every rung (incl. Sonnet) with CIs' },
    { title: 'Analyze', detail: 'analysis.md + report.html (ladder trajectory, ablation comparison, 2-component timelines, verified-mutation attribution)' },
  ],
}

// ----------------------------------------------------------------- knobs (?? so explicit 0 is honored)
let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
// Absolute path to this repo on the machine running Claude Code (agents run shell commands from here).
// Override per-run with {"ccroot": "/abs/path/to/evolving-agent-harnesses", ...} in the Workflow `args`.
const CCROOT = (A && A.ccroot) || '/ABSOLUTE/PATH/TO/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_decomp_evo')
const SEED = A.seed ?? 0
const GEN = A.generations ?? 6
const POP = A.pop ?? 12
const SURVIVORS = A.survivors ?? 4
const REFINE = A.refine_rounds ?? 4
const SIMS_EVOLVE = A.sims_evolve ?? 120
const SIMS_ADMIT = A.sims_admit ?? 200
const SIMS_FINAL = A.sims_final ?? 1500
const SIMS_REFINE = A.sims_refine ?? 36     // token-free per-round refine eval vs the moderate rung
const SIMS_LADDER_SANITY = A.sims_sanity ?? 120
const BEST_OF_N = A.best_of_n ?? 8
const CROSSOVERS = A.crossovers ?? 0        // keep per-lens attribution clean (verified gate is the filter)
const HALT_TOKENS = A.halt_tokens ?? 9_000_000    // backstop on THIS RUN's output-token DELTA (generous safety net)
const spent = () => { try { return budget && budget.spent ? budget.spent() : 0 } catch (e) { return 0 } }
const _spentStart = spent()                       // baseline: spent() counts the whole session, so measure the delta
const runSpent = () => Math.max(0, spent() - _spentStart)
const CODER = 'haiku'      // ALL harness execution (planner/specialists/referee/debugger) — strict policy
const REFLECT = 'sonnet'   // outer evolution (mutators) + the frozen Sonnet ladder rung
const py = `cd ${CCROOT} && python3 -m cc_decomp.control`
const pad2 = n => String(n).padStart(2, '0')

// ----------------------------------------------------------------- schemas
const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, seed_ids: { type: 'array', items: { type: 'string' } }, battlesnake_commit: { type: 'string' }, codeclash_commit: { type: 'string' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, specialists: { type: 'array', items: { type: 'string' } }, referee_policy: { type: 'string' }, tester: { type: 'boolean' }, refine_rounds: { type: 'number' }, exists: { type: 'boolean' } }, required: ['ok'] }
const REFI_S = { type: 'object', properties: { ok: { type: 'boolean' }, baseline_score: { type: 'number' }, valid: { type: 'boolean' }, winrate_vs_moderate: { type: ['number', 'null'] }, refine_rounds: { type: 'number' } }, required: ['ok'] }
const KEEP_S = { type: 'object', properties: { ok: { type: 'boolean' }, kept: { type: 'boolean' }, valid: { type: 'boolean' }, new_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const SCORE_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] }, ranking: { type: 'array' } }, required: ['ok'] }
const SEL_S = { type: 'object', properties: { ok: { type: 'boolean' }, survivors: { type: 'array', items: { type: 'string' } }, champion: { type: ['string', 'null'] } }, required: ['ok'] }
const BREED_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, survivors: { type: 'array' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const ADMIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, admitted: { type: 'boolean' }, delta: { type: ['number', 'null'] }, ci_low: { type: ['number', 'null'] }, ci_high: { type: ['number', 'null'] }, child_fit: { type: ['number', 'null'] }, parent_fit: { type: ['number', 'null'] } }, required: ['ok'] }
const FIN_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, ids: { type: 'array', items: { type: 'string' } }, new_ids: { type: 'array', items: { type: 'string' } }, carried: { type: 'array', items: { type: 'string' } }, n_admitted: { type: 'number' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok', 'ids'] }
const SAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, order_ok: { type: 'boolean' }, sonnet_competitive: { type: ['boolean', 'null'] }, fitness: { type: 'object' } }, required: ['ok'] }
const GATE_S = { type: 'object', properties: { ok: { type: 'boolean' }, pass: { type: 'boolean' }, specialists_spawned: { type: 'boolean' }, bot_reflects_genotype: { type: 'boolean' }, ladder_ranks_sane: { type: 'boolean' }, paired_ci_computed: { type: 'boolean' }, fitness_from_sims: { type: 'boolean' }, details: { type: 'object' } }, required: ['ok', 'pass'] }
const STAT_S = { type: 'object', properties: { ok: { type: 'boolean' }, exists: { type: 'boolean' } }, required: ['ok'] }
const BON_S = { type: 'object', properties: { ok: { type: 'boolean' }, best_run: { type: ['number', 'null'] }, best_fitness: { type: 'number' } }, required: ['ok'] }
const FINAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, headline: { type: 'object' }, champion_vs_ablations: { type: 'object' } }, required: ['ok'] }

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

const LENS_GUIDE = {
  strategy: 'Sharpen the planner_prompt\'s overall strategy framing and priorities (clearer tactics, better guidance for how the planner briefs/integrates the specialists). Edit ONLY planner_prompt.md.',
  concept: 'Add exactly ONE strategic concept the parent is MISSING (e.g. head-to-head pressure, trap-avoidance, length-race, endgame stalling, edge-safety) to planner_prompt.md, woven into the framing. Edit ONLY planner_prompt.md.',
  decomposition: 'Make exactly ONE structural edit to decomposition.json: ADD one specialist OR REMOVE one specialist (from {space_control,combat,food,endgame,hazard}) OR change referee_policy (priority_order|weighted_vote|planner_merge). Keep planner_prompt.md as-is.',
  robustness: 'Strengthen robustness via decomposition.json: turn the tester ON (if off) and/or adjust refine_rounds. Edit ONLY decomposition.json.',
}

function mutatePrompt(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id)
  const cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are an OUTER-EVOLUTION reflection lens = "${off.lens}" (model=SONNET). You evolve a HARNESS genotype ` +
    `with TWO components: planner_prompt.md (strategy framing + how the planner briefs/decomposes for specialists) ` +
    `and decomposition.json {specialists: subset of [space_control,combat,food,endgame,hazard], referee_policy in ` +
    `[priority_order,weighted_vote,planner_merge], tester: bool, refine_rounds: int}.\n` +
    `PARENT genotype: ${pd}/planner_prompt.md and ${pd}/decomposition.json . PARENT performance: ${pd}/metrics.json ` +
    `(ladder_fitness + per_rung win-rates, incl. vs the strong and sonnet rungs — diagnose where it is weak).\n` +
    `THROUGH YOUR LENS make ONE incremental single-aspect edit: ${LENS_GUIDE[off.lens]}\n` +
    `Write the CHILD's TWO files with the Write tool: ${cd}/planner_prompt.md and ${cd}/decomposition.json (copy the ` +
    `UNCHANGED component verbatim from the parent; decomposition.json must be valid JSON with those four keys). ` +
    `ALSO update ${cd}/lineage.json: set "changed_components" (list) and "diff" (one-line description of the single ` +
    `change you made). Make the smallest change that plausibly raises win-rate vs the ladder. Return one line.`
}

function crossoverPrompt(gen, off) {
  const p0 = gdir(off.parent_gen, off.parent_id)
  const p1 = gdir(off.parent_gen, off.parent_id2)
  const cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are OUTER-EVOLUTION CROSSOVER (model=SONNET), winner x winner. Merge two high-fitness parent HARNESSES ` +
    `into one child. Parent A (weight more): ${p0}/ . Parent B: ${p1}/ . Read each planner_prompt.md + ` +
    `decomposition.json + metrics.json. Compose a coherent child: the stronger strategy framing + a sensible union of ` +
    `specialists and the better referee_policy/tester/refine_rounds. Write ${cd}/planner_prompt.md and ` +
    `${cd}/decomposition.json (valid JSON) and update ${cd}/lineage.json (changed_components, diff). Return one line.`
}

// ----------------------------------------------------------------- one nested harness run (Haiku)
async function runHarness(gen, aid, phase) {
  const plan = await runPy(`harness-plan --out ${OUT} --gen ${gen} --agent ${aid}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`harness CACHED [g${gen}/${aid}]`); return { cached: true } }
  const specs = plan.specialists || []
  // 1. planner -> briefs
  await agent(plannerPrompt(gen, aid, specs), { label: `plan-brief:${aid}`, phase, model: CODER })
  // 2. specialists in parallel (fan-out)
  await parallel(specs.map(s => () => agent(specialistPrompt(gen, aid, s), { label: `spec:${aid}:${s}`, phase, model: CODER })))
  // 3. referee (planner_merge only)
  if (plan.referee_policy === 'planner_merge') {
    await agent(refereePrompt(gen, aid, specs), { label: `ref:${aid}`, phase, model: CODER })
  }
  // 4. assemble + verified refine loop (refute-until-converge)
  await runPy(`assemble --out ${OUT} --gen ${gen} --agent ${aid}`, OK, `asm:${aid}`, phase)
  const ri = await runPy(`refine-init --out ${OUT} --gen ${gen} --agent ${aid} --sims ${SIMS_REFINE} --seed ${SEED}`, REFI_S, `refi:${aid}`, phase)
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
// ---- Init -------------------------------------------------------------------
phase('Init')
const init = await runPy(`init --out ${OUT} --seed ${SEED} --generations ${GEN} --pop ${POP} --survivors ${SURVIVORS} ` +
  `--refine-rounds ${REFINE} --crossovers ${CROSSOVERS} --sims-evolve ${SIMS_EVOLVE} --sims-admit ${SIMS_ADMIT} --sims-final ${SIMS_FINAL}`,
  INIT_S, 'init', 'Init')
const SEEDS = init.seed_ids || []
log(`init ok. ${SEEDS.length} seeds=${SEEDS.join(',')} battlesnake=${init.battlesnake_commit} codeclash=${init.codeclash_commit}`)

// ---- Ladder: produce the frozen Sonnet rung + sanity ------------------------
phase('Ladder')
const SONNET_RUNG = `${OUT}/ladder_build/sonnet_rung`
await runSimple(SONNET_RUNG, 'You are producing the aspirational TOP ladder rung — a strong reference bot.', REFLECT, 1, REFINE, 'Ladder', 'sonnet_rung')
await runPy(`install-sonnet-rung --out ${OUT} --path ${SONNET_RUNG}/produced_bot/main.py`, OK, 'install-sonnet', 'Ladder')
const san = await runPy(`ladder-sanity --out ${OUT} --sims ${SIMS_LADDER_SANITY} --seed 4242`, SAN_S, 'ladder-sanity', 'Ladder')
log(`ladder sanity: order_ok=${san.order_ok} sonnet_competitive=${san.sonnet_competitive} fitness=${JSON.stringify(san.fitness)}`)
if (!san.order_ok) log('WARNING: ladder ranking not strictly weak<moderate<strong — continuing (fitness still ladder-anchored).')

// ---- Gate: verification on the richest gen-0 harness ------------------------
phase('Gate')
const GATE_AGENT = ['generalist', 'tactician', 'balanced'].find(s => SEEDS.includes(s)) || SEEDS[0]
await runHarness(0, GATE_AGENT, 'Gate')
const gate = await runPy(`gate --out ${OUT} --gen 0 --agent ${GATE_AGENT}`, GATE_S, 'gate-check', 'Gate')
log(`GATE [${GATE_AGENT}]: pass=${gate.pass} (specialists=${gate.specialists_spawned} reflects=${gate.bot_reflects_genotype} ladder=${gate.ladder_ranks_sane} pairedCI=${gate.paired_ci_computed} simsfit=${gate.fitness_from_sims})`)
if (!gate.pass) { log('VERIFICATION GATE FAILED — halting before the expensive run.'); return { halted: 'gate_failed', gate } }

// ---- Ablations (Haiku baselines to beat) ------------------------------------
phase('Ablations')
await runSimple(`${OUT}/ablations/simple_refine`, 'A plain iterative-refinement Haiku bot (no decomposition) — the primary baseline.', CODER, 1, REFINE, 'Ablations', 'simple_refine')
// best-of-N: N independent simple-refine runs, keep the best by ladder fitness
await parallel(Array.from({ length: BEST_OF_N }, (_, k) => () =>
  runSimple(`${OUT}/ablations/best_of_n/run_${k}`, `Independent simple-refinement attempt #${k} (vary your approach).`, CODER, 0, Math.max(1, REFINE - 1), 'Ablations', `bon${k}`)))
const bon = await runPy(`pick-best-of-n --out ${OUT} --dir ${OUT}/ablations/best_of_n --n ${BEST_OF_N} --sims ${SIMS_EVOLVE} --seed ${SEED}`, BON_S, 'pick-bon', 'Ablations')
log(`ablations done. best-of-${BEST_OF_N}: run ${bon.best_run} (ladder_fitness=${bon.best_fitness && bon.best_fitness.toFixed(3)})`)

// ---- Gen 0: run the remaining seed harnesses + score ------------------------
phase('Gen0')
const rest = SEEDS.filter(s => s !== GATE_AGENT)
await parallel(rest.map(aid => () => runHarness(0, aid, 'Gen0')))
const sc0 = await runPy(`score-pop --out ${OUT} --gen 0 --sims ${SIMS_EVOLVE} --seed ${SEED}`, SCORE_S, 'score:g0', 'Gen0')
await runPy(`population-summary --out ${OUT} --gen 0`, OK, 'popsum:g0', 'Gen0')
log(`gen 0 scored. champion=${sc0.champion} ladder_fitness=${sc0.champion_fitness && sc0.champion_fitness.toFixed(3)}`)

// ---- Evolve -----------------------------------------------------------------
phase('Evolve')
let championCurve = [{ gen: 0, champion: sc0.champion, fitness: sc0.champion_fitness }]
for (let gen = 0; gen < GEN; gen++) {
  log(`--- entering generation ${gen} (this-run output tokens: ${Math.round(runSpent() / 1000)}k) ---`)
  if (runSpent() > HALT_TOKENS) { log(`HALT: this-run output-token backstop (${Math.round(runSpent() / 1000)}k > ${Math.round(HALT_TOKENS / 1000)}k) at gen ${gen}. Finalizing with what exists.`); break }
  const sel = await runPy(`select --out ${OUT} --gen ${gen} --survivors ${SURVIVORS}`, SEL_S, `select:g${gen}`, 'Evolve')
  log(`gen ${gen}: survivors=${(sel.survivors || []).join(',')} champion=${sel.champion}`)
  const br = await runPy(`breed-plan --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS} --crossovers ${CROSSOVERS}`, BREED_S, `breed:g${gen}`, 'Evolve')
  const plan = br.plan || []
  // Pipeline each offspring: Sonnet mutate -> Haiku harness run -> score -> verified-acceptance gate.
  await pipeline(plan,
    async (off) => {       // 1. Sonnet writes the child genotype (skip if already bred — disk-resume)
      if (!off.exists) {
        await agent(off.type === 'crossover' ? crossoverPrompt(gen, off) : mutatePrompt(gen, off),
          { label: `${off.type === 'crossover' ? 'xover' : 'mutate'}:${off.new_id}:${off.lens}`, phase: 'Evolve', model: REFLECT })
      }
      return off
    },
    async (off) => {       // 2. run the child's nested harness (Haiku) + 3. score vs ladder
      await runHarness(gen + 1, off.new_id, 'Evolve')
      await runPy(`score-pop --out ${OUT} --gen ${gen + 1} --agent ${off.new_id} --sims ${SIMS_EVOLVE} --seed ${SEED}`, SCORE_S, `score:${off.new_id}`, 'Evolve')
      return off
    },
    async (off) => {       // 4. VERIFIED-acceptance gate: paired common-seed 95% CI vs PARENT
      const ad = await runPy(`admit --out ${OUT} --gen ${gen + 1} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id} --sims ${SIMS_ADMIT} --seed ${SEED}`, ADMIT_S, `admit:${off.new_id}`, 'Evolve')
      log(`  offspring ${off.new_id} [${off.lens}] vs parent ${off.parent_id}: delta=${ad.delta != null ? ad.delta.toFixed(3) : '?'} CI=[${ad.ci_low != null ? ad.ci_low.toFixed(3) : '?'},${ad.ci_high != null ? ad.ci_high.toFixed(3) : '?'}] -> ${ad.admitted ? 'ADMITTED' : 'rejected'}`)
      return off
    })
  const fin = await runPy(`finalize-gen --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}`, FIN_S, `finalize:g${gen}`, 'Evolve')
  championCurve.push({ gen: gen + 1, champion: fin.champion, fitness: fin.champion_fitness })
  log(`gen ${gen} -> ${gen + 1}: ${fin.n_admitted} admitted. pop=${(fin.ids || []).join(',')} | champion=${fin.champion} fitness=${fin.champion_fitness && fin.champion_fitness.toFixed(3)}`)
}

// ---- Final headline eval ----------------------------------------------------
phase('Final')
const fe = await runPy(`final-eval --out ${OUT} --gen ${GEN} --sims ${SIMS_FINAL} --seed ${SEED}`, FINAL_S, 'final-eval', 'Final')
log(`FINAL champion=${fe.champion}. ladder per-rung (winrate): ${JSON.stringify(Object.fromEntries(Object.entries(fe.headline.champion || {}).map(([k, v]) => [k, v.winrate != null ? +v.winrate.toFixed(3) : v])))}`)
log(`champion vs ablations: ${JSON.stringify(fe.champion_vs_ablations)}`)

// ---- Analyze + report -------------------------------------------------------
phase('Analyze')
await agent(`Run EXACTLY this command and return its last-line JSON via structured output:\n\`\`\`\n${py.replace('cc_decomp.control', 'cc_decomp.analysis')} --out ${OUT}\n\`\`\``,
  { label: 'analysis', phase: 'Analyze', model: CODER, schema: OK })
const rep = await agent(`Run EXACTLY this command and return its last-line JSON via structured output:\n\`\`\`\n${py.replace('cc_decomp.control', 'cc_decomp.viz')} --out ${OUT}\n\`\`\``,
  { label: 'report', phase: 'Analyze', model: CODER, schema: { type: 'object', properties: { ok: { type: 'boolean' }, report: { type: 'string' } }, required: ['ok'] } })
await agent(`You are writing the executive summary for a SINGLE-LEVEL evolution of a NESTED multi-agent BattleSnake ` +
  `harness (a planner fans out parallel Haiku specialist coders -> referee -> a verified refine loop; Sonnet evolves ` +
  `the harness genotype with every accepted edit VERIFIED to beat its parent on a fixed opponent ladder). Read the ` +
  `computed results ${OUT}/analysis_data.json and the current ${OUT}/analysis.md . PREPEND to analysis.md a ` +
  `"## Executive Summary" section (right after the H1), 200-320 words, grounded ONLY in the numbers: (1) the champion's ` +
  `ladder trajectory (monotone by construction) and its final per-rung win-rates vs weak/moderate/STRONG/SONNET with ` +
  `CIs; (2) the CONTRIBUTION TEST — did the evolved champion beat BOTH ablations (simple-refinement and best-of-N) on ` +
  `ladder fitness? quote the numbers; (3) how the two genotype components evolved (planner_prompt concepts + ` +
  `decomposition structure), each tied to verified gains; (4) the verified-mutation attribution per lens (which lenses ` +
  `produced admitted edits); (5) one honest caveat (n=1 seed; the Sonnet rung is a simple-refinement bot, so beating ` +
  `it means evolved-Haiku-harness >= plain-refinement-Sonnet — do NOT claim transfer). Cite ACTUAL values, invent ` +
  `nothing. Keep the rest of analysis.md intact. Return a one-line confirmation.`,
  { label: 'synthesis', phase: 'Analyze', model: REFLECT })
log('analysis.md + report.html written.')

return {
  output_dir: OUT,
  generations: GEN,
  knobs: { POP, SURVIVORS, REFINE, SIMS_EVOLVE, SIMS_ADMIT, SIMS_FINAL, BEST_OF_N },
  champion: fe.champion,
  champion_curve: championCurve,
  champion_per_rung: fe.headline.champion,
  champion_vs_ablations: fe.champion_vs_ablations,
  report: (rep && rep.report) || `${OUT}/report.html`,
}
