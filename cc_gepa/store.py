"""Filesystem schema + helpers for the recursive two-level GEPA run.

Layout (OUTER_DIR):
  config.json
  baselines/{haiku,sonnet}/{genotype...,main.py,inner_gepa/...,metrics.json}
  gen_NN/
    population.json                      # ids in this generation + summary
    genotypes/agent_<id>/
      system_prompt.md
      revision_prompts.json
      harness_structure.json
      lineage.json
      inner_gepa/round_RR/
        cand_<k>/main.py                 # candidate bot code (the inner population)
        pool.json                        # candidates + sim fitness + telemetry
        feedback.json                    # code-generated per-candidate feedback (for reflectors)
        selected.json                    # survivors chosen by the selection policy
        reflections/<lens>.md            # reflector outputs (written by inner sub-agents)
      produced_bot/main.py               # final best candidate (the phenotype)
      produced_bot/curve.json            # best fitness per inner round (+ slope)
      metrics.json
    tournament/match_matrix.csv, vs_haiku_baseline.csv, vs_sonnet_baseline.csv
    mutations.json                       # every OUTER mutation this gen
    population_summary.json
  final/                                 # SIMS_FINAL headline comparisons
  analysis_data.json, analysis.md, report.html
"""
import json
import os
import tempfile
from pathlib import Path


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
        # an LLM agent may have written malformed JSON; degrade gracefully
        return default


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def read_text(path, default=""):
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return default


def gen_dir(out, gen):
    return Path(out) / f"gen_{gen:02d}"


def agent_dir(out, gen, aid):
    return gen_dir(out, gen) / "genotypes" / f"agent_{aid}"


def round_dir(out, gen, aid, rnd):
    return agent_dir(out, gen, aid) / "inner_gepa" / f"round_{rnd:02d}"


def baseline_dir(out, which):
    return Path(out) / "baselines" / which


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
        "system_prompt": read_text(d / "system_prompt.md"),
        "revision_prompts": read_json(d / "revision_prompts.json", []),
        "harness_structure": read_json(d / "harness_structure.json", {}),
        "lineage": read_json(d / "lineage.json", {}),
    }


def save_genotype(out, gen, geno):
    d = agent_dir(out, gen, geno["id"])
    d.mkdir(parents=True, exist_ok=True)
    write_text(d / "system_prompt.md", geno["system_prompt"])
    write_json(d / "revision_prompts.json", geno["revision_prompts"])
    write_json(d / "harness_structure.json", geno["harness_structure"])
    write_json(d / "lineage.json", geno.get("lineage", {}))


def config(out):
    return read_json(Path(out) / "config.json", {})
