Always create and run a minimal automated test (happy path plus 1 small edge case) to verify that your suggestion or code change works; include a brief PASS/FAIL summary in your reply.

Try to write as little code as possible.

Do exlain as well, how everything works.

Engineering principles to follow (SOLID, KISS, DRY)

- SOLID
	- Single Responsibility: Functions, classes, and modules must do one thing well. If a unit handles multiple concerns, split it.
	- Open/Closed: Prefer adding new code over modifying stable code paths. Extend via small adapters, strategies, or hooks.
	- Liskov Substitution: Respect contracts. Subtypes must not weaken preconditions or change return shapes/semantics.
	- Interface Segregation: Keep interfaces small and focused. Avoid “god” objects with many unrelated methods.
	- Dependency Inversion: Depend on abstractions, not concretions. Inject dependencies; avoid hard-coded globals/singletons.

- KISS
	- Choose the simplest design that solves the problem. Avoid unnecessary abstractions and premature optimization.
	- Prefer straight-line code, clear names, and small functions (~30–40 lines max) over cleverness.
	- Use the standard library first; add third-party deps only when they clearly reduce risk/complexity.
	- Fail fast with clear errors and minimal branching; remove dead code and unused parameters.

- DRY
	- Eliminate duplication by extracting helpers/utilities and reusing them across modules.
	- Centralize constants/configuration. Parameterize templates instead of copy/paste variants.
	- When adding code, scout for existing similar logic and refactor to a single implementation.

Implementation and review hygiene

- Keep changes small, cohesive, and reversible. Maintain backward compatibility unless explicitly requested otherwise.
- Add or update minimal tests (happy path + 1–2 edge cases) for any new public behavior. Keep tests fast and deterministic.
- Type annotate public functions and critical paths. Prefer pure functions where practical; isolate side effects.
- Document public functions briefly (1–3 lines) and record trade-offs in the PR description.
- Run build/lint/tests locally and ensure PASS before completion. Address new warnings or clearly justify deferrals.

Refactoring rules during assistance

- If you touch logic already present elsewhere, consolidate to avoid drift. Don’t duplicate code across features.
- Prefer composition over inheritance when introducing extensibility points.
- If a change impacts >3 files or alters public APIs, include a short migration note and update examples/usages.
- For risky behavior changes, use feature flags or configuration toggles when feasible.

Defaults and style

- Consistent naming, explicit returns, and clear error handling. Avoid hidden side effects; validate inputs at boundaries.
- Keep functions/classes small; extract private helpers when complexity grows.
- Prefer clarity over cleverness. If a reviewer could misread it, rewrite it.

Try to stick to the MVC (model, view, controller) principles as closely as possible.