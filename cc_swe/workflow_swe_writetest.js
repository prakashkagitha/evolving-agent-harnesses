export const meta = {
  name: 'cc-swe-writetest',
  description: 'Run ONE explicit-role SWE harness seed (draft -> write_test -> fix...) on a split and report fitness. The 4 agent types: draft = localize + minimal source fix (no test); write_test = write a RIGOROUS reproduction test that exercises the REAL repo API (the independent judge); critique = diagnose from test feedback; fix = refine source using the test traceback. The draft is NOT scored until write_test writes the test, so the deployable proxy no longer saturates at the draft and the fix steps can climb. No evolution — just solve + hidden-test fitness for the seed, to compare vs 1-shot Haiku.',
  phases: [{ title: 'Solve', detail: 'run the write_test harness seed on each instance + hidden-test fitness' }],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OUT = A.out
const N = A.N ?? 8
const SPLIT = A.split || 'eval'
const NINST = A.n_inst ?? 27
const IDS = A.ids || ['wt_seed']
const TIMEOUT = A.timeout ?? 1200
const HARD = A.agent_budget ?? 850
const APPT = 'APPTAINER_CACHEDIR=/hdd/pk669/apptainer/cache APPTAINER_TMPDIR=/hdd/pk669/apptainer/tmp HF_HOME=/local-ssd/pk669/.cache/huggingface'
const py = `cd ${CCROOT} && ${APPT} CC_SWE_TIMEOUT=${TIMEOUT} python3 -m cc_swe.control_swe`
const pad3 = n => String(n).padStart(3, '0')

let nAgents = 0
const PERINST = 16

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' }, label: { type: 'string' }, exists: { type: 'boolean' } }, required: ['ok'] }
const PREP_S = { type: 'object', properties: { ok: { type: 'boolean' }, work: { type: 'string' }, instance_id: { type: 'string' }, repo: { type: 'string' }, already_solved: { type: 'boolean' } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, cand_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_fail: { type: 'number' }, summary: { type: 'string' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, solved: { type: 'number' }, n_prob: { type: 'number' } }, required: ['ok'] }

async function runPy(cmd, schema, label, phase, model = 'haiku') {
  const prompt = `Run ONLY this exact shell command, verbatim, with the Bash tool — nothing else:\n\`\`\`\n${py} ${cmd}\n\`\`\`\n` +
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
async function agentR(promptStr, opts, tries = 4) {
  for (let i = 0; i < tries; i++) {
    nAgents += 1
    try { return await agent(promptStr, { ...opts, label: i ? `${opts.label}~r${i}` : opts.label }) }
    catch (e) { log(`agent ${opts.label}: attempt ${i + 1} threw — retry`) }
  }
  return null
}

const gdir = aid => `${OUT}/gen_00/genotypes/agent_${aid}`
const instView = r => `${OUT}/instances/${SPLIT}/inst_${pad3(r)}.json`

// ---- per-instance role prompts ----
function draftPrompt(aid, r, model, work) {
  const d = gdir(aid)
  return `You are the DRAFT agent (model=${model.toUpperCase()}). Read the issue at ${instView(r)} (problem_statement + repo) ` +
    `and your role guidance at ${d}/prompts/draft.md . The repository is checked out at ${work} — work ONLY there: use ` +
    `Grep/Read to LOCALIZE the defect in the real source, then use Edit to make the MINIMAL correct source fix. Do NOT ` +
    `write any test (a separate agent does that); do NOT create repro files. Do NOT modify existing test files (under ` +
    `tests/). SAFETY: ONLY Read/Grep/Glob/Edit inside ${work}; never run git/rm/cleanup or touch files outside ${work}. ` +
    `Return one line naming the source file(s) you changed.`
}
function writeTestPrompt(aid, r, work) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are the WRITE_TEST agent (model=HAIKU) — the independent judge of the fix. Read the issue at ${instView(r)} , ` +
    `the repository at ${work} (read-only: Grep/Read to find the REAL public API/entry point for the buggy behavior), and ` +
    `your role guidance at ${d}/prompts/write_test.md . Write a reproduction test as RAW python with the Write tool to ` +
    `${rd}/repro_cc.py that IMPORTS and CALLS the repository's real API exercising the buggy path (NEVER reimplement, copy, ` +
    `or locally redefine the function under test), and asserts the SPECIFIC behavior the issue requires with a TIGHT ` +
    `assertion that FAILS on buggy/incomplete code and passes ONLY when truly fixed. Do NOT edit any repository source under ` +
    `${work}; write ONLY ${rd}/repro_cc.py . SAFETY: never run git/rm/cleanup. Return one line describing what behavior the test asserts.`
}
function critiquePrompt(aid, r) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are the CRITIQUE agent (model=HAIKU). Read the test feedback ${rd}/feedback.json — its "summary" gives the ` +
    `reproduction test's ACTUAL error/traceback if it still fails, the names of any regression tests broken, and whether the ` +
    `patch applied. Also read the issue ${instView(r)} and ${d}/prompts/critique.md . Name the SINGLE biggest root cause and ` +
    `exactly what to change (file/function/lines). Write that diagnosis with the Write tool to ${rd}/note.txt . SAFETY: ONLY ` +
    `Read/Grep/Write; never run git/rm/cleanup. Return one line.`
}
function fixPrompt(aid, r, work) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are the FIX agent (model=HAIKU). The repository at ${work} ALREADY has the current best patch applied. Read the ` +
    `issue ${instView(r)} , the test feedback ${rd}/feedback.json (its "summary" gives the write_test reproduction test's ` +
    `actual error/traceback and the names of any regression tests you broke), the review note ${rd}/note.txt (if present), and ` +
    `${d}/prompts/fix.md . Use those concrete errors to make a TARGETED source correction under ${work} (Grep/Read/Edit) so the ` +
    `reproduction test passes and no regression tests break; keep it minimal; never edit existing test files. Do NOT edit ` +
    `${rd}/repro_cc.py (the test is fixed by write_test). SAFETY: ONLY Read/Grep/Glob/Edit inside ${work}; never run ` +
    `git/rm/cleanup or touch files outside ${work}. Return one line.`
}

async function runInstance(aid, r, roles, model, phase) {
  let cand = 0
  for (const role of roles) {
    if (role === 'draft') {
      const pp = await runPy(`swe-prep --gen 0 --agent ${aid} --repl ${r} --cand 0 --role draft --out ${OUT} --split ${SPLIT}`, PREP_S, `prep:${aid}:i${r}:0`, phase)
      if (pp.already_solved) { log(`i${r} already solved (resume) — reuse best.patch`); return }
      const work = pp.work || `${gdir(aid)}/repl_${r}/work`
      await agentR(draftPrompt(aid, r, model, work), { label: `draft:${aid}:i${r}`, phase, model })
      // NOT scored here: the draft's patch is scored by write_test against the rigorous repro test.
    } else if (role === 'write_test') {
      const work = `${gdir(aid)}/repl_${r}/work`
      await agentR(writeTestPrompt(aid, r, work), { label: `writetest:${aid}:i${r}`, phase, model: 'haiku' })
      // score the draft's source patch (cand 0) against the newly written rigorous test
      await runPy(`swe-score-cand --gen 0 --agent ${aid} --repl ${r} --cand 0 --out ${OUT} --split ${SPLIT}`, SC_S, `score:${aid}:i${r}:0`, phase)
      cand = 1
    } else if (role === 'critique') {
      await runPy(`swe-feedback --gen 0 --agent ${aid} --repl ${r} --out ${OUT} --split ${SPLIT}`, FB_S, `fb:${aid}:i${r}`, phase)
      await agentR(critiquePrompt(aid, r), { label: `crit:${aid}:i${r}`, phase, model: 'haiku' })
    } else { // fix
      await runPy(`swe-feedback --gen 0 --agent ${aid} --repl ${r} --out ${OUT} --split ${SPLIT}`, FB_S, `fb:${aid}:i${r}:${cand}`, phase)
      const pp = await runPy(`swe-prep --gen 0 --agent ${aid} --repl ${r} --cand ${cand} --role fix --out ${OUT} --split ${SPLIT}`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      const work = pp.work || `${gdir(aid)}/repl_${r}/work`
      await agentR(fixPrompt(aid, r, work), { label: `fix:${aid}:i${r}:${cand}`, phase, model: 'haiku' })
      await runPy(`swe-score-cand --gen 0 --agent ${aid} --repl ${r} --cand ${cand} --out ${OUT} --split ${SPLIT}`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
      cand++
    }
  }
}

async function runHarness(aid, phase) {
  const plan = await runPy(`pipe-plan --out ${OUT} --gen 0 --agent ${aid} --N ${N}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`harness CACHED [${aid}]`); return { cached: true } }
  if (nAgents + NINST * PERINST > HARD) { log(`CAP guard before [${aid}] at ${nAgents} — relaunch to continue`); return { paused: true } }
  const roles = plan.roles || ['draft']; const model = plan.draft_model || 'haiku'
  log(`harness [${aid}] = ${roles.join(' -> ')}`)
  await parallel(Array.from({ length: NINST }, (_, r) => () => runInstance(aid, r, roles, model, phase)))
  const ev = await runPy(`swe-eval-score --out ${OUT} --gen 0 --agent ${aid} --n-prob ${NINST} --split ${SPLIT}`, EVAL_S, `eval:${aid}`, phase)
  log(`harness [${aid}] resolved=${ev.solved}/${ev.n_prob} fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'} (${SPLIT})`)
  return { cached: false, fitness: ev.fitness }
}

// =================================================================== RUN
phase('Solve')
log(`write_test harness run: ids=${JSON.stringify(IDS)} N=${N} split=${SPLIT} n_inst=${NINST}`)
const fits = {}
for (const aid of IDS) {
  const h = await runHarness(aid, 'Solve')
  if (h.paused) { return { output_dir: OUT, phase: 'writetest-paused', done: Object.keys(fits), agents: nAgents } }
  const ev = await runPy(`swe-eval-score --out ${OUT} --gen 0 --agent ${aid} --n-prob ${NINST} --split ${SPLIT}`, EVAL_S, `evalread:${aid}`, 'Solve')
  fits[aid] = ev.fitness
}
log(`RESULT: ${IDS.map(i => `${i}=${fits[i] != null ? fits[i].toFixed(3) : '?'}`).join(' ')} (${SPLIT}) vs haiku_1shot baseline`)
return { output_dir: OUT, phase: 'writetest-done', fits, split: SPLIT, agents: nAgents }
