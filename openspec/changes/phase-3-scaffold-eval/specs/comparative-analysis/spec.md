## ADDED Requirements

### Requirement: Scaffold evaluation uses identical conditions to baseline
The system SHALL run the scaffold agent on the same task set, with the same max turns and timeout, as the Phase 1 baseline.

#### Scenario: Identical task set
- **WHEN** the scaffold evaluation is run
- **THEN** it executes on exactly the same tasks as the Phase 1 baseline, in the same order

### Requirement: Comparative analysis quantifies improvement
The system SHALL produce a comparison report between baseline and scaffold results.

#### Scenario: Achievement rate comparison
- **WHEN** both baseline and scaffold evaluations are complete
- **THEN** a report shows: baseline achievement rate, scaffold achievement rate, absolute improvement, and relative improvement

#### Scenario: Failure mode shift analysis
- **WHEN** both evaluations are complete
- **THEN** a report shows the failure mode distribution for each, highlighting categories where scaffold reduced failures (mechanical) and where it did not (reasoning)
