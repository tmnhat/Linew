# Third-Party Licenses

This document lists the open-source dependencies used in the Linew project and their respective licenses.

## Project License

**Linew** is licensed under the **Apache License, Version 2.0**.

Copyright (c) 2026 Linew Contributors

---

## Python Dependencies

| Package | Version | License | Notes |
|---------|---------|---------|-------|
| fastapi | >=0.111.0 | MIT | Web framework |
| uvicorn | >=0.30.0 | BSD-3-Clause | ASGI server |
| pydantic | >=2.7 | MIT | Data validation |
| pydantic-settings | >=2.3 | MIT | Settings management |
| sqlalchemy | >=2.0 | MIT | ORM |
| alembic | >=1.13 | MIT | Database migrations |
| psycopg2-binary | >=2.9 | LGPL | PostgreSQL driver |
| celery | >=5.4 | BSD-3-Clause | Task queue |
| redis | >=5.0 | MIT | Redis client |
| feedparser | >=6.0 | BSD-2-Clause | RSS/Atom parsing |
| readability-lxml | >=0.8.1 | Apache-2.0 | Web scraping / article extraction |
| httpx | >=0.27 | BSD-3-Clause | HTTP client |
| beautifulsoup4 | >=4.12 | MIT | HTML parsing |
| lxml | >=5.2 | BSD-3-Clause | XML/HTML processing |
| openai | >=1.30 | Apache-2.0 | OpenAI API client |
| anthropic | >=0.25 | Apache-2.0 | Anthropic API client |
| requests | >=2.32 | Apache-2.0 | HTTP library |
| yfinance | >=0.2 | Apache-2.0 | Yahoo Finance |
| numpy | >=1.26 | BSD-3-Clause | Numerical computing |
| pandas | >=2.2 | BSD-3-Clause | Data analysis |
| torch | >=2.2 | Apache-2.0 | Machine learning |
| vnstock | >=0.3 | MIT | Vietnamese stock data |
| fredapi | >=0.5.0 | MIT | FRED economic data |
| dbnomics | >=0.5.0 | MIT | Economic data |
| finnhub-python | >=2.4.0 | ISC | Financial data |
| scipy | >=1.12 | BSD-3-Clause | Scientific computing |
| statsmodels | >=0.14 | BSD-3-Clause | Statistical models |
| websockets | >=12.0 | Apache-2.0 | WebSocket client/server |
| python-dotenv | >=1.0 | BSD-3-Clause | Environment variables |
| Pillow | >=10.3 | HPND | Image processing |
| python-jose | >=3.3 | MIT | JWT encoding/decoding |
| google-auth | >=2.28 | Apache-2.0 | Google auth |
| APScheduler | >=3.10 | MIT | Task scheduling |
| tweepy | >=4.14 | Apache-2.0 | Twitter API |
| aiotelegram | >=0.3 | MIT | Telegram bot |
| aiosmtplib | >=3.0 | MIT/Asahi | SMTP client |
| jinja2 | >=3.1 | BSD-3-Clause | Template engine |
| pytest | >=8.0 | MIT | Testing framework |
| pytest-asyncio | >=0.23 | Apache-2.0 | Async test support |
| email-validator | >=2.0 | CC0-1.0 | Email validation |
| asyncpg | >=0.29 | Apache-2.0 | Async PostgreSQL |
| gevent | >=24.2 | MIT | Async I/O |
| sse-starlette | >=2.0 | BSD-3-Clause | SSE support |

---

## JavaScript Dependencies (Dashboard)

| Package | Version | License | Notes |
|---------|---------|---------|-------|
| react | ^18.3.1 | MIT | UI library |
| react-dom | ^18.3.1 | MIT | DOM renderer |
| react-router-dom | ^6.22.0 | MIT | Routing |
| axios | ^1.6.7 | MIT | HTTP client |
| zustand | ^4.5.0 | MIT | State management |
| clsx | ^2.1.0 | MIT | Class name utility |
| date-fns | ^3.3.1 | MIT | Date utilities |
| vite | ^5.1.0 | MIT | Build tool |
| tailwindcss | ^3.4.1 | MIT | CSS framework |
| postcss | ^8.4.35 | MIT | CSS processing |
| autoprefixer | ^10.4.17 | MIT | CSS prefixes |
| eslint | ^8.56.0 | MIT | Linter |
| typescript | ^5.3.3 | Apache-2.0 | TypeScript |

---

## JavaScript Dependencies (Prediction Widget)

| Package | Version | License | Notes |
|---------|---------|---------|-------|
| react | ^18.2.0 | MIT | UI library |
| react-dom | ^18.2.0 | MIT | DOM renderer |
| chart.js | ^4.4.0 | MIT | Chart library |
| react-chartjs-2 | ^5.2.0 | MIT | React charts |
| axios | ^1.6.0 | MIT | HTTP client |
| vite | ^5.0.0 | MIT | Build tool |
| typescript | ^5.3.0 | Apache-2.0 | TypeScript |

---

## License Compatibility Notes

### License Status

As of the migration to Apache License 2.0, Linew contains **zero copyleft (GPL/AGPL) dependencies**. All previously identified GPL dependencies have been removed:

- **trafilatura** (GPL-3.0) — replaced with **readability-lxml** (Apache-2.0)
- **python-wordpress-xmlrpc** (GPL-2.0+) — removed (was in requirements.txt but never imported)

### Permissive Dependencies

All remaining dependencies use permissive or weak-copyleft licenses (MIT, BSD-3-Clause, Apache-2.0, ISC, etc.) that are fully compatible with Apache License 2.0.

### LGPL Dependency

- **psycopg2-binary** (LGPL) — PostgreSQL driver. psycopg2 is dynamically linked at runtime; the LGPL explicitly permits this usage pattern. Linew never statically links psycopg2 into distributed artifacts.

### Commercial APIs

The following services require API keys and have their own terms of service:
- OpenAI API
- Anthropic API
- Yahoo Finance (via yfinance)
- Finnhub
- Google Services

---

## Attribution

Third-party code bundled in build artifacts (like `dist/widget.iife.js`) retains its original licenses and copyright notices.

---

*Last updated: 2026-06-15*
