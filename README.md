# hh-cv-helper

Automates checking and publishing resumes on HeadHunter (hh.ru) using the HeadHunter OAuth2 API. It provides a small command‑line tool that keeps resumes "fresh" by republishing them if they haven't been updated recently.

---

## Table of contents

* [Project overview](#project-overview)
* [Features](#features)
* [Prerequisites](#prerequisites)
* [Repository structure](#repository-structure)
* [Installation](#installation)
* [Configuration](#configuration)

  * [HeadHunter application credentials](#headhunter-application-credentials)
  * [Environment variables](#environment-variables)
  * [Resumes list format](#resumes-list-format)
* [Initial authentication (OAuth)](#initial-authentication-oauth)

  * [Interactive on a desktop](#interactive-on-a-desktop)
  * [Options for headless machines](#options-for-headless-machines)
* [Usage examples](#usage-examples)
* [Running periodically (scheduling)](#running-periodically-scheduling)

  * [Cron example](#cron-example)
  * [Systemd timer example](#systemd-timer-example)
* [Development & debugging](#development--debugging)
* [Troubleshooting](#troubleshooting)
* [Security notes](#security-notes)
* [Contributing](#contributing)
* [License](#license)
* [Acknowledgements](#acknowledgements)

---

## Project overview

`hh-cv-helper` is a lightweight Python utility to automate republishing resumes on HeadHunter (hh.ru). Some employers prefer recently updated resumes; this tool keeps a list of resumes and will publish those that haven't been updated within a configurable threshold.

It implements:

* OAuth2 authentication against HeadHunter (initial interactive flow using a tiny Flask app)
* Token saving and refresh
* Resume status checking and publishing via the HH API
* CLI for running checks and dry-run mode

## Features

* Non-interactive mode for regular runs once tokens are obtained.
* Dry-run option to preview actions without making API calls.
* Simple JSON file to configure the list of resumes to manage.
* Token storage location configurable by environment variable.

## Prerequisites

* Python 3.8+ (pyproject/requirements provide dependencies)
* `pip` and virtual environment tool (`venv` recommended)
* A registered HeadHunter developer application (to get `client_id` and `client_secret`)

## Repository structure

```
hh-cv-helper/
├─ src/
│  ├─ api.py                # API endpoints logic
│  └─ app.py                # Flask app used for initial OAuth authorization
|  └─ auth.py               # Authorization and token management
|  └─ json_helpers.py       # Methods for JSON manipulation
|  └─ main.py               # CLI entrypoint: loads resumes, checks and publishes
|  └─ resume_helpers.py     # resume manipulation methods
|  └─ time_helpers.py       # methods for time calculation
├─ default_resumes.json  # Example resumes.json
├─ default.env           # Example environment variables
├─ requirements.txt
└─ README.md             # The README for the project
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/inpv/hh-cv-helper.git
cd hh-cv-helper
```

2. Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate   # Windows (PowerShell/CMD)
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

### HeadHunter application credentials

Register an application at the HeadHunter developer portal and obtain the `client_id` and `client_secret`. When registering, choose **Web application** and set a redirect URI that will be used during the initial OAuth flow (for example `http://localhost:5000/callback`).

### Environment variables

The project reads configuration from environment variables. You can use `default.env` as an example and create your own `.env` (or export variables directly).

* `HH_CLIENT_ID` — HeadHunter application client ID (required)
* `HH_CLIENT_SECRET` — HeadHunter application client secret (required)
* `HH_REDIRECT_URI` — Redirect URI configured in the HH app (defaults to `http://localhost:5000/callback`)
* `HH_TOKENS_PATH` — Path where OAuth tokens are stored (defaults to `~/.config/hh-bot/tokens.json`)
* `HH_DRY_RUN` — If set (truthy), the tool will simulate actions by default (can also be overridden via CLI)
* `HH_UPDATE_THRESHOLD_HOURS` — Threshold in hours to decide whether to republish a resume (default: `4`)

You can load variables with `export` or use tools such as `direnv`, `dotenv`, or run `source default.env` (after copying/adjusting it).

### Resumes list format

Create a JSON file (e.g. `resumes.json`) containing an array of objects with `id` and `name` fields. Example:

```json
[
  { "id": "12345678", "name": "John Smith" },
  { "id": "87654321", "name": "Jane Doe" }
]
```

Point the CLI at this file with `--resume-ids path/to/resumes.json`.

## Initial authentication (OAuth)

The first run requires an interactive OAuth authorization to obtain tokens. The repository includes `app.py`, a tiny Flask web server used for this purpose.

### Interactive on a desktop

1. Make sure your environment variables are set (`HH_CLIENT_ID`, `HH_CLIENT_SECRET`, `HH_REDIRECT_URI` if you changed it).
2. Start the helper normally (when it detects no tokens it will launch `app.py` automatically) or run the Flask helper directly:

```bash
python app.py
```

3. Open `http://localhost:5000/` in your browser and click **Authorize HeadHunter**. You will be redirected to the HeadHunter authorization page.
4. After granting permission you will be redirected back to `http://localhost:5000/callback`. The tokens will be saved to `HH_TOKENS_PATH`.
5. Stop the Flask server. You can now run `python main.py` non-interactively.

### Options for headless machines

If you need to deploy to a headless machine (Raspberry Pi or remote server) you have a few secure options:

* **Perform initial auth locally, copy tokens**: Run `app.py` on your desktop, complete the OAuth, and then copy the saved tokens file (value of `HH_TOKENS_PATH`) to the headless machine. Ensure file permissions are set correctly.

* **SSH local port forwarding**: Start `app.py` on the headless machine, use SSH with remote port forwarding or local port forwarding to expose `http://localhost:5000` on your desktop (or forward the callback). Example:

```bash
# forward remote port 5000 to local port 5000
ssh -R 5000:localhost:5000 user@headless
# then open http://localhost:5000 on your local browser
```

* **Use a short-lived tunnel**: Tools like `ngrok` or `localtunnel` can expose the local Flask server to the internet for the duration of the auth. If you use this method, prefer ephemeral tunnels and revoke credentials after.

> Security note: avoid checking client secrets or token files into source control. Treat `HH_TOKENS_PATH` as sensitive.

## Usage examples

Basic run (non-destructive, will normally be dry-run unless you set `HH_DRY_RUN` to false or pass `--dry-run` appropriately):

```bash
python main.py --resume-ids path/to/resumes.json
```

Dry-run explicitly:

```bash
python main.py --resume-ids path/to/resumes.json --dry-run
```

Set threshold (publish resumes not updated in last 24 hours):

```bash
python main.py --resume-ids path/to/resumes.json --threshold-hours 24
```

Common flags

* `--resume-ids` — path to JSON file with resume IDs (required)
* `--dry-run` — run the script without actually publishing (helpful for testing)
* `--threshold-hours` — hours since last update before deciding to republish

## Running periodically (scheduling)

You can run the tool periodically using `cron`, `systemd` timers, or any job scheduler.

### Cron example

Edit crontab with `crontab -e` and add a line to run daily at 3:00 AM:

```cron
0 3 * * * /usr/bin/python3 /path/to/project/main.py --resume-ids /path/to/resumes.json
```

Make sure the cron job runs as the user that owns the token file and that environment variables are available. Often the easiest approach is to wrap invocation in a small shell script that sources a `.env` file.

### Systemd timer example

Create a systemd service unit `/etc/systemd/system/hh-cv-helper.service`:

```ini
[Unit]
Description=HH CV Helper - publish resumes

[Service]
Type=oneshot
User=youruser
WorkingDirectory=/path/to/hh-cv-helper
EnvironmentFile=/path/to/hh-cv-helper/.env
ExecStart=/path/to/hh-cv-helper/.venv/bin/python /path/to/hh-cv-helper/main.py --resume-ids /path/to/hh-cv-helper/resumes.json
```

Create a timer `/etc/systemd/system/hh-cv-helper.timer`:

```ini
[Unit]
Description=Run hh-cv-helper daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Then enable and start the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hh-cv-helper.timer
```

## Development & debugging

* To run unit tests (if any are added), use `pytest` in a virtual environment.
* Use logging outputs from `main.py` and `hh_client.py` to debug API interactions.
* Check saved `tokens.json` contents to ensure refresh tokens exist and are being rotated properly.

## Troubleshooting

**Tokens not saved / invalid redirect URI**

* Make sure the `HH_REDIRECT_URI` in your environment matches the one configured in the HeadHunter app exactly.

**Script fails on headless machine during auth**

* Use the "perform auth on desktop and copy tokens" method or SSH port forwarding as described above.

**Permission errors writing tokens file**

* Ensure the directory for `HH_TOKENS_PATH` exists and is writable by the user running the script.

**Rate limits or 4xx/5xx from HH API**

* Check the client ID/secret and tokens. Implement backoff if you schedule frequent runs. The tool should be used conservatively to avoid hitting API limits.

## Security notes

* Do not commit `.env`, `tokens.json`, or any file containing credentials to git.
* Use proper file permissions for the tokens file (e.g., `chmod 600 tokens.json`).
* If credentials are compromised, revoke the HeadHunter application credentials and generate new ones.

## Contributing

Contributions are welcome. Suggested workflow:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Open a pull request describing the change

Please include clear documentation for new behaviors and consider adding examples.

## License

GNU GPL v 3.0 public license.

## Acknowledgements

* HeadHunter API docs and developer portal for OAuth2 details
