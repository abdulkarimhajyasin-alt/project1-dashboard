# Web Dashboard

A standalone FastAPI admin dashboard with Jinja2 templates, PostgreSQL, protected admin login, users management, records management, and general settings.

This project is intentionally independent and does not include Telegram or bot code.

## Requirements

- Python 3.11+
- PostgreSQL

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a PostgreSQL database, then copy the example environment file:

```bash
copy .env.example .env
```

Update `.env` with your own values:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/web_dashboard
SECRET_KEY=your-long-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
```

Load environment variables in PowerShell:

```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
    [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
  }
}
```

Create the first admin account:

```bash
python scripts/create_admin.py
```

Run the app locally:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Render Deployment

The included `render.yaml` is ready for Render Blueprint deployments.

Render start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required environment variables:

```text
DATABASE_URL
SECRET_KEY
```

Optional environment variables:

```text
APP_NAME
SESSION_COOKIE_NAME
ADMIN_USERNAME
ADMIN_PASSWORD
```

After deployment, create the first admin using a Render Shell or one-off job with:

```bash
python scripts/create_admin.py
```
