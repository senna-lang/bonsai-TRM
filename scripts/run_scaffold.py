"""
Phase 3: スキャフォールド評価 (test_normal 168 タスク)
RunPod 用スタンドアロンスクリプト

使い方:
    bash setup_runpod.sh
    python3 run_scaffold.py
"""
import json
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import appworld
import tiktoken
from appworld import AppWorld, load_task_ids
from appworld.task import Task
from openai import OpenAI

# --- 設定 ---
BONSAI_PORT = 8090
WORKSPACE = Path("/workspace")
RESULTS_DIR = WORKSPACE / "phase3_results"
RESULTS_DIR.mkdir(exist_ok=True)

appworld.update_root(str(WORKSPACE))

client = OpenAI(base_url=f"http://localhost:{BONSAI_PORT}/v1", api_key="dummy")

# --- トークンカウント ---
try:
    _encoder = tiktoken.get_encoding("cl100k_base")
except Exception:
    _encoder = None


def count_tokens(text: str) -> int:
    if _encoder:
        return len(_encoder.encode(text))
    return len(text) // 4


def count_messages_tokens(messages: list[dict]) -> int:
    return sum(count_tokens(m.get("content", "")) for m in messages)


# --- LLM 呼び出し ---
def call_llm(messages: list[dict], max_tokens: int = 3000) -> str:
    response = client.chat.completions.create(
        model="bonsai-8b",
        messages=messages,
        temperature=0,
        max_tokens=max_tokens,
        seed=100,
    )
    return response.choices[0].message.content


def extract_code(text: str) -> str | None:
    pattern = r"```python\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    if "apis." in text:
        return text.strip()
    return None


def extract_api_endpoints(code: str) -> list[str]:
    pattern = r"apis\.(\w+)\.(\w+)"
    return [f"{m[0]}.{m[1]}" for m in re.findall(pattern, code)]


# --- システムプロンプト ---
AGENT_PROMPT = """You are an AI assistant that solves tasks by writing Python code.
You have access to APIs via the `apis` object. Write code to accomplish the task.
Always wrap your code in ```python ... ``` blocks.
Keep your code concise and focused on the task.
When you are done, call `apis.supervisor.complete_task()` to finish."""

SUMMARIZER_PROMPT = """You are a conversation summarizer for an AI coding agent.
Your task is to compress the conversation history while preserving critical information.

You MUST preserve the following verbatim (do not paraphrase):
- Authentication tokens and credentials (access tokens, API keys, session IDs)
- API endpoint names and their observed response schemas
- Error messages and their resolutions
- Pagination states and iteration progress
- Task completion status indicators
- User IDs, email addresses, and other identifiers discovered during execution

Output a concise summary that another AI agent can use to continue the task.
Start with "Summary of previous actions:" and list the key facts."""

CORRECTOR_PROMPT = """You are a code correction agent. You receive a proposed Python code snippet and relevant API documentation.
You do NOT have access to the conversation history.

Your task:
1. Classify the issue (if any) into: authentication error, API schema mismatch, wrong API name, formatting error, or no issue
2. Cite evidence from the execution output (if provided)
3. Output a corrected version of the code

Rules:
- The corrected code MUST contain exactly one ```python ... ``` code block
- The code MUST include at least one `apis.*` call
- Parameter names MUST match the API documentation exactly
- If you are uncertain about the correct parameters, query the documentation:
  `apis.api_docs.show_api_doc("app_name", "endpoint_name")`
- If the original code looks correct, return it unchanged

Output format:
Diagnosis: <one line>
```python
<corrected code>
```"""

# --- Summarizer ---
SUMMARIZER_CHAR_THRESHOLD = 12000
SUMMARIZER_TOKEN_THRESHOLD = 3000
N_FIRST = 13
K_LAST = 3


def should_summarize(messages: list[dict]) -> bool:
    total_chars = sum(len(m.get("content", "")) for m in messages)
    total_tokens = count_messages_tokens(messages)
    return total_chars > SUMMARIZER_CHAR_THRESHOLD or total_tokens > SUMMARIZER_TOKEN_THRESHOLD


def run_summarizer(messages: list[dict]) -> list[dict]:
    if len(messages) <= N_FIRST + K_LAST:
        return messages

    first_messages = messages[:N_FIRST]
    last_messages = messages[-K_LAST:]
    middle_messages = messages[N_FIRST:-K_LAST]

    middle_text = "\n".join(
        f"[{m['role']}]: {m['content'][:500]}" for m in middle_messages
    )

    summary_request = [
        {"role": "system", "content": SUMMARIZER_PROMPT},
        {"role": "user", "content": f"Summarize the following conversation segment:\n\n{middle_text}"},
    ]

    try:
        summary = call_llm(summary_request, max_tokens=1000)
    except Exception:
        return messages

    return first_messages + [
        {"role": "user", "content": f"[CONTEXT SUMMARY]\n{summary}"}
    ] + last_messages


# --- Corrector ---
def run_corrector(agent_code: str, last_execution_output: str | None = None) -> str:
    endpoints = extract_api_endpoints(agent_code)
    api_info = f"Referenced API endpoints: {', '.join(endpoints)}" if endpoints else "No API endpoints detected"

    corrector_input = f"Proposed code:\n```python\n{agent_code}\n```\n\n{api_info}"

    if last_execution_output:
        corrector_input += f"\n\nLast execution output:\n```\n{last_execution_output[:1000]}\n```"

    corrector_messages = [
        {"role": "system", "content": CORRECTOR_PROMPT},
        {"role": "user", "content": corrector_input},
    ]

    try:
        corrector_output = call_llm(corrector_messages, max_tokens=2000)
        corrected_code = extract_code(corrector_output)
        if corrected_code:
            return corrected_code
    except Exception:
        pass

    return agent_code


# --- スキャフォールド統合 ---
def run_scaffold_task(task_id: str, max_steps: int = 40) -> dict:
    result = {
        "task_id": task_id,
        "success": False,
        "steps": 0,
        "turns": [],
        "wall_time": 0,
        "error": None,
        "summarizer_invocations": 0,
        "corrector_changes": 0,
    }
    t0 = time.time()

    try:
        with AppWorld(task_id=task_id, experiment_name="phase3_scaffold") as world:
            messages = [
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": (
                    f"Task: {world.task.instruction}\n\n"
                    f"Supervisor: {world.task.supervisor}\n\n"
                    f"Available apps: {list(world.task.app_descriptions.keys())}"
                )},
            ]

            last_execution_output = None

            for step in range(max_steps):
                turn_t0 = time.time()
                turn_log = {"step": step, "summarizer_used": False, "corrector_changed": False}

                # Tier 1: Summarizer
                if should_summarize(messages):
                    messages = run_summarizer(messages)
                    turn_log["summarizer_used"] = True
                    result["summarizer_invocations"] += 1

                # Tier 2: Agent
                try:
                    agent_output = call_llm(messages)
                except Exception as llm_err:
                    result["error"] = str(llm_err)
                    result["steps"] = step
                    break

                agent_code = extract_code(agent_output)
                turn_log["agent_output"] = agent_output
                turn_log["agent_code_extracted"] = agent_code is not None

                if agent_code is None:
                    turn_log["observation"] = "ERROR: No code block found in Agent output"
                    messages.append({"role": "assistant", "content": agent_output})
                    messages.append({"role": "user", "content": turn_log["observation"]})
                    turn_log["turn_time"] = time.time() - turn_t0
                    result["turns"].append(turn_log)
                    continue

                # Tier 3: Corrector
                corrected_code = run_corrector(agent_code, last_execution_output)
                turn_log["corrector_changed"] = (corrected_code != agent_code)
                if turn_log["corrector_changed"]:
                    result["corrector_changes"] += 1

                final_code = corrected_code

                # AppWorld 実行
                try:
                    output = world.execute(final_code)
                    turn_log["observation"] = output
                    last_execution_output = output
                except Exception as e:
                    output = f"Execution error: {e}"
                    turn_log["observation"] = output
                    last_execution_output = output

                messages.append({"role": "assistant", "content": agent_output})
                messages.append({"role": "user", "content": f"Output:\n```\n{output}\n```"})

                turn_log["turn_time"] = time.time() - turn_t0
                result["turns"].append(turn_log)
                result["steps"] = step + 1

                if world.task_completed():
                    result["success"] = True
                    break

    except Exception as e:
        result["error"] = str(e)

    result["wall_time"] = time.time() - t0
    return result


# --- メイン実行 ---
def main():
    # サーバー確認
    import requests
    try:
        r = requests.get(f"http://localhost:{BONSAI_PORT}/health")
        print(f"Server health: {r.json()}")
    except Exception as e:
        print(f"Server not ready: {e}")
        print("Run setup_runpod.sh first")
        return

    test_task_ids = load_task_ids("test_normal")
    print(f"test_normal: {len(test_task_ids)} tasks")

    checkpoint_file = RESULTS_DIR / "phase3_scaffold.jsonl"

    all_results = []
    completed_ids = set()
    if checkpoint_file.exists():
        with open(checkpoint_file) as f:
            for line in f:
                r = json.loads(line)
                completed_ids.add(r["task_id"])
                all_results.append(r)
        print(f"Resuming: {len(completed_ids)}/{len(test_task_ids)} completed")

    start_time = time.time()

    for i, task_id in enumerate(test_task_ids):
        if task_id in completed_ids:
            continue

        done = len(all_results)
        if done > len(completed_ids):
            elapsed = time.time() - start_time
            avg = elapsed / (done - len(completed_ids))
            remaining = len(test_task_ids) - done
            eta_min = avg * remaining / 60
            eta_str = f", ETA: {eta_min:.0f}min"
        else:
            eta_str = ""

        print(f"[{i+1}/{len(test_task_ids)}] {task_id}{eta_str}")
        result = run_scaffold_task(task_id, max_steps=40)
        all_results.append(result)
        completed_ids.add(task_id)

        with open(checkpoint_file, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")

        status = "OK" if result["success"] else "FAIL"
        summ = f" summ={result['summarizer_invocations']}"
        corr = f" corr={result['corrector_changes']}"
        err = f" [{result['error'][:50]}]" if result["error"] else ""
        print(f"  {status} steps={result['steps']} time={result['wall_time']:.1f}s{summ}{corr}{err}")

    total_time = (time.time() - start_time) / 60
    print(f"\nTotal time: {total_time:.1f} min")

    # --- 結果サマリ ---
    print("\n" + "=" * 60)
    print("PHASE 3 SCAFFOLD RESULTS")
    print("=" * 60)

    successes = sum(1 for r in all_results if r["success"])
    total = len(all_results)
    errors = sum(1 for r in all_results if r["error"])
    times = [r["wall_time"] for r in all_results]
    summ_total = sum(r["summarizer_invocations"] for r in all_results)
    corr_total = sum(r["corrector_changes"] for r in all_results)

    print(f"Tasks: {total}")
    print(f"Success: {successes}/{total} ({successes/total*100:.1f}%)")
    print(f"Errors: {errors}/{total}")
    print(f"Wall time: mean={sum(times)/len(times):.1f}s, total={sum(times)/60:.1f}min")
    print(f"Summarizer invocations: {summ_total}")
    print(f"Corrector changes: {corr_total}")

    # 難易度別
    print("\n=== By Difficulty ===")
    scaffold_by_d = {}
    for r in all_results:
        task = Task.load(task_id=r["task_id"])
        d = task.ground_truth.metadata["difficulty"]
        if d not in scaffold_by_d:
            scaffold_by_d[d] = {"total": 0, "success": 0}
        scaffold_by_d[d]["total"] += 1
        if r["success"]:
            scaffold_by_d[d]["success"] += 1

    for d in sorted(scaffold_by_d):
        info = scaffold_by_d[d]
        rate = info["success"] / info["total"] * 100
        print(f"  Difficulty {d}: {info['success']}/{info['total']} ({rate:.1f}%)")

    # 論文比較
    print("\n=== Paper Comparison (reference) ===")
    print(f"Bonsai-8B (ours):    0.0% -> {successes/total*100:.1f}%")
    print(f"Qwen3-8B FP16:       5.4% -> 8.9%")
    print(f"Qwen3-8B AWQ:        3.0% -> 5.9%")

    # エラーパターン
    error_types = Counter()
    for r in all_results:
        if r["error"]:
            if "exceeds" in r["error"]:
                error_types["context_overflow"] += 1
            else:
                error_types["other"] += 1

    print(f"\nContext overflow: Phase1=22, Phase3={error_types.get('context_overflow', 0)}")

    # レポート保存
    report = {
        "timestamp": datetime.now().isoformat(),
        "phase": "3-scaffold",
        "total_tasks": total,
        "successes": successes,
        "success_rate": successes / total if total > 0 else 0,
        "errors": errors,
        "total_wall_time_minutes": sum(times) / 60,
        "summarizer_invocations_total": summ_total,
        "corrector_changes_total": corr_total,
        "by_difficulty": {
            str(d): info for d, info in sorted(scaffold_by_d.items())
        },
        "error_patterns": dict(error_types),
    }

    report_file = RESULTS_DIR / "phase3_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_file}")


if __name__ == "__main__":
    main()
