## ADDED Requirements

### Requirement: Evaluation harness runs all tasks with checkpoint recovery
The system SHALL execute all tasks in the determined scope with automatic checkpoint and resume capability.

#### Scenario: Normal execution
- **WHEN** the evaluation harness is started with a task list
- **THEN** each task is executed sequentially, and results are saved to persistent storage after each task

#### Scenario: Session interruption and resume
- **WHEN** the evaluation is interrupted (Colab session timeout) and restarted
- **THEN** already-completed tasks are skipped and evaluation resumes from the next incomplete task

### Requirement: LLM interaction logs are captured per turn
The system SHALL capture all LLM inputs and outputs for every turn of every task.

#### Scenario: Log completeness
- **WHEN** a task completes (success or failure)
- **THEN** a JSON Lines file exists containing: turn number, full prompt sent to LLM, full LLM response, AppWorld observation, and wall-clock time for each turn

### Requirement: Evaluation uses paper-consistent parameters
The system SHALL use the same evaluation parameters as McClendon et al. (2026) for comparability.

#### Scenario: Greedy decoding
- **WHEN** the evaluation harness calls the LLM
- **THEN** it uses `temperature=0` (greedy decoding), `seed=100`, and `max_tokens=3000` (max completion tokens per generation)

#### Scenario: Single-trial evaluation
- **WHEN** a task is evaluated
- **THEN** it is run exactly once (pass@1, single trial) — not pass@4 or Avg@4

### Requirement: Failure mode classification uses paper's 9-category taxonomy
The system SHALL classify each failed task using the same 9-category taxonomy as the paper (Table 1).

#### Scenario: Failure categorization
- **WHEN** a task fails
- **THEN** the failure is classified into one of the 9 categories:
  1. Authentication / credential issue
  2. Reasoning / planning error
  3. Wrong API params / schema mismatch
  4. Other
  5. Missing API call / wrong API name
  6. Repetition / loop
  7. Formatting / code block error
  8. Pagination / incomplete iteration
  9. Context length / token limit
