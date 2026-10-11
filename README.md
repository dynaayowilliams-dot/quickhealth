# QuickHealth

QuickHealth is a hackathon prototype of an AI-assisted clerking and triage interface. It asks one history question at a time, adapts follow-up questions to the answers, and can produce a structured clerking note and plain-language summary. It is **not a diagnostic tool** and does not replace a health professional.

## Who it is for

The prototype is intended for demonstration to nurses, health workers, and hackathon reviewers interested in history-taking workflows in Nigeria. It has general, paediatric, antenatal, and postpartum pathways. Use made-up training cases only. Do not enter real patient information.

## Run it on Windows

Open PowerShell and run these commands from the project folder:

```powershell
Set-Location C:\Users\HP\Documents\quickhealth
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create a private `.env` from the placeholder template if you do not already have one, then edit it locally:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Set `OPENAI_API_KEY`, `OPENAI_MODEL`, and `NEATLOGS_API_KEY` in that private file. `QUICKHEALTH_ACCESS_CODE` is optional locally and enables the access-code gate when set. Do not paste or commit those values. `.env` is listed in `.gitignore`; `.env.example` has placeholders only.

Start QuickHealth:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit prints a local address in the PowerShell window and usually opens it in a browser. Use only fictional cases. The app displays a medical disclaimer and danger-sign emergency notice.

Run the automated tests and scripted evaluation:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe run_eval.py --version v2 --demo-recovery
.\.venv\Scripts\python.exe cost_report.py
```

The SQLite database is stored locally at `data\quickhealth.sqlite3`; the `data` folder is ignored by Git and is created automatically when needed. Streamlit Community Cloud uses an ephemeral filesystem, so saved sessions may not persist online or survive app restarts. The daily demo-call counter is also stored in this SQLite database and can reset when the cloud app restarts. The app caps each fictional session at 12 model calls, the shared daily allowance at 100 calls, and each answer at 2,000 characters. Do not put real patient data in it.

For Streamlit Community Cloud deployment, follow [docs/DEPLOY.md](docs/DEPLOY.md).

## Architecture

The app is split into small Python components. In each user turn, safety rules run before the app asks another model question.

1. **Intake and pathway selection** — `quickhealth/intake.py` and `quickhealth/pathways.py` identify the likely patient pathway from the fictional history. The pathway rules cover infants under two months, children under five, pregnancy by trimester (including unknown trimester), postpartum, other adults, and unknown patient type.
2. **Adaptive clerking loop** — `quickhealth/clerking.py` asks for one concise question at a time and uses the prior answers to guide the next question. Pathway guidance adds child, caregiver, pregnancy, or postpartum history topics.
3. **Rules-based red-flag checker** — `quickhealth/safety_rules.py` reads the pathway rules from `rules/red_flags.json`. It alone assigns `EMERGENCY_NOW`, `SEE_CLINICIAN_TODAY`, or `ROUTINE`. An emergency stops routine questioning. Missing or unsafe-to-assess rules must not silently produce a routine outcome.
4. **Completeness check** — `quickhealth/verification.py` checks pathway-required sections before the app can finish. Prescribed, herbal/traditional, and over-the-counter medicine history are separate required sections. Unknown or unanswered items remain incomplete.
5. **Contradiction check** — `quickhealth/verification.py` checks recorded facts and pauses for clarification when it finds a material conflict. Structured checks include age/development and LMP/gestational-age comparisons. Model-assisted free-text detection can suggest a candidate, but does not decide urgency or silently resolve the facts.
6. **Note generator** — `quickhealth/clerking.py` asks the OpenAI model to format the history as a structured note and plain-language summary after the safety and verification gates allow completion. The model does not assign urgency or diagnose.
7. **SQLite state store** — `quickhealth/storage.py` saves session history, verification state, urgency, pathway, and any completed note in SQLite. It also records aggregate model token counts and call latency for the cost report; it does not need those counts to make a safety decision.

The Streamlit UI is in `app.py` and `quickhealth/ui.py`. The application is a prototype: pathway selection and free-text matching can be imperfect, and it needs clinical review before any use beyond fictional demonstrations.

## neatlogs tracing

QuickHealth initializes neatlogs with workflow name `quickhealth-clerking` and OpenAI instrumentation before importing the OpenAI client. The app reads `NEATLOGS_API_KEY` from `.env` and calls `neatlogs.flush()` when the session ends so queued spans can be sent to the Neatlogs workspace configured for that key.

Named spans cover the clerking workflow, intake and pathway selection, adaptive questions, rules-based red-flag checking, completeness and contradiction checks, note generation, SQLite operations, and storage retry recovery. The scripted evaluator tags its traces with the `--version` label and fictional case ID. The failure-recovery demo has a parent workflow span and a `sqlite_write_recovery` span. Its safe attributes report the operation, attempt/retry counts, recovery status, and version; patient answers and keys are not intended as span attributes. App-defined spans disable automatic input/output capture, and a masking function is configured for trace content. Review the Neatlogs workspace access and retention settings for your own deployment.

The SQLite cost metrics are a separate local record of aggregate input tokens, output tokens, and model-call time. `cost_report.py` reads these numbers for completed sessions and calculates estimated average cost using the configured model's standard rates. Earlier sessions without recorded token counts cannot contribute to those averages. This report does not retrieve historical spans from Neatlogs.

## Entire session recording

The repository owner has Entire CLI enabled to record coding-agent work sessions. Entire records development activity; Git commits record repository snapshots. Neither Entire nor Git is the app's runtime session store or the Neatlogs observability system. Keep `.env` and patient data out of both Git commits and shared session materials.

## Scripted evaluation results

### Evaluation scope

`run_eval.py` is a scripted behaviour check of the rules-based safety layer, the completeness check, and the contradiction check. It uses fixed fictional answers and scripted model responses; it makes **no live language model calls**. It does not measure language-model quality.

Covered by the scripted evaluation:

- Whether selected fictional inputs produce the expected rules-based urgency.
- Whether the scripted workflow asks specified key questions.
- Whether the contradiction check catches the expected scripted conflict.
- Separately, when `--demo-recovery` is used, whether a simulated temporary SQLite write failure is retried successfully.

Not covered by the scripted evaluation:

- Live model behaviour with real conversations.
- The quality, safety, or consistency of questions or notes produced by a live language model.
- Clinical safety, accuracy, or improved health outcomes.

Not yet tested: live model behaviour with real conversations. The cases are fictional, and this project has not been clinically validated.

The repository's saved fictional-case results show these totals:

| Evaluation | Passed | Failed |
|---|---:|---:|
| v1 (rerun on restored cases) | 14 / 14 | 0 |
| v2 (rerun on restored cases) | 14 / 14 | 0 |

Both reports were rerun against the same restored fictional case definitions. O1 is again a small headache followed by blurred vision in a 28-week pregnancy, with expected `EMERGENCY_NOW`; the rules now conservatively escalate when a headache and visual change are both reported. O4 again describes much less fetal movement at 36 weeks and expects `SEE_CLINICIAN_TODAY`. P1, P6, and O2 retain their original intended expected outcomes. The earlier saved v1/v2 reports used different O1/O4 inputs or expectations and are superseded by these reruns.

The v2 run includes a separate recovery demonstration: it injects one temporary SQLite busy error, retries the fictional write once, and records successful recovery. The saved summary is `results/v2.json`.

## Safety and guideline-source notes

- QuickHealth must not diagnose. If a differential is ever shown, it must be labelled **for clinician consideration**.
- The application is not medical advice. Its visible notice directs people to call emergency services for danger signs.
- Use fictional cases only. Do not enter names, contact details, or any other real patient information.
- Urgency comes from deterministic rules in `rules/red_flags.json`, not from the language model. When the checker cannot safely assess a case, it should escalate rather than imply routine care.
- The JSON rules include `source` and `reviewed_by_clinician` metadata. Every current rule has `reviewed_by_clinician: false`. These rules have not been clinician-reviewed as part of this project; source labels are recorded metadata, not proof that this implementation faithfully applies a guideline.

The source labels in the current rules file refer to:

- WHO, *Integrated Management of Childhood Illness (IMCI) Chart Booklet*.
- WHO, *Management of the Sick Young Infant Aged Up to 2 Months*.
- WHO, *Recommendations on Postnatal Care of the Mother and Newborn* (2013), postpartum danger signs.
- WHO maternal danger signs and danger signs after childbirth.
- Nigeria Federal Ministry of Health ANC Orientation Package / ANC Orientation Package for Health Care Providers and Safe Motherhood guidance.
- Nigeria Federal Ministry of Health and Social Welfare, *National Guideline for the Management of Postpartum Haemorrhage* (2024).
- Nigeria Federal Ministry of Health postpartum care and Safe Motherhood guidance.

The rule file itself lists the source attached to each rule. The rules and wording still need review by a qualified clinician familiar with current Nigerian guidance before any use with real people.

## Limitations

- This is a hackathon prototype and has **not been clinically validated**. Passing scripted tests does not demonstrate clinical safety, accuracy, or improved outcomes.
- Red-flag recognition uses explicit text patterns and can miss an unexpected phrase or misunderstand context. An answer that is ambiguous or not covered must be checked by a human; the app is not an emergency service.
- The model can ask an incomplete or unsuitable question and can format an inaccurate note. A health professional must review any output.
- Rules are source-labelled but not clinician-reviewed (`reviewed_by_clinician: false`). They may be incomplete, over- or under-inclusive, and may not reflect all current local protocols.
- To meet the O1 fictional case's conservative emergency expectation, the pregnancy headache/visual-change pattern also matches a headache described as small. The named source phrase refers to severe headache with visual changes; this broader matcher requires clinician review and is not represented as a guideline-confirmed threshold.
- The v1/v2 evaluation uses a small set of scripted fictional cases and a scripted model substitute. It is a software behavior check, not a clinical evaluation. Some v1/v2 expected inputs changed as described above.
- The cost report only covers sessions whose model responses included token usage and whose note was completed after usage tracking was added. It uses standard uncached token rates, so actual billing may differ because of caching, model/provider changes, or other fees.
- SQLite is local to this machine and is not a managed clinical record system. Protect the computer and delete fictional test records when they are no longer needed.

## Development checkpoints

Git commits and pushes publish code checkpoints on the repository's `main` branch. Entire recordings are a separate record of the coding-agent work session; they do not replace the code history in Git.
Built during neatHack 2026 with Codex, Entire and neatlogs.
Entire checkpoint test, third attempt.
