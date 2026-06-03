"""Filesystem schema + helpers for the single-level decomposition-harness evolution.

Layout (OUTER_DIR, default ./cc_decomp_evo/):
  config.json                          # knobs, model-per-level, seed, CodeClash commit, ladder defs
  ladder/
    weak.py moderate.py strong.py sonnet.py   # the four fixed rung bots
    sanity.json                        # pairwise rung sanity (strong>moderate>weak; sonnet competitive)
  ablations/
    simple_refine/{main.py, refine_trace.json, metrics.json}
    best_of_n/{run_<k>/main.py, best/main.py, metrics.json}
  gen_NN/
    population.json                    # ids in this generation
    genotypes/agent_<id>/
      planner_prompt.md                # genotype component 1
      decomposition.json               # genotype component 2 (specialists, referee_policy, tester, refine_rounds)
      lineage.json                     # parent_id, origin, lens, component(s) changed + diff
      briefs.json                      # planner output: {specialist: brief}
      specialists/<name>.py            # each active specialist's scoring module (Haiku)
      produced_bot/main.py             # the phenotype
      produced_bot/refine_trace.json   # each refine round: edit + tester findings + verified kept?
      metrics.json                     # ladder fitness (mean) + per-rung win-rates + verified-vs-parent
    admissions.json                    # every offspring: parent, lens, component, diff, paired delta+CI, admitted?
    population_summary.json            # champion ladder fitness (monotone), distribution, structure/concept inventory
  final/headline.json                  # SIMS_FINAL champion + ablations per rung (with CIs)
  ladder_cache/                        # cached per-(bot,rung,nsims,seed) win-rate scores (token-free, disk-resume)
  analysis_data.json analysis.md report.html
"""
import json
import os
import tempfile
from pathlib import Path

RUNGS = ["weak", "moderate", "strong", "sonnet"]
SPECIALIST_MENU = ["space_control", "combat", "food", "endgame", "hazard"]
REFEREE_POLICIES = ["priority_order", "weighted_vote", "planner_merge"]
LENSES = ["strategy", "concept", "decomposition", "robustness"]


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, ValueError):
        return default  # an LLM agent may have written malformed JSON; degrade gracefully


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def read_text(path, default=""):
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return default


# ----------------------------------------------------------------- path helpers
def gen_dir(out, gen):
    return Path(out) / f"gen_{gen:02d}"


def agent_dir(out, gen, aid):
    return gen_dir(out, gen) / "genotypes" / f"agent_{aid}"


def ladder_dir(out):
    return Path(out) / "ladder"


def ladder_path(out, rung):
    return ladder_dir(out) / f"{rung}.py"


def ablation_dir(out):
    return Path(out) / "ablations"


def config(out):
    return read_json(Path(out) / "config.json", {})


def list_agents(out, gen):
    g = gen_dir(out, gen)
    pop = read_json(g / "population.json", {})
    if pop and "ids" in pop:
        return pop["ids"]
    gd = g / "genotypes"
    if not gd.exists():
        return []
    return sorted(p.name[len("agent_"):] for p in gd.iterdir() if p.name.startswith("agent_"))


def load_genotype(out, gen, aid):
    d = agent_dir(out, gen, aid)
    return {
        "id": aid,
        "planner_prompt": read_text(d / "planner_prompt.md"),
        "decomposition": read_json(d / "decomposition.json", {}),
        "lineage": read_json(d / "lineage.json", {}),
    }


def save_genotype(out, gen, geno):
    d = agent_dir(out, gen, geno["id"])
    d.mkdir(parents=True, exist_ok=True)
    write_text(d / "planner_prompt.md", geno["planner_prompt"])
    write_json(d / "decomposition.json", geno["decomposition"])
    write_json(d / "lineage.json", geno.get("lineage", {}))


def produced_bot_path(out, gen, aid):
    return agent_dir(out, gen, aid) / "produced_bot" / "main.py"
