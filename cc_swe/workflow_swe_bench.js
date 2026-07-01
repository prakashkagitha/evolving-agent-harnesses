export const meta = {
  name: 'cc-swe-bench',
  description: 'Evaluate a fixed list of pre-staged harness genotypes on the CURATED 20-problem held-out set (cc_swe_bench_v2, eval split). Each harness dir (gen_90/genotypes/agent_<id>) holds roles.json + prompts/ + harness.json; solving reuses the 4-role chain (draft/write_test/critique/fix) with harness.json runtime/instruction injection (so the evolved Self-Harness champion is evaluated faithfully). TRUE resolution via swe-eval-score. RESUMABLE (per-split eval cache) + cap-guarded. Emits a leaderboard of resolved/N per harness.',
  phases: [{ title: 'Bench', detail: 'solve each staged harness on the curated held-out split + leaderboard' }],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_swe_bench_v2')
const GEN = A.gen ?? 90
const SPLIT = A.split || 'eval'
const NINST = A.n_inst ?? 20
const TIMEOUT = A.timeout ?? 1200
const HARD = A.agent_budget ?? 900
const HARNESSES = A.harnesses || ['haiku_1shot', 'sonnet_1shot', 'best_of_4', 'refine_4', 'wt_refine', 'sh_champ']
const APPT = 'APPTAINER_CACHEDIR=/hdd/pk669/apptainer/cache APPTAINER_TMPDIR=/hdd/pk669/apptainer/tmp HF_HOME=/local-ssd/pk669/.cache/huggingface'
const baseSwe = `cd ${CCROOT} && ${APPT} CC_SWE_TIMEOUT=${TIMEOUT} python3 -m cc_swe.control_swe`
const baseSH = `cd ${CCROOT} && ${APPT} python3 -m cc_swe.control_selfharness`
const pad3 = n => String(n).padStart(3, '0')
let nAgents = 0

const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' }, label: { type: 'string' }, n_steps: { type: 'number' }, eval_done: { type: 'boolean' }, eval_solved: { type: ['number', 'null'] } }, required: ['ok', 'roles'] }
const PREP_S = { type: 'object', properties: { ok: { type: 'boolean' }, work: { type: 'string' }, already_solved: { type: 'boolean' } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, cand_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_fail: { type: 'number' }, summary: { type: 'string' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, solved: { type: 'number' }, n_prob: { type: 'number' } }, required: ['ok'] }

async function runPy(base, cmd, schema, label, model = 'haiku') {
  const prompt = `Run ONLY this exact shell command, verbatim, with the Bash tool — nothing else:\n\`\`\`\n${base} ${cmd}\n\`\`\`\n` +
    `It prints a single JSON object on its last stdout line. Return THAT JSON object via structured output. ` +
    `It may take a few minutes (runs tests in an Apptainer container).\n` +
    `HARD RULES: Do NOT add, prefix, chain (&&/;/|), or substitute any other command. NEVER run rm/rmdir/git clean/ ` +
    `find -delete or ANY deletion/"cleanup" — disk has space; a "No space left" error is transient. If the command ` +
    `exits non-zero, run the SAME command once more; if it still fails, return {"ok": false, "error": "<stderr tail>"} and stop.`
  let r = null
  for (let i = 0; i < 4; i++) {
    nAgents += 1
    try { r = await agent(prompt, { label: i ? `${label}~r${i}` : label, phase: 'Bench', schema, model }); if (r && r.ok !== false) return r }
    catch (e) { log(`py ${label}: attempt ${i + 1} threw — retry`); r = { ok: false } }
  }
  return r || { ok: false }
}
const runSwe = (cmd, schema, label) => runPy(baseSwe, cmd, schema, label)
const runSH = (cmd, schema, label) => runPy(baseSH, cmd, schema, label)
async function agentR(promptStr, opts, tries = 4) {
  for (let i = 0; i < tries; i++) {
    nAgents += 1
    try { return await agent(promptStr, { ...opts, label: i ? `${opts.label}~r${i}` : opts.label, phase: 'Bench' }) }
    catch (e) { log(`agent ${opts.label}: attempt ${i + 1} threw — retry`) }
  }
  return null
}

const gdir = aid => `${OUT}/gen_${GEN}/genotypes/agent_${aid}`
const instView = r => `${OUT}/instances/${SPLIT}/inst_${pad3(r)}.json`
function harnessRule(d, slot) {
  return `Also read ${d}/harness.json and OBEY it: follow system_preamble (global rules); follow the "${slot}" instruction if ` +
    `non-empty; honor runtime_policy — if max_tool_calls>0, finalize within ~that many tool calls; if redirect_after_calls>0, ` +
    `move from exploration to a concrete edit by then; if a tool/test error occurs and runtime_policy.error_middleware is set, follow it.`
}
function draftPrompt(aid, r, model, work) {
  const d = gdir(aid)
  return `You are the DRAFT agent (model=${model.toUpperCase()}). Read the issue at ${instView(r)} (problem_statement + repo) and your ` +
    `role guidance at ${d}/prompts/draft.md . ${harnessRule(d, 'bootstrap')}\nThe repository is checked out at ${work} — work ONLY there: ` +
    `Grep/Read to LOCALIZE the defect in the real source, then Edit the MINIMAL correct source fix. Do NOT write any test; do NOT create ` +
    `repro files; do NOT modify existing test files (under tests/). SAFETY: ONLY Read/Grep/Glob/Edit inside ${work}; never run git/rm/cleanup. Return one line.`
}
function writeTestPrompt(aid, r, work) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are the WRITE_TEST agent (model=HAIKU) — the independent judge of the fix. Read the issue at ${instView(r)} , the repository at ` +
    `${work} (read-only), your role guidance at ${d}/prompts/write_test.md , and ${harnessRule(d, 'verification')}\nWrite a reproduction test as RAW ` +
    `python with the Write tool to ${rd}/repro_cc.py that IMPORTS and CALLS the repository's real API exercising the buggy path (NEVER reimplement/ ` +
    `copy/redefine the function under test), asserting the SPECIFIC behavior with a TIGHT assertion that FAILS on buggy code and passes ONLY when ` +
    `fixed. Do NOT edit repository source. SAFETY: never run git/rm/cleanup. Return one line.`
}
function critiquePrompt(aid, r) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are the CRITIQUE agent (model=HAIKU). Read the test feedback ${rd}/feedback.json (its "summary" has the actual failure detail), the ` +
    `issue ${instView(r)} , the critique guidance ${d}/prompts/critique.md , and ${harnessRule(d, 'verification')}\nName the SINGLE biggest root cause and ` +
    `exactly what to change (file/function/lines). Write that diagnosis with the Write tool to ${rd}/note.txt . SAFETY: ONLY Read/Grep/Write. Return one line.`
}
function fixPrompt(aid, r, work) {
  const d = gdir(aid), rd = `${d}/repl_${r}`
  return `You are the FIX agent (model=HAIKU) refining a fix. The repo at ${work} ALREADY has the current best patch applied. Read the issue ${instView(r)} , ` +
    `the test feedback ${rd}/feedback.json (its "summary" gives the reproduction test's actual error/traceback + broken regression tests), the review note ` +
    `${rd}/note.txt (if present), the fix guidance ${d}/prompts/fix.md , and ${harnessRule(d, 'failure_recovery')}\nMake a TARGETED correction under ${work} ` +
    `(Grep/Read/Edit) so the reproduction test passes and no regression tests break; keep it minimal; never edit existing test files. Update ${rd}/repro_cc.py ` +
    `if needed. SAFETY: ONLY Read/Grep/Glob/Edit/Write inside ${work}; never run git/rm/cleanup. Return one line.`
}

async function runInstance(aid, r, roles, model) {
  let cand = 0, drafted = false, scoredDraft = false
  const G = `--gen ${GEN} --agent ${aid} --out ${OUT} --split ${SPLIT}`
  for (const role of roles) {
    if (role === 'draft') {
      const pp = await runSwe(`swe-prep ${G} --repl ${r} --cand ${cand} --role draft`, PREP_S, `prep:${aid}:i${r}:${cand}`)
      if (pp.already_solved) { log(`i${r} already solved (resume)`); return }
      const work = pp.work || `${gdir(aid)}/repl_${r}/work`
      await agentR(draftPrompt(aid, r, model, work), { label: `draft:${aid}:i${r}:${cand}`, model })
      drafted = true
      if (!roles.includes('write_test')) {
        await runSwe(`swe-score-cand ${G} --repl ${r} --cand ${cand}`, SC_S, `score:${aid}:i${r}:${cand}`)
        scoredDraft = true; cand++
      }
    } else if (role === 'write_test') {
      const work = `${gdir(aid)}/repl_${r}/work`
      await agentR(writeTestPrompt(aid, r, work), { label: `writetest:${aid}:i${r}`, model: 'haiku' })
      if (drafted && !scoredDraft) {
        await runSwe(`swe-score-cand ${G} --repl ${r} --cand 0`, SC_S, `score:${aid}:i${r}:0`)
        scoredDraft = true; cand = 1
      }
    } else if (role === 'critique') {
      await runSwe(`swe-feedback ${G} --repl ${r}`, FB_S, `fb:${aid}:i${r}`)
      await agentR(critiquePrompt(aid, r), { label: `crit:${aid}:i${r}`, model: 'haiku' })
    } else {
      await runSwe(`swe-feedback ${G} --repl ${r}`, FB_S, `fb:${aid}:i${r}:${cand}`)
      const pp = await runSwe(`swe-prep ${G} --repl ${r} --cand ${cand} --role fix`, PREP_S, `prep:${aid}:i${r}:${cand}`)
      const work = pp.work || `${gdir(aid)}/repl_${r}/work`
      await agentR(fixPrompt(aid, r, work), { label: `fix:${aid}:i${r}:${cand}`, model: 'haiku' })
      await runSwe(`swe-score-cand ${G} --repl ${r} --cand ${cand}`, SC_S, `score:${aid}:i${r}:${cand}`)
      cand++
    }
  }
}

async function benchHarness(aid) {
  const plan = await runSH(`sh-plan --out ${OUT} --gen ${GEN} --agent ${aid}`, PLAN_S, `plan:${aid}`)
  if (plan.eval_done) { log(`CACHED [${aid}] ${plan.label} resolved=${plan.eval_solved}/${NINST}`); return { aid, label: plan.label, resolved: plan.eval_solved, cached: true } }
  const roles = plan.roles || ['draft']; const model = plan.draft_model || 'haiku'
  const perInst = (plan.n_steps || roles.length) * 3 + 3
  if (nAgents + NINST * perInst > HARD) { log(`CAP guard before [${aid}] at ${nAgents} — relaunch`); return { paused: true } }
  await parallel(Array.from({ length: NINST }, (_, r) => () => runInstance(aid, r, roles, model)))
  const ev = await runSwe(`swe-eval-score --out ${OUT} --gen ${GEN} --agent ${aid} --n-prob ${NINST} --split ${SPLIT}`, EVAL_S, `eval:${aid}`)
  log(`[${aid}] ${plan.label} resolved=${ev.solved}/${ev.n_prob} (${((ev.solved / ev.n_prob) || 0).toFixed(3)})`)
  return { aid, label: plan.label, resolved: ev.solved, cached: false }
}

// =================================================================== RUN
phase('Bench')
log(`bench: curated held-out (${SPLIT}, ${NINST} instances). harnesses: ${HARNESSES.join(', ')}`)
const results = []
for (const aid of HARNESSES) {
  const r = await benchHarness(aid)
  if (r.paused) return { output_dir: OUT, phase: 'bench-paused', done: results, agents: nAgents }
  results.push(r)
}
results.sort((a, b) => (b.resolved ?? -1) - (a.resolved ?? -1))
log(`\n=== LEADERBOARD (curated ${NINST}-problem held-out) ===`)
for (const r of results) log(`  ${String(r.resolved).padStart(2)}/${NINST} (${((r.resolved / NINST) || 0).toFixed(3)})  ${r.aid} [${r.label}]`)
return { output_dir: OUT, n_inst: NINST, leaderboard: results, agents: nAgents }
