export const meta = {
  name: 'cc-pipe-reeval-finish',
  description: 'Finish an interrupted champion re-eval: complete ONLY the missing replicates of agents lacking metrics, SEQUENTIALLY (one agent at a time, low agent count to stay under the workflow cap), then emit the full robust report. Salvages already-completed replicates.',
  phases: [{ title: 'Finish', detail: 'complete missing replicates sequentially + final report' }],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_pipe_reeval')
const SIMS_CAND = A.sims_cand ?? 60
const SEED = A.seed ?? 0
const MAXW = A.maxw ?? 6
const py = `cd ${CCROOT} && CC_MAXW=${MAXW} python3 -m cc_pipe.control_pipe`

const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, todo: { type: 'array', items: { type: 'object', properties: { label: { type: 'string' }, tag: { type: 'string' }, R: { type: 'number' }, done: { type: 'number' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' } }, required: ['label', 'R', 'done', 'roles', 'draft_model'] } } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, R_valid: { type: 'number' } }, required: ['ok'] }
const REP_S = { type: 'object', properties: { ok: { type: 'boolean' }, rows: { type: 'object' }, comparisons: { type: 'object' }, bars: { type: 'array', items: { type: 'string' } } }, required: ['ok'] }

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

const gdir = (aid) => `${OUT}/gen_00/genotypes/agent_${aid}`
function draftPrompt(aid, r, idx, model) {
  const d = gdir(aid)
  return `You are a BattleSnake CODER (model=${model.toUpperCase()}), replicate ${r} attempt ${idx}. Read the contract ` +
    `${OUT}/contracts/simple_bot_contract.txt and the strategy ${d}/prompts/draft.md . Write the strongest complete ` +
    `single-file bot you can as raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py (info/start/end/move; pure; never raises; stdlib only; fast). Return one line.`
}
function critiquePrompt(aid, r) {
  const d = gdir(aid)
  return `You are a BattleSnake bot REVIEWER (model=HAIKU). Read the current best bot ${d}/repl_${r}/best.py , the engine ` +
    `feedback ${d}/repl_${r}/feedback.json , and the critique guidance ${d}/prompts/critique.md . Name the SINGLE biggest ` +
    `concrete weakness and exactly what to change; write it with the Write tool to ${d}/repl_${r}/note.txt . Return one line.`
}
function fixPrompt(aid, r, idx) {
  const d = gdir(aid)
  return `You are a BattleSnake IMPROVER (model=HAIKU), replicate ${r}. Read the current best bot ${d}/repl_${r}/best.py , the ` +
    `engine feedback ${d}/repl_${r}/feedback.json , the critique note ${d}/repl_${r}/note.txt (if present), and the fix guidance ` +
    `${d}/prompts/fix.md . Apply the critique and fix the failures to produce an IMPROVED complete single-file bot (keep info/start/end/move; pure; never raises; stdlib only). Write raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py . Return one line.`
}

async function finishAgent(ag, phase) {
  const aid = ag.label, roles = ag.roles, model = ag.draft_model
  for (let r = ag.done; r < ag.R; r++) {
    let cand = 0
    for (const role of roles) {
      if (role === 'draft') {
        await agent(draftPrompt(aid, r, cand, model), { label: `draft:${aid}:r${r}:${cand}`, phase, model })
        await runPy(`pipe-score-cand --out ${OUT} --gen 0 --agent ${aid} --repl ${r} --cand ${cand} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SC_S, `score:${aid}:r${r}:${cand}`, phase)
        cand++
      } else if (role === 'critique') {
        await runPy(`pipe-feedback --out ${OUT} --gen 0 --agent ${aid} --repl ${r}`, FB_S, `fb:${aid}:r${r}`, phase)
        await agent(critiquePrompt(aid, r), { label: `crit:${aid}:r${r}`, phase, model: 'haiku' })
      } else {
        await runPy(`pipe-feedback --out ${OUT} --gen 0 --agent ${aid} --repl ${r}`, FB_S, `fb:${aid}:r${r}:${cand}`, phase)
        await agent(fixPrompt(aid, r, cand), { label: `fix:${aid}:r${r}:${cand}`, phase, model: 'haiku' })
        await runPy(`pipe-score-cand --out ${OUT} --gen 0 --agent ${aid} --repl ${r} --cand ${cand} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SC_S, `score:${aid}:r${r}:${cand}`, phase)
        cand++
      }
    }
  }
  const ev = await runPy(`pipe-eval-score --out ${OUT} --gen 0 --agent ${aid} --R ${ag.R} --sims-cand ${SIMS_CAND} --seed ${SEED}`, EVAL_S, `eval:${aid}`, phase)
  log(`finished [${aid}] ${ag.tag}: R8-fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'} (R_valid=${ev.R_valid}/${ag.R})`)
}

// =================================================================== RUN
phase('Finish')
const plan = await runPy(`reeval-resume-plan --out ${OUT}`, PLAN_S, 'resume-plan', 'Finish')
const TODO = plan.todo || []
log(`incomplete agents: ${TODO.map(t => `${t.label}(${t.done}/${t.R})`).join(', ') || 'none'}`)
for (const ag of TODO) await finishAgent(ag, 'Finish')   // SEQUENTIAL — one agent at a time (cap-safe, clean scoring)
const rep = await runPy(`reeval-report --out ${OUT}`, REP_S, 'report', 'Finish')
log(`RE-EVAL COMPLETE. rows=${JSON.stringify(Object.fromEntries(Object.entries(rep.rows || {}).map(([k, v]) => [k, v.mean])))}`)
return { output_dir: OUT, rows: rep.rows, comparisons: rep.comparisons, bars: rep.bars }
