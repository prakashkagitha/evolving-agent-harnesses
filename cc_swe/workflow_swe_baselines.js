export const meta = {
  name: 'cc-swe-baselines',
  description: 'Budget-matched baseline gate on SWE-bench Verified. For each reference harness (single-shot Haiku/Sonnet/Opus, best-of-N Haiku, refine-N Haiku) solve each EVAL instance by editing the repo checkout (R=1/instance), keep-best by the deployable signal (regression+repro), score by TRUE resolution (hidden FAIL_TO_PASS+PASS_TO_PASS). Establishes headroom (Haiku vs Sonnet/Opus) and whether naive budget use closes the gap.',
  phases: [{ title: 'Baselines', detail: 'init + run the selected reference harnesses on the eval split + report' }],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_swe_gate')
const N = A.N ?? 4
const NTRAIN = A.n_train ?? 30
const NEVAL = A.n_eval ?? 30
const SEED = A.seed ?? 0
const SPLIT = A.split || 'eval'
const ONLY = A.baselines || null
const REUSE_SPLIT = A.reuse_split || null   // dir with instances/{train,eval}_full.json to reuse verbatim
const MAXW = A.maxw ?? 6
const TIMEOUT = A.timeout ?? 1200
const AGENT_BUDGET = A.agent_budget ?? 850
const APPT = 'APPTAINER_CACHEDIR=/hdd/pk669/apptainer/cache APPTAINER_TMPDIR=/hdd/pk669/apptainer/tmp HF_HOME=/local-ssd/pk669/.cache/huggingface'
const py = `cd ${CCROOT} && ${APPT} CC_SWE_TIMEOUT=${TIMEOUT} python3 -m cc_swe.control_swe`
const pad3 = n => String(n).padStart(3, '0')

let nAgents = 0
const PERINST = 14
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, baselines: { type: 'array', items: { type: 'string' } }, n_eval: { type: 'number' }, n_train: { type: 'number' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' }, label: { type: 'string' } }, required: ['ok'] }
const PREP_S = { type: 'object', properties: { ok: { type: 'boolean' }, work: { type: 'string' }, already_solved: { type: 'boolean' } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_fail: { type: 'number' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, solved: { type: 'number' }, n_prob: { type: 'number' } }, required: ['ok'] }
const REP_S = { type: 'object', properties: { ok: { type: 'boolean' }, results: { type: 'object' } }, required: ['ok'] }

async function runPy(cmd, schema, label, phase, model = 'haiku') {
  const prompt = `Run ONLY this exact shell command, verbatim, with the Bash tool — nothing else:\n\`\`\`\n${py} ${cmd}\n\`\`\`\n` +
    `It prints a single JSON object on its last stdout line. Return THAT JSON object via structured output. It may take ` +
    `minutes (Apptainer test run).\nHARD RULES: Do NOT add, prefix, chain (&&/;/|), or substitute any other command. NEVER ` +
    `run rm/rmdir/rmtree, git clean, find -delete, or ANY deletion or "cleanup" — disk management is NOT your job and the ` +
    `disk has free space; a "No space left on device" error is transient. If it exits non-zero, run the SAME command once ` +
    `more; if it still fails, return {"ok": false} and stop. Never try to "reset" or "free space".`
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

const bdir = aid => `${OUT}/baselines/${aid}`
const instView = (r) => `${OUT}/instances/${SPLIT}/inst_${pad3(r)}.json`
function draftPrompt(aid, r, model, work) {
  const rd = `${bdir(aid)}/repl_${r}`
  return `You are an expert software engineer (model=${model.toUpperCase()}) fixing a real GitHub issue. Read the issue at ` +
    `${instView(r)} (problem_statement + repo). The repository is checked out at ${work} — work ONLY there: Grep/Read to ` +
    `LOCALIZE the defect, then Edit the source for the MINIMAL correct fix. Do NOT modify existing test files. ALSO write a ` +
    `standalone reproduction test as RAW python with the Write tool to ${rd}/repro_cc.py . SAFETY: use ONLY ` +
    `Read/Grep/Glob/Edit/Write inside ${work}; do NOT run git, rm, rmdir, git clean, or any deletion/cleanup, and never ` +
    `touch files outside ${work}. Return one line.`
}
function fixPrompt(aid, r, work) {
  const rd = `${bdir(aid)}/repl_${r}`
  return `You are an expert software engineer (model=HAIKU) refining a fix. The repo at ${work} ALREADY has the current ` +
    `best patch applied. Read the issue ${instView(r)} and feedback ${rd}/feedback.json , then improve the source under ` +
    `${work} (Grep/Read/Edit) so the issue is fixed without breaking tests; minimal; never edit existing tests. Update ` +
    `${rd}/repro_cc.py if needed. SAFETY: use ONLY Read/Grep/Glob/Edit/Write inside ${work}; do NOT run git, rm, rmdir, ` +
    `git clean, or any deletion/cleanup, and never touch files outside ${work}. Return one line.`
}

async function runInstance(aid, r, roles, model, phase) {
  let cand = 0
  for (const role of roles) {
    if (role === 'draft') {
      const pp = await runPy(`swe-prep --gen -1 --agent ${aid} --repl ${r} --cand ${cand} --role draft --out ${OUT} --split ${SPLIT}`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      if (pp.already_solved) { log(`i${r} already solved (resume) — reuse best.patch`); return }
      const work = pp.work || `${bdir(aid)}/repl_${r}/work`
      await agentR(draftPrompt(aid, r, model, work), { label: `draft:${aid}:i${r}:${cand}`, phase, model })
      await runPy(`swe-score-cand --gen -1 --agent ${aid} --repl ${r} --cand ${cand} --out ${OUT} --split ${SPLIT}`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
      cand++
    } else {
      await runPy(`swe-feedback --gen -1 --agent ${aid} --repl ${r} --out ${OUT} --split ${SPLIT}`, FB_S, `fb:${aid}:i${r}:${cand}`, phase)
      const pp = await runPy(`swe-prep --gen -1 --agent ${aid} --repl ${r} --cand ${cand} --role fix --out ${OUT} --split ${SPLIT}`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      const work = pp.work || `${bdir(aid)}/repl_${r}/work`
      await agentR(fixPrompt(aid, r, work), { label: `fix:${aid}:i${r}:${cand}`, phase, model: 'haiku' })
      await runPy(`swe-score-cand --gen -1 --agent ${aid} --repl ${r} --cand ${cand} --out ${OUT} --split ${SPLIT}`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
      cand++
    }
  }
}

async function runBaseline(aid, nInst, phase) {
  const plan = await runPy(`pipe-plan --out ${OUT} --gen -1 --agent ${aid} --N ${N}`, PLAN_S, `plan:${aid}`, phase)
  const roles = plan.roles || ['draft']; const model = plan.draft_model || 'haiku'
  log(`baseline ${aid} = ${plan.label} (model=${model}) over ${nInst} ${SPLIT} instances`)
  await parallel(Array.from({ length: nInst }, (_, r) => () => runInstance(aid, r, roles, model, phase)))
  const ev = await runPy(`swe-eval-score --out ${OUT} --gen -1 --agent ${aid} --n-prob ${nInst} --split ${SPLIT}`, EVAL_S, `eval:${aid}`, phase)
  log(`baseline ${aid}: resolved=${ev.solved}/${ev.n_prob} (${ev.fitness != null ? ev.fitness.toFixed(3) : '?'})`)
}

// =================================================================== RUN
phase('Baselines')
const init = await runPy(`init --out ${OUT} --N ${N} --pop 6 --survivors 3 --n-train ${NTRAIN} --n-eval ${NEVAL} --seed ${SEED} --optimizer gepa${REUSE_SPLIT ? ` --reuse-split ${REUSE_SPLIT}` : ''}`, INIT_S, 'init', 'Baselines')
const allBase = init.baselines || []
const run = ONLY ? allBase.filter(b => ONLY.includes(b)) : allBase
const nInst = init.n_eval ?? NEVAL
log(`init ok. eval=${nInst} train=${init.n_train}. running baselines: ${run.join(', ')}`)
for (const aid of run) {
  if (nAgents > AGENT_BUDGET) { log(`AGENT-BUDGET GUARD at ${nAgents} — stopping before ${aid}`); break }
  await runBaseline(aid, nInst, 'Baselines')
}
const rep = await runPy(`baseline-report --out ${OUT}`, REP_S, 'report', 'Baselines')
log(`CODE-SWE BASELINES (${SPLIT}, n=${nInst}): ${JSON.stringify(rep.results)}`)
return { output_dir: OUT, n_eval: nInst, split: SPLIT, ran: run, results: rep.results, agents: nAgents }
