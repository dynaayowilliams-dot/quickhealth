# Deploy QuickHealth on Streamlit Community Cloud

QuickHealth is a fictional-case demonstration only. It is not medical advice, has not been clinically reviewed, and must not receive real patient information. Sessions are traced. Community Cloud's local SQLite file is ephemeral: saved sessions and the daily model-call counter may disappear or reset when the app restarts.

## Prepare the repository

1. Confirm the project is pushed to GitHub and that `app.py`, `requirements.txt`, `.streamlit/config.toml`, and the `quickhealth`, `rules`, and `data` paths are present in the repository. The `data` directory is created automatically when the app first opens its database.
2. Keep credentials out of Git. `.env`, `.venv`, `data`, and `.streamlit/secrets.toml` are ignored by `.gitignore`.

## Create the Cloud app

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with the GitHub account that can access the repository.
2. From your workspace, select **Create app**.
3. When asked whether you already have an app, select **Yup, I have an app**.
4. Select the `dynaayowilliams-dot/quickhealth` repository, the `main` branch, and `app.py` as the main file path. Enter those values manually if they are not listed.
5. Open **Advanced settings** and choose Python 3.12.
6. In the **Secrets** field, add the required names listed below with their actual values. Enter them directly in Streamlit's private Secrets field; never put values in this document or in Git.
7. Select **Save**, then select **Deploy**.
8. Wait for the app to finish starting, then open the generated app URL.
9. Confirm the safety notice, traced-session warning, fictional-case checkbox, and access-code gate are visible before starting a case.

## Secret names

Required:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `NEATLOGS_API_KEY`

Recommended for a public demo:

- `QUICKHEALTH_ACCESS_CODE`

The app checks environment variables first, then Streamlit Secrets, then the local `.env` file. Streamlit Community Cloud should use its Secrets editor; do not upload `.env` or `.streamlit/secrets.toml`. See [Streamlit's deployment steps](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [Secrets guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) if the Cloud interface changes.

## Demo limits and data

The app allows up to 12 model calls per fictional session, 100 model calls per UTC day across the running app database, and 2,000 characters per answer. When a limit is reached, the app displays a friendly notice. The shared daily counter uses SQLite, so it is best-effort on Community Cloud and can reset after a restart or redeployment. Set provider-side spending limits as an additional control.

Saved sessions are not durable on Community Cloud. Do not use this prototype for real patient data, ongoing care, diagnoses, or clinical decisions.
