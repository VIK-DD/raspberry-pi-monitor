# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅        |

## Reporting a vulnerability

Please report security issues **privately** through GitHub Security Advisories
— open the **Security** tab and choose **"Report a vulnerability"** — instead of
filing a public issue. I will respond as soon as possible.

## Hardening notes

- **Never commit secrets.** `.env`, TLS certificates, databases and logs are
  excluded by `.gitignore` — keep them out of version control.
- **`DEMO_MODE` disables authentication on purpose.** Never expose a demo-mode
  instance to the public internet.
- For real deployments, put the dashboard behind a reverse proxy with TLS, or
  expose it only over a private network / VPN (e.g. Tailscale).
- Passwords are stored as salted **PBKDF2-SHA256** hashes.
