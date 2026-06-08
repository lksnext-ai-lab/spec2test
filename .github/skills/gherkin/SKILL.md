---
name: gherkin
description: Guide for generating high-quality Gherkin feature files for E2E automation with strong happy-path and edge-case coverage. Use when creating or refining .feature files.
---

# Skill: Gherkin Feature Authoring

This skill defines rules for writing readable, maintainable, and coverage-driven Gherkin feature files for UI E2E tests.

## Scope

Use this skill when you need to:
- Create new .feature files from requirements, crawls, or user flows.
- Improve existing scenarios for clarity and reuse.
- Add meaningful edge-case coverage.

## Core Rules

1. Use business language, not implementation details.
- Avoid Selenium terms such as click, xpath, css selector, wait, or DOM.
- Prefer domain intent: submit form, register owner, update pet.

2. Keep steps declarative and reusable.
- Describe what behavior happens, not how the UI is manipulated.
- Reuse identical phrasing for equivalent actions across scenarios.

3. Keep scenarios focused.
- One business rule per scenario.
- Prefer 3-5 steps per scenario.
- Split large scenarios that test multiple outcomes.

4. Cover both happy paths and edge cases.
- Include positive flow, validation failures, and boundary data.
- Add comment # Proposed edge case above agent-proposed cases.

5. Use Background only for shared semantic context.
- Maximum 3-4 steps.
- Do not place heavy setup data in Background.

## Good Practices (BRIEF-aligned)

1. Use cases and scenario titles start with verbs.
- Good: "Scenario: Validate credit card".
- Bad: "Scenario: Credit Card".

2. Actors are named with nouns.
- Good: "Given the Admin is logged in".
- Bad: "Given To Manage is logged in".

3. Keep scenario scope unified (one business rule).
- Good: "Scenario: Customer books a flight" (single outcome).
- Bad: "Scenario: Customer searches, books, and cancels a flight".

4. Write declarative steps that state what happens.
- Good: "When I log in".
- Bad: "When I click the OK button".

5. Use active sentences with clear subjects.
- Good: "Then the system validates the ID".
- Bad: "Then the ID is validated".

6. Distinguish user actions from system responses.
- Good: "When the customer submits the order" / "Then the system confirms the order".
- Bad: "When the system confirms the order".

7. Use Background for semantic context only.
- Good: "Background: Given I am an Admin".
- Bad: "Background: Given I create 1000 records".

8. Use Scenario Outline for data-driven rules.
- Good: One outline with an Examples table for roles.
- Bad: Copying the same scenario for each role.

9. Parameterize steps for reuse.
- Good: "When I buy \"5\" items".
- Bad: "When I buy five items".

10. Make titles intention-revealing.
- Good: "Scenario: Redirect to dashboard after login".
- Bad: "Scenario: Login".

11. Use ubiquitous business language.
- Good: "When the subscriber logs in".
- Bad: "When I POST to /api/login".

## Bad Practices to Avoid

1. Incidental details in functional scenarios.
- Bad: "Then I see the copyright footer".
- Good: "Then the user is logged in".

2. Conjunctive steps that combine actions.
- Bad: "Given I am logged in and I have added an item".
- Good: "Given I am logged in" / "And I have added an item".

3. Hard-coded data that becomes stale.
- Bad: "Then the date is \"2026-12-31\"".
- Good: "Then the date should be 30 days from today".

4. Scenario Outline overuse.
- Bad: Examples table with dozens of invalid email formats.
- Good: 1-3 representative invalid email cases.

5. Superfluous scenarios.
- Bad: "Scenario: Login page loads" plus "Scenario: User logs in".
- Good: Keep only "Scenario: User logs in".

6. Imperative, procedural wording.
- Bad: "When I type \"bob\" into field \"user\"".
- Good: "When I log in as \"Bob\"".

7. Background overuse.
- Bad: "Background: Given I create 1000 records".
- Good: "Background: Given I am an Admin".

## File Structure

Each feature file should follow:

- Optional tags
- Feature title and short business goal
- Optional Background
- Scenarios and Scenario Outlines

Example layout:

```gherkin
@pet-management
Feature: Pet Management
  As a clinic staff member, I want to manage pets for owners
  so that records remain accurate.

  Background:
    Given the application is running
    And a registered owner exists in the system

  Scenario: Add a new pet to an existing owner
    When I add a new pet with valid details
    Then the pet should appear in the owner's profile
```

## Scenario Outline Guidance

Use Scenario Outline when the same business rule is validated with multiple data variations.

- Use placeholders like <pet_type>.
- Keep examples representative, not exhaustive.
- Target up to 8-10 rows in one examples table.

## Quality Checklist

Before finishing, verify:
- Every scenario title is intention-revealing.
- No imperative UI mechanics in steps.
- No duplicate scenarios.
- Edge cases are present and clearly marked when proposed.
- Syntax is valid Gherkin.
