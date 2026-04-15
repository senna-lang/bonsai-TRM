## ADDED Requirements

### Requirement: AppWorld installs and runs on target environment
The system SHALL install AppWorld and its data bundle, and execute at least one task with a dummy agent.

#### Scenario: Installation and data download
- **WHEN** `pip install appworld && appworld install && appworld download data` is executed
- **THEN** the installation completes without errors and task data is available

#### Scenario: Dummy agent execution
- **WHEN** a dummy agent (AppWorld's built-in tutorial) is run on a single task
- **THEN** the task completes (pass or fail) without runtime errors

### Requirement: Bonsai connects to AppWorld agent loop
The system SHALL replace the LLM backend in AppWorld's `simplified_react_code_agent` with Bonsai-8B.

#### Scenario: End-to-end single task
- **WHEN** the modified agent runs a single difficulty-1 task with Bonsai as LLM backend
- **THEN** the task loop executes (agent sends actions, receives observations) and terminates normally (success or max-turns)

### Requirement: Pilot evaluation produces actionable scope data
The system SHALL run 5-10 difficulty-1 tasks and produce data sufficient to decide Phase 1 scope.

#### Scenario: Pilot run
- **WHEN** 5-10 difficulty-1 tasks are run with Bonsai baseline
- **THEN** the following data is collected per task: success/failure, failure category, turn count, wall-clock time, LLM input/output logs
