"""
10 チャンクの分類結果を集約して最終的な失敗モード分布を計算する。
"""
import json
from collections import Counter
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"
CHUNKS_DIR = DATA_DIR / "classification_chunks"


def main():
    all_classifications = []
    for i in range(10):
        f = CHUNKS_DIR / f"chunk_{i:02d}_classified.json"
        if not f.exists():
            print(f"MISSING: {f}")
            continue
        with open(f) as fp:
            chunk = json.load(fp)
            all_classifications.extend(chunk)

    print(f"Total classifications: {len(all_classifications)}")
    print()

    # プライマリカテゴリの集計
    primary = Counter()
    primary_weighted = {}  # confidence で重み付け
    for c in all_classifications:
        cat = c["primary"]
        primary[cat] += 1
        primary_weighted.setdefault(cat, 0.0)
        primary_weighted[cat] += c.get("confidence", 1.0)

    # セカンダリカテゴリの集計
    secondary = Counter()
    for c in all_classifications:
        sec = c.get("secondary")
        if sec:
            secondary[sec] += 1

    total = len(all_classifications)

    # 論文の Table 1 と同じ形式で表示
    print("=" * 70)
    print("FAILURE MODE DISTRIBUTION (Bonsai-8B + Scaffold, AppWorld test_normal)")
    print("=" * 70)
    print(f"{'Category':<30} {'Count':<10} {'%':<10} {'Conf.-Weighted'}")
    print("-" * 70)

    # 論文と同じ順序で表示
    order = [
        "success",
        "api_misuse",
        "auth_credentials",
        "reasoning_planning",
        "api_params_schema",
        "missing_api",
        "repetition_loop",
        "formatting_code",
        "pagination_incomplete",
        "context_length",
        "other",
    ]

    # 順序にないものは最後に
    remaining = [c for c in primary if c not in order]
    for c in remaining:
        order.append(c)

    for cat in order:
        count = primary.get(cat, 0)
        if count == 0:
            continue
        pct = count / total * 100
        weighted = primary_weighted.get(cat, 0.0)
        print(f"{cat:<30} {count:<10} {pct:<10.1f} {weighted:.2f}")

    print()
    print("=" * 70)
    print("SECONDARY CATEGORIES (non-null)")
    print("=" * 70)
    for cat, count in secondary.most_common():
        print(f"  {cat:<25} {count}")

    # 失敗のみでの内訳 (論文 Table 1 と同じ)
    failures = [c for c in all_classifications if c["primary"] != "success"]
    failure_primary = Counter(c["primary"] for c in failures)
    failure_total = len(failures)

    print()
    print("=" * 70)
    print(f"FAILURE-ONLY DISTRIBUTION (N={failure_total})")
    print("=" * 70)
    print(f"{'Category':<30} {'Count':<10} {'%':<10}")
    print("-" * 50)
    for cat in order:
        if cat == "success":
            continue
        count = failure_primary.get(cat, 0)
        if count == 0:
            continue
        pct = count / failure_total * 100
        print(f"{cat:<30} {count:<10} {pct:<10.1f}")

    # JSON に保存
    result = {
        "total_tasks": total,
        "primary_distribution": dict(primary),
        "primary_weighted": primary_weighted,
        "secondary_distribution": dict(secondary),
        "failure_only_distribution": dict(failure_primary),
        "classifications": all_classifications,
    }

    out_file = DATA_DIR / "analysis" / "failure_classification.json"
    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_file}")


if __name__ == "__main__":
    main()
