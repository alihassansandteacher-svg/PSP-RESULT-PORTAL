# People's School — Sujawal Result Portal

A Flask result portal for the 2025–26 academic session. Includes class-specific and all-class GR lookup, subject marks, grade summaries, server-generated PDF cards, printing, and leadership/development credits. The interface uses local CSS, JavaScript, and an SVG favicon; it requires no frontend build or CDN services.

## Requirements and local setup

Python 3.11 or 3.12 is recommended. From the extracted project directory:

```sh
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```sh
source .venv/bin/activate
```

Then install and start:

```sh
python -m pip install -r requirements.txt
python -m flask --app app run --host 127.0.0.1 --port 5000
```

Visit http://127.0.0.1:5000. Use Flask rather than VS Code Live Server: this project requires a Python backend. No API key, database, Node.js, or npm installation is needed.

## Tests and build checks

```sh
python -m unittest discover -s tests -v
python -m compileall -q app.py tests
```

Optional browser regression checks (uses temporary synthetic student records):

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install firefox
python tests/browser_smoke.py
```

On Linux, if system browser dependencies are missing, install them using Playwright's documented OS dependency setup. Node.js users can additionally check syntax with `node --check static/script.js`.

There is no separate asset compilation step. Flask renders templates and serves the prepared static files directly.

## Production deployment

Use a Python-capable Linux host, not GitHub Pages. Keep student CSVs in private storage and mount them on the server. They are included in this delivered archive for continuity but ignored by Git to reduce accidental public publication. Never force-add them to a public repository.

Install dependencies and start the WSGI server:

```sh
python -m pip install -r requirements.txt
python -m gunicorn app:app --bind 0.0.0.0:8000 --workers 2 --timeout 30 --access-logfile -
```

Place an HTTPS reverse proxy in front of port 8000. For platforms that supply `$PORT`, the supplied `Procfile` uses:

```sh
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 30 --access-logfile -
```

Set `RESULT_DATA_DIR` to the absolute path containing the class CSVs. For example, in a POSIX shell before starting the server:

```sh
export RESULT_DATA_DIR=/srv/psp/private-data
```

The default data directory is the directory containing `app.py`, independent of the current working directory. Missing or invalid files are logged without crashing the whole portal. `/healthz` is a process liveness check; it does not certify that result files are ready. Verify `/api/classes` and the startup logs after deployment. Keep request logs private: legacy lookup URLs contain GR numbers. The app intentionally avoids logging student names or lookup identifiers itself.

This remains a GR-based lookup service without student authentication. A GR number is not a password. For restricted access, configure school SSO or an authenticated gateway and request limits at the hosting edge before exposing student records online. Public bulk student listings have been removed from the legacy stats endpoint. Do not interpret the new headers as a substitute for access control.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `RESULT_DATA_DIR` | Project directory | Private directory holding `class_6.csv` through `class_12.csv` |
| `ENABLE_CLASS_STATS` | `0` | Set to `1` to enable aggregate-only statistics; no student directory is returned |
| `PORT` | `5000` | Port when launching `python app.py`; hosting Procfile also reads this variable |

`.env.example` documents these variables; `.env` files are not automatically loaded. Set them in your shell or host settings. Debug mode is off when launching `python app.py`.

## Updating results

Keep existing CSV headers. GR fields must contain 1–20 ASCII digits; leading zeros are accepted. Leave mark cells blank when not provided, use `A` for absent, and use `0` for zero marks. Totals, grades, and percentages are taken from the school's records, not recalculated: subject maximum marks and grading rules were not supplied. Restart all WSGI workers after editing data because records load at startup.

Duplicate normalized GR numbers within a class block that student's lookup with HTTP 409, including PDF download. Matches across classes require selecting a specific class. Blank and nonnumeric identifiers are logged and excluded from lookup; the original CSVs remain unchanged. Fix these identifiers using the school's authoritative register, not guesses.

Classes 6 and 12 currently have headers but no student rows. They are displayed as not published. See `AUDIT_AND_TESTS.md` for the exact source-data issues and verification results.

## API compatibility

- `GET /api/classes` — classes and availability/publication flags.
- `GET /api/get-result/<class>/<gr>` — original record fields plus `class` and a shared `subjects` list.
- `GET /api/search-result/<gr>` — searches all loaded classes, rejects ambiguous matches.
- `GET /api/generate-pdf/<class>/<gr>` — downloadable PDF result card.
- `GET /api/class-stats/<class>` — disabled by default (403); aggregate count and mean only when enabled. The original public `students` directory was deliberately removed for privacy.

Error responses contain an `error` message with HTTP 400 (invalid input), 404 (missing record/class), or 409 (ambiguous record). API/PDF responses use `Cache-Control: no-store`.

## Project layout

```text
app.py                  Application factory, validation, lookup, PDF generation
class_6.csv … class_12.csv  Preserved source records (private, Git-ignored)
templates/index.html    Semantic page and result markup
static/style.css        Responsive interface and print styles
static/script.js        Forms, fetch state, safe DOM rendering, downloads
static/favicon.svg      Local brand asset
fonts/                  Embedded PDF fonts and license
requirements*.txt       Runtime and optional browser-test dependencies
Procfile                Production start command
tests/                  Backend and browser regression checks
```

Team names and roles are retained. Initial-based portraits replace unavailable third-party placeholder photographs. The original bundled Windows virtual environment and Python caches are excluded; recreate dependencies using the commands above.
