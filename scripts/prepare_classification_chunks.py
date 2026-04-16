"""
失敗タスクの分類用データを準備して 10 チャンクに分割する。
各チャンクは 1 サブエージェントが担当する。
"""
import json
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"
CHUNKS_DIR = DATA_DIR / "classification_chunks"
CHUNKS_DIR.mkdir(exist_ok=True)


def extract_task_summary(result: dict) -> dict:
    """分類に必要な情報だけを抽出"""
    turns = result.get("turns", [])

    # 最後の 3 ターンのエージェント出力と観察結果
    last_turns = []
    for t in turns[-3:]:
        last_turns.append({
            "step": t.get("step"),
            "agent_output": (t.get("agent_output", "") or "")[:800],
            "observation": (str(t.get("observation", "") or ""))[:800],
        })

    return {
        "task_id": result["task_id"],
        "success": result["success"],
        "steps": result["steps"],
        "wall_time": result.get("wall_time", 0),
        "error": result.get("error"),
        "summarizer_invocations": result.get("summarizer_invocations", 0),
        "corrector_changes": result.get("corrector_changes", 0),
        "last_turns": last_turns,
    }


def main():
    results = []
    with open(DATA_DIR / "phase3_scaffold.jsonl") as f:
        for line in f:
            results.append(json.loads(line))

    summaries = [extract_task_summary(r) for r in results]
    print(f"Total tasks: {len(summaries)}")

    # 10 チャンクに分割
    NUM_CHUNKS = 10
    chunk_size = (len(summaries) + NUM_CHUNKS - 1) // NUM_CHUNKS
    for i in range(NUM_CHUNKS):
        start = i * chunk_size
        end = min(start + chunk_size, len(summaries))
        chunk = summaries[start:end]
        if not chunk:
            break
        chunk_file = CHUNKS_DIR / f"chunk_{i:02d}.json"
        with open(chunk_file, "w") as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)
        print(f"  chunk_{i:02d}: tasks {start}-{end-1} ({len(chunk)} tasks)")

    print(f"\nChunks saved to {CHUNKS_DIR}")


if __name__ == "__main__":
    main()
