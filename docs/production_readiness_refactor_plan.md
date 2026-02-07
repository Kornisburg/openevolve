# OpenEvolve Production-Readiness Refactor Plan

## Repository understanding (current state)

OpenEvolve is a Python package and CLI for LLM-driven evolutionary code optimization, with three main usage modes:

1. **CLI workflow** via `openevolve-run`/`openevolve/cli.py`.
2. **Library workflow** via high-level APIs in `openevolve/api.py`.
3. **Research/integration workflows** via examples and integration tests.

Core runtime path today:

- `OpenEvolve` in `openevolve/controller.py` orchestrates the run loop and coordinates prompt sampling, LLM generation, evaluation, and DB updates.
- `ProgramDatabase` in `openevolve/database.py` stores programs, supports MAP-Elites + island mechanics, and persists state.
- `Evaluator` and process controller modules handle candidate evaluation and execution isolation (`openevolve/evaluator.py`, `openevolve/process_parallel.py`).
- Configuration is dataclass-driven in `openevolve/config.py`, loaded from YAML and CLI overrides.

This is a strong foundation (meaningful test coverage and several entry points), but it is still organized as a research-first codebase rather than an operations-first product.

## Production-readiness gaps observed

### 1) Large, high-blast-radius modules

Several critical modules are very large (e.g., `database.py` at 2.5K+ lines, `process_parallel.py` and `evaluator.py` around 700 lines), which increases regression risk and slows maintenance.

### 2) Layering and duplication issues

`controller.py` imports formatting helpers from `utils/format_utils.py` but also defines similarly named local formatting functions, signaling architectural drift and unclear ownership of utilities.

### 3) Incomplete governance for quality gates

The repository has Black/isort/mypy config and many tests, but the `Makefile` only runs Black under `lint`; type checks and style checks are not consistently codified in one default CI-quality command.

### 4) API/CLI/domain concerns are intermixed

High-level APIs, orchestration, persistence, and process execution are tightly coupled. This makes it difficult to:

- swap infrastructure components,
- run in distributed/cloud workers,
- enforce strict failure boundaries.

### 5) Production operations features are not explicit

There is some tracing and artifact management, but this should be formalized into:

- structured logs,
- metrics standards,
- clear SLO-driven health surfaces,
- versioned checkpoint/DB schema lifecycle policies.

## Target architecture (refactor direction)

Move to a clean, layered architecture with explicit boundaries:

- **Domain layer**: evolution primitives (Program, metrics, island/migration logic, selection strategies).
- **Application layer**: run orchestration use-cases (`run_iteration`, `resume_checkpoint`, `migrate_islands`).
- **Infrastructure layer**: LLM clients, persistence backends, evaluator runtime/executors, artifact storage.
- **Interface layer**: CLI and library API as thin adapters.

### Suggested package map

- `openevolve/domain/`
  - `program.py`, `population.py`, `selection.py`, `migration.py`
- `openevolve/application/`
  - `engine.py`, `iteration_service.py`, `checkpoint_service.py`
- `openevolve/infrastructure/`
  - `db/`, `llm/`, `executors/`, `artifacts/`, `observability/`
- `openevolve/interfaces/`
  - `cli.py`, `api.py`

## Refactor roadmap (phased)

### Phase 0 (1-2 weeks): Safety rails before large changes

- Freeze public API contracts with characterization tests for `openevolve/api.py` and CLI behavior.
- Add a single quality gate command (e.g., `make verify`) running:
  - unit tests,
  - `pytest -m "not integration"`,
  - mypy,
  - formatting/lint checks.
- Establish baseline benchmarks (iteration throughput, eval latency, memory).

### Phase 1 (2-3 weeks): Extract domain model from `database.py`

- Split `Program` and related datatypes into dedicated domain modules.
- Extract MAP-Elites feature binning/scaling and island migration into testable strategy classes.
- Keep current JSON storage behavior behind a `ProgramRepository` interface.

Deliverable: functionally equivalent behavior with lower cyclomatic complexity and finer-grained tests.

### Phase 2 (2-3 weeks): Isolate orchestration/application services

- Refactor `OpenEvolve` loop into application services with explicit dependency injection:
  - prompt service,
  - model generation service,
  - evaluation service,
  - persistence service.
- Eliminate utility duplication and centralize formatting/logging helpers.

Deliverable: smaller `controller` surface and composable execution pipeline.

### Phase 3 (2 weeks): Harden evaluator/process execution

- Introduce executor abstractions (local process, sandboxed container, remote worker).
- Add strict timeout/cancellation semantics and standardized error taxonomy.
- Add idempotent retry policy where safe.

Deliverable: operationally predictable runtime behavior under load/failure.

### Phase 4 (2 weeks): Observability and operations hardening

- Structured logs with run_id/iteration/program_id correlation keys.
- Metrics (Prometheus/OpenTelemetry) for:
  - iteration duration,
  - eval success/failure rates,
  - LLM call latency/token usage,
  - checkpoint save/load timings.
- Add health endpoints for long-running server-style deployments.

### Phase 5 (ongoing): Platform maturity

- Multi-backend persistence (filesystem -> sqlite/postgres option).
- Formal migration framework for checkpoints/database schemas.
- Release engineering: semantic versioning policy + changelog automation.

## Concrete production readiness backlog

1. **Module decomposition epic**: break up `database.py`, `evaluator.py`, `process_parallel.py`.
2. **Configuration hardening**:
   - strict schema validation,
   - deprecation warnings + migration tool for old config keys.
3. **Security controls**:
   - evaluator execution sandbox profile,
   - artifact redaction policy,
   - secret handling policy verification.
4. **Reliability controls**:
   - circuit breakers around LLM providers,
   - bounded queues and backpressure in parallel execution.
5. **Developer experience**:
   - `make verify` + `make ci-local`,
   - architecture decision records (ADRs).

## Success criteria (definition of done)

- **Maintainability**: no core module > 500 lines in critical path.
- **Quality**: >90% coverage for domain/application layers.
- **Reliability**: deterministic checkpoint resume across supported environments.
- **Operability**: dashboards and alerts for key run metrics.
- **Backward compatibility**: existing CLI commands and `openevolve.api` public behavior preserved for one major cycle.

## Recommended first implementation slice

If implementing immediately, start with:

1. Introduce `ProgramRepository` and migrate persistence calls behind it.
2. Extract feature binning/migration logic from `ProgramDatabase` into standalone strategies.
3. Convert `OpenEvolve` iteration step into an `IterationService` with injected dependencies.

This delivers the highest long-term leverage while minimizing immediate product risk.
