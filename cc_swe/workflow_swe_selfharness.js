export const meta = {
  name: 'cc-swe-selfharness',
  description: 'Self-Harness (Zhang et al. 2026, arXiv:2606.09498) on SWE-bench Verified: a FIXED model (Haiku) improves its OWN operating harness — no stronger external model (contrast: our prior GEPA runs used a Sonnet mutator = the paper Meta-Harness baseline). Starts from a MINIMAL harness (single draft = 1-shot Haiku) and runs the paper loop each round: Weakness Mining (Haiku clusters held-in verifier-grounded failures into an evidence bundle) -> Harness Proposal (Haiku proposes K diverse-yet-minimal bounded edits to declared surfaces: role sequence, per-role prompts, system preamble, bootstrap/verification/failure_recovery instructions, runtime policy {max_tool_calls, redirect_after_calls, error_middleware}) -> Proposal Validation (each candidate solved on BOTH held-in train AND held-out eval; accept iff non-regressive d_in>=0 AND d_ho>=0 AND max>0; merge accepted edits over disjoint surfaces -> h_{t+1}). Held-out is the in-loop regression gate, never shown to the proposer. Solving/scoring reuse control_swe (Apptainer, TRUE FAIL_TO_PASS+PASS_TO_PASS resolution). RESUMABLE + cap-guarded.',
  phases: [
    { title: 'Init', detail: 'sh-init (minimal harness h0) + status' },
    { title: 'Round', detail: 'per round: solve h_t on both splits -> mine -> propose K -> solve candidates both splits -> gate -> merge' },
    { title: 'Report', detail: 'final lineage table vs reference bars' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_swe_selfharness')
const N = A.N ?? 4
const ROUNDS = A.rounds ?? 3
const K = A.K ?? 3
const NTRAIN = A.n_train ?? 28
const NEVAL = A.n_eval ?? 27
const SEED = A.seed ?? 0
const TIMEOUT = A.timeout ?? 1200
const HARD = A.agent_budget ?? 900
const PROPOSER = A.proposer || 'haiku'     // Self-Harness: the SAME fixed model improves its own harness
const MINER = A.miner || 'haiku'
const REUSE_SPLIT = A.reuse_split || null
const APPT = 'APPTAINER_CACHEDIR=/hdd/pk669/apptainer/cache APPTAINER_TMPDIR=/hdd/pk669/apptainer/tmp HF_HOME=/local-ssd/pk669/.cache/huggingface'
const baseSwe = `cd ${CCROOT} && ${APPT} CC_SWE_TIMEOUT=${TIMEOUT} python3 -m cc_swe.control_swe`
const baseSH = `cd ${CCROOT} && ${APPT} python3 -m cc_swe.control_selfharness`
const pad2 = n => String(n).padStart(2, '0')
const pad3 = n => String(n).padStart(3, '0')

let nAgents = 0

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_train: { type: 'number' }, n_eval: { type: 'number' }, rounds: { type: 'number' }, K: { type: 'number' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' }, label: { type: 'string' }, n_steps: { type: 'number' }, train_done: { type: 'boolean' }, eval_done: { type: 'boolean' }, train_solved: { type: ['number', 'null'] }, eval_solved: { type: ['number', 'null'] }, mined: { type: 'boolean' }, n_fail: { type: 'number' } }, required: ['ok', 'roles'] }
const PREP_S = { type: 'object', properties: { ok: { type: 'boolean' }, work: { type: 'string' }, instance_id: { type: 'string' }, repo: { type: 'string' }, already_solved: { type: 'boolean' } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, cand_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_fail: { type: 'number' }, summary: { type: 'string' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, solved: { type: 'number' }, n_prob: { type: 'number' } }, required: ['ok'] }
const STATUS_S = { type: 'object', properties: { ok: { type: 'boolean' }, round: { type: 'number' }, cur: { type: 'string' }, cur_gen: { type: 'number' }, rounds: { type: 'number' }, train_done: { type: 'boolean' }, eval_done: { type: 'boolean' }, train_solved: { type: ['number', 'null'] }, eval_solved: { type: ['number', 'null'] }, done: { type: 'boolean' }, label: { type: 'string' } }, required: ['ok', 'round', 'cur'] }
const CLONE_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array' } }, required: ['ok'] }
const DIFF_S = { type: 'object', properties: { ok: { type: 'boolean' }, cand_exists: { type: 'boolean' }, changed: { type: 'boolean' }, surfaces: { type: 'array' }, roles_valid: { type: 'boolean' }, roles_msg: { type: 'string' } }, required: ['ok'] }
const GATE_S = { type: 'object', properties: { ok: { type: 'boolean' }, admitted: { type: 'boolean' }, d_in: { type: ['number', 'null'] }, d_ho: { type: ['number', 'null'] }, cand_train: { type: ['number', 'null'] }, cand_eval: { type: ['number', 'null'] }, surfaces_changed: { type: 'array' }, reason: { type: 'string' } }, required: ['ok'] }
const MERGE_S = { type: 'object', properties: { ok: { type: 'boolean' }, next: { type: 'string' }, next_gen: { type: 'number' }, n_accepted: { type: 'number' }, surfaces_taken: { type: 'array' }, roles: { type: 'array' } }, required: ['ok'] }
const REPORT_S = { type: 'object', properties: { ok: { type: 'boolean' }, lineage: { type: 'array' }, baselines: { type: 'object' } }, required: ['ok'] }

async function runPy(base, cmd, schema, label, phase, model = 'haiku') {
  const prompt = `Run ONLY this exact shell command, verbatim, with the Bash tool — nothing else:\n\`\`\`\n${base} ${cmd}\n\`\`\`\n` +
    `It prints a single JSON object on its last stdout line. Return THAT JSON object via structured output. ` +
    `It may take a few minutes (it runs tests in an Apptainer container).\n` +
    `HARD RULES: Do NOT add, prefix, chain (&&/;/|), or substitute any other command. NEVER run rm/rmdir/rmtree, ` +
    `git clean, find -delete, or ANY deletion or "cleanup" — disk management is NOT your job and the disk has free ` +
    `space. A "No space left on device" error is transient. If the command exits non-zero, run the SAME command ` +
    `once more; if it still fails, return {"ok": false, "error": "<stderr tail>"} and stop. Never try to "reset" or "free space".`
  let r = null
  for (let i = 0; i < 4; i++) {
    nAgents += 1
    try { r = await agent(prompt, { label: i ? `${label}~r${i}` : label, phase, schema, model }); if (r && r.ok !== false) return r }
    catch (e) { log(`py ${label}: attempt ${i + 1} threw — retry`); r = { ok: false } }
  }
  return r || { ok: false }
}
const runSwe = (cmd, schema, label, phase) => runPy(baseSwe, cmd, schema, label, phase)
const runSH = (cmd, schema, label, phase) => runPy(baseSH, cmd, schema, label, phase)
async function agentR(promptStr, opts, tries = 4) {
  for (let i = 0; i < tries; i++) {
    nAgents += 1
    try { return await agent(promptStr, { ...opts, label: i ? `${opts.label}~r${i}` : opts.label }) }
    catch (e) { log(`agent ${opts.label}: attempt ${i + 1} threw — retry`) }
  }
  return null
}

const gdir = (gen, aid) => `${OUT}/gen_${pad2(gen)}/genotypes/agent_${aid}`
const instView = (split, r) => `${OUT}/instances/${split}/inst_${pad3(r)}.json`

// ---- harness.json injection (the workflow JS cannot read files, so each agent reads harness.json itself) ----
function harnessRule(d, slot) {
  return `Also read ${d}/harness.json and OBEY it: follow system_preamble (global rules for every step); follow the ` +
    `"${slot}" entry of instructions if non-empty; and honor runtime_policy — if max_tool_calls>0, stop exploring and ` +
    `finalize your edit within about that many tool calls; if redirect_after_calls>0, move from exploration to a concrete ` +
    `edit by then; if a tool/test error occurs and runtime_policy.error_middleware is set, follow that recovery instruction.`
}

// ---- per-instance solver prompts (4-role chain + harness.json injection) ----
function draftPrompt(gen, aid, r, split, model, work) {
  const d = gdir(gen, aid)
  return `You are the DRAFT agent (model=${model.toUpperCase()}). Read the issue at ${instView(split, r)} (problem_statement ` +
    `+ repo) and your role guidance at ${d}/prompts/draft.md . ${harnessRule(d, 'bootstrap')}\nThe repository is checked out at ` +
    `${work} — work ONLY there: Grep/Read to LOCALIZE the defect in the real source, then Edit the MINIMAL correct source fix. ` +
    `Do NOT write any test; do NOT create repro files; do NOT modify existing test files (under tests/). SAFETY: ONLY ` +
    `Read/Grep/Glob/Edit inside ${work}; never run git/rm/cleanup or touch files outside ${work}. Return one line naming the source file(s) you changed.`
}
function writeTestPrompt(gen, aid, r, split, work) {
  const d = gdir(gen, aid), rd = `${d}/repl_${r}`
  return `You are the WRITE_TEST agent (model=HAIKU) — the independent judge of the fix. Read the issue at ${instView(split, r)} , ` +
    `the repository at ${work} (read-only: Grep/Read to find the REAL public API/entry point for the buggy behavior), your role ` +
    `guidance at ${d}/prompts/write_test.md , and ${harnessRule(d, 'verification')}\nWrite a reproduction test as RAW python with ` +
    `the Write tool to ${rd}/repro_cc.py that IMPORTS and CALLS the repository's real API exercising the buggy path (NEVER ` +
    `reimplement, copy, or locally redefine the function under test), and asserts the SPECIFIC behavior the issue requires with a ` +
    `TIGHT assertion that FAILS on buggy/incomplete code and passes ONLY when truly fixed. Do NOT edit any repository source under ` +
    `${work}; write ONLY ${rd}/repro_cc.py . SAFETY: never run git/rm/cleanup. Return one line describing what behavior the test asserts.`
}
function critiquePrompt(gen, aid, r, split) {
  const d = gdir(gen, aid), rd = `${d}/repl_${r}`
  return `You are the CRITIQUE agent (model=HAIKU). Read the test feedback ${rd}/feedback.json — its "summary" field has the ACTUAL ` +
    `failure detail (did the patch apply? the reproduction test's traceback if it still fails; which regression tests broke). Also ` +
    `read the issue ${instView(split, r)} , the critique guidance ${d}/prompts/critique.md , and ${harnessRule(d, 'verification')}\n` +
    `Using the concrete errors, name the SINGLE biggest root cause and exactly what to change (file/function/lines). Write that ` +
    `diagnosis with the Write tool to ${rd}/note.txt . SAFETY: ONLY Read/Grep/Write; no git/rm/cleanup. Return one line.`
}
function fixPrompt(gen, aid, r, split, work) {
  const d = gdir(gen, aid), rd = `${d}/repl_${r}`
  return `You are the FIX agent (model=HAIKU) refining a fix. The repository at ${work} ALREADY has the current best patch applied. ` +
    `Read the issue ${instView(split, r)} , the test feedback ${rd}/feedback.json (its "summary" gives the reproduction test's actual ` +
    `error/traceback and the names of any regression tests you broke), the review note ${rd}/note.txt (if present), the fix guidance ` +
    `${d}/prompts/fix.md , and ${harnessRule(d, 'failure_recovery')}\nUse those concrete errors to make a TARGETED correction. Improve ` +
    `the source under ${work} (Grep/Read/Edit) so the reproduction test passes and no regression tests break; keep it minimal; never ` +
    `edit existing test files. Update ${rd}/repro_cc.py if needed. SAFETY: ONLY Read/Grep/Glob/Edit/Write inside ${work}; never run ` +
    `git/rm/cleanup or touch files outside ${work}. Return one line.`
}

async function runInstance(gen, aid, r, roles, model, split, phase) {
  let cand = 0, drafted = false, scoredDraft = false
  const G = `--gen ${gen} --agent ${aid} --out ${OUT} --split ${split}`
  for (const role of roles) {
    if (role === 'draft') {
      const pp = await runSwe(`swe-prep ${G} --repl ${r} --cand ${cand} --role draft`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      if (pp.already_solved) { log(`i${r} already solved (resume)`); return }
      const work = pp.work || `${gdir(gen, aid)}/repl_${r}/work`
      await agentR(draftPrompt(gen, aid, r, split, model, work), { label: `draft:${aid}:i${r}:${cand}`, phase, model })
      drafted = true
      if (!roles.includes('write_test')) {
        await runSwe(`swe-score-cand ${G} --repl ${r} --cand ${cand}`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
        scoredDraft = true; cand++
      }
    } else if (role === 'write_test') {
      const work = `${gdir(gen, aid)}/repl_${r}/work`
      await agentR(writeTestPrompt(gen, aid, r, split, work), { label: `writetest:${aid}:i${r}`, phase, model: 'haiku' })
      if (drafted && !scoredDraft) {
        await runSwe(`swe-score-cand ${G} --repl ${r} --cand 0`, SC_S, `score:${aid}:i${r}:0`, phase)
        scoredDraft = true; cand = 1
      }
    } else if (role === 'critique') {
      await runSwe(`swe-feedback ${G} --repl ${r}`, FB_S, `fb:${aid}:i${r}`, phase)
      await agentR(critiquePrompt(gen, aid, r, split), { label: `crit:${aid}:i${r}`, phase, model: 'haiku' })
    } else { // fix
      await runSwe(`swe-feedback ${G} --repl ${r}`, FB_S, `fb:${aid}:i${r}:${cand}`, phase)
      const pp = await runSwe(`swe-prep ${G} --repl ${r} --cand ${cand} --role fix`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      const work = pp.work || `${gdir(gen, aid)}/repl_${r}/work`
      await agentR(fixPrompt(gen, aid, r, split, work), { label: `fix:${aid}:i${r}:${cand}`, phase, model: 'haiku' })
      await runSwe(`swe-score-cand ${G} --repl ${r} --cand ${cand}`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
      cand++
    }
  }
}

// Solve ONE genotype dir on ONE split (dual-split gate needs each candidate solved on train AND eval, in
// separate agent dirs). Cache-gated on evals_<split>.json (sh-plan) and cap-guarded so a round can span
// multiple invocations. Returns {cached|paused|solved}.
async function solveSplit(gen, aid, split, nInst, phase) {
  const plan = await runSH(`sh-plan --out ${OUT} --gen ${gen} --agent ${aid}`, PLAN_S, `plan:${aid}:${split}`, phase)
  const done = split === 'train' ? plan.train_done : plan.eval_done
  if (done) { log(`solve CACHED [g${gen}/${aid} ${split}] solved=${split === 'train' ? plan.train_solved : plan.eval_solved}`); return { cached: true } }
  const roles = plan.roles || ['draft']; const model = plan.draft_model || 'haiku'
  const perInst = (plan.n_steps || roles.length) * 3 + 3
  if (nAgents + nInst * perInst > HARD) { log(`CAP guard before [g${gen}/${aid} ${split}] at ${nAgents} — relaunch`); return { paused: true } }
  await parallel(Array.from({ length: nInst }, (_, r) => () => runInstance(gen, aid, r, roles, model, split, phase)))
  const ev = await runSwe(`swe-eval-score --out ${OUT} --gen ${gen} --agent ${aid} --n-prob ${nInst} --split ${split}`, EVAL_S, `eval:${aid}:${split}`, phase)
  log(`solve [g${gen}/${aid} ${split}] ${plan.label} resolved=${ev.solved}/${ev.n_prob} fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'}`)
  return { cached: false, solved: ev.solved }
}

// Solve a genotype on BOTH splits (its canonical dir = train, its <id>_ev clone = eval). The _ev clone must
// already exist (sh-init creates h0_ev; sh-merge creates h{t+1}_ev; candidates clone their own _ev below).
async function solveBoth(gen, aid, phase) {
  const t = await solveSplit(gen, aid, 'train', NTRAIN, phase); if (t.paused) return { paused: true }
  const e = await solveSplit(gen, `${aid}_ev`, 'eval', NEVAL, phase); if (e.paused) return { paused: true }
  return { paused: false }
}

// ---- Self-Harness stage agents (Haiku — the SAME fixed model improves its own harness) ----
const SURFACES_DESC = `Editable harness surfaces: (A) STRUCTURE ${`${OUT}`}/<cand>/roles.json = {"roles":[<=${N} steps from ` +
  `{"draft","write_test","critique","fix"}; step0="draft"; no trailing "critique"; if you include "write_test" there must be ` +
  `EXACTLY ONE draft at index 0 and the write_test at index 1],"draft_model":"haiku"}; (B) PROMPTS <cand>/prompts/{draft,` +
  `write_test,critique,fix}.md (per-role strategy text); (C) RUNTIME/INSTRUCTIONS <cand>/harness.json = {"system_preamble":` +
  `"<global rule prepended to every step>","instructions":{"bootstrap":"<draft>","verification":"<write_test/critique>",` +
  `"failure_recovery":"<fix, applied after a tool/test error>"},"runtime_policy":{"max_tool_calls":<int, 0=off>,` +
  `"redirect_after_calls":<int, 0=off>,"error_middleware":"<instruction injected into fix on tool/test error>"}}.`

function minePrompt(gen, cur, nFail) {
  const d = gdir(gen, cur)
  return `You are the WEAKNESS-MINING stage of Self-Harness (model=${MINER.toUpperCase()}). The fixed model ran the CURRENT ` +
    `harness on the held-in (train) split; ${nFail} instances FAILED. Turn those failures into structured, reusable evidence.\n` +
    `1. Read ${d}/failures.json — a per-instance TRAJECTORY (role sequence, ordered candidate records with deployable score / ` +
    `applied / repro_pass / regression / feedback, the kept best_cand, the resolved flag = TRUE hidden-test outcome, a repro ` +
    `excerpt, and artifacts_dir).\n2. For several FAILED instances (resolved=0), OPEN the real artifacts under ` +
    `${d}/repl_<idx>/ : the candidate diffs c*.patch, the execution/test log tails c*.log, and repro_cc.py.\n` +
    `3. CLUSTER the failures by a verifier-grounded SIGNATURE = (terminal cause from the verifier, the agent behavior/causal ` +
    `status that led there, the abstract reusable MECHANISM). Group only failures that share all three.\n` +
    `Write ${d}/evidence_bundle.json with the Write tool: a JSON array (ordered by support, biggest first) of ` +
    `{"signature":{"cause":"...","behavior":"...","mechanism":"..."},"support":<#instances>,"instances":["id",...],` +
    `"symptom":"<one line>","addressable_surface":"<which editable surface could fix it: roles | prompt:<role> | preamble | ` +
    `bootstrap | verification | failure_recovery | runtime>"}. Only include clusters plausibly fixable by a harness edit (skip ` +
    `task-specific difficulty / pure model-capability limits). Return one line with the number of clusters.`
}

const FOCI = [
  `STRUCTURE — add or retype ONE step to address the dominant mechanism (e.g. add a "write_test" right after the draft so the ` +
  `fix step has a real signal to push against; or insert a "critique" before a "fix" that keeps breaking regressions). If you ` +
  `add a step, also write/strengthen that role's prompt. Respect the write_test invariant.`,
  `RUNTIME POLICY & MIDDLEWARE — set harness.json runtime_policy and the failure_recovery instruction (e.g. cap max_tool_calls / ` +
  `redirect_after_calls to stop unproductive exploration loops; set error_middleware so that after a tool/test error the model ` +
  `recreates the required artifact / fixes parsing rather than retrying or deleting). Minimal, mechanism-targeted.`,
  `PROMPTS & INSTRUCTIONS — rewrite the SINGLE weakest role prompt and/or set system_preamble / bootstrap / verification ` +
  `instructions to fix the dominant mechanism (e.g. "localize before editing", "create the required artifact early then verify ` +
  `it"). Keep every other surface unchanged.`,
]

function proposePrompt(gen, cur, cand, focus, trainSolved) {
  const cd = gdir(gen, cand), curd = gdir(gen, cur)
  return `You are the HARNESS-PROPOSAL stage of Self-Harness (model=${PROPOSER.toUpperCase()}). You improve YOUR OWN operating ` +
    `harness for fixing GitHub issues — no stronger model helps you. The candidate ${cand} currently holds an EXACT COPY of the ` +
    `current harness; edit it IN PLACE.\n` +
    `READ FIRST: the evidence bundle ${curd}/evidence_bundle.json (mined recurring held-in failure clusters), and the current ` +
    `harness ${cd}/roles.json , ${cd}/harness.json , ${cd}/prompts/{draft,write_test,critique,fix}.md . The current harness ` +
    `already solves ${trainSolved} held-in instances — your edit MUST NOT regress those (it will be rejected if it does).\n` +
    `${SURFACES_DESC}\n` +
    `Propose ONE BOUNDED, MINIMAL edit that targets a PRIMARY failure cluster from the evidence. FOCUS THIS BRANCH ON: ${focus}\n` +
    `Diversity across branches, minimality within: change ONLY the surface(s) the chosen mechanism needs; preserve everything ` +
    `else verbatim. Use the Write tool to overwrite the edited file(s) under ${cd}/ . ALSO write ${cd}/lineage.json with ` +
    `{"round":${gen},"targeted_cluster":"<signature.mechanism>","surfaces_changed":[...],"expected_effect":"...","regression_risk":"..."}.\n` +
    `MANDATE: change >=1 surface MATERIALLY versus the current harness (identical files = a FAILED proposal). Keep roles.json ` +
    `valid (step0=draft, <=${N} steps, write_test invariant, no trailing critique). Return one line naming what you changed and why.`
}

// Clone current harness -> candidate, run the proposer, and VERIFY a real+valid edit landed BEFORE the
// expensive two-split solve (Haiku proposers can silently no-op). Retry with escalation up to 4x.
async function proposeVerified(gen, cur, cand, focusIdx, trainSolved) {
  // RESUME-SAFE: check the candidate FIRST. If a valid proposal already landed (prior invocation), skip entirely —
  // do NOT re-clone (that would wipe the edit while its eval cache persists -> gate mismatch). Clone only to
  // create the candidate or to reset a partial/invalid one before (re)proposing.
  let v = await runSH(`sh-diff --out ${OUT} --cur-gen ${gen} --cur ${cur} --cand-gen ${gen} --cand ${cand}`, DIFF_S, `diff:${cand}`, 'Round')
  if (v.cand_exists && v.changed && v.roles_valid) { log(`  propose ${cand} already applied (resume): ${(v.surfaces || []).join(',')}`); return true }
  const focus = FOCI[focusIdx % FOCI.length]
  for (let t = 0; t < 4; t++) {
    // (re)clone a clean base whenever the candidate is missing or not yet a valid distinct edit
    if (!v.cand_exists || !(v.changed && v.roles_valid)) await runSH(`sh-clone --out ${OUT} --src-gen ${gen} --src ${cur} --dst-gen ${gen} --dst ${cand}`, CLONE_S, `clone:${cand}${t ? '~v' + t : ''}`, 'Round')
    const esc = t === 0 ? '' :
      `\n\nESCALATION: your previous attempt did not land a valid change (changed=${v.changed} roles_valid=${v.roles_valid} ${v.roles_msg || ''}). ` +
      `You MUST use the Write tool to overwrite >=1 surface file with materially new, valid content before returning.`
    await agentR(proposePrompt(gen, cur, cand, focus, trainSolved) + esc, { label: `propose:${cand}:f${focusIdx}${t ? '~v' + t : ''}`, phase: 'Round', model: PROPOSER })
    v = await runSH(`sh-diff --out ${OUT} --cur-gen ${gen} --cur ${cur} --cand-gen ${gen} --cand ${cand}`, DIFF_S, `diff:${cand}${t ? '~v' + t : ''}`, 'Round')
    if (v.changed && v.roles_valid) { log(`  propose ${cand} [f${focusIdx}] applied ✓ ${(v.surfaces || []).join(',')}`); return true }
    log(`  propose ${cand} [f${focusIdx}] attempt ${t + 1}: changed=${v.changed} valid=${v.roles_valid} — retry`)
  }
  log(`  ⚠ propose ${cand} FAILED to land a valid edit after 4 tries — will gate as no-op (rejected)`)
  return false
}

// =================================================================== RUN
phase('Init')
const init = await runSH(`sh-init --out ${OUT} --N ${N} --n-train ${NTRAIN} --n-eval ${NEVAL} --seed ${SEED} --rounds ${ROUNDS} --K ${K} --proposer ${PROPOSER}${REUSE_SPLIT ? ` --reuse-split ${REUSE_SPLIT}` : ''}`, INIT_S, 'sh-init', 'Init')
log(`init ok. SELF-HARNESS proposer=${PROPOSER} N=${N} rounds=${ROUNDS} K=${K} train=${init.n_train} eval=${init.n_eval}`)
let st = await runSH(`sh-status --out ${OUT} --rounds ${ROUNDS}`, STATUS_S, 'status', 'Init')
log(`status: round=${st.round} cur=${st.cur} (${st.label}) train_done=${st.train_done} eval_done=${st.eval_done} done=${st.done}`)

phase('Round')
while (st.round < ROUNDS) {
  const gen = st.round, cur = st.cur
  log(`=== ROUND ${gen}: current harness ${cur} (${st.label}) — agents so far ${nAgents} ===`)
  // 1. solve current harness on BOTH splits
  const sb = await solveBoth(gen, cur, 'Round')
  if (sb.paused) return { output_dir: OUT, phase: `round${gen}-solve-cur-paused`, agents: nAgents }
  // 2. weakness mining (held-in only) -> evidence_bundle.json
  let plan = await runSH(`sh-plan --out ${OUT} --gen ${gen} --agent ${cur}`, PLAN_S, `plan:${cur}:mine`, 'Round')
  if (!plan.mined) {
    if (plan.n_fail === 0) { log(`  round ${gen}: 0 held-in failures — nothing to mine; writing empty evidence`) }
    await agentR(minePrompt(gen, cur, plan.n_fail), { label: `mine:${cur}`, phase: 'Round', model: MINER })
    plan = await runSH(`sh-plan --out ${OUT} --gen ${gen} --agent ${cur}`, PLAN_S, `plan:${cur}:mined`, 'Round')
  }
  log(`  round ${gen}: mined=${plan.mined} held-in failures=${plan.n_fail} solved=${plan.train_solved}/${NTRAIN}`)
  // 3+4. propose K candidates, solve each on both splits
  const cands = []
  for (let j = 0; j < K; j++) {
    const cand = `c${j}`
    await proposeVerified(gen, cur, cand, j, plan.train_solved ?? 0)
    // candidate eval twin must clone the EDITED candidate genotype, then solve both splits
    await runSH(`sh-clone --out ${OUT} --src-gen ${gen} --src ${cand} --dst-gen ${gen} --dst ${cand}_ev`, CLONE_S, `clone:${cand}_ev`, 'Round')
    const cb = await solveBoth(gen, cand, 'Round')
    if (cb.paused) return { output_dir: OUT, phase: `round${gen}-solve-${cand}-paused`, agents: nAgents }
    cands.push(cand)
  }
  // 5. gate each candidate (two-split non-regressive rule)
  const accepted = []
  for (const cand of cands) {
    const g = await runSH(`sh-gate --out ${OUT} --cur-gen ${gen} --cur ${cur} --cand-gen ${gen} --cand ${cand}`, GATE_S, `gate:${cand}`, 'Round')
    log(`  gate ${cand}: d_in=${g.d_in} d_ho=${g.d_ho} surfaces=${(g.surfaces_changed || []).join(',')} -> ${g.admitted ? 'ACCEPT' : 'reject'} (${g.reason})`)
    if (g.admitted) accepted.push(cand)
  }
  // 6. merge accepted edits over disjoint surfaces -> h_{gen+1}
  const m = await runSH(`sh-merge --out ${OUT} --round ${gen} --cur-gen ${gen} --cur ${cur} --cand-gen ${gen} --accepted ${accepted.join(',')}`, MERGE_S, `merge:g${gen}`, 'Round')
  log(`  round ${gen} -> ${m.next} (${(m.roles || []).join('→')}): ${m.n_accepted} accepted, surfaces taken=${JSON.stringify(m.surfaces_taken)}`)
  st = await runSH(`sh-status --out ${OUT} --rounds ${ROUNDS}`, STATUS_S, `status:g${gen}`, 'Round')
}

// final harness: ensure it is solved on both splits (held-out number for the report)
log(`=== FINAL harness ${st.cur} (${st.label}) — solve both splits ===`)
const fb = await solveBoth(st.cur_gen, st.cur, 'Round')
if (fb.paused) return { output_dir: OUT, phase: 'final-solve-paused', agents: nAgents }

phase('Report')
const rep = await runSH(`sh-report --out ${OUT}`, REPORT_S, 'sh-report', 'Report')
const line = (rep.lineage || []).map(L => `h${L.round}[${L.label}] in=${L.train_solved}/${NTRAIN} ho=${L.eval_solved}/${NEVAL}`).join('  |  ')
log(`SELF-HARNESS DONE. lineage: ${line}`)
return { output_dir: OUT, mode: 'self-harness', proposer: PROPOSER, N, rounds: ROUNDS, K,
  lineage: rep.lineage, baselines: rep.baselines, agents: nAgents }
