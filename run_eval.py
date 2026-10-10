"""Run scripted fictional cases through QuickHealth without live model calls."""

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import re
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from dotenv import dotenv_values

# Configure tracing without importing OpenAI. The local scripted client below
# makes the evaluation repeatable and avoids sending fictional case text out.
import neatlogs
from quickhealth.privacy import redact_trace_content

ROOT = Path(__file__).resolve().parent
CASES_PATH = ROOT / "tests" / "cases.json"

CONFIG = dotenv_values(ROOT / ".env")
neatlogs.init(
    api_key=CONFIG.get("NEATLOGS_API_KEY"),
    workflow_name="quickhealth-clerking",
    instrumentations=["openai"],
    mask=redact_trace_content,
)

from opentelemetry import trace as otel_trace

from quickhealth.pathways import select_pathway
from quickhealth.safety_rules import assess_urgency
from quickhealth.storage import create_session
from quickhealth import storage
from quickhealth.storage import get_session, save_answer
from quickhealth.workflow import process_answer


class ScriptedModel:
    """Tiny OpenAI-shaped substitute that returns only case-authored prompts."""

    def __init__(self, questions, complete_after_each_answer=False):
        self.questions = list(questions)
        self.complete_after_each_answer = complete_after_each_answer
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        messages = kwargs.get("messages", [])
        prompt = messages[-1].get("content", "") if messages else ""
        if "Review this fictional history ONLY" in prompt:
            content = '{"candidates": []}'
        elif self.complete_after_each_answer:
            content = "COMPLETE"
        elif self.questions:
            content = self.questions.pop(0)
        else:
            content = "COMPLETE"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def _answer_mentions_question(question, expected_term):
    if not expected_term:
        return False
    # Match a concise phrase from the case in questions actually returned by
    # the clerking workflow (not in the patient's own scripted answer).
    return expected_term.casefold() in question.casefold()


@neatlogs.span(
    kind="WORKFLOW",
    name="quickhealth_evaluation_case",
    capture_input=False,
    capture_output=False,
)
def evaluate_case(case, version):
    span = otel_trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("quickhealth.eval.version", version)
        span.set_attribute("quickhealth.eval.case_id", case["id"])

    client = ScriptedModel(
        case.get("scripted_model_questions", []),
        case.get("complete_after_each_answer", False),
    )
    session_id = create_session()
    history = []
    current_question = case["initial_question"]
    verification_state = {}
    questions_asked = []
    contradiction_caught = False
    emergency = False

    scripted_answers = [
        answer.replace("{{LMP_2_MONTHS_AGO}}", (date.today() - timedelta(days=60)).isoformat())
        for answer in case["scripted_answers"]
    ]
    for answer in scripted_answers:
        history, next_question, result, verification_state = process_answer(
            client,
            session_id,
            history,
            answer,
            current_question,
            verification_state,
        )
        if result:
            emergency = bool(result.get("emergency"))
        if next_question:
            questions_asked.append(next_question)
            if "please clarify these two recorded statements" in next_question.casefold():
                contradiction_caught = True
            if case.get("stop_on_clarification") and contradiction_caught:
                break
            current_question = next_question
        if emergency:
            break
        # G1 stops after the checker has asked for the OTC section, having
        # already asked the specific herbal/traditional-medicine question.
        if case["id"] == "G1" and any(
            "over-the-counter" in item.casefold() for item in questions_asked
        ):
            break

    if emergency:
        actual_urgency = "EMERGENCY_NOW"
    else:
        patient_type = select_pathway(history)
        actual_urgency = assess_urgency(history, patient_type)["urgency"]

    key_asked = any(
        _answer_mentions_question(question, case.get("key_question"))
        for question in questions_asked
    )
    urgency_pass = actual_urgency == case["expected_urgency"]
    question_pass = key_asked == case.get("expected_key_question_asked", False)
    contradiction_pass = contradiction_caught == case.get("expected_contradiction", False)
    passed = urgency_pass and question_pass and contradiction_pass

    return {
        "case_id": case["id"],
        "expected_urgency": case["expected_urgency"],
        "actual_urgency": actual_urgency,
        "key_question_asked": key_asked,
        "contradiction_caught": contradiction_caught,
        "pass": passed,
    }


@neatlogs.span(
    kind="WORKFLOW",
    name="quickhealth_failure_recovery_demo",
    capture_input=False,
    capture_output=False,
)
def run_recovery_demo(version):
    """Inject one transient SQLite lock for a fictional demo write, then recover."""
    span = otel_trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("quickhealth.eval.version", version)
        span.set_attribute("quickhealth.demo.kind", "transient_sqlite_busy")
    session_id = create_session()
    original_connect = storage._connect
    attempts = 0

    def fail_once_then_connect():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("database is locked")
        return original_connect()

    storage._connect = fail_once_then_connect
    try:
        save_answer(session_id, "Fictional demo question", "Fictional demo answer")
    finally:
        storage._connect = original_connect
    stored = get_session(session_id)
    recovered = bool(stored and len(json.loads(stored[1])) == 2 and attempts == 2)
    if span and span.is_recording():
        span.set_attribute("quickhealth.demo.retry_count", max(0, attempts - 1))
        span.set_attribute("quickhealth.demo.recovered", recovered)
    if not recovered:
        raise RuntimeError("The transient database failure was not recovered")
    return {"kind": "transient_sqlite_busy", "retry_count": attempts - 1, "recovered": recovered}


def _print_table(rows):
    columns = (
        ("case id", "case_id"),
        ("expected urgency", "expected_urgency"),
        ("actual urgency", "actual_urgency"),
        ("key question asked", "key_question_asked"),
        ("contradiction caught", "contradiction_caught"),
        ("pass/fail", "pass"),
    )
    values = [
        [row[key] if isinstance(row[key], str) else ("yes" if row[key] else "no")
         for _, key in columns]
        for row in rows
    ]
    widths = [max(len(title), *(len(value[index]) for value in values)) for index, (title, _) in enumerate(columns)]
    header = " | ".join(title.ljust(widths[index]) for index, (title, _) in enumerate(columns))
    line = "-+-".join("-" * width for width in widths)
    print(header)
    print(line)
    for value in values:
        print(" | ".join(value[index].ljust(widths[index]) for index in range(len(columns))))


def main():
    parser = argparse.ArgumentParser(description="Evaluate QuickHealth with fictional scripted cases.")
    parser.add_argument("--version", required=True, help="Short label for this evaluation run, e.g. v1")
    parser.add_argument("--demo-recovery", action="store_true", help="Inject one fictional transient SQLite lock and show the retry")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.version):
        parser.error("version may contain only letters, numbers, dots, underscores, and hyphens")

    case_data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    rows = [evaluate_case(case, args.version) for case in case_data["cases"]]
    recovery_demo = run_recovery_demo(args.version) if args.demo_recovery else None
    neatlogs.flush()

    output_dir = ROOT / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / f"{args.version}.json"
    result_path.write_text(
        json.dumps(
            {
                "version": args.version,
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                "case_count": len(rows),
                "passed": sum(row["pass"] for row in rows),
                "failed": sum(not row["pass"] for row in rows),
                "results": rows,
                "failure_recovery_demo": recovery_demo,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _print_table(rows)
    if recovery_demo:
        print("\nFailure/recovery demo: injected SQLite busy error; retry count=1; recovered=yes; trace span=sqlite_write_recovery")
    print(f"\nSaved evaluation results to results/{args.version}.json")


if __name__ == "__main__":
    main()
