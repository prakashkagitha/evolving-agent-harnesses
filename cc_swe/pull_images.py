"""Parallel pre-pull of SWE-bench Apptainer images for the selected instances (idempotent; skips existing .sif).
Run: python3 -m cc_swe.pull_images [ids_file] [concurrency]   (default ids file = /hdd/pk669/swe/selected_instances.txt)"""
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from cc_swe import swe_harness as H

ids_file = sys.argv[1] if len(sys.argv) > 1 else "/hdd/pk669/swe/selected_instances.txt"
conc = int(sys.argv[2]) if len(sys.argv) > 2 else 5
ids = [x.strip() for x in open(ids_file) if x.strip()]
todo = [i for i in ids if not H.sif_path(i).exists()]
print(f"[pull] {len(ids)} selected, {len(todo)} to pull (conc={conc})", flush=True)


def _one(iid):
    try:
        H.ensure_image(iid)
        return (iid, True, "")
    except Exception as e:
        return (iid, False, str(e)[-200:])


done = 0
with ThreadPoolExecutor(max_workers=conc) as ex:
    futs = {ex.submit(_one, i): i for i in todo}
    for f in as_completed(futs):
        iid, ok, err = f.result(); done += 1
        print(f"[pull {done}/{len(todo)}] {iid} {'OK' if ok else 'FAIL '+err}", flush=True)
have = sum(1 for i in ids if H.sif_path(i).exists())
print(f"[pull] DONE: {have}/{len(ids)} images present", flush=True)
