## ADDED Requirements

### Requirement: Corrector revises Agent output without access to conversation history
The system SHALL pass Agent output through a Corrector role that operates on the proposed action and API documentation only, **without access to the conversation history h_t**. This history isolation is an intentional regularizer (per paper Eq. 3) that prevents the Corrector from inheriting the Agent's potentially corrupted reasoning chain.

#### Scenario: Corrector input isolation
- **WHEN** the Corrector is invoked
- **THEN** it receives only: (1) the Agent's proposed code output `a_t`, (2) relevant API documentation `d_t` for endpoints referenced in the code, and (3) the most recent execution result if a prior step failed. It does NOT receive the conversation history.

#### Scenario: API schema correction via documentation
- **WHEN** the Agent generates an API call with incorrect parameter names or types
- **THEN** the Corrector consults the API documentation `d_t` and attempts to fix the call to match the correct schema. If uncertain, the Corrector queries `apis.api_docs.show_api_doc(...)` to retrieve the documentation.

#### Scenario: Code format enforcement
- **WHEN** the Corrector revises the action
- **THEN** the output contains exactly one code block, includes at least one `apis.*` call, and matches API documentation argument names exactly (per paper specification)

#### Scenario: Loop breaking
- **WHEN** the Agent generates the same or substantially similar action as the previous N turns
- **THEN** the Corrector modifies the action to break the loop, grounded in API documentation rather than conversation history

#### Scenario: Parse error fallback
- **WHEN** the Corrector's own output fails to parse as valid code
- **THEN** the system falls back to the original Agent output without modification

### Requirement: Corrector limitation at higher difficulties is acknowledged
The Corrector's history isolation means it cannot access state variables (access tokens, user IDs) established in earlier trajectory steps. This is a known trade-off (paper p.7): stability for simple tasks vs. state awareness for complex tasks.

#### Scenario: Difficulty-3 degradation
- **WHEN** a difficulty-3 task requires the Corrector to reference state variables from earlier turns
- **THEN** the Corrector may hallucinate placeholder values. This is expected behavior and should be logged for analysis, not treated as a bug.
