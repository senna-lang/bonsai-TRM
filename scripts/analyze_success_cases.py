"""
成功タスク 25 件の詳細分析

抽出するもの:
1. どんなタスクが成功したか (パターン分析)
2. ステップ数・推論時間の分布
3. Corrector が決定打になったケース
4. 難易度別の成功例
"""
import json
import re
from collections import Counter
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"


def load_results():
    results = []
    with open(DATA_DIR / "phase3_scaffold.jsonl") as f:
        for line in f:
            results.append(json.loads(line))
    return results


def extract_task_category(task_id: str) -> str:
    """タスク ID のプレフィックスからシナリオ ID を抽出"""
    return task_id.rsplit("_", 1)[0]


def analyze():
    results = load_results()
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    print(f"Total: {len(results)}, Success: {len(successes)}, Fail: {len(failures)}")
    print()

    # --- 成功タスクのシナリオ分布 ---
    # タスク ID は {scenario}_{variant} の形式で、
    # 同じシナリオで難易度の異なるバリアントが存在する
    success_scenarios = Counter(extract_task_category(r["task_id"]) for r in successes)
    print("=" * 60)
    print("SUCCESS BY SCENARIO")
    print("=" * 60)
    print(f"Unique scenarios: {len(success_scenarios)}")
    for scenario, count in success_scenarios.most_common():
        print(f"  {scenario}: {count} successful variant(s)")
    print()

    # --- 最初のコード抽出成功率 ---
    # ステップ 1 で成功 → 超簡単なタスク
    quick_wins = [r for r in successes if r["steps"] <= 2]
    print("=" * 60)
    print("QUICK WINS (steps <= 2)")
    print("=" * 60)
    print(f"Count: {len(quick_wins)}/{len(successes)} ({len(quick_wins)/len(successes)*100:.0f}%)")
    for r in quick_wins[:5]:
        first_turn = r["turns"][0] if r["turns"] else {}
        agent_out = first_turn.get("agent_output", "")[:200]
        print(f"\n  {r['task_id']} (steps={r['steps']}, time={r['wall_time']:.1f}s)")
        print(f"  Agent (first 200 chars): {agent_out}")
    print()

    # --- Corrector が決定打になった事例 ---
    # Corrector が 1 回以上発動して成功したタスク
    corrector_helped = [r for r in successes if r["corrector_changes"] > 0]
    print("=" * 60)
    print("CORRECTOR-ASSISTED SUCCESSES")
    print("=" * 60)
    print(f"Count: {len(corrector_helped)}/{len(successes)}")
    print(f"Total corrector changes in successes: {sum(r['corrector_changes'] for r in successes)}")

    # 最も Corrector が活躍したケース
    top_corrector = sorted(successes, key=lambda r: -r["corrector_changes"])[:3]
    print("\nTop 3 Corrector-heavy successes:")
    for r in top_corrector:
        print(f"  {r['task_id']}: {r['corrector_changes']} corrections, {r['steps']} steps")
    print()

    # --- Summarizer が発動した成功ケース ---
    summ_helped = [r for r in successes if r["summarizer_invocations"] > 0]
    print("=" * 60)
    print("SUMMARIZER-ASSISTED SUCCESSES")
    print("=" * 60)
    print(f"Count: {len(summ_helped)}/{len(successes)}")
    for r in summ_helped:
        print(f"  {r['task_id']}: {r['summarizer_invocations']} summarizations, {r['steps']} steps")
    print()

    # --- 成功タスクの具体的な例 (3 件) ---
    print("=" * 60)
    print("DETAILED SUCCESS EXAMPLES")
    print("=" * 60)

    # 1. 最短成功 (1 ステップ)
    shortest = min(successes, key=lambda r: r["steps"])
    print(f"\n--- SHORTEST: {shortest['task_id']} ({shortest['steps']} step, {shortest['wall_time']:.1f}s) ---")
    if shortest["turns"]:
        t = shortest["turns"][0]
        print(f"Agent output:\n{(t.get('agent_output', '') or '')[:600]}")
        print(f"\nObservation:\n{str(t.get('observation', ''))[:400]}")

    # 2. Corrector 多用の成功
    print(f"\n--- CORRECTOR-HEAVY: {top_corrector[0]['task_id']} ({top_corrector[0]['corrector_changes']} corrections) ---")
    r = top_corrector[0]
    for t in r["turns"][:3]:
        print(f"\nStep {t['step']}: corrected={t.get('corrector_changed')}, summ={t.get('summarizer_used')}")
        print(f"Agent: {(t.get('agent_output', '') or '')[:300]}")

    # 3. 難易度 3 の成功例
    from appworld.task import Task as _T  # 遅延 import
    try:
        difficulty_3_successes = []
        for r in successes:
            try:
                task = _T.load(task_id=r["task_id"])
                if task.ground_truth.metadata["difficulty"] == 3:
                    difficulty_3_successes.append(r)
            except Exception:
                pass

        if difficulty_3_successes:
            r = difficulty_3_successes[0]
            print(f"\n--- DIFFICULTY 3 SUCCESS: {r['task_id']} ({r['steps']} steps) ---")
            if r["turns"]:
                t = r["turns"][-1]  # 最後のターン
                print(f"Final agent output:\n{(t.get('agent_output', '') or '')[:400]}")
    except Exception as e:
        print(f"\n(AppWorld not available locally: {e})")

    # --- 統計サマリの保存 ---
    summary = {
        "total_successes": len(successes),
        "unique_scenarios_succeeded": len(success_scenarios),
        "quick_wins": len(quick_wins),
        "corrector_assisted": len(corrector_helped),
        "summarizer_assisted": len(summ_helped),
        "steps_distribution": dict(Counter(r["steps"] for r in successes)),
        "success_task_ids": [r["task_id"] for r in successes],
        "scenarios_with_any_success": list(success_scenarios.keys()),
    }
    out = DATA_DIR / "analysis" / "success_cases.json"
    with open(out, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    analyze()
