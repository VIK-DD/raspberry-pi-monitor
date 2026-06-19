# Contributing to Pi Guardian

Thanks for your interest in improving Pi Guardian! Contributions of all
kinds are welcome — bug reports, feature ideas, documentation fixes and pull
requests.

## Getting started

1. **Fork** the repository and clone your fork.
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy the environment template and enable demo mode so you can run without a
   Raspberry Pi:
   ```bash
   cp .env.example .env
   echo "DEMO_MODE=1" >> .env
   ```
4. Run the dashboard:
   ```bash
   cd dashboard && uvicorn main:app --reload --port 8080
   ```
5. Open <http://localhost:8080>.

## Development guidelines

- **Keep it dependency-light.** The project intentionally runs on a Raspberry
  Pi Zero 2 W. Prefer the standard library; justify any new dependency.
- **Code style.** Follow PEP 8. Keep functions small and readable.
- **English only.** All code, comments, UI strings and docs are in English.
- **Never commit secrets.** `.env`, certificates, databases and logs are
  gitignored — keep it that way. Use `.env.example` for new settings.
- **Demo mode.** If you add a data source, also add a matching synthetic
  payload in `demo_data.py` so the app keeps working with `DEMO_MODE=1`.

## Running the tests

```bash
pip install pytest
pytest
```

## Submitting a pull request

1. Create a feature branch: `git checkout -b feature/my-change`.
2. Make your change with clear, focused commits.
3. Make sure the app still starts in demo mode and the tests pass.
4. Open a pull request describing **what** changed and **why**.

## Reporting bugs

Open an issue and include:

- What you expected to happen and what actually happened.
- Steps to reproduce.
- Your environment (OS, Python version, Raspberry Pi model if relevant).
- Relevant log output (with any secrets redacted).

By contributing you agree that your contributions are licensed under the
project's [Apache 2.0 License](LICENSE).
