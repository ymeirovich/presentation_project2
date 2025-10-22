# Repository Guidelines

## Project Structure & Module Organization
- `src/mcp/` hosts the production MCP server, schemas, and tool wiring used by the JSON-RPC orchestrator.
- `src/mcp_lab/` contains the CLI entry point (`python -m src.mcp_lab`) and client/orchestrator prototypes used during local development.
- `src/agent/` retains reusable presentation, image, and validation modules; most services import from here rather than duplicating logic.
- `presgen_training*/` and `presgen-ui/` hold the avatar video and web UI stacks; refer to their phase guides before editing.
- Tests live in `tests/` (unit + smoke) and `test/` (ad-hoc integration fixtures). Generated artifacts land in `out/` and cache state in `output/`; keep these out of commits.

## Build, Test, and Development Commands
- `make smoke-test` runs the fast pytest target against `tests/test_cache_unit.py`.
- `make fmt` and `make lint` apply Black formatting and Flake8 checks across `src` and `tests`.
- `make run-orchestrator` (aliased to `python -m src.mcp_lab ./examples/report_demo.txt`) executes the end-to-end slide generation demo.
- `RUN_SMOKE=1 python -m pytest -q tests/test_orchestrator_live.py tests/test_batch_live.py` triggers live external calls; only run with valid API credentials.

## Coding Style & Naming Conventions
- Python code uses Black defaults (4-space indent, 88-char lines) and Flake8; pre-format before opening PRs.
- Module names stay lowercase_with_underscores; classes are PascalCase; async helpers and RPC handlers use verb-based snake_case.
- Central configuration belongs in `config.yaml` or under `config/`; environment-specific overrides should end in `_local.py` and remain untracked.

## Testing Guidelines
- Prefer pytest for new coverage; co-locate unit tests beside the module in `tests/` and name them `test_<feature>.py`.
- Mark network-dependent cases with `RUN_SMOKE` gating to keep CI green.
- Update or regenerate fixtures in `examples/` when API contracts change, and capture new outputs under `out/` for manual QA only.

## Commit & Pull Request Guidelines
- Follow the existing history: imperative subjects with optional prefixes (`feat:`, `fix:`, `docs:`); keep bodies focused on intent and impact.
- PRs should include: summary of behaviour, links to related docs/issues, test evidence (`make smoke-test` output or live run notes), and screenshots for UI/video-facing changes.

## Security & Configuration Tips
- Never commit service account JSON or OAuth tokens; use the checked-in samples (`presgen-service-account.json`) as placeholders only.
- Document any new ports or secrets in `config/` and the relevant deployment guide, and update `start_services.sh` if runtime entry points move.
