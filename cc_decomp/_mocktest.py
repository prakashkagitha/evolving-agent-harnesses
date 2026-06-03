"""Token-free end-to-end test of the decomposition-evolution CONTROLLER.

Mocks every LLM agent (planner, specialists, referee, debugger, Sonnet mutator) by writing
plausible code/files directly, then drives the full controller pipeline through one full
generation: init -> ladder -> sonnet rung -> ablations -> gen-0 harnesses -> score -> gate ->
select -> breed -> offspring harnesses -> admit (paired CI) -> finalize -> final-eval.

Run:  python3 -m cc_decomp._mocktest
Exits non-zero on any failed assertion. NO model tokens are spent.
"""
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

from . import control, harness, store

OUT = "/tmp/cc_decomp_mocktest"

# ----- mock specialist implementations (real-ish, so bots actually play) -----
_FLOOD = '''
def _blocked(board):
    b=set()
    for s in board["snakes"]:
        pts=[(c["x"],c["y"]) for c in s["body"]]
        ja=len(pts)>=2 and pts[-1]==pts[-2]
        for p in (pts if ja else pts[:-1]): b.add(p)
    return b
def _flood(c,bl,w,h,cap=121):
    if not(0<=c[0]<w and 0<=c[1]<h) or c in bl: return 0
    seen={c}; st=[c]; n=0
    while st and n<cap:
        x,y=st.pop(); n+=1
        for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
            p=(x+dx,y+dy)
            if 0<=p[0]<w and 0<=p[1]<h and p not in bl and p not in seen: seen.add(p); st.append(p)
    return n
'''
MOCK_SPECIALISTS = {
    "space_control": _FLOOD + '''
def score(game_state):
    b=game_state["board"]; w,h=b["width"],b["height"]; me=game_state["you"]
    hd=me["body"][0]; hx,hy=hd["x"],hd["y"]; bl=_blocked(b); ml=me["length"]; out={}
    for mv,(dx,dy) in {"up":(0,1),"down":(0,-1),"left":(-1,0),"right":(1,0)}.items():
        c=(hx+dx,hy+dy)
        if not(0<=c[0]<w and 0<=c[1]<h) or c in bl: out[mv]=-1e9; continue
        sp=_flood(c,bl,w,h); out[mv]=-1e9 if sp<ml else float(sp)
    return out
''',
    "combat": '''
def score(game_state):
    b=game_state["board"]; me=game_state["you"]; hd=me["body"][0]; hx,hy=hd["x"],hd["y"]; ml=me["length"]
    threat=set(); kill=set()
    for s in b["snakes"]:
        if s["id"]==me["id"]: continue
        eh=(s["body"][0]["x"],s["body"][0]["y"])
        for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
            cc=(eh[0]+dx,eh[1]+dy); (threat if s["length"]>=ml else kill).add(cc)
    out={}
    for mv,(dx,dy) in {"up":(0,1),"down":(0,-1),"left":(-1,0),"right":(1,0)}.items():
        c=(hx+dx,hy+dy)
        out[mv]=-1e9 if c in threat else (5.0 if c in kill else 0.0)
    return out
''',
    "food": '''
def score(game_state):
    b=game_state["board"]; w,h=b["width"],b["height"]; me=game_state["you"]; hd=me["body"][0]
    hx,hy=hd["x"],hd["y"]; foods=[(f["x"],f["y"]) for f in b.get("food",[])]
    occ=set()
    for s in b["snakes"]:
        for c in s["body"][:-1]: occ.add((c["x"],c["y"]))
    want = me["health"]<50 or me["length"]<=4; out={}
    for mv,(dx,dy) in {"up":(0,1),"down":(0,-1),"left":(-1,0),"right":(1,0)}.items():
        c=(hx+dx,hy+dy)
        if not(0<=c[0]<w and 0<=c[1]<h) or c in occ: out[mv]=-1e9; continue
        if foods and want:
            d=min(abs(c[0]-fx)+abs(c[1]-fy) for fx,fy in foods); out[mv]=float(20-d)
        else: out[mv]=0.0
    return out
''',
    "endgame": '''
def score(game_state):
    b=game_state["board"]; w,h=b["width"],b["height"]; me=game_state["you"]; hd=me["body"][0]
    hx,hy=hd["x"],hd["y"]; out={}; cx,cy=w//2,h//2
    for mv,(dx,dy) in {"up":(0,1),"down":(0,-1),"left":(-1,0),"right":(1,0)}.items():
        c=(hx+dx,hy+dy)
        if not(0<=c[0]<w and 0<=c[1]<h): out[mv]=-1e9; continue
        out[mv]=float(-(abs(c[0]-cx)+abs(c[1]-cy)))
    return out
''',
    "hazard": '''
def score(game_state):
    b=game_state["board"]; w,h=b["width"],b["height"]; me=game_state["you"]; hd=me["body"][0]
    hx,hy=hd["x"],hd["y"]; haz=set((c["x"],c["y"]) for c in b.get("hazards",[])); out={}
    for mv,(dx,dy) in {"up":(0,1),"down":(0,-1),"left":(-1,0),"right":(1,0)}.items():
        c=(hx+dx,hy+dy)
        if not(0<=c[0]<w and 0<=c[1]<h): out[mv]=-1e9; continue
        edge = (c[0]==0 or c[0]==w-1 or c[1]==0 or c[1]==h-1)
        out[mv]=(-5.0 if c in haz else 0.0)+(-1.0 if edge else 0.0)
    return out
''',
}
# a genuinely-bad edit: steer into the snake's own neck (instant death) -> score regresses -> revert.
MOCK_SUICIDE = '''
def score(game_state):
    me=game_state["you"]; bd=me["body"]; hd=bd[0]
    nk=bd[1] if len(bd)>1 else hd
    key=(nk["x"]-hd["x"], nk["y"]-hd["y"])
    mv={(0,1):"up",(0,-1):"down",(-1,0):"left",(1,0):"right"}.get(key)
    out={m:0.0 for m in ("up","down","left","right")}
    if mv: out[mv]=1000.0
    return out
'''
MOCK_REFEREE = '''
def referee(scores, game_state, legal):
    best=None; bv=None
    for mv in legal:
        tot=0.0
        for sc in scores.values():
            v=sc.get(mv,0.0); tot += -1e6 if v<=-5e8 else max(-50.0,min(50.0,v))
        if bv is None or tot>bv: bv,tot_best=tot,mv; best=mv
    return best or legal[0]
'''


def mock_harness(out, gen, aid):
    """Mock the planner + specialist coders + referee + debugger for one harness run."""
    d = store.agent_dir(out, gen, aid)
    dec = store.read_json(d / "decomposition.json", {})
    specs = harness.canonical_specialists(dec)
    store.write_json(d / "briefs.json", {s: f"Implement {s} for this strategy." for s in specs})
    for s in specs:
        store.write_text(d / "specialists" / f"{s}.py", MOCK_SPECIALISTS[s])
    if dec.get("referee_policy") == "planner_merge":
        store.write_text(d / "specialists" / "_referee.py", MOCK_REFEREE)
    control.cmd_assemble(NS(out=out, gen=gen, agent=aid))
    rr = int(dec.get("refine_rounds", 0))
    control.cmd_refine_init(NS(out=out, gen=gen, agent=aid, simple="", round=0,
                              sims=20, seed=0, tester=int(bool(dec.get("tester")))))
    for r in range(1, rr + 1):
        # mock debugger: round 1 makes a BAD edit (suicide -> regression -> reverted); others no-op
        if r == 1 and specs:
            for s in specs:
                store.write_text(d / "specialists" / f"{s}.py", MOCK_SUICIDE)
        else:
            for s in specs:
                store.write_text(d / "specialists" / f"{s}.py", MOCK_SPECIALISTS[s])
        control.cmd_refine_keep(NS(out=out, gen=gen, agent=aid, simple="", round=r,
                                  sims=20, seed=0, tester=int(bool(dec.get("tester")))))


def mock_simple(out, dest_dir, tester=1, rounds=2):
    """Mock a simple-refinement run (whole-bot, no decomposition) for ablation / sonnet rung."""
    d = Path(dest_dir)
    (d / "produced_bot").mkdir(parents=True, exist_ok=True)
    # a complete decent bot = strong rung code (stand-in for a Haiku/Sonnet write)
    store.write_text(d / "produced_bot" / "main.py", (store.ladder_dir(out) / "strong.py").read_text())
    control.cmd_refine_init(NS(out=out, gen=0, agent="", simple=str(d), round=0, sims=20, seed=1, tester=tester))
    for r in range(1, rounds + 1):
        control.cmd_refine_keep(NS(out=out, gen=0, agent="", simple=str(d), round=r, sims=20, seed=1, tester=tester))


def mock_offspring_genotype(out, gen, plan_item):
    """Mock the Sonnet mutator: copy parent genotype, apply an incremental single-aspect edit."""
    pg, pid = plan_item["parent_gen"], plan_item["parent_id"]
    nid, lens = plan_item["new_id"], plan_item["lens"]
    pd = store.agent_dir(out, pg, pid)
    cd = store.agent_dir(out, gen + 1, nid)
    cd.mkdir(parents=True, exist_ok=True)
    pp = store.read_text(pd / "planner_prompt.md")
    dec = store.read_json(pd / "decomposition.json", {})
    changed, diff = [], ""
    if lens == "concept":
        pp = pp + " Also actively cut off the opponent's escape space (head-to-head pressure)."
        changed, diff = ["planner_prompt"], "+aggression concept"
    elif lens == "strategy":
        pp = pp.replace("Strategy:", "Strategy (refined):", 1)
        changed, diff = ["planner_prompt"], "reframed strategy"
    elif lens == "decomposition":
        for s in store.SPECIALIST_MENU:
            if s not in dec.get("specialists", []):
                dec["specialists"] = dec.get("specialists", []) + [s]; diff = f"+specialist {s}"; break
        changed = ["decomposition"]
    elif lens == "robustness":
        dec["tester"] = True; dec["refine_rounds"] = int(dec.get("refine_rounds", 2)) + 1
        changed, diff = ["decomposition"], "tester on + refine+1"
    store.write_text(cd / "planner_prompt.md", pp)
    store.write_json(cd / "decomposition.json", dec)
    store.write_json(cd / "lineage.json", {"parent_id": pid, "parent_gen": pg, "lens": lens,
                     "origin": "mutation", "changed_components": changed, "diff": diff})


def check(cond, msg):
    print(("  OK  " if cond else " FAIL ") + msg)
    if not cond:
        raise AssertionError(msg)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    print("== init ==")
    r = control.cmd_init(NS(out=OUT, seed=0, generations=1, pop=4, survivors=2, refine_rounds=2,
                            crossovers=0, sims_evolve=24, sims_admit=40, sims_final=40))
    seeds_ids = r["seed_ids"]; check(len(seeds_ids) == 4, f"4 seeds: {seeds_ids}")

    print("== sonnet rung + ladder sanity ==")
    son = Path(OUT) / "ablations" / "sonnet_rung"
    mock_simple(OUT, son, tester=1, rounds=2)
    control.cmd_install_sonnet_rung(NS(out=OUT, path=str(son / "produced_bot" / "main.py")))
    s = control.cmd_ladder_sanity(NS(out=OUT, sims=90, seed=4242))
    check(s["order_ok"], f"ladder ranks weak<moderate<strong: {s['fitness']}")
    check(store.ladder_path(OUT, "sonnet").exists(), "sonnet rung installed")

    print("== ablations (simple-refine + best-of-2) ==")
    mock_simple(OUT, Path(OUT) / "ablations" / "simple_refine", tester=1, rounds=2)
    bon = Path(OUT) / "ablations" / "best_of_n"
    for k in range(2):
        mock_simple(OUT, bon / f"run_{k}", tester=0, rounds=1)
    (bon / "best").mkdir(parents=True, exist_ok=True)
    shutil.copy(bon / "run_0" / "produced_bot" / "main.py", bon / "best" / "main.py")
    check((bon / "best" / "main.py").exists(), "best-of-N bot chosen")

    print("== gen-0 harnesses ==")
    for aid in seeds_ids:
        mock_harness(OUT, 0, aid)
        bot = store.produced_bot_path(OUT, 0, aid)
        ok, reason = control._validate(bot)
        check(ok, f"produced bot valid [{aid}]: {reason}")
        tr = store.read_json(store.agent_dir(OUT, 0, aid) / "produced_bot" / "refine_trace.json", {})
        round1 = [x for x in tr["rounds"] if x["round"] == 1]
        check(round1 and not round1[0]["kept"], f"bad round-1 edit reverted [{aid}]")

    print("== score gen 0 + summary ==")
    sc = control.cmd_score_pop(NS(out=OUT, gen=0, agent="", sims=24, seed=0))
    check(sc["champion"] is not None, f"champion: {sc['champion']} fit={round(sc['champion_fitness'],3)}")
    check(all(0 <= row["ladder_fitness"] <= 1 for row in sc["ranking"]), "fitnesses in [0,1]")
    control.cmd_population_summary(NS(out=OUT, gen=0))
    psum = store.read_json(store.gen_dir(OUT, 0) / "population_summary.json", {})
    check("concept_inventory" in psum and "structure" in psum, "gen0 summary has concept+structure")

    print("== gate ==")
    g = control.cmd_gate(NS(out=OUT, gen=0, agent=seeds_ids[0]))
    check(g["pass"], f"verification gate passes: {g}")

    print("== select + breed ==")
    sel = control.cmd_select(NS(out=OUT, gen=0, survivors=2))
    check(len(sel["survivors"]) == 2, f"survivors: {sel['survivors']}")
    bp = control.cmd_breed_plan(NS(out=OUT, gen=0, pop=4, survivors=2, crossovers=0))
    plan = bp["plan"]; check(len(plan) == 2, f"2 offspring planned: {[p['new_id'] for p in plan]}")
    lenses = {p["lens"] for p in plan}; check(len(lenses) == 2, f"distinct lenses fired: {lenses}")

    print("== offspring harnesses + admit ==")
    for it in plan:
        mock_offspring_genotype(OUT, 0, it)
        mock_harness(OUT, 1, it["new_id"])
        ad = control.cmd_admit(NS(out=OUT, gen=1, child=it["new_id"], parent_gen=0,
                                  parent=it["parent_id"], sims=40, seed=0))
        check("ci_low" in ad and "ci_high" in ad, f"paired CI computed for {it['new_id']}: "
              f"delta={round(ad['delta'],3)} CI=[{round(ad['ci_low'],3)},{round(ad['ci_high'],3)}] "
              f"admitted={ad['admitted']}")

    print("== finalize gen 0 -> gen 1 ==")
    fin = control.cmd_finalize_gen(NS(out=OUT, gen=0, pop=4, survivors=2))
    check(len(fin["ids"]) == 4, f"gen1 refilled to pop=4: {fin['ids']}")
    check(sel["survivors"][0] in fin["ids"], "champion carried (elitism)")
    g0champ = store.read_json(store.gen_dir(OUT, 0) / "population_summary.json", {})["champion_fitness"]
    g1champ = fin["champion_fitness"]
    check(g1champ >= g0champ - 1e-9, f"champion fitness monotone: {round(g0champ,3)} -> {round(g1champ,3)}")
    adm = store.read_json(store.gen_dir(OUT, 1) / "admissions.json", {})
    check("offspring" in adm, "admissions.json written")

    print("== final eval ==")
    fe = control.cmd_final_eval(NS(out=OUT, gen=1, sims=40, seed=0))
    check("champion" in fe["headline"], f"final headline has champion: "
          f"{ {k: round(v['ladder_mean']['winrate'],3) for k,v in fe['headline'].items()} }")
    check("simple_refine" in fe["headline"], "ablation in final headline")

    print("\nALL MOCK CHECKS PASSED")


if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        sys.exit(1)
