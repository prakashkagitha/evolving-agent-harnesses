export const meta = {
  name: 'cc-swe-evolve',
  description: 'Evolve a budget-N Haiku self-correction harness on SWE-bench Verified with GEPA or CORE. Genotype = role sequence in {draft,critique,fix} (step0=draft) + per-role strategy prompt; structure+prompts evolve via a Sonnet mutator. Per TRAIN instance the agent EDITS a host checkout (Read/Grep/Edit/Bash) to fix the issue + writes a reproduction test; controller derives the patch via git diff and scores it by a DEPLOYABLE signal (regression sample + repro test) for keep-best; FITNESS = TRUE resolution (hidden FAIL_TO_PASS+PASS_TO_PASS) on the train set (R=1/instance). Two-sample bootstrap admit gate over per-instance resolved. RESUMABLE + cap-guarded; a final launch runs the champion on the HELD-OUT eval split.',
  phases: [
    { title: 'Init', detail: 'init-if-needed + resumability probe' },
    { title: 'Gen0', detail: 'solve train instances with each seed harness + hidden-test resolution scoring' },
    { title: 'Evolve', detail: 'per gen: select -> [CORE reflect] -> Sonnet mutate -> solve+score -> bootstrap gate -> finalize' },
    { title: 'Heldout', detail: 'run the champion on the held-out eval split + final-compare' },
  ],
}

let A = {}
try { A = (typeof args === 'string') ? JSON.parse(args) : (args || {}) } catch (e) { A = {} }
const CCROOT = A.ccroot || '/local-ssd/pk669/programming/co-evolution/evolving-agent-harnesses'
const OPT = (A.optimizer === 'core') ? 'core' : 'gepa'
const OUT = A.out || (CCROOT + '/cc_swe_evo_' + OPT)
const N = A.N ?? 4
const GEN = A.generations ?? 3
const POP = A.pop ?? 6
const SURVIVORS = A.survivors ?? 3
const NTRAIN = A.n_train ?? 30
const NEVAL = A.n_eval ?? 30
const SEED = A.seed ?? 0
const PAIRS = A.pairs ?? SURVIVORS
const TOPK = A.topk ?? 3
const MAX_LESSONS = A.max_lessons ?? 4
const MAXW = A.maxw ?? 6
const TIMEOUT = A.timeout ?? 1200
const HARD = A.agent_budget ?? 850
const REFLECT = 'sonnet'
const REUSE_SPLIT = A.reuse_split || null   // dir with instances/{train,eval}_full.json to reuse verbatim
const GBREED = A.breed_topfit ? 'breed-plan-gepa-topfit' : 'breed-plan-gepa'  // topfit: mutate only from max-fitness parent(s)
const COMBINE = !!A.combine_mut   // every mutation changes STRUCTURE + one ROLE PROMPT together (co-evolution)
const APPT = 'APPTAINER_CACHEDIR=/hdd/pk669/apptainer/cache APPTAINER_TMPDIR=/hdd/pk669/apptainer/tmp HF_HOME=/local-ssd/pk669/.cache/huggingface'
const py = `cd ${CCROOT} && ${APPT} CC_SWE_TIMEOUT=${TIMEOUT} python3 -m cc_swe.control_swe`
const pad2 = n => String(n).padStart(2, '0')
const pad3 = n => String(n).padStart(3, '0')

let nAgents = 0
const PERINST = 14            // ~agents per instance solve (prep/agent/score across N steps) for cap guards
const genCost = nOff => nOff * NTRAIN * PERINST + 40
const heldoutCost = () => NEVAL * PERINST + 40

const OK = { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] }
const INIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, seed_ids: { type: 'array', items: { type: 'string' } }, seed_labels: { type: 'object' }, n_train: { type: 'number' }, n_eval: { type: 'number' } }, required: ['ok'] }
const STATUS_S = { type: 'object', properties: { ok: { type: 'boolean' }, next_gen: { type: 'number' }, gen0_done: { type: 'boolean' }, all_done: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] }, heldout_done: { type: 'boolean' } }, required: ['ok'] }
const PLAN_S = { type: 'object', properties: { ok: { type: 'boolean' }, roles: { type: 'array', items: { type: 'string' } }, draft_model: { type: 'string' }, label: { type: 'string' }, exists: { type: 'boolean' } }, required: ['ok'] }
const PREP_S = { type: 'object', properties: { ok: { type: 'boolean' }, work: { type: 'string' }, instance_id: { type: 'string' }, repo: { type: 'string' }, already_solved: { type: 'boolean' } }, required: ['ok'] }
const SC_S = { type: 'object', properties: { ok: { type: 'boolean' }, cand_score: { type: 'number' }, best_score: { type: 'number' } }, required: ['ok'] }
const FB_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_fail: { type: 'number' }, summary: { type: 'string' } }, required: ['ok'] }
const EVAL_S = { type: 'object', properties: { ok: { type: 'boolean' }, fitness: { type: 'number' }, solved: { type: 'number' }, n_prob: { type: 'number' } }, required: ['ok'] }
const SCORE_S = { type: 'object', properties: { ok: { type: 'boolean' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok'] }
const SEL_S = { type: 'object', properties: { ok: { type: 'boolean' }, survivors: { type: 'array', items: { type: 'string' } }, champion: { type: ['string', 'null'] } }, required: ['ok'] }
const BREED_S = { type: 'object', properties: { ok: { type: 'boolean' }, plan: { type: 'array', items: { type: 'object', properties: { new_id: { type: 'string' }, parent_id: { type: 'string' }, parent_gen: { type: 'number' }, lens: { type: 'string' }, exists: { type: 'boolean' }, parent_fit: { type: 'number' } }, required: ['new_id', 'parent_id', 'parent_gen', 'lens', 'exists'] } } }, required: ['ok', 'plan'] }
const ADMIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, admitted: { type: 'boolean' }, delta: { type: ['number', 'null'] }, ci_low: { type: ['number', 'null'] }, ci_high: { type: ['number', 'null'] } }, required: ['ok'] }
const FIN_S = { type: 'object', properties: { ok: { type: 'boolean' }, ids: { type: 'array', items: { type: 'string' } }, n_admitted: { type: 'number' }, champion: { type: ['string', 'null'] }, champion_fitness: { type: ['number', 'null'] } }, required: ['ok', 'ids'] }
const REFLECT_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_pairs: { type: 'number' }, plan: { type: 'array' } }, required: ['ok', 'plan'] }
const INGEST_S = { type: 'object', properties: { ok: { type: 'boolean' }, added: { type: 'number' }, merged: { type: 'number' }, bank_size: { type: 'number' } }, required: ['ok'] }
const CREDIT_S = { type: 'object', properties: { ok: { type: 'boolean' }, n_credited: { type: 'number' }, bank_size: { type: 'number' } }, required: ['ok'] }
const BANK_S = { type: 'object', properties: { ok: { type: 'boolean' }, bank_size: { type: 'number' } }, required: ['ok'] }
const HE_S = { type: 'object', properties: { ok: { type: 'boolean' }, agent: { type: 'string' }, roles: { type: 'array', items: { type: 'string' } }, n_eval: { type: 'number' } }, required: ['ok'] }
const MUT_S = { type: 'object', properties: { ok: { type: 'boolean' }, changed: { type: 'boolean' }, valid: { type: 'boolean' }, kind: { type: 'string' }, detail: { type: 'string' } }, required: ['ok'] }

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

const gdir = (gen, aid) => `${OUT}/gen_${pad2(gen)}/genotypes/agent_${aid}`
const instView = (split, r) => `${OUT}/instances/${split}/inst_${pad3(r)}.json`

// ---- per-instance solver prompts (agent EDITS the host checkout; controller derives the patch) ----
function draftPrompt(gen, aid, r, split, model, work) {
  const d = gdir(gen, aid)
  return `You are the DRAFT agent (model=${model.toUpperCase()}). Read the issue at ${instView(split, r)} (problem_statement ` +
    `+ repo) and your role guidance at ${d}/prompts/draft.md . The repository is checked out at ${work} — work ONLY there: ` +
    `use Grep/Read to LOCALIZE the defect in the real source, then use Edit to make the MINIMAL correct source fix. Do NOT ` +
    `write any test (a separate write_test agent does that); do NOT create repro files. Do NOT modify existing test files ` +
    `(under tests/). SAFETY: ONLY Read/Grep/Glob/Edit inside ${work}; never run git/rm/cleanup or touch files outside ${work}. ` +
    `Return one line naming the source file(s) you changed.`
}
function writeTestPrompt(gen, aid, r, split, work) {
  const d = gdir(gen, aid), rd = `${d}/repl_${r}`
  return `You are the WRITE_TEST agent (model=HAIKU) — the independent judge of the fix. Read the issue at ${instView(split, r)} , ` +
    `the repository at ${work} (read-only: Grep/Read to find the REAL public API/entry point for the buggy behavior), and your ` +
    `role guidance at ${d}/prompts/write_test.md . Write a reproduction test as RAW python with the Write tool to ` +
    `${rd}/repro_cc.py that IMPORTS and CALLS the repository's real API exercising the buggy path (NEVER reimplement, copy, or ` +
    `locally redefine the function under test), and asserts the SPECIFIC behavior the issue requires with a TIGHT assertion that ` +
    `FAILS on buggy/incomplete code and passes ONLY when truly fixed. Do NOT edit any repository source under ${work}; write ` +
    `ONLY ${rd}/repro_cc.py . SAFETY: never run git/rm/cleanup. Return one line describing what behavior the test asserts.`
}
function critiquePrompt(gen, aid, r, split) {
  const d = gdir(gen, aid), rd = `${d}/repl_${r}`
  return `You are a patch REVIEWER (model=HAIKU). Read the test feedback ${rd}/feedback.json — its "summary" field ` +
    `contains the ACTUAL failure detail: whether the patch applied, the reproduction test's error/traceback if it still ` +
    `fails, and the names of any regression tests your change broke. Also read the issue ${instView(split, r)} and the ` +
    `critique guidance ${d}/prompts/critique.md . Using the concrete errors in the feedback, name the SINGLE biggest root ` +
    `cause of the current best patch's failure and exactly what to change (which file/function/lines). Write that diagnosis ` +
    `with the Write tool to ${rd}/note.txt . SAFETY: use ONLY Read/Grep/Write; do NOT run git, rm, git clean, or any deletion/cleanup. Return one line.`
}
function fixPrompt(gen, aid, r, split, work) {
  const d = gdir(gen, aid), rd = `${d}/repl_${r}`
  return `You are an expert software engineer (model=HAIKU) refining a fix. The repository at ${work} ALREADY has the ` +
    `current best patch applied. Read the issue ${instView(split, r)} , the test feedback ${rd}/feedback.json (its ` +
    `"summary" gives the reproduction test's actual error/traceback and the names of any regression tests you broke), the ` +
    `review note ${rd}/note.txt (if present), and the fix guidance ${d}/prompts/fix.md . Use those concrete errors to make ` +
    `a TARGETED correction. Improve the source under ${work} ` +
    `(Grep/Read/Edit) so the reproduction test passes and no regression tests break; keep it minimal; never edit existing ` +
    `test files. Update ${rd}/repro_cc.py if needed. SAFETY: use ONLY Read/Grep/Glob/Edit/Write inside ${work}; do NOT run ` +
    `git, rm, rmdir, git clean, or any deletion/cleanup, and never touch files outside ${work}. Return one line.`
}

async function runInstance(gen, aid, r, roles, model, split, phase) {
  // 4-role chain. The DRAFT edits source but is NOT scored until a write_test writes the rigorous test
  // (so the deployable proxy isn't fed a neutral/self-satisfying repro). write_test then scores the draft's
  // patch (cand 0) against that test; fixes refine source using the test feedback. (Seeds without a write_test
  // step fall back to scoring the draft immediately, repro=neutral — legacy behavior.)
  let cand = 0, drafted = false, scoredDraft = false
  for (const role of roles) {
    if (role === 'draft') {
      const pp = await runPy(`swe-prep --gen ${gen} --agent ${aid} --repl ${r} --cand ${cand} --role draft --out ${OUT} --split ${split}`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      if (pp.already_solved) { log(`i${r} already solved (resume) — reuse best.patch`); return }
      const work = pp.work || `${gdir(gen, aid)}/repl_${r}/work`
      await agentR(draftPrompt(gen, aid, r, split, model, work), { label: `draft:${aid}:i${r}:${cand}`, phase, model })
      drafted = true
      // If no write_test step exists in this genotype, score the draft now (legacy, repro=neutral).
      if (!roles.includes('write_test')) {
        await runPy(`swe-score-cand --gen ${gen} --agent ${aid} --repl ${r} --cand ${cand} --out ${OUT} --split ${split}`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
        scoredDraft = true; cand++
      }
    } else if (role === 'write_test') {
      const work = `${gdir(gen, aid)}/repl_${r}/work`
      await agentR(writeTestPrompt(gen, aid, r, split, work), { label: `writetest:${aid}:i${r}`, phase, model: 'haiku' })
      // score the draft's source patch (cand 0) against the newly written rigorous test (once)
      if (drafted && !scoredDraft) {
        await runPy(`swe-score-cand --gen ${gen} --agent ${aid} --repl ${r} --cand 0 --out ${OUT} --split ${split}`, SC_S, `score:${aid}:i${r}:0`, phase)
        scoredDraft = true; cand = 1
      }
    } else if (role === 'critique') {
      await runPy(`swe-feedback --gen ${gen} --agent ${aid} --repl ${r} --out ${OUT} --split ${split}`, FB_S, `fb:${aid}:i${r}`, phase)
      await agentR(critiquePrompt(gen, aid, r, split), { label: `crit:${aid}:i${r}`, phase, model: 'haiku' })
    } else { // fix
      await runPy(`swe-feedback --gen ${gen} --agent ${aid} --repl ${r} --out ${OUT} --split ${split}`, FB_S, `fb:${aid}:i${r}:${cand}`, phase)
      const pp = await runPy(`swe-prep --gen ${gen} --agent ${aid} --repl ${r} --cand ${cand} --role fix --out ${OUT} --split ${split}`, PREP_S, `prep:${aid}:i${r}:${cand}`, phase)
      const work = pp.work || `${gdir(gen, aid)}/repl_${r}/work`
      await agentR(fixPrompt(gen, aid, r, split, work), { label: `fix:${aid}:i${r}:${cand}`, phase, model: 'haiku' })
      await runPy(`swe-score-cand --gen ${gen} --agent ${aid} --repl ${r} --cand ${cand} --out ${OUT} --split ${split}`, SC_S, `score:${aid}:i${r}:${cand}`, phase)
      cand++
    }
  }
}

async function runHarness(gen, aid, split, nInst, phase) {
  const plan = await runPy(`pipe-plan --out ${OUT} --gen ${gen} --agent ${aid} --N ${N}`, PLAN_S, `plan:${aid}`, phase)
  if (plan.exists) { log(`harness CACHED [g${gen}/${aid}]`); return { cached: true } }
  // PER-HARNESS cap guard: one N-step harness over nInst instances is the chunking unit. The runtime caps
  // a workflow invocation at ~1000 agents, and at N=8 one full generation exceeds that — so we pause BEFORE
  // solving an uncached harness if the budget would be exceeded, and resume it next invocation (per-instance
  // already_solved + per-instance eval cache make the resume free).
  if (nAgents + nInst * PERINST > HARD) { log(`CAP guard before [g${gen}/${aid}] at ${nAgents} — relaunch to continue`); return { paused: true } }
  const roles = plan.roles || ['draft']; const model = plan.draft_model || 'haiku'
  await parallel(Array.from({ length: nInst }, (_, r) => () => runInstance(gen, aid, r, roles, model, split, phase)))
  const ev = await runPy(`swe-eval-score --out ${OUT} --gen ${gen} --agent ${aid} --n-prob ${nInst} --split ${split}`, EVAL_S, `eval:${aid}`, phase)
  log(`harness [g${gen}/${aid}] ${plan.label} resolved=${ev.solved}/${ev.n_prob} fitness=${ev.fitness != null ? ev.fitness.toFixed(3) : '?'} (${split})`)
  return { cached: false, fitness: ev.fitness }
}

// ---- mutation agents (SWE-domain) ----
const GENO_DESC = `The genotype is a budget-${N} self-correction harness for fixing a GitHub issue in a repo: roles.json = ` +
  `{"roles":[${N} steps each "draft"|"critique"|"fix"; step0="draft", no trailing "critique"],"draft_model":"haiku"} + a ` +
  `strategy prompt per role at prompts/{draft,critique,fix}.md. Execution per instance is a keep-best chain: draft/fix edit ` +
  `the repo checkout + write a reproduction test (scored by a deployable signal = regression sample + repro test); critique ` +
  `reads the test feedback and writes a diagnosis the next fix uses. The child already CONTAINS the parent's files — edit in place.`

function gepaMutate(gen, off) {
  const pd = gdir(off.parent_gen, off.parent_id), cd = gdir(off.parent_gen + 1, off.new_id)
  // REFLECT-FIRST: the mutator must read the parent's per-instance failure digest and diagnose RECURRING
  // failure modes before changing anything — this is what makes the mutation reflective rather than a blind paraphrase.
  const reflect = `REFLECT FIRST — reconstruct the TRAJECTORY STORY before changing anything:\n` +
    `1. Read ${pd}/metrics.json (aggregate) AND ${pd}/failures.json — a per-train-instance TRAJECTORY: the role sequence ` +
    `(structure), the ORDERED candidate records (each step's deployable score, applied / repro_pass / regression, and ` +
    `feedback), the kept best_cand, the resolved flag (TRUE hidden-test outcome), and a repro-test excerpt.\n` +
    `2. For the FAILED instances (resolved=0), especially recurring ones, OPEN THE ACTUAL ARTIFACTS under ${pd}/repl_<idx>/ ` +
    `(the failures.json "artifacts_dir"): the candidate diffs c0.patch, c1.patch, … (what each draft/fix step actually ` +
    `changed in the source), c<cand>.log (the REAL execution/test log tail), and repro_cc.py (the test that was run). Read ` +
    `several of them — do not rely on the summary alone.\n` +
    `3. Read the parent genotype: ${pd}/roles.json and ${pd}/prompts/{draft,write_test,critique,fix}.md .\n` +
    `4. Tell the TRAJECTORY STORY of the recurring failures: how did the STRUCTURE shape what the LLM produced and refined, ` +
    `and WHERE in the chain (which role/step) and WHY did it fall short? e.g. "the draft (c0.patch) localized to the wrong ` +
    `function; write_test wrote a trivially-passing test (repro_cc.py) so the deployable score saturated at c0 and the fix ` +
    `steps had nothing to push against; the hidden test failed because required behavior X was never implemented (c<best>.log)". ` +
    `Your mutation (structure + prompts) MUST target those concrete trajectory failures — cite them in lineage.json "diff".`
  if (COMBINE) {
    const role = off.lens   // a prompt role used only as a soft focus to keep sibling offspring diverse
    return `You are an OUTER-OPTIMIZER doing a COMBINED mutation (model=SONNET) evolving a budget-${N} SWE-bench ` +
      `self-correction harness. ${GENO_DESC}\n${reflect}\nNow make a COHERENT change with FULL FREEDOM — the prompt edits ` +
      `must exploit the new structure, all targeting the failure modes you found:\n` +
      `(A) STRUCTURE — use the Write tool to OVERWRITE ${cd}/roles.json with {"roles":[...],"draft_model":"haiku"} whose ` +
      `sequence DIFFERS from the parent's (keep ${N} steps, step0="draft", step types from {draft,write_test,critique,fix}, ` +
      `no trailing "critique"). HARD RULE: if you include a write_test, there must be EXACTLY ONE draft (at index 0) and the ` +
      `write_test must be at index 1 (right after the draft) — NO extra draft and NO fix before the write_test (the harness ` +
      `scores the single draft against that test). You may instead drop write_test for a no-test structure. E.g. swap a fix ` +
      `for a critique before a fix that breaks regressions; add/remove a trailing fix; toggle the write_test on/off.\n` +
      `(B) PROMPTS — you have FULL FREEDOM to rewrite ANY OR ALL of the role prompts ${cd}/prompts/{draft,write_test,critique,` +
      `fix}.md — rewrite as many as the failures warrant (you MAY rewrite all four in one mutation). Use the Write tool for ` +
      `each. Make each rewritten prompt materially better, coherent with the new structure, and targeted at the recurring ` +
      `failures (draft: localize + minimal correct edit; write_test: a test that exercises the REAL repo API and fails on ` +
      `incomplete fixes; critique: pin the root cause from feedback; fix: apply feedback + guard regressions). Improve on the ` +
      `parent's prompts; don't discard what works. (Sibling offspring should differ — this one may emphasize the "${role}" ` +
      `role, but you are not restricted to it.)\n` +
      `MANDATE: change SOMETHING materially versus the parent — the structure (roles.json) AND/OR one or more role prompts ` +
      `(the child currently holds exact copies of the parent's files). STRONGLY PREFER changing BOTH structure and prompts ` +
      `when the failures warrant it, but a prompt-only or structure-only change is acceptable. Making NO change at all ` +
      `(identical roles.json AND identical prompts) = a FAILED mutation. ALSO write ${cd}/lineage.json "diff" naming the ` +
      `failure mode(s) you targeted and which components you changed. Return one line.`
  }
  if (off.lens === 'structure') {
    return `You are an OUTER-OPTIMIZER STRUCTURE lens (model=SONNET) evolving a budget-${N} SWE-bench self-correction ` +
      `harness. ${GENO_DESC}\n${reflect}\nThen make ONE structural change to ${cd}/roles.json that addresses the dominant ` +
      `failure mode: retype/reorder a single step (keep ${N} steps, step0="draft", no trailing "critique") — e.g. if fixes ` +
      `break regressions, insert a "critique" before a "fix"; if localization is wrong, add a "draft" for a second ` +
      `independent attempt; if drafts are already strong, convert a redundant draft into a "fix" to refine. Write valid JSON ` +
      `{"roles":[...],"draft_model":"haiku"} to ${cd}/roles.json. ALSO write ${cd}/lineage.json "diff" naming the failure ` +
      `mode you targeted.\nMANDATE: the child currently holds an EXACT COPY of the parent's roles.json (the sequence you ` +
      `read in step 2). You MUST use the Write tool to overwrite ${cd}/roles.json with a role sequence that DIFFERS from ` +
      `that parent sequence (keep ${N} steps, step0="draft", no trailing "critique"). An identical sequence is a FAILED ` +
      `mutation. Return one line.`
  }
  const role = off.lens
  return `You are an OUTER-OPTIMIZER lens = "${role}" (model=SONNET) evolving a budget-${N} SWE-bench self-correction ` +
    `harness. ${GENO_DESC}\n${reflect}\nThen rewrite ONLY the "${role}" strategy prompt at ${cd}/prompts/${role}.md so it ` +
    `directly prevents the recurring failure modes you found (for "draft": better localization + a reproduction test that ` +
    `truly captures the issue's required behavior + minimal correct edit; "critique": pin the real root cause from the ` +
    `repro/regression errors in the feedback; "fix": apply the critique and resolve regressions with guards rather than ` +
    `reverting). Improve on the parent's existing prompt (don't discard what works). ALSO write ${cd}/lineage.json "diff" ` +
    `naming the failure mode(s) you targeted.\nMANDATE: the child currently holds an EXACT COPY of the parent's ` +
    `${role}.md (the prompt you read in step 2). You MUST use the Write tool to OVERWRITE ${cd}/prompts/${role}.md with a ` +
    `materially revised prompt — concrete new instructions that target the failure modes, not a paraphrase and not ` +
    `unchanged text. Writing identical or trivially-different text is a FAILED mutation. The Write is the deliverable; do ` +
    `it before you return. Return one line.`
}
function coreReflect(p) {
  return `You are a CONTRASTIVE-REFLECTION analyst (model=SONNET) studying how to design a budget-${N} SWE-bench ` +
    `self-correction harness (roles in {draft,critique,fix} + a prompt per role). Two harnesses were each run on the SAME ` +
    `train issues:\n[WINNER] (resolved ${p.winner_fitness}, shape ${p.winner_label}) — ${p.winner_dir}/ , metrics ${p.winner_dir}/metrics.json\n` +
    `[LOSER] (resolved ${p.loser_fitness}, shape ${p.loser_label}) — ${p.loser_dir}/ , metrics ${p.loser_dir}/metrics.json\n` +
    `LOSER profile: ${p.weakness}\n\nRead both harnesses' roles.json + prompts/*.md + metrics. Which difference — the role ` +
    `SHAPE or a role PROMPT — most plausibly caused the gap? Distil EXACTLY ${MAX_LESSONS} short INSIGHTS about SWE harness ` +
    `design (e.g. "localize before editing", "write the reproduction test first", "critique-before-fix beats blind fix", ` +
    `"keep edits minimal to avoid regressions"). Write a JSON array of ${MAX_LESSONS} objects {"lesson":"<=30 words","label":` +
    `"specific"|"meta"} with the Write tool to ${p.lessons_path} (valid JSON, no fences). Return one line.`
}
function coreMutate(gen, off) {
  const cd = gdir(off.parent_gen + 1, off.new_id)
  return `You are a CORE MUTATION operator (model=SONNET) evolving a budget-${N} SWE-bench self-correction harness. ` +
    `${GENO_DESC}\nRETRIEVED INSIGHTS (read ${cd}/breed_context.json). Apply the most relevant insight(s) by editing the ` +
    `child in place: change ${cd}/roles.json (shape — keep ${N} steps, step0="draft", no trailing critique) AND/OR rewrite ` +
    `one role prompt at ${cd}/prompts/<role>.md. ALSO update ${cd}/lineage.json "changed_components"+"diff" (+insight ids); ` +
    `keep "lessons_used".\nMANDATE: the child currently holds an EXACT COPY of the parent's genotype. You MUST use the ` +
    `Write tool to materially change at least the targeted component (roles.json OR a prompt) — identical files are a ` +
    `FAILED mutation. The Write is the deliverable. Return one line.`
}

// Run the mutation agent and VERIFY the change actually landed on disk (the agent can silently no-op by
// returning an ack without writing — that left every surviving genotype a byte-identical clone of its parent
// in the first run, so "evolution" selected over identical harnesses). Loop mutate->verify with escalation
// until the mutated component differs from the parent (and is valid); fail loudly if it never does. The
// initial verify makes this idempotent/resumable: an already-mutated child returns immediately, no agent call.
async function mutateVerified(gen, off) {
  const ng = off.parent_gen + 1
  const mutChk = lbl => runPy(`mut-verify --out ${OUT} --gen ${ng} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id} --lens ${off.lens}${COMBINE ? ' --combined' : ''}`, MUT_S, lbl, 'Evolve')
  let v = await mutChk(`mutchk:${off.new_id}`)
  if (v.changed && v.valid) { log(`  mutate ${off.new_id} [${off.lens}] already applied (resume): ${v.detail || ''}`); return true }
  for (let t = 0; t < 4; t++) {
    const esc = t === 0 ? '' :
      `\n\nESCALATION: your previous attempt did NOT land a valid change (verify: changed=${v.changed} valid=${v.valid}; ${v.detail || ''}). ` +
      `You MUST now use the Write tool to OVERWRITE the target file with materially new, valid content before returning. This is mandatory.`
    const base = OPT === 'core' ? coreMutate(gen, off) : gepaMutate(gen, off)
    await agentR(base + esc, { label: `mutate:${off.new_id}:${off.lens}${t ? '~v' + t : ''}`, phase: 'Evolve', model: REFLECT })
    v = await mutChk(`mutchk:${off.new_id}${t ? '~v' + t : ''}`)
    if (v.changed && v.valid) { log(`  mutate ${off.new_id} [${off.lens}] applied ✓ ${v.detail || ''}`); return true }
    log(`  mutate ${off.new_id} [${off.lens}] attempt ${t + 1}: changed=${v.changed} valid=${v.valid} — retry`)
  }
  log(`  ⚠ mutate ${off.new_id} [${off.lens}] FAILED to land a real change after 4 tries (${v.detail || ''}) — proceeding as no-op (gate will reject)`)
  return false
}

// =================================================================== RUN
phase('Init')
const init = await runPy(`init --out ${OUT} --N ${N} --pop ${POP} --survivors ${SURVIVORS} --n-train ${NTRAIN} --n-eval ${NEVAL} --seed ${SEED} --optimizer ${OPT}${REUSE_SPLIT ? ` --reuse-split ${REUSE_SPLIT}` : ''}`, INIT_S, 'init', 'Init')
const SEEDS = init.seed_ids || []
log(`init ok. optimizer=${OPT} N=${N} train=${init.n_train} eval=${init.n_eval}. seeds: ${JSON.stringify(init.seed_labels)}`)
let st = await runPy(`evolve-status --out ${OUT} --generations ${GEN}`, STATUS_S, 'status', 'Init')
log(`status: gen0_done=${st.gen0_done} next_gen=${st.next_gen} all_done=${st.all_done} champ=${st.champion} heldout=${st.heldout_done}`)

if (!st.gen0_done) {
  phase('Gen0')
  for (const aid of SEEDS) {
    const h = await runHarness(0, aid, 'train', NTRAIN, 'Gen0')
    if (h.paused) { return { output_dir: OUT, optimizer: OPT, phase: 'gen0-partial', agents: nAgents } }
  }
  st = await runPy(`evolve-status --out ${OUT} --generations ${GEN}`, STATUS_S, 'status:g0', 'Gen0')
  if (!st.gen0_done) { log(`gen0 still incomplete — relaunch`); return { output_dir: OUT, optimizer: OPT, phase: 'gen0-partial', agents: nAgents } }
  const sc0 = await runPy(`score-pop --out ${OUT} --gen 0`, SCORE_S, 'score:g0', 'Gen0')
  await runPy(`population-summary --out ${OUT} --gen 0`, OK, 'popsum:g0', 'Gen0')
  log(`gen0 scored. champion=${sc0.champion} fitness=${sc0.champion_fitness != null ? sc0.champion_fitness.toFixed(3) : '?'}`)
}

phase('Evolve')
const N_OFF = POP - SURVIVORS
while (st.next_gen < GEN) {
  const gen = st.next_gen
  log(`--- evolve gen ${gen} (agents so far ${nAgents}) ---`)
  const sel = await runPy(`select --out ${OUT} --gen ${gen} --survivors ${SURVIVORS}`, SEL_S, `select:g${gen}`, 'Evolve')
  log(`gen ${gen}: survivors=${(sel.survivors || []).join(',')} champion=${sel.champion}`)
  if (OPT === 'core') {
    const rp = await runPy(`core-reflect-plan --out ${OUT} --gen ${gen} --pairs ${PAIRS}`, REFLECT_S, `reflect:g${gen}`, 'Evolve')
    await parallel((rp.plan || []).map(p => () => agentR(coreReflect(p), { label: `reflect:g${gen}:${p.winner_id}>${p.loser_id}`, phase: 'Evolve', model: REFLECT })))
    const ing = await runPy(`core-ingest --out ${OUT} --gen ${gen} --max-lessons ${MAX_LESSONS}`, INGEST_S, `ingest:g${gen}`, 'Evolve')
    log(`gen ${gen}: +${ing.added}/${ing.merged}m insights; bank=${ing.bank_size}`)
  }
  const br = await runPy(`${OPT === 'core' ? 'core-breed-plan' : GBREED} --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}${OPT === 'core' ? ` --topk ${TOPK}` : ''}`, BREED_S, `breed:g${gen}`, 'Evolve')
  // Process offspring SEQUENTIALLY with a per-harness cap guard so a generation can span multiple
  // workflow invocations (one full gen at N=8 exceeds the ~1000-agent invocation cap). Each offspring's
  // mutate→solve→admit is resumable: breed-plan skips already-created children, runHarness is cache-gated,
  // admit is idempotent. finalize runs ONLY after every offspring is scored.
  const offs = br.plan || []
  for (let i = 0; i < offs.length; i++) {
    const off = offs[i]
    if (!off.new_id) off.new_id = `g${pad2(gen + 1)}_${pad2(i)}`
    if (off.parent_gen == null) off.parent_gen = gen
    await mutateVerified(gen, off)
    const h = await runHarness(gen + 1, off.new_id, 'train', NTRAIN, 'Evolve')
    if (h.paused) { log(`evolve gen ${gen} partial — ${off.new_id} pending; relaunch`); return { output_dir: OUT, optimizer: OPT, phase: `evolve-paused-g${gen}`, agents: nAgents } }
    const ad = await runPy(`admit --out ${OUT} --gen ${gen + 1} --child ${off.new_id} --parent-gen ${off.parent_gen} --parent ${off.parent_id}`, ADMIT_S, `admit:${off.new_id}`, 'Evolve')
    log(`  ${off.new_id} [${off.lens}] vs ${off.parent_id}: d=${ad.delta != null ? ad.delta.toFixed(3) : '?'} -> ${ad.admitted ? 'ADMITTED' : 'rejected'}`)
  }
  if (OPT === 'core') await runPy(`core-credit --out ${OUT} --gen ${gen}`, CREDIT_S, `credit:g${gen}`, 'Evolve')
  const fin = await runPy(`finalize-gen --out ${OUT} --gen ${gen} --pop ${POP} --survivors ${SURVIVORS}`, FIN_S, `finalize:g${gen}`, 'Evolve')
  log(`gen ${gen} -> ${gen + 1}: ${fin.n_admitted} admitted. champion=${fin.champion} fitness=${fin.champion_fitness != null ? fin.champion_fitness.toFixed(3) : '?'}`)
  st = await runPy(`evolve-status --out ${OUT} --generations ${GEN}`, STATUS_S, `status:g${gen}`, 'Evolve')
}

if (st.all_done && !st.heldout_done) {
  if (nAgents + heldoutCost() > HARD) { log(`CAP guard at ${nAgents} — held-out needs its own launch; relaunch`); return { output_dir: OUT, optimizer: OPT, phase: 'heldout-pending', champion: st.champion, agents: nAgents } }
  phase('Heldout')
  const he = await runPy(`heldout-setup --out ${OUT} --src-gen ${GEN} --champion ${st.champion}`, HE_S, 'he-setup', 'Heldout')
  log(`held-out: champion ${st.champion} (${(he.roles || []).join('→')}) on ${he.n_eval} eval instances`)
  await runHarness(90, he.agent, 'eval', he.n_eval || NEVAL, 'Heldout')
  await runPy(`final-compare --out ${OUT}`, OK, 'final-compare', 'Heldout')
}
let bank = null
if (OPT === 'core') bank = await runPy(`bank-status --out ${OUT}`, BANK_S, 'bank-final', 'Evolve')
st = await runPy(`evolve-status --out ${OUT} --generations ${GEN}`, STATUS_S, 'status:final', 'Evolve')
log(`DONE [${OPT}] all_done=${st.all_done} heldout_done=${st.heldout_done} champion=${st.champion} train_fit=${st.champion_fitness}`)
return { output_dir: OUT, optimizer: OPT, N, generations: GEN, all_done: st.all_done, heldout_done: st.heldout_done,
  champion: st.champion, champion_train_fitness: st.champion_fitness, bank_final: bank, agents: nAgents }
