# QuickHealth project instructions

## Project and working context
- QuickHealth is a 3-day neatHack project: an AI clerking assistant for nurses and health workers in Nigeria.
- It supports hospital-style history taking, including special pathways for children under 5 (including infants) and pregnant or postpartum women.
- This is a triage and history-taking tool, not a diagnostic tool.
- The project folder is `C:\Users\HP\Documents\quickhealth`. Work only inside this folder.
- The owner is new to coding. Explain steps in plain language and provide exact Windows PowerShell commands whenever they need to run something.
- The repository is already a Git repo, pushed to a public GitHub repository, with Entire CLI enabled to record sessions.

## Stack
- Python
- Streamlit interface
- SQLite for saved sessions
- OpenAI API; read `OPENAI_API_KEY` and `OPENAI_MODEL` from `.env`

## Hackathon requirements
- Use neatlogs tracing on every run. Install with `pip install "neatlogs[openai]"`.
- Read `NEATLOGS_API_KEY` from `.env` without printing, logging, committing, or asking the owner to paste any API key.
- Call `neatlogs.init(workflow_name="quickhealth-clerking", instrumentations=["openai"])` before importing `openai`.
- Wrap each clerking session in `@span(kind="WORKFLOW")` and call `neatlogs.flush()` so traces are sent.
- Give each architecture component its own traced span: intake and patient-type detection, adaptive clerking loop, rules-based red-flag checker, completeness verifier, contradiction checker, note generator, and SQLite state store.
- All code is written during the hackathon.
- Commit after every working step with a clear message and push to `origin main`, so Entire records checkpoints. Never rewrite Git history.

## Safety rules — always follow
- Never diagnose. Label any differential as **for clinician consideration**.
- Urgency (`EMERGENCY_NOW`, `SEE_CLINICIAN_TODAY`, `ROUTINE`) must be decided by a rules file, never by the language model. Escalate when unsure.
- Use only fictional patients. Never store or request real patient data.
- Show a clear notice in the app: this is not medical advice and users should call emergency services for danger signs.
- Never print, log, commit, or ask the owner to paste any API key. Keys belong only in `.env`, which must be in `.gitignore`.
- Never claim clinical validation.

## Working style
- Before big changes, present a plan and wait for the owner's approval.
- Make small changes and test after each one.
- Tell the owner exactly how to run and check the app.
