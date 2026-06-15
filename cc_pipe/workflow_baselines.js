export const meta = {
  name: 'cc-pipe-baselines',
  description: 'Headroom gate for the Haiku->Sonnet PoC: evaluate four reference pipelines on the fixed ladder at a budget of N LLM calls, R replicates each — haiku_1shot, sonnet_1shot, haiku_bestN (N drafts, keep best), haiku_refineN (draft + N-1 engine-feedback fixes). Tells us (a) headroom (Haiku-1shot vs Sonnet-1shot) and (b) whether the naive Haiku baselines already match single-shot Sonnet (the "rethink" signal) before building the pipeline evolver.',
  phases: [{ title: 'Baselines', detail: 'run the 4 reference pipelines (R replicates) + clean ladder scoring + report' }],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = (A && A.ccroot) || '/ABSOLUTE/PATH/TO/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_pipe_evo')
const N = A.N ?? 4
const R = A.R ?? 5
const SEED = A.seed ?? 0
const SIMS_EVAL = A.sims_eval ?? 100
const SIMS_CAND = A.sims_cand ?? 60
const MAXW = A.maxw ?? 12
const py = `cd ${CCROOT} && CC_MAXW=${MAXW} python3 -m cc_pipe.control_pipe`

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, N: { type: 'number' }, baselines: { type: 'array', items: { type: 'string' } } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' }, label: { type: 'string' }, exists: { type: 'boolean' } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, cand_score: { type: 'number' }, best_score: { type: 'number' }, valid: { type: 'boolean' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_fail: { type: 'number' }, summary: { type: 'string' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, R_valid: { type: 'number' }, per_rung: { type: 'object' } }, required: ['ok'] }
const REP_S = { type: 'object', properties: { ok: { type: 'boolean' }, results: { type: 'object' }, sonnet_1shot: { type: ['number', 'null'] } }, required: ['ok'] }

async function runPy(cmd, schema, label, phase, model = 'haiku') {
  const prompt = `Run EXACTLY this shell command and report its result:\n\`\`\`\n${py} ${cmd}\n\`\`\`\n` +
    `It prints a single JSON object on its last stdout line. Return THAT JSON object via structured output. ` +
    `If it exits non-zero, run it once more; if it still fails, return {"ok": false, "error": "<stderr tail>"}.`
  let r = null
  for (let i = 0; i < 4; i++) {
    try { r = await agent(prompt, { label: i ? `${label}~r${i}` : label, phase, schema, model }); if (r && r.ok !== false) return r }
    catch (e) { log(`py ${label}: attempt ${i + 1} threw — retry`); r = { ok: false } }
  }
  return r || { ok: false }
}

// gen -1 = the baselines namespace
const bdir = aid => `${OUT}/baselines/${aid}`

function draftPrompt(aid, r, idx, model) {
  const d = bdir(aid)
  return `You are a BattleSnake CODER (model=${model.toUpperCase()})${R > 1 ? `, replicate ${r}, attempt ${idx}` : ''}. Read the ` +
    `contract ${OUT}/contracts/simple_bot_contract.txt and the strategy ${d}/prompts/draft.md . Write the strongest ` +
    `complete single-file bot you can as raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py ` +
    `(define info/start/end/move; pure; never raises; stdlib only; fast). Return one line.`
}
function critiquePrompt(aid, r) {
  const d = bdir(aid)
  return `You are a BattleSnake bot REVIEWER (model=HAIKU). Read the current best bot ${d}/repl_${r}/best.py , the ` +
    `engine feedback ${d}/repl_${r}/feedback.json (failed adversarial boards: out-of-bounds / body-collision / losing ` +
    `head-to-head / crash), and the critique guidance ${d}/prompts/critique.md . Name the SINGLE biggest concrete ` +
    `weakness and exactly what to change. Write it (a few sentences) with the Write tool to ${d}/repl_${r}/note.txt . Return one line.`
}
function fixPrompt(aid, r, idx) {
  const d = bdir(aid)
  return `You are a BattleSnake DEBUGGER/IMPROVER (model=HAIKU), replicate ${r}. Read the current best bot ` +
    `${d}/repl_${r}/best.py , the engine feedback ${d}/repl_${r}/feedback.json , the critique note ${d}/repl_${r}/note.txt ` +
    `(if present), and the fix guidance ${d}/prompts/fix.md . Apply the critique and fix the specific failures in the ` +
    `feedback to produce an IMPROVED complete single-file bot (keep info/start/end/move; pure; never raises; stdlib only). ` +
    `Write raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py . Return one line.`
}

async function runPipe(aid, phase) {
  const plan = await runPy(`pipe-plan --out ${OUT} --gen -1 --agent ${aid} --N ${N}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`baseline CACHED [${aid}]`); return }
  const roles = plan.roles || ['draft']
  const model = plan.draft_model || 'haiku'
  log(`baseline ${aid} = ${plan.label} (draft_model=${model})`)
  for (let r = 0; r < R; r++) {
    let cand = 0
    for (const role of roles) {
      if (role === 'draft') {
        await agent(draftPrompt(aid, r, cand, model), { label: `draft:${aid}:r${r}:${cand}`, phase, model })
        await runPy(`pipe-score-cand --out ${OUT} --gen -1 --agent ${aid} --repl ${r} --cand ${cand} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SC_S, `score:${aid}:r${r}:${cand}`, phase)
        cand++
      } else if (role === 'critique') {
        await runPy(`pipe-feedback --out ${OUT} --gen -1 --agent ${aid} --repl ${r}`, FB_S, `fb:${aid}:r${r}`, phase)
        await agent(critiquePrompt(aid, r), { label: `crit:${aid}:r${r}`, phase, model: 'haiku' })
      } else { // fix
        await runPy(`pipe-feedback --out ${OUT} --gen -1 --agent ${aid} --repl ${r}`, FB_S, `fb:${aid}:r${r}:${cand}`, phase)
        await agent(fixPrompt(aid, r, cand), { label: `fix:${aid}:r${r}:${cand}`, phase, model: 'haiku' })
        await runPy(`pipe-score-cand --out ${OUT} --gen -1 --agent ${aid} --repl ${r} --cand ${cand} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SC_S, `score:${aid}:r${r}:${cand}`, phase)
        cand++
      }
    }
  }
  const ev = await runPy(`pipe-eval-score --out ${OUT} --gen -1 --agent ${aid} --R ${R} --sims-cand ${SIMS_CAND} --seed ${SEED}`, EVAL_S, `eval:${aid}`, phase)
  log(`baseline ${aid}: fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'} (R_valid=${ev.R_valid}) per_rung=${JSON.stringify(ev.per_rung)}`)
}

// =================================================================== RUN
phase('Baselines')
const init = await runPy(`init --out ${OUT} --N ${N} --R ${R} --sims-eval ${SIMS_EVAL} --sims-cand ${SIMS_CAND} --seed ${SEED}`, INIT_S, 'init', 'Baselines')
const BASE = init.baselines || []
log(`init ok. N=${N} budget. baselines: ${BASE.join(', ')}`)
for (const aid of BASE) await runPipe(aid, 'Baselines')
const rep = await runPy(`baseline-report --out ${OUT}`, REP_S, 'report', 'Baselines')
log(`BASELINES: ${JSON.stringify(rep.results)}`)
return { output_dir: OUT, N, R, baselines: rep.results, sonnet_1shot: rep.sonnet_1shot }
