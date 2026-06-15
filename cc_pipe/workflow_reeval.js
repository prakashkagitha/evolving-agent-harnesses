export const meta = {
  name: 'cc-pipe-reeval',
  description: 'Robust higher-R confirmatory re-eval of evolved champions + frontier baselines. Re-executes each champion PIPELINE (its evolved structure+prompts, copied from its source run) R times with fresh draws, scores each realization on the fixed ladder, and reports a replicate-level bootstrap CI (the honest unit) plus a two-sample pooled-game bootstrap vs robust single-shot Sonnet/Opus and best-of-8. Settles whether the N=8 0.809/0.631 point estimates hold beyond R=3.',
  phases: [
    { title: 'Setup', detail: 'stage champion + baseline genotypes into a flat gen_00' },
    { title: 'Re-exec', detail: 'run every genotype R times (keep-best chain) + ladder score' },
    { title: 'Report', detail: 'replicate-level CI + two-sample bootstrap vs frontier bars' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OUT = A.out || (CCROOT + '/cc_pipe_reeval')
const SPECS = A.specs || (CCROOT + '/cc_pipe/specs_reeval.json')
const SIMS_EVAL = A.sims_eval ?? 100
const SIMS_CAND = A.sims_cand ?? 60
const SEED = A.seed ?? 0
const MAXW = A.maxw ?? 10
const py = `cd ${CCROOT} && CC_MAXW=${MAXW} python3 -m cc_pipe.control_pipe`
const pad2 = n => String(n).padStart(2, '0')

const SETUP_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_agents: { type: 'number' }, agents: { type: 'array', items: { type: 'object', properties: { label: { type: 'string' }, tag: { type: 'string' }, draft_model: { type: 'string' }, roles: { type: 'array', items: { type: 'string' } }, R: { type: 'number' } }, required: ['label', 'draft_model', 'roles', 'R'] } } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, cand_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_fail: { type: 'number' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, R_valid: { type: 'number' }, per_rung: { type: 'object' } }, required: ['ok'] }
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
    `single-file bot you can as raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py (info/start/end/move; ` +
    `pure; never raises; stdlib only; fast). Return one line.`
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
    `${d}/prompts/fix.md . Apply the critique and fix the specific failures to produce an IMPROVED complete single-file bot ` +
    `(keep info/start/end/move; pure; never raises; stdlib only). Write raw Python (NO fences) with the Write tool to ${d}/repl_${r}/c${idx}.py . Return one line.`
}

async function reevalOne(ag, phase) {
  const aid = ag.label, roles = ag.roles, model = ag.draft_model, R = ag.R
  for (let r = 0; r < R; r++) {
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
  const ev = await runPy(`pipe-eval-score --out ${OUT} --gen 0 --agent ${aid} --R ${R} --sims-cand ${SIMS_CAND} --seed ${SEED}`, EVAL_S, `eval:${aid}`, phase)
  log(`re-eval [${aid}] ${ag.tag}: fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'} (R=${R}, R_valid=${ev.R_valid})`)
  return ev
}

// =================================================================== RUN
phase('Setup')
const setup = await runPy(`reeval-setup --out ${OUT} --specs ${SPECS} --sims-eval ${SIMS_EVAL} --sims-cand ${SIMS_CAND} --seed ${SEED}`, SETUP_S, 'setup', 'Setup')
const AG = setup.agents || []
log(`staged ${AG.length} genotypes: ${AG.map(a => `${a.label}(R${a.R})`).join(', ')}`)

phase('Re-exec')
await parallel(AG.map(ag => () => reevalOne(ag, 'Re-exec')))

phase('Report')
const rep = await runPy(`reeval-report --out ${OUT}`, REP_S, 'report', 'Report')
log(`RE-EVAL DONE. rows=${JSON.stringify(Object.fromEntries(Object.entries(rep.rows || {}).map(([k, v]) => [k, [v.mean, v.ci_lo, v.ci_hi]])))}`)
return { output_dir: OUT, rows: rep.rows, comparisons: rep.comparisons, bars: rep.bars }
