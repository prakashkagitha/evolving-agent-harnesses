export const meta = {
  name: 'cc-swe-variance',
  description: 'Measure R=N fitness variance of EXPLICIT pre-created genotypes on the SWE-bench train split (no init, no breeding, no heldout). Each genotype dir (gen_00/genotypes/agent_<id>) must already hold roles.json + prompts/. Solves each fresh (28 train instances, keep-best N-step chain) and reports per-genotype TRUE-resolution fitness so single-draw R=1 noise can be quantified.',
  phases: [{ title: 'Solve', detail: 'solve each replicate genotype on the train split + hidden-test fitness' }],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OUT = A.out
const N = A.N ?? 8
const NTRAIN = A.n_train ?? 28
const IDS = A.ids || ['var0', 'var1', 'var2']
const TIMEOUT = A.timeout ?? 1200
const HARD = A.agent_budget ?? 850
const APPT = 'APPTAINER_CACHEDIR=/hdd/pk669/apptainer/cache APPTAINER_TMPDIR=/hdd/pk669/apptainer/tmp HF_HOME=/local-ssd/pk669/.cache/huggingface'
const py = `cd ${CCROOT} && ${APPT} CC_SWE_TIMEOUT=${TIMEOUT} python3 -m cc_swe.control_swe`
const pad3 = n => String(n).padStart(3, '0')

let nAgents = 0
const PERINST = 14

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
const instView = r => `${OUT}/instances/train/inst_${pad3(r)}.json`

function draftPrompt(aid, r, model, work) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are an expert software engineer (model=${model.toUpperCase()}) fixing a real GitHub issue. Read the issue ` +
    `at ${instView(r)} (problem_statement + repo) AND your team's evolved strategy at ${d}/prompts/draft.md . The ` +
    `repository is checked out at ${work} — work ONLY there: use Grep/Read to LOCALIZE the defect in the source, then use ` +
    `Edit to make the MINIMAL correct fix. Do NOT modify any existing test files (anything under tests/). ALSO write a ` +
    `small standalone reproduction test (imports the repo's public API, asserts the buggy behavior is now fixed) as RAW ` +
    `python with the Write tool to ${rd}/repro_cc.py . SAFETY: use ONLY Read/Grep/Glob/Edit/Write inside ${work}; do ` +
    `NOT run git, rm, rmdir, git clean, or any deletion/cleanup, and never touch files outside ${work}. Return one line naming the file(s) you changed.`
}
function critiquePrompt(aid, r) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are a patch REVIEWER (model=HAIKU). Read the test feedback ${rd}/feedback.json — its "summary" field ` +
    `contains the ACTUAL failure detail: whether the patch applied, the reproduction test's error/traceback if it still ` +
    `fails, and the names of any regression tests your change broke. Also read the issue ${instView(r)} and the ` +
    `critique guidance ${d}/prompts/critique.md . Using the concrete errors in the feedback, name the SINGLE biggest root ` +
    `cause of the current best patch's failure and exactly what to change (which file/function/lines). Write that diagnosis ` +
    `with the Write tool to ${rd}/note.txt . SAFETY: use ONLY Read/Grep/Write; do NOT run git, rm, git clean, or any deletion/cleanup. Return one line.`
}
function fixPrompt(aid, r, work) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are an expert software engineer (model=HAIKU) refining a fix. The repository at ${work} ALREADY has the ` +
    `current best patch applied. Read the issue ${instView(r)} , the test feedback ${rd}/feedback.json (its ` +
    `"summary" gives the reproduction test's actual error/traceback and the names of any regression tests you broke), the ` +
    `review note ${rd}/note.txt (if present), and the fix guidance ${d}/prompts/fix.md . Use those concrete errors to make ` +
    `a TARGETED correction. Improve the source under ${work} ` +
    `(Grep/Read/Edit) so the reproduction test passes and no regression tests break; keep it minimal; never edit existing ` +
    `test files. Update ${rd}/repro_cc.py if needed. SAFETY: use ONLY Read/Grep/Glob/Edit/Write inside ${work}; do NOT run ` +
    `git, rm, rmdir, git clean, or any deletion/cleanup, and never touch files outside ${work}. Return one line.`
}

async function runInstance(aid, r, roles, model, phase) {
  let cand = 0
  for (const role of roles) {
    if (role === 'draft') {
      const pp = await runPy(`swe-prep --gen 0 --agent ${aid} --repl ${r} --cand ${cand} --role draft --out ${OUT} --split train`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      if (pp.already_solved) { log(`i${r} already solved (resume) — reuse best.patch`); return }
      const work = pp.work || `${gdir(aid)}/repl_${r}/work`
      await agentR(draftPrompt(aid, r, model, work), { label: `draft:${aid}:i${r}:${cand}`, phase, model })
      await runPy(`swe-score-cand --gen 0 --agent ${aid} --repl ${r} --cand ${cand} --out ${OUT} --split train`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
      cand++
    } else if (role === 'critique') {
      await runPy(`swe-feedback --gen 0 --agent ${aid} --repl ${r} --out ${OUT} --split train`, FB_S, `fb:${aid}:i${r}`, phase)
      await agentR(critiquePrompt(aid, r), { label: `crit:${aid}:i${r}`, phase, model: 'haiku' })
    } else {
      await runPy(`swe-feedback --gen 0 --agent ${aid} --repl ${r} --out ${OUT} --split train`, FB_S, `fb:${aid}:i${r}:${cand}`, phase)
      const pp = await runPy(`swe-prep --gen 0 --agent ${aid} --repl ${r} --cand ${cand} --role fix --out ${OUT} --split train`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      const work = pp.work || `${gdir(aid)}/repl_${r}/work`
      await agentR(fixPrompt(aid, r, work), { label: `fix:${aid}:i${r}:${cand}`, phase, model: 'haiku' })
      await runPy(`swe-score-cand --gen 0 --agent ${aid} --repl ${r} --cand ${cand} --out ${OUT} --split train`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
      cand++
    }
  }
}

async function runHarness(aid, phase) {
  const plan = await runPy(`pipe-plan --out ${OUT} --gen 0 --agent ${aid} --N ${N}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`replicate CACHED [${aid}]`); return { cached: true, fitness: null } }
  if (nAgents + NTRAIN * PERINST > HARD) { log(`CAP guard before [${aid}] at ${nAgents} — relaunch to continue`); return { paused: true } }
  const roles = plan.roles || ['draft']; const model = plan.draft_model || 'haiku'
  await parallel(Array.from({ length: NTRAIN }, (_, r) => () => runInstance(aid, r, roles, model, phase)))
  const ev = await runPy(`swe-eval-score --out ${OUT} --gen 0 --agent ${aid} --n-prob ${NTRAIN} --split train`, EVAL_S, `eval:${aid}`, phase)
  log(`replicate [${aid}] ${(roles || []).join('→')} resolved=${ev.solved}/${ev.n_prob} fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'}`)
  return { cached: false, fitness: ev.fitness }
}

// =================================================================== RUN
phase('Solve')
log(`variance run: ids=${JSON.stringify(IDS)} N=${N} n_train=${NTRAIN}`)
const fits = {}
for (const aid of IDS) {
  const h = await runHarness(aid, 'Solve')
  if (h.paused) { return { output_dir: OUT, phase: 'variance-paused', done: Object.keys(fits), agents: nAgents } }
  // read fitness from disk for cached ones too
  const ev = await runPy(`swe-eval-score --out ${OUT} --gen 0 --agent ${aid} --n-prob ${NTRAIN} --split train`, EVAL_S, `evalread:${aid}`, 'Solve')
  fits[aid] = ev.fitness
}
const vals = IDS.map(i => fits[i]).filter(v => v != null)
const mean = vals.reduce((a, b) => a + b, 0) / (vals.length || 1)
const mn = Math.min(...vals), mx = Math.max(...vals)
log(`VARIANCE RESULT: ${IDS.map(i => `${i}=${fits[i] != null ? fits[i].toFixed(3) : '?'}`).join(' ')} | mean=${mean.toFixed(3)} range=[${mn.toFixed(3)},${mx.toFixed(3)}] spread=${(mx - mn).toFixed(3)}`)
return { output_dir: OUT, phase: 'variance-done', fits, mean, min: mn, max: mx, spread: mx - mn, agents: nAgents }
