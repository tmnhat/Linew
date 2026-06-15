# Security Policy

## Supported versions

Only the latest release line on the `main` branch receives security fixes.
Older versions are not maintained.

| Version  | Supported          |
|----------|--------------------|
| `main`   | ✅ Yes             |
| older    | ❌ No              |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.**

Send a private report to the maintainers (open a *private* maintainer channel
or use GitHub's *Report a vulnerability* button on the Security tab). Include:

- A clear description of the issue and its impact.
- Steps to reproduce, ideally with a proof of concept.
- Affected version / commit SHA.
- Any known mitigations or workarounds.

You can expect:

- An acknowledgement within **72 hours**.
- A status update within **7 days**, with a plan for a fix or a rationale
  for declining.
- Credit in the release notes (unless you prefer to remain anonymous).

## Secrets and configuration

- **Never** commit `.env`, application passwords, API keys, or
  `google-service-account.json`. These are listed in `.gitignore` — keep it
  that way.
- Rotate any credential that has appeared in a commit, even if it has
  since been removed from history. Git history is forever.
- Production deployments should source secrets from a secret manager
  (Doppler, HashiCorp Vault, AWS Secrets Manager, etc.), not from `.env`
  files on disk.

## Best practices for operators

- Run the stack behind HTTPS (Caddy / Nginx with a real certificate).
- Keep Docker images up to date — `docker compose pull` regularly.
- Restrict the WordPress admin panel to a trusted IP range or VPN.
- Treat `data/archive/*.db` files as confidential if they contain user data.
- Backups (`app/backup/`) should be encrypted at rest when stored off-host.

## Hall of fame

We appreciate responsible disclosure. Reporters who follow this policy will
be acknowledged here (with their permission) once a fix ships.
