## ADDED Requirements

### Requirement: Summarizer compresses history when context exceeds threshold
The system SHALL invoke a Summarizer role to compress conversation history when predefined thresholds are exceeded. The Summarizer runs on the same frozen model with a different system prompt.

#### Scenario: History compression trigger (Bonsai-adjusted)
- **WHEN** the accumulated conversation history exceeds **12,000 characters or 3,000 tokens** (Bonsai-adjusted; paper uses 24,000 chars / 6,000 tokens for Qwen3-8B)
- **THEN** the Summarizer is invoked before the next Agent turn to produce a compressed summary

#### Scenario: Message retention strategy (N-first, K-last)
- **WHEN** the Summarizer compresses history
- **THEN** it retains the first N messages and the last K messages verbatim, summarizing the intermediate history. Initial values: **N=13, K=3** (Bonsai-adjusted; paper uses N=26, K=6 for Qwen3-8B with 12K/32K context). These values should be tuned based on Phase 0 context length observations.

#### Scenario: Critical artifact preservation
- **WHEN** the Summarizer compresses history
- **THEN** the summary retains verbatim (not paraphrased): authentication tokens and credentials obtained during execution, API endpoint names and their observed response schemas, error patterns and their resolutions, pagination states and iteration progress, task completion status indicators

#### Scenario: Below threshold bypass
- **WHEN** the conversation history is below both thresholds (12,000 characters AND 3,000 tokens)
- **THEN** the Summarizer is not invoked and the full history is passed to the Agent

#### Scenario: Separate inference endpoint
- **WHEN** the Summarizer is invoked
- **THEN** it runs as a separate LLM call with its own system prompt, using the same frozen Bonsai model weights
