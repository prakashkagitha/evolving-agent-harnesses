export const meta = {
  name: 'codeclash-core-frontier-probe',
  description: 'FRONTIER PROBE for CORE: tests whether contrastive reflection can improve the CHAMPION harness when the negative trace is reframed as the champion\'s OWN losses to the rungs it cannot beat (strong/sonnet), rather than weaker population harnesses. Runs on top of an existing cc_core_evo run: each round reflects on champion-vs-the-opponents-that-beat-it -> frontier lessons -> breed every child FROM the champion conditioned on those lessons -> verified-acceptance gate vs the champion. Reuses the cc_core/cc_decomp controllers + CodeClash sims.',
  phases: [
    { title: 'Frontier', detail: 'ROUNDS rounds: champion-frontier reflection (Sonnet) -> ingest lessons -> breed K children FROM the champion (lesson-conditioned) -> harness (Haiku) -> verified gate vs champion -> credit -> finalize' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = (A && A.ccroot) || '/ABSOLUTE/PATH/TO/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_core_evo')
const SEED = A.seed ?? 0
const START_GEN = A.start_gen ?? 4          // the last finalized gen of the base run (champion lives here)
const ROUNDS = A.rounds ?? 3
const POP = A.pop ?? 8
const SURVIVORS = A.survivors ?? 4
const REFINE = A.refine_rounds ?? 2
const SIMS_EVOLVE = A.sims_evolve ?? 120
const SIMS_ADMIT = A.sims_admit ?? 200
const SIMS_REFINE = A.sims_refine ?? 36
const TOPK = A.topk ?? 3
const MAX_LESSONS = A.max_lessons ?? 4
const CODER = 'haiku'
const REFLECT = 'sonnet'
const py = `cd ${CCROOT} && python3 -m cc_core.control`
const pad2 = n => String(n).padStart(2, '0')

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, specialists: { type: 'array', items: { type: 'string' } }, referee_policy: { type: 'string' }, tester: { type: 'boolean' }, refine_rounds: { type: 'number' }, exists: { type: 'boolean' } }, required: ['ok'] }
const REFI_S = { type: 'object', properties: { ok: { type: 'boolean' }, baseline_score: { type: 'number' }, valid: { type: 'boolean' }, refine_rounds: { type: 'number' } }, required: ['ok'] }
const KEEP_S = { type: 'object', properties: { ok: { type: 'boolean' }, kept: { type: 'boolean' }, new_score: { type: 'number' } }, required: ['ok'] }
const SCORE_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok'] }
const SEL_S = { type: 'object', properties: { ok: { type: 'boolean' }, survivors: { type: 'array', items: { type: 'string' } }, champion: { type: ['string', 'null'] } }, required: ['ok'] }
const ADMIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, admitted: { type: 'boolean' }, delta: { type: ['number', 'null'] }, ci_low: { type: ['number', 'null'] }, ci_high: { type: ['number', 'null'] } }, required: ['ok'] }
const FIN_S = { type: 'object', properties: { ok: { type: 'boolean' }, ids: { type: 'array', items: { type: 'string' } }, n_admitted: { type: 'number' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok', 'ids'] }
const FRONT_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] }, losing_rungs: { type: 'array' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const INGEST_S = { type: 'object', properties: { ok: { type: 'boolean' }, added: { type: 'number' }, merged: { type: 'number' }, bank_size: { type: 'number' } }, required: ['ok'] }
const BREED_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, survivors: { type: 'array' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const CREDIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_credited: { type: 'number' }, bank_size: { type: 'number' } }, required: ['ok'] }

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
    `feedback ${d}/produced_bot/feedback.json and the current specialist code in ${d}/specialists/ (active: ${specs.join(', ')}). ` +
    `Diagnose the SINGLE biggest weakness and FIX it by editing the most relevant specialist file(s) with the Write ` +
    `tool (raw Python, keep \`def score(game_state)->dict\`; pure; never raises). Edit ONLY files in ${d}/specialists/ . ` +
    `Your edit is kept only if it does not regress fitness (verified automatically). Return one line.`
}

// FRONTIER reflection: contrast the CHAMPION against the opponents that beat it -> lessons to improve IT.
function frontierReflectPrompt(t) {
  const oppLines = (t.losing_rungs || []).map(r => `  - ${r} rung (champion win-rate ${t.per_rung[r]}): ${t.opponents[r]}`).join('\n')
  return `You are a FRONTIER CONTRASTIVE-REFLECTION analyst (model=SONNET). Unlike ordinary contrastive ` +
    `reflection (which compares two population harnesses), here you must improve the CURRENT CHAMPION harness — the ` +
    `best harness in the tournament, which no weaker harness can teach. A harness has two evolvable components: ` +
    `planner_prompt.md (strategy framing + how the planner briefs/decomposes for specialists) and decomposition.json ` +
    `{specialists: subset of [space_control,combat,food,endgame,hazard], referee_policy in [priority_order,` +
    `weighted_vote,planner_merge], tester: bool, refine_rounds: int}.\n\n` +
    `CHAMPION genotype: ${t.champion_dir}/planner_prompt.md and ${t.champion_dir}/decomposition.json ; per-rung ` +
    `win-rates: ${t.champion_dir}/metrics.json (ladder_fitness ${t.champion_fitness}).\n` +
    `The champion DOMINATES the easy rungs but LOSES to the opponents it cannot beat:\n${oppLines}\n\n` +
    `Read the champion's two genotype files and its metrics. Think step by step: (1) the champion already activates ` +
    `several specialists — is the problem that its planner_merge/weighting DILUTES the decisive concern (e.g. ` +
    `head-to-head combat or space denial) that these strong opponents punish? (2) would a SHARPER planner framing, a ` +
    `different referee_policy, dropping a distracting specialist, or deeper refine rounds plausibly close the gap on ` +
    `the strong/sonnet rungs? (3) what specifically does a flood-fill + head-to-head opponent do that the champion ` +
    `fails to counter?\n` +
    `Distil EXACTLY ${MAX_LESSONS} short LESSONS that would most improve THIS champion against the rungs it loses ` +
    `(not generic advice for weak harnesses). Write a JSON array of ${MAX_LESSONS} objects, each {"lesson": ` +
    `"<imperative; <=30 words; about sharpening or restructuring an ALREADY-COMPLETE harness to beat strong ` +
    `head-to-head/space opponents>", "label": "specific" or "meta"}. Write ONLY that JSON array with the Write tool ` +
    `to ${t.lessons_path} (valid JSON, no prose, no fences). Return one line.`
}

// lesson-conditioned mutation (reused idea): apply the retrieved frontier lessons to the champion.
function coreMutatePrompt(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id)
  const cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are a CORE MUTATION operator (model=SONNET) in the FRONTIER probe. You evolve a HARNESS genotype ` +
    `(planner_prompt.md + decomposition.json {specialists subset of [space_control,combat,food,endgame,hazard], ` +
    `referee_policy in [priority_order,weighted_vote,planner_merge], tester, refine_rounds}).\n` +
    `PARENT = the CHAMPION: ${pd}/planner_prompt.md , ${pd}/decomposition.json , ${pd}/metrics.json (note the rungs ` +
    `it LOSES — strong/sonnet).\n` +
    `RETRIEVED FRONTIER LESSONS (distilled from contrasting the champion against the opponents that beat it, ranked ` +
    `by relevance + verified track record): read ${cd}/breed_context.json .\n` +
    `Make ONE incremental, single-aspect edit that APPLIES the most relevant lesson to help the champion beat the ` +
    `strong/sonnet rungs — either sharpen planner_prompt.md OR make exactly one structural change to ` +
    `decomposition.json (add/remove one specialist, change referee_policy, toggle tester, adjust refine_rounds), not ` +
    `both. The champion is already strong, so prefer SHARPENING/FOCUSING over piling on; a structural simplification ` +
    `(e.g. a more decisive referee_policy or dropping a diluting specialist) is allowed if a lesson supports it.\n` +
    `Write the CHILD's TWO files with the Write tool: ${cd}/planner_prompt.md and ${cd}/decomposition.json (copy the ` +
    `UNCHANGED component verbatim from the parent; valid JSON, four keys). ALSO update ${cd}/lineage.json: set ` +
    `"changed_components" and "diff" (one line: the change + which lesson id(s) it applied). Keep the existing ` +
    `"lessons_used" field. Return one line.`
}

async function runHarness(gen, aid, phase) {
  const plan = await runPy(`harness-plan --out ${OUT} --gen ${gen} --agent ${aid}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`harness CACHED [g${gen}/${aid}]`); return }
  const specs = plan.specialists || []
  await agent(plannerPrompt(gen, aid, specs), { label: `plan-brief:${aid}`, phase, model: CODER })
  await parallel(specs.map(s => () => agent(specialistPrompt(gen, aid, s), { label: `spec:${aid}:${s}`, phase, model: CODER })))
  if (plan.referee_policy === 'planner_merge') await agent(refereePrompt(gen, aid, specs), { label: `ref:${aid}`, phase, model: CODER })
  await runPy(`assemble --out ${OUT} --gen ${gen} --agent ${aid}`, OK, `asm:${aid}`, phase)
  await runPy(`refine-init --out ${OUT} --gen ${gen} --agent ${aid} --sims ${SIMS_REFINE} --seed ${SEED}`, REFI_S, `refi:${aid}`, phase)
  const rounds = plan.refine_rounds || REFINE
  for (let r = 1; r <= rounds; r++) {
    await agent(debuggerPrompt(gen, aid, specs), { label: `debug:${aid}:r${r}`, phase, model: CODER })
    await runPy(`refine-keep --out ${OUT} --gen ${gen} --agent ${aid} --round ${r} --sims ${SIMS_REFINE} --seed ${SEED}`, KEEP_S, `keep:${aid}:r${r}`, phase)
  }
  log(`harness done [g${gen}/${aid}] specs=[${specs.join(',')}] policy=${plan.referee_policy}`)
}

// =================================================================== RUN
phase('Frontier')
const refDir = g => `${OUT}/core_bank/reflections/gen_${pad2(g)}`
let curve = []
const base = await runPy(`bank-status --out ${OUT}`, { type: 'object', properties: { ok: { type: 'boolean' }, bank_size: { type: 'number' } }, required: ['ok'] }, 'bank-start', 'Frontier')
log(`frontier probe: starting from gen ${START_GEN}, bank=${base.bank_size} lessons, ${ROUNDS} rounds x ${POP - SURVIVORS} champion-children`)

for (let k = 0; k < ROUNDS; k++) {
  const gen = START_GEN + k
  const sel = await runPy(`select --out ${OUT} --gen ${gen} --survivors ${SURVIVORS}`, SEL_S, `select:g${gen}`, 'Frontier')
  // 1. FRONTIER reflection on the champion vs the opponents that beat it
  const fp = await runPy(`core-frontier-plan --out ${OUT} --gen ${gen}`, FRONT_S, `frontier-plan:g${gen}`, 'Frontier')
  const t = (fp.plan || [])[0]
  if (!t) { log(`gen ${gen}: no champion to reflect on — stopping`); break }
  log(`gen ${gen}: champion ${fp.champion} (fit ${fp.champion_fitness}) loses to [${(fp.losing_rungs || []).join(',')}] — frontier reflection`)
  await agent(frontierReflectPrompt(t), { label: `frontier-reflect:g${gen}:${fp.champion}`, phase: 'Frontier', model: REFLECT })
  const ing = await runPy(`core-ingest --out ${OUT} --gen ${gen} --max-lessons ${MAX_LESSONS} --plan ${refDir(gen)}/frontier_plan.json`, INGEST_S, `ingest:g${gen}`, 'Frontier')
  log(`gen ${gen}: +${ing.added} frontier lessons (${ing.merged} merged); bank=${ing.bank_size}`)
  // 2. breed every child FROM the champion, conditioned on the frontier lessons
  const br = await runPy(`core-breed-plan --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS} --topk ${TOPK} --champion-only 1`, BREED_S, `breed:g${gen}`, 'Frontier')
  const plan = br.plan || []
  await pipeline(plan,
    async (off) => { if (!off.exists) await agent(coreMutatePrompt(gen, off), { label: `mutate:${off.new_id}:L${off.n_lessons}`, phase: 'Frontier', model: REFLECT }); return off },
    async (off) => { await runHarness(gen + 1, off.new_id, 'Frontier'); await runPy(`score-pop --out ${OUT} --gen ${gen + 1} --agent ${off.new_id} --sims ${SIMS_EVOLVE} --seed ${SEED}`, SCORE_S, `score:${off.new_id}`, 'Frontier'); return off },
    async (off) => {
      const ad = await runPy(`admit --out ${OUT} --gen ${gen + 1} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id} --sims ${SIMS_ADMIT} --seed ${SEED}`, ADMIT_S, `admit:${off.new_id}`, 'Frontier')
      log(`  child ${off.new_id} vs champion ${off.parent_id}: delta=${ad.delta != null ? ad.delta.toFixed(3) : '?'} CI=[${ad.ci_low != null ? ad.ci_low.toFixed(3) : '?'},${ad.ci_high != null ? ad.ci_high.toFixed(3) : '?'}] -> ${ad.admitted ? 'ADMITTED (frontier improved!)' : 'rejected'}`)
      return off
    })
  await runPy(`core-credit --out ${OUT} --gen ${gen}`, CREDIT_S, `credit:g${gen}`, 'Frontier')
  const fin = await runPy(`finalize-gen --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}`, FIN_S, `finalize:g${gen}`, 'Frontier')
  curve.push({ gen: gen + 1, champion: fin.champion, fitness: fin.champion_fitness, n_admitted: fin.n_admitted })
  log(`gen ${gen} -> ${gen + 1}: ${fin.n_admitted} frontier-admitted. champion=${fin.champion} fitness=${fin.champion_fitness && fin.champion_fitness.toFixed(3)}`)
}

const bank = await runPy(`bank-status --out ${OUT}`, { type: 'object', properties: { ok: { type: 'boolean' }, bank_size: { type: 'number' }, total_wins: { type: 'number' } }, required: ['ok'] }, 'bank-final', 'Frontier')
log(`FRONTIER PROBE DONE. champion curve: ${JSON.stringify(curve.map(c => [c.gen, c.fitness && +c.fitness.toFixed(3), c.n_admitted]))}`)
return { probe: 'frontier', start_gen: START_GEN, rounds: ROUNDS, champion_curve: curve, bank_final: bank,
  note: 'Re-run cc_core.reeval afterward for contention-safe final numbers.' }
