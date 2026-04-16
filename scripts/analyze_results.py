"""
Phase 3 結果分析スクリプト

phase3_scaffold.jsonl から以下を抽出:
1. 成功タスクの具体例 (難易度別)
2. Corrector の修正例
3. 失敗モード分類 (論文の 9 カテゴリ)
4. Summarizer 発動パターン
5. ターン数・実行時間の分布
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "analysis"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_results() -> list[dict]:
    results = []
    with open(DATA_DIR / "phase3_scaffold.jsonl") as f:
        for line in f:
            results.append(json.loads(line))
    return results


def classify_failure(result: dict) -> str:
    """論文の 9 カテゴリで失敗を分類"""
    if result["success"]:
        return "success"

    if result.get("error"):
        if "exceeds" in result["error"]:
            return "context_length"

    # 最後のターンの observation から推定
    if not result["turns"]:
        return "no_turns"

    last_obs = ""
    for t in reversed(result["turns"]):
        if t.get("observation"):
            last_obs = str(t["observation"])[:2000].lower()
            break

    # キーワードベースの分類
    if "unauthorized" in last_obs or "invalid token" in last_obs or "authentication" in last_obs or "access_token" in last_obs or "login" in last_obs:
        return "auth_credentials"
    if "unprocessable" in last_obs or "validation error" in last_obs or "422" in last_obs or "invalid" in last_obs and "param" in last_obs:
        return "api_params_schema"
    if "not found" in last_obs and ("api" in last_obs or "endpoint" in last_obs or "404" in last_obs):
        return "missing_api"
    if "syntax" in last_obs or "indentation" in last_obs or "traceback" in last_obs:
        return "formatting_code"

    # ターン履歴からループ検出
    if len(result["turns"]) >= 5:
        recent_codes = []
        for t in result["turns"][-5:]:
            code = t.get("agent_output", "")
            if isinstance(code, str):
                recent_codes.append(code[:200])
        if len(set(recent_codes)) <= 2:
            return "repetition_loop"

    # ステップ数上限到達
    if result["steps"] >= 40:
        return "reasoning_planning"

    return "other"


def extract_corrector_examples(results: list[dict], max_examples: int = 5) -> list[dict]:
    """Corrector が修正した代表例を抽出"""
    examples = []
    for r in results:
        if not r["success"]:
            continue
        for turn in r["turns"]:
            if turn.get("corrector_changed"):
                examples.append({
                    "task_id": r["task_id"],
                    "step": turn["step"],
                    "agent_output": turn.get("agent_output", "")[:500],
                })
                if len(examples) >= max_examples:
                    return examples
    return examples


def analyze():
    results = load_results()
    print(f"Loaded {len(results)} tasks")
    print()

    # --- 全体統計 ---
    total = len(results)
    successes = sum(1 for r in results if r["success"])
    errors = sum(1 for r in results if r["error"])
    total_turns = sum(len(r["turns"]) for r in results)
    total_summ = sum(r.get("summarizer_invocations", 0) for r in results)
    total_corr = sum(r.get("corrector_changes", 0) for r in results)

    print("=" * 60)
    print("OVERALL STATS")
    print("=" * 60)
    print(f"Total tasks: {total}")
    print(f"Successes: {successes} ({successes/total*100:.1f}%)")
    print(f"Errors: {errors}")
    print(f"Total turns: {total_turns}")
    print(f"Total summarizer invocations: {total_summ} ({total_summ/total_turns*100:.1f}% of turns)")
    print(f"Total corrector changes: {total_corr} ({total_corr/total_turns*100:.1f}% of turns)")
    print()

    # --- 失敗モード分類 ---
    print("=" * 60)
    print("FAILURE MODE CLASSIFICATION")
    print("=" * 60)
    failure_modes = Counter()
    for r in results:
        mode = classify_failure(r)
        failure_modes[mode] += 1

    for mode, count in failure_modes.most_common():
        pct = count / total * 100
        print(f"  {mode:<25} {count:>4} ({pct:>5.1f}%)")
    print()

    # --- 成功タスクの特徴 ---
    successful = [r for r in results if r["success"]]
    print("=" * 60)
    print("SUCCESS CASE ANALYSIS")
    print("=" * 60)
    print(f"Success steps: min={min(r['steps'] for r in successful)}, "
          f"max={max(r['steps'] for r in successful)}, "
          f"mean={sum(r['steps'] for r in successful)/len(successful):.1f}")
    print(f"Success times: min={min(r['wall_time'] for r in successful):.1f}s, "
          f"max={max(r['wall_time'] for r in successful):.1f}s, "
          f"mean={sum(r['wall_time'] for r in successful)/len(successful):.1f}s")
    print(f"Success Summarizer usage: {sum(r['summarizer_invocations'] for r in successful)} total")
    print(f"Success Corrector changes: {sum(r['corrector_changes'] for r in successful)} total")
    print()

    # --- Summarizer 使用分布 ---
    print("=" * 60)
    print("SUMMARIZER INVOCATION DISTRIBUTION")
    print("=" * 60)
    summ_dist = Counter()
    for r in results:
        s = r.get("summarizer_invocations", 0)
        if s == 0:
            bucket = "0"
        elif s <= 5:
            bucket = "1-5"
        elif s <= 10:
            bucket = "6-10"
        elif s <= 20:
            bucket = "11-20"
        else:
            bucket = "21+"
        summ_dist[bucket] += 1

    for bucket in ["0", "1-5", "6-10", "11-20", "21+"]:
        count = summ_dist.get(bucket, 0)
        print(f"  {bucket:<8} {count} tasks")
    print()

    # --- Corrector 修正例 ---
    print("=" * 60)
    print("CORRECTOR EXAMPLES (from successful tasks)")
    print("=" * 60)
    examples = extract_corrector_examples(results, max_examples=3)
    for i, ex in enumerate(examples, 1):
        print(f"\n--- Example {i}: task={ex['task_id']}, step={ex['step']} ---")
        print(f"Agent output (first 300 chars):")
        print(ex['agent_output'][:300])
    print()

    # --- 論文比較 ---
    print("=" * 60)
    print("PAPER COMPARISON")
    print("=" * 60)
    print(f"{'Config':<30} {'Baseline':<12} {'Scaffold':<12} {'Δ'}")
    print(f"{'Bonsai-8B (1-bit, ours)':<30} {'0.0%':<12} {'14.9%':<12} +14.9pp")
    print(f"{'Qwen3-8B FP16 (paper)':<30} {'5.4%':<12} {'8.9%':<12} +3.5pp")
    print(f"{'Qwen3-8B AWQ (paper)':<30} {'3.0%':<12} {'5.9%':<12} +2.9pp")
    print(f"{'DeepSeek-Coder 33B':<30} {'—':<12} {'7.1%':<12} —")
    print()

    # --- 結果を JSON に保存 ---
    analysis = {
        "total_tasks": total,
        "successes": successes,
        "success_rate": successes / total,
        "errors": errors,
        "total_turns": total_turns,
        "summarizer_invocations": total_summ,
        "summarizer_invocation_rate": total_summ / total_turns,
        "corrector_changes": total_corr,
        "corrector_change_rate": total_corr / total_turns,
        "failure_modes": dict(failure_modes),
        "summarizer_distribution": dict(summ_dist),
        "success_stats": {
            "steps_min": min(r['steps'] for r in successful),
            "steps_max": max(r['steps'] for r in successful),
            "steps_mean": sum(r['steps'] for r in successful) / len(successful),
            "time_min": min(r['wall_time'] for r in successful),
            "time_max": max(r['wall_time'] for r in successful),
            "time_mean": sum(r['wall_time'] for r in successful) / len(successful),
        },
        "paper_comparison": {
            "bonsai_1bit_baseline": 0.0,
            "bonsai_1bit_scaffold": 14.9,
            "qwen3_fp16_baseline": 5.4,
            "qwen3_fp16_scaffold": 8.9,
            "qwen3_awq_baseline": 3.0,
            "qwen3_awq_scaffold": 5.9,
            "deepseek_33b_baseline": 7.1,
        },
    }

    out_file = OUTPUT_DIR / "analysis.json"
    with open(out_file, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"Analysis saved: {out_file}")


if __name__ == "__main__":
    analyze()
