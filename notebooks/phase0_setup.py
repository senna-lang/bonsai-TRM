# ---
# Phase 0: Bonsai-8B + AppWorld 環境構築 & パイロット評価
# Colab Pro notebook (A100/V100)
#
# このスクリプトは以下を行う:
# 1. GPU 確認
# 2. Bonsai-8B GGUF (Q1_0_g128) のダウンロードと推論サーバー起動
# 3. AppWorld のインストールと動作確認
# 4. Bonsai × AppWorld 統合テスト
# 5. パイロット評価 (5-10 タスク, 難易度 1)
# ---

# %% [markdown]
# # Phase 0: Bonsai-8B + AppWorld on Colab Pro
#
# **目的**: 推論バックエンド確立 → AppWorld 統合 → 5-10 タスク実測 → スコープ決定

# %% [markdown]
# ## 1. GPU 確認

# %%
import os
import json
import re
import subprocess
import time
from pathlib import Path
from datetime import datetime

# %%
# GPU 確認
!nvidia-smi

# %% [markdown]
# ## 2. Bonsai-8B GGUF 推論サーバー
#
# 上流 llama.cpp は Q1_0_g128 未サポート。PrismML フォークが必要。
# フォールバック順序:
# 1. PrismML-Eng/llama.cpp (CUDA ビルド)
# 2. Mintplex-Labs/prism-ml-llama.cpp
# 3. lilyanatia/Bonsai-8B-requantized + 上流 llama.cpp
# 4. MLX ローカル (最終手段, Colab では使わない)

# %%
# --- Step 2.1: Bonsai-8B GGUF ダウンロード ---
!pip install -q huggingface_hub

from huggingface_hub import hf_hub_download

MODEL_DIR = Path("/content/bonsai-8b-gguf")
MODEL_DIR.mkdir(exist_ok=True)

# Q1_0_g128 モデルファイルをダウンロード
model_path = hf_hub_download(
    repo_id="prism-ml/Bonsai-8B-gguf",
    filename="Bonsai-8B-Q1_0_g128.gguf",  # ファイル名は HF で要確認
    local_dir=str(MODEL_DIR),
)
print(f"Model downloaded to: {model_path}")

# %%
# --- Step 2.2: PrismML フォーク llama.cpp CUDA ビルド ---
# まず PrismML フォークを試す
!git clone https://github.com/PrismML-Eng/llama.cpp /content/llama-cpp-prism
%cd /content/llama-cpp-prism
!cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native 2>&1 | tail -5
!cmake --build build --config Release -j$(nproc) 2>&1 | tail -10

# ビルド成功確認
!ls -la build/bin/llama-server 2>/dev/null || echo "BUILD FAILED - try fallback"

# %%
# --- Step 2.2b: [フォールバック 1] Mintplex フォーク ---
# PrismML フォークが失敗した場合のみ実行
# !git clone https://github.com/Mintplex-Labs/prism-ml-llama.cpp /content/llama-cpp-mintplex
# %cd /content/llama-cpp-mintplex
# !cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native 2>&1 | tail -5
# !cmake --build build --config Release -j$(nproc) 2>&1 | tail -10

# %%
# --- Step 2.2c: [フォールバック 2] 再量子化版 + 上流 llama.cpp ---
# フォーク全滅時のみ実行。注意: 真の 1-bit ではなくなる
# from huggingface_hub import hf_hub_download
# model_path = hf_hub_download(
#     repo_id="lilyanatia/Bonsai-8B-requantized",
#     filename="...",  # 要確認
#     local_dir=str(MODEL_DIR),
# )
# !git clone https://github.com/ggml-org/llama.cpp /content/llama-cpp-upstream
# %cd /content/llama-cpp-upstream
# !cmake -B build -DGGML_CUDA=ON && cmake --build build --config Release -j$(nproc)

# %%
# --- Step 2.3: Bonsai を OpenAI 互換 API として起動 ---
LLAMA_SERVER = "/content/llama-cpp-prism/build/bin/llama-server"
MODEL_FILE = str(list(MODEL_DIR.glob("*.gguf"))[0])

# バックグラウンドで起動
server_proc = subprocess.Popen(
    [
        LLAMA_SERVER,
        "-m", MODEL_FILE,
        "--host", "0.0.0.0",
        "--port", "8080",
        "-ngl", "99",       # 全レイヤーGPU
        "-c", "4096",        # コンテキスト長 (Bonsai は 6K 超で劣化)
        "--temp", "0",       # greedy decoding
    ],
    stdout=open("/content/llama_server.log", "w"),
    stderr=subprocess.STDOUT,
)

print("Waiting for server to start...")
time.sleep(15)

# ヘルスチェック
import requests
try:
    r = requests.get("http://localhost:8080/health")
    print(f"Server health: {r.json()}")
except Exception as e:
    print(f"Server not ready: {e}")
    print("Check logs: !cat /content/llama_server.log | tail -30")

# %%
# --- Step 2.4: 応答確認 ---
!pip install -q openai
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="dummy")

# bonsai-bankai と同じ math probe で比較
test_prompts = [
    {"role": "user", "content": "What is 15 + 27?"},
    {"role": "user", "content": "Tags: machine learning, neural networks"},
]

for prompt in test_prompts:
    t0 = time.time()
    response = client.chat.completions.create(
        model="bonsai-8b",
        messages=[prompt],
        temperature=0,
        max_tokens=200,
        seed=100,
    )
    elapsed = time.time() - t0
    print(f"\nPrompt: {prompt['content']}")
    print(f"Response: {response.choices[0].message.content}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Tokens: {response.usage}")

# %% [markdown]
# ## 3. AppWorld セットアップ

# %%
# --- Step 3.1-3.2: AppWorld インストール ---
!pip install -q appworld
!appworld install
!appworld download data

# %%
# --- Step 3.3: AppWorld チュートリアル (ダミーエージェントで 1 タスク) ---
from appworld import AppWorld, load_task_ids

# dev セットで試す (test_normal は評価用に温存)
dev_task_ids = load_task_ids("dev")
print(f"Dev tasks: {len(dev_task_ids)}")

# 最初のタスクの構造を確認
test_task_id = dev_task_ids[0]
with AppWorld(task_id=test_task_id, experiment_name="phase0_test") as world:
    print(f"Task ID: {test_task_id}")
    print(f"Instruction: {world.task.instruction}")
    print(f"Supervisor: {world.task.supervisor}")
    print(f"Difficulty: {world.task.ground_truth.metadata['difficulty']}")
    print(f"Apps: {list(world.task.app_descriptions.keys())}")

# %%
# --- Step 3.4: タスク構造の把握 (難易度別タスク数) ---
for split in ["dev", "test_normal"]:
    task_ids = load_task_ids(split)
    print(f"\n=== {split} ({len(task_ids)} tasks) ===")

    # 難易度別カウント
    if split == "dev":
        from collections import Counter
        from appworld.task import Task
        difficulties = Counter()
        for tid in task_ids:
            task = Task.load(task_id=tid)
            difficulties[task.ground_truth.metadata["difficulty"]] += 1
        for d in sorted(difficulties):
            print(f"  Difficulty {d}: {difficulties[d]} tasks")

# %% [markdown]
# ## 4. Bonsai × AppWorld 統合

# %%
# --- Step 4.1-4.3: Bonsai をバックエンドにして 1 タスク実行 ---

def call_bonsai(messages: list[dict], max_tokens: int = 3000) -> str:
    """Bonsai LLM を OpenAI 互換 API 経由で呼び出す"""
    response = client.chat.completions.create(
        model="bonsai-8b",
        messages=messages,
        temperature=0,
        max_tokens=max_tokens,
        seed=100,
    )
    return response.choices[0].message.content


def extract_code(text: str) -> str | None:
    """LLM 出力から Python コードブロックを抽出"""
    pattern = r"```python\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # コードブロックがない場合、全体をコードとして扱う
    if "apis." in text:
        return text.strip()
    return None


SYSTEM_PROMPT = """You are an AI assistant that solves tasks by writing Python code.
You have access to APIs via the `apis` object. Write code to accomplish the task.
Always wrap your code in ```python ... ``` blocks.
Keep your code concise and focused on the task."""


def run_baseline_task(task_id: str, max_steps: int = 20) -> dict:
    """ベースライン: 単一 LLM 呼び出しで 1 タスクを実行"""
    result = {
        "task_id": task_id,
        "success": False,
        "steps": 0,
        "turns": [],
        "wall_time": 0,
        "error": None,
    }

    t0 = time.time()

    try:
        with AppWorld(task_id=task_id, experiment_name="phase0_baseline") as world:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Task: {world.task.instruction}\n\n"
                    f"Supervisor: {world.task.supervisor}\n\n"
                    f"Available apps: {list(world.task.app_descriptions.keys())}"
                )},
            ]

            for step in range(max_steps):
                # LLM 呼び出し
                turn_t0 = time.time()
                llm_output = call_bonsai(messages)
                turn_time = time.time() - turn_t0

                # コード抽出
                code = extract_code(llm_output)

                turn_log = {
                    "step": step,
                    "prompt_messages": len(messages),
                    "llm_output": llm_output,
                    "code_extracted": code is not None,
                    "turn_time": turn_time,
                }

                if code is None:
                    turn_log["observation"] = "ERROR: No code block found in LLM output"
                    messages.append({"role": "assistant", "content": llm_output})
                    messages.append({"role": "user", "content": turn_log["observation"]})
                    result["turns"].append(turn_log)
                    continue

                # AppWorld で実行
                try:
                    output = world.execute(code)
                    turn_log["observation"] = output
                except Exception as e:
                    output = f"Execution error: {e}"
                    turn_log["observation"] = output

                messages.append({"role": "assistant", "content": llm_output})
                messages.append({"role": "user", "content": f"Output:\n```\n{output}\n```"})

                result["turns"].append(turn_log)
                result["steps"] = step + 1

                if world.task_completed():
                    result["success"] = True
                    break

    except Exception as e:
        result["error"] = str(e)

    result["wall_time"] = time.time() - t0
    return result


# 統合テスト: dev の最初のタスクで 1 回実行
print("Running integration test...")
test_result = run_baseline_task(dev_task_ids[0], max_steps=5)
print(f"Task: {test_result['task_id']}")
print(f"Success: {test_result['success']}")
print(f"Steps: {test_result['steps']}")
print(f"Wall time: {test_result['wall_time']:.1f}s")
print(f"Error: {test_result['error']}")

# 各ターンの概要
for turn in test_result["turns"]:
    print(f"\n--- Step {turn['step']} ({turn['turn_time']:.1f}s) ---")
    print(f"Code extracted: {turn['code_extracted']}")
    obs = turn["observation"][:200] if turn.get("observation") else "N/A"
    print(f"Observation: {obs}")

# %% [markdown]
# ## 5. パイロット評価 (5-10 タスク, 難易度 1)

# %%
# --- Step 5.1: 難易度 1 タスクを選定 ---
from appworld.task import Task

difficulty_1_tasks = []
for tid in dev_task_ids:
    task = Task.load(task_id=tid)
    if task.ground_truth.metadata["difficulty"] == 1:
        difficulty_1_tasks.append(tid)

# 最大 10 タスク
pilot_tasks = difficulty_1_tasks[:10]
print(f"Pilot tasks (difficulty 1): {len(pilot_tasks)}")
print(pilot_tasks)

# %%
# --- Step 5.2-5.3: パイロット実行 ---
RESULTS_DIR = Path("/content/phase0_results")
RESULTS_DIR.mkdir(exist_ok=True)

pilot_results = []
checkpoint_file = RESULTS_DIR / "phase0_pilot.jsonl"

# チェックポイント読み込み (中断再開対応)
completed_ids = set()
if checkpoint_file.exists():
    with open(checkpoint_file) as f:
        for line in f:
            r = json.loads(line)
            completed_ids.add(r["task_id"])
            pilot_results.append(r)
    print(f"Resuming: {len(completed_ids)} tasks already completed")

for i, task_id in enumerate(pilot_tasks):
    if task_id in completed_ids:
        print(f"[{i+1}/{len(pilot_tasks)}] {task_id} — skipped (already done)")
        continue

    print(f"\n[{i+1}/{len(pilot_tasks)}] Running {task_id}...")
    result = run_baseline_task(task_id, max_steps=20)
    pilot_results.append(result)

    # チェックポイント保存
    with open(checkpoint_file, "a") as f:
        f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")

    print(f"  Success: {result['success']}, Steps: {result['steps']}, "
          f"Time: {result['wall_time']:.1f}s, Error: {result['error']}")

# %%
# --- Step 5.4: 結果サマリ ---
print("\n" + "=" * 60)
print("PHASE 0 PILOT RESULTS")
print("=" * 60)

successes = sum(1 for r in pilot_results if r["success"])
total = len(pilot_results)
times = [r["wall_time"] for r in pilot_results]
steps = [r["steps"] for r in pilot_results]

print(f"Tasks: {total}")
print(f"Success: {successes}/{total} ({successes/total*100:.1f}%)")
print(f"Wall time: mean={sum(times)/len(times):.1f}s, "
      f"median={sorted(times)[len(times)//2]:.1f}s, "
      f"max={max(times):.1f}s")
print(f"Steps: mean={sum(steps)/len(steps):.1f}, max={max(steps)}")

# エラーパターン
errors = [r["error"] for r in pilot_results if r["error"]]
if errors:
    print(f"\nErrors ({len(errors)}):")
    for e in errors:
        print(f"  - {e[:100]}")

# ターンごとのコード抽出成功率
all_turns = [t for r in pilot_results for t in r["turns"]]
code_extracted = sum(1 for t in all_turns if t["code_extracted"])
print(f"\nCode extraction rate: {code_extracted}/{len(all_turns)} "
      f"({code_extracted/len(all_turns)*100:.1f}%)")

# %% [markdown]
# ## 6. スコープ決定
#
# パイロット結果に基づいて Phase 1 のスコープを決定する。
#
# | 条件 | スコープ |
# |---|---|
# | 1タスク以上成功 or 全完走 | フル (test_normal 全タスク) |
# | 1タスク30分超 | ミディアム (難易度1のみ) or ミニマム (30タスク) |
# | エラー停止多発 | 問題切り分け → 修正 → 再実行 |

# %%
# --- Phase 0 完了レポート ---
report = {
    "timestamp": datetime.now().isoformat(),
    "inference_backend": "llama.cpp (PrismML fork)",  # 実際に使ったものに更新
    "gpu": "TODO: nvidia-smi から取得",
    "pilot_tasks": len(pilot_results),
    "successes": successes,
    "success_rate": successes / total if total > 0 else 0,
    "mean_wall_time_seconds": sum(times) / len(times) if times else 0,
    "max_wall_time_seconds": max(times) if times else 0,
    "code_extraction_rate": code_extracted / len(all_turns) if all_turns else 0,
    "scope_decision": "TODO: フル / ミディアム / ミニマム",
    "notes": "TODO: 観察メモ",
}

report_file = RESULTS_DIR / "phase0_report.json"
with open(report_file, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f"Report saved: {report_file}")
print(json.dumps(report, indent=2, ensure_ascii=False))
