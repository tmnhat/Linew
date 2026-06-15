# Linew

> AI-powered news automation platform — collect, enrich, write, govern, publish, and distribute.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

Linew is an end-to-end pipeline that turns raw web signals into publish-ready,
SEO-optimized articles on WordPress, then distributes them to Telegram, Facebook,
X (Twitter), and email newsletters. It also ships a stock & crypto **prediction
system** (TimesFM + Holt-Winters) and a WordPress widget for displaying
forecasts on your site.

---

## Features

- **Pipeline orchestration** — Signal → Categorize → Score → Research → Write
  → Govern → Publish, with distributed locks, hard-stop signals, and circuit
  breakers for AI & external services.
- **AI Gateway** — Provider-agnostic interface for OpenAI, Anthropic, and
  Vertex; per-task model and prompt configuration.
- **WordPress publisher** — REST + Application Password auth, SEO meta, schema
  markup, OpenGraph, and image generation.
- **Multi-channel distribution** — Telegram, Facebook, X, and SMTP newsletter,
  each with its own enable/pause, rate limit, and idempotency lock.
- **Prediction system** — TimesFM 2.5-200m with Holt-Winters and linear
  fallbacks; covers VN stocks, crypto, and macro indicators (FRED).
- **React dashboard** — Vite + Tailwind UI to control the pipeline, browse
  articles, view predictions, and inspect logs.
- **Production-grade infra** — Docker Compose stack (FastAPI, Celery worker,
  PostgreSQL, Redis, Temporal, NATS, FlareSolverr, WordPress) behind an Nginx
  reverse proxy.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Nginx / Caddy (reverse proxy)               │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  FastAPI API │  WordPress   │  Dashboard   │   Celery Worker   │
│  (port 8000) │  (port 8888) │  (React SPA) │   (async tasks)   │
├──────────────┴──────────────┴──────────────┴───────────────────┤
│                Core infrastructure (Docker)                     │
├──────────┬──────────┬──────────┬──────────┬────────────────────┤
│ Postgres │  Redis   │ Temporal │ NATS     │   FlareSolverr     │
└──────────┴──────────┴──────────┴──────────┴────────────────────┘
```

The app code lives in `app/` and is split into:

| Module             | Responsibility                                                |
|--------------------|---------------------------------------------------------------|
| `app/pipeline/`    | State machine, tasks (categorize, score, research, write…)    |
| `app/ai_gateway/`  | Pluggable LLM client (OpenAI / Anthropic / Vertex)            |
| `app/publisher/`   | WordPress REST integration + SEO helpers                      |
| `app/distribution/`| Telegram, Facebook, X, Newsletter dispatchers                 |
| `app/prediction/`  | Forecaster (TimesFM / Holt-Winters), data fetchers, alerts    |
| `app/archive/`     | PostgreSQL → SQLite hot/cold storage and retention jobs       |
| `app/backup/`      | PostgreSQL, WordPress, and Google Drive backup routines       |
| `app/worker/`      | Celery app, beat schedule, task wiring                        |
| `app/routers/`     | FastAPI routers (storage, prediction, distribution, …)        |
| `dashboard/`       | React + Vite SPA                                              |
| `wordpress/`       | Custom `linew-viral` theme + `prediction-widget` plugin       |

---

## Quick start (Docker)

> Requires Docker 24+ and Docker Compose v2.

```bash
git clone https://github.com/<your-org>/linew.git
cd linew

# 1. Copy and edit environment template
cp .env.example .env
$EDITOR .env

# 2. Build and start the stack
docker compose build
docker compose up -d

# 3. Run database migrations
docker compose exec api alembic upgrade head

# 4. Open the dashboard
open http://localhost:5173
```

The API is exposed on `http://localhost:8000`, WordPress on
`http://localhost:8888`, and the dashboard (Vite dev server) on
`http://localhost:5173`. See [`LINEW-SETUP-GUIDE.md`](./LINEW-SETUP-GUIDE.md)
for the full production walkthrough.

### Local development (without Docker)

```bash
# Backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Dashboard
cd dashboard
npm install
npm run dev
```

---

## Configuration

All runtime configuration is environment-driven. The canonical reference
lives in `.env.example` — copy it to `.env` and fill in the values for your
deployment.

Key variables:

| Variable             | Purpose                                                |
|----------------------|--------------------------------------------------------|
| `DATABASE_URL`       | PostgreSQL DSN                                         |
| `REDIS_URL`          | Redis URL (locks, broker, cache)                       |
| `AI_PROVIDER`        | `openai` / `anthropic` / `vertex`                      |
| `OPENAI_API_KEY`     | OpenAI key (if `AI_PROVIDER=openai`)                   |
| `VERTEX_API_KEY`     | Vertex API key                                         |
| `WP_URL`             | WordPress site URL (e.g. `https://litimez.ai`)         |
| `WP_USERNAME`        | WordPress username                                     |
| `WP_APP_PASSWORD`    | WordPress application password                         |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token                                     |
| `NEWSLETTER_SMTP_*`  | SMTP credentials for the newsletter channel            |
| `TIMESFM_ENABLED`    | `true` to use TimesFM, `false` for Holt-Winters only   |

> **Never commit a real `.env` file.** Only `.env.example` (with empty
> placeholders) is tracked.

---

## Testing

```bash
# Activate the venv first
source venv/bin/activate

# Run the full suite
pytest tests/ -v

# Run a single file
pytest tests/test_pipeline.py -v
```

Test dependencies are declared in `requirements-dev.txt` (if present) or the
`dev` extras of `requirements.txt`.

---

## Operations

- **Run the pipeline** — `POST /api/pipeline/start` or click **Start** in the
  dashboard. The Celery beat schedule also triggers recurring tasks.
- **Hard stop** — `POST /api/pipeline/stop`. A Redis stop-signal is checked
  before every batch and every article.
- **Logs** — `docker compose logs -f api worker`.
- **Backups** — `app/backup/tasks.py` is scheduled by Celery beat; PostgreSQL
  dumps, WordPress uploads, and Google Drive backups are produced on rotation.
- **Archive** — Hot rows in PostgreSQL are periodically offloaded to SQLite
  files under `data/archive/` and pruned from the live DB.

See [`PRODUCTION_SETUP.md`](./PRODUCTION_SETUP.md) and
[`WORDPRESS_SETUP.md`](./WORDPRESS_SETUP.md) for deployment specifics.

---

## Contributing

Contributions are welcome!

1. Fork the repo and create a feature branch (`git checkout -b feat/my-change`).
2. Run the tests locally (`pytest tests/`) and the linter.
3. Open a Pull Request describing the motivation, design, and test plan.
4. Be patient — maintainers review on a best-effort basis.

Please **do not** commit secrets, generated data (`data/archive/`, `*.db`),
or vendored dependencies (`node_modules/`, `venv/`) — they're all covered by
`.gitignore`.

---

## Security

If you discover a vulnerability, please **do not** open a public issue. Email
the maintainers (see `SECURITY.md` once published) with a description and
reproduction steps.

---

## License

This project is released under the [MIT License](./LICENSE).

## Acknowledgements

- WordPress and the [WP REST API](https://developer.wordpress.org/rest-api/)
  for content publishing.
- [TimesFM](https://github.com/google-research/timesfm) for the forecasting
  backbone.
- The FastAPI, SQLAlchemy, Celery, and React communities for the excellent
  open-source building blocks.
