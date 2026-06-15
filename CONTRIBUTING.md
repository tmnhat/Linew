# Contributing to Linew

Thanks for your interest in improving Linew! This guide covers the workflow,
coding conventions, and review process.

## Code of conduct

Be respectful. Assume good faith. Disagree on ideas, not on people. Harassment
of any kind is not tolerated.

## Workflow

1. **Fork** the repository and clone your fork.
2. Create a feature branch off `main`:
   ```bash
   git checkout -b feat/short-description
   ```
3. Make your changes. Keep commits small and focused; write meaningful
   commit messages (`feat: …`, `fix: …`, `refactor: …`, `docs: …`,
   `test: …`).
4. Run the test suite and the linter before pushing:
   ```bash
   pytest tests/ -v
   ```
5. Push your branch and open a Pull Request against `main`.
6. Address review feedback by pushing additional commits (or force-push if
   you squashed locally).

## Project layout

| Path             | What lives here                                            |
|------------------|------------------------------------------------------------|
| `app/`           | FastAPI application — routers, services, models, pipeline  |
| `app/pipeline/`  | State machine, tasks, locks, stability primitives          |
| `app/prediction/`| Forecasting models and data fetchers                        |
| `dashboard/`     | React + Vite single-page app                               |
| `wordpress/`     | Custom theme and plugin source                             |
| `tests/`         | Pytest suite                                              |
| `alembic/`       | Database migrations                                        |
| `scripts/`       | Operational shell scripts                                 |
| `docs/`          | Long-form documentation                                    |

## Coding conventions

- **Python**: PEP 8 with type hints. Prefer `async` for I/O. Use Pydantic
  models for request/response schemas. Keep modules focused — split a file
  if it exceeds ~400 lines.
- **Imports**: `from app.X import Y` is preferred over `import app.X`. No
  wildcard imports. Sort with `isort`/`ruff`.
- **Formatting**: `ruff format` (or `black` if you prefer). Lint with `ruff
  check` (or `flake8`).
- **TypeScript / React**: Functional components, hooks, no `any` unless
  wrapped in a comment that explains why. ESLint + Prettier.
- **PHP (WordPress theme)**: Follow [WordPress PHP coding standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/php/).
  Escape everything, sanitize all input, use nonces for state-changing
  requests.

## Testing

- Add or update tests for every behavior change.
- Unit tests live next to the existing pytest files; use `pytest-asyncio` for
  async code and `unittest.mock` for collaborators.
- Keep tests deterministic — no real network calls, no real Redis/Postgres
  required (mock at the boundary).

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(pipeline): add semantic deduplication guard
fix(writer): resolve image_keywords reference order
docs(readme): clarify Google Drive backup setup
```

## Pull request checklist

- [ ] Branch is up to date with `main`.
- [ ] `pytest tests/` passes locally.
- [ ] New behavior is covered by tests.
- [ ] No secrets, credentials, or generated data are committed.
- [ ] Public APIs (routes, function signatures) are documented in the
      docstring.
- [ ] The PR description explains **why** the change is needed and how it
      was validated.

## Reporting issues

When filing a bug, please include:

- Linew version (commit SHA or tag).
- Environment (Docker / bare metal, OS, Python version).
- Steps to reproduce, expected vs. actual behavior, and relevant log output.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](./LICENSE).
