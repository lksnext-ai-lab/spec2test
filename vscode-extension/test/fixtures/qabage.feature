# Inputs: SoA.md, QABAGE.md
# Created: 2026-09-30

Feature: Assess Gherkin scenarios against the QABAGE quality attributes
  As a quality engineer
  I want each scenario scored against the eight QABAGE attributes
  So that I know which scenarios violate which attribute

  Background:
    Given a Gherkin suite has been loaded for assessment

  # Source: QABAGE.md | Created: 2026-09-30
  Scenario: Flag a scenario that lacks a When step
    Given a scenario "Check the idle server" without a "When" step
    When the suite is assessed
    Then the scenario "Check the idle server" is marked as not integrous

  # Source: QABAGE.md | Created: 2026-09-30
  Scenario: Detect semantic duplicates within one feature file
    Given a feature file with these scenarios:
      | id  | event                        | outcome                       |
      | mu1 | update language to "Polish"  | default language is "Polish"  |
      | mu2 | update language to "Turkish" | default language is "Turkish" |
    When the suite is assessed
    Then the scenarios "mu1, mu2" are marked as semantic duplicates

  # Source: QABAGE.md | Created: 2026-09-30
  Scenario: Detect a feature that lacks a prerequisite scenario
    Given a feature file whose only scenario adds a person to a running address book
    When the suite is assessed
    Then the feature is marked as incomplete

  # Source: SoA.md | Created: 2026-09-30
  Scenario: Route a low-confidence judgement to the LLM
    Given the fast triage model answers "Clarity" with confidence "low"
    When the suite is assessed
    Then the judgement is decided by "LLM"
