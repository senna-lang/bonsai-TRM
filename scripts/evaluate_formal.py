"""
Phase 3 の結果を AppWorld の公式 evaluate_task で再評価する。

world.task_completed() は「complete_task() が呼ばれたか」を返す可能性があり、
論文の task_goal_completion とは異なる。evaluate_task() が正式な指標。

事前条件: Phase 3 実行時に experiment_name="phase3_scaffold" を使っていたこと。
"""
import json
from collections import Counter
from pathlib import Path

import appworld
from appworld import evaluate_task, load_task_ids
from appworld.task import Task

appworld.update_root("/workspace")

RESULTS_DIR = Path("/workspace/phase3_results")
CHECKPOINT = RESULTS_DIR / "phase3_scaffold.jsonl"
OUT = RESULTS_DIR / "formal_evaluation.json"

# Phase 3 の結果を読み込み
our_results = {}
with open(CHECKPOINT) as f:
    for line in f:
        r = json.loads(line)
        our_results[r["task_id"]] = r

print(f"Loaded {len(our_results)} our results")

# 全 task_id で evaluate_task を実行
tasks = load_task_ids("test_normal")
print(f"Evaluating {len(tasks)} tasks")

formal_results = []
for i, tid in enumerate(tasks):
    try:
        tracker = evaluate_task(task_id=tid, experiment_name="phase3_scaffold")
        formal = {
            "task_id": tid,
            "formal_success": bool(tracker.success),
            "pass_count": tracker.pass_count,
            "num_tests": tracker.num_tests,
        }
    except Exception as e:
        formal = {
            "task_id": tid,
            "formal_success": None,
            "error": str(e),
        }

    # 我々の結果と比較
    ours = our_results.get(tid, {})
    our_success = ours.get("success", None)
    formal["our_success"] = our_success
    formal["match"] = our_success == formal["formal_success"]

    # 難易度取得
    try:
        task = Task.load(task_id=tid)
        formal["difficulty"] = task.ground_truth.metadata["difficulty"]
    except Exception:
        formal["difficulty"] = None

    formal_results.append(formal)

    if (i + 1) % 20 == 0:
        print(f"  [{i+1}/{len(tasks)}]")

# --- 集計 ---
total = len(formal_results)
our_succ = sum(1 for r in formal_results if r["our_success"])
formal_succ = sum(1 for r in formal_results if r["formal_success"])
matches = sum(1 for r in formal_results if r["match"])
false_positives = sum(1 for r in formal_results if r["our_success"] and not r["formal_success"])
false_negatives = sum(1 for r in formal_results if not r["our_success"] and r["formal_success"])

print()
print("=" * 60)
print("FORMAL EVALUATION RESULTS")
print("=" * 60)
print(f"Our reported:     {our_succ}/{total} ({our_succ/total*100:.1f}%)")
print(f"Formal (TGC):     {formal_succ}/{total} ({formal_succ/total*100:.1f}%)")
print(f"Matches:          {matches}/{total}")
print(f"False positives:  {false_positives} (we said success, formal says fail)")
print(f"False negatives:  {false_negatives} (we said fail, formal says success)")

# 難易度別
print("\n=== By Difficulty (FORMAL) ===")
by_d = {}
for r in formal_results:
    d = r.get("difficulty")
    if d is None:
        continue
    by_d.setdefault(d, {"total": 0, "success": 0})
    by_d[d]["total"] += 1
    if r["formal_success"]:
        by_d[d]["success"] += 1

for d in sorted(by_d):
    info = by_d[d]
    rate = info["success"] / info["total"] * 100
    print(f"  Difficulty {d}: {info['success']}/{info['total']} ({rate:.1f}%)")

# 保存
summary = {
    "total_tasks": total,
    "our_success_rate": our_succ / total,
    "formal_success_rate": formal_succ / total,
    "matches": matches,
    "false_positives": false_positives,
    "false_negatives": false_negatives,
    "by_difficulty_formal": {
        str(d): info for d, info in sorted(by_d.items())
    },
    "per_task": formal_results,
}

with open(OUT, "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {OUT}")
