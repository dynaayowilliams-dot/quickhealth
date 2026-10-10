# QuickHealth - AI clerking assistant (neatHack 2026)

QuickHealth is a prototype history-taking assistant for **fictional cases only**. It is
not a diagnostic tool and does not provide medical advice. Call emergency services for
danger signs.

## Set up (Windows PowerShell)

If Python 3 is not installed, install it from PowerShell, then close and reopen
PowerShell:

```powershell
winget install --id Python.Python.3.12 --exact
```

From the project folder, create a virtual environment, then install the packages:

```powershell
cd C:\Users\HP\Documents\quickhealth
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create your private `.env` file from the placeholder template and fill the three values
locally. Never share or commit this file:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Start the app:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Use made-up details only. The app stores each session in `data\quickhealth.sqlite3`, a
local folder excluded from Git. The OpenAI model asks one history question at a time,
but urgency categories are assigned by local rules in `quickhealth\safety_rules.py`.
