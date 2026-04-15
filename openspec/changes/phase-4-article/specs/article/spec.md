## ADDED Requirements

### Requirement: Article covers all experimental results with honest framing
The article SHALL present baseline and scaffold results with appropriate caveats about comparison limitations.

#### Scenario: Honest comparison with paper
- **WHEN** the article references McClendon et al. (2026) Qwen3-8B results
- **THEN** it explicitly states that the paper's numbers were not reproduced in the author's environment and that direct comparison includes environmental differences

#### Scenario: Any-result framing
- **WHEN** the scaffold shows improvement over baseline
- **THEN** the article frames it as "the technique works at 1-bit scale"
- **WHEN** the scaffold shows no improvement
- **THEN** the article frames it as "analysis of 1-bit LLM limitations for agent tasks"

### Requirement: Repository is reproducible
The GitHub repository SHALL contain sufficient information for others to reproduce the experiments.

#### Scenario: Reproduction
- **WHEN** a reader follows the README instructions
- **THEN** they can install dependencies, set up the inference backend, and run at least a subset of tasks
