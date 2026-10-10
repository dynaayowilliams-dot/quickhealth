"""Deterministic, explainable urgency checks using the project rules file."""

import json
import re
from pathlib import Path

import neatlogs

RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "red_flags.json"
URGENCY_LEVELS = {"EMERGENCY_NOW", "SEE_CLINICIAN_TODAY", "ROUTINE"}
UNCERTAIN_URGENCY = "SEE_CLINICIAN_TODAY"


class RulesError(ValueError):
    """The rules data is missing or does not follow its required schema."""


def load_rules(path=None):
    """Load and validate rules before allowing them to influence urgency."""
    try:
        with Path(path or RULES_PATH).open(encoding="utf-8") as rules_file:
            data = json.load(rules_file)
    except (OSError, json.JSONDecodeError) as error:
        raise RulesError("Rules file is missing or invalid JSON") from error

    if not isinstance(data, dict) or data.get("version") != 1:
        raise RulesError("Unsupported rules file format")
    pathways = data.get("pathways")
    rules = data.get("rules")
    if not isinstance(pathways, dict) or not pathways or not isinstance(rules, list):
        raise RulesError("Rules file must define pathways and rules")

    rule_ids = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise RulesError("Each rule must be an object")
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id or rule_id in rule_ids:
            raise RulesError("Rule IDs must be non-empty and unique")
        rule_ids.add(rule_id)
        if rule.get("level") not in URGENCY_LEVELS:
            raise RulesError(f"Rule {rule_id} has an unsupported urgency level")
        if (not isinstance(rule.get("patterns"), list) or not rule["patterns"]
                or not all(isinstance(pattern, str) and pattern for pattern in rule["patterns"])):
            raise RulesError(f"Rule {rule_id} must have text patterns")
        if not isinstance(rule.get("pathways"), list) or not rule["pathways"]:
            raise RulesError(f"Rule {rule_id} must name applicable pathways")
        if not isinstance(rule.get("message"), str) or not rule["message"].strip():
            raise RulesError(f"Rule {rule_id} must have a user-facing message")
        if not isinstance(rule.get("source"), str) or not rule["source"].strip():
            raise RulesError(f"Rule {rule_id} must include its source metadata")
        if rule.get("reviewed_by_clinician") is not False:
            raise RulesError(f"Rule {rule_id} must state reviewed_by_clinician: false")
        try:
            for pattern in rule["patterns"]:
                re.compile(pattern, re.IGNORECASE)
        except re.error as error:
            raise RulesError(f"Rule {rule_id} has an invalid text pattern") from error

    for pathway_name, pathway in pathways.items():
        if (not isinstance(pathway, dict)
                or pathway.get("default_level") not in URGENCY_LEVELS
                or not isinstance(pathway.get("rule_ids"), list)):
            raise RulesError(f"Pathway {pathway_name} is invalid")
        if any(rule_id not in rule_ids for rule_id in pathway["rule_ids"]):
            raise RulesError(f"Pathway {pathway_name} references an unknown rule")
    for rule in rules:
        if any(pathway not in pathways for pathway in rule["pathways"]):
            raise RulesError(f"Rule {rule['id']} references an unknown pathway")
    return data


def _is_negated(match_start, text):
    preceding = text[max(0, match_start - 45):match_start]
    return re.search(r"\b(?:no|not|never|denies|without)\s+(?:\w+\s+){0,3}$", preceding) is not None


def _complete_negative_screen(history, pathway_name, pathway, rules):
    """Accept a ROUTINE default only after a complete question gets a clear no."""
    if len(history) < 2:
        return False
    question, answer = history[-2:]
    if question.get("role") != "assistant" or answer.get("role") != "user":
        return False
    question_text = question.get("content", "")
    answer_text = answer.get("content", "").strip()
    if not re.match(r"^(?:no|none|negative|not present)\b", answer_text, re.IGNORECASE):
        return False

    listed_ids = set(pathway["rule_ids"])
    covered_ids = {
        rule["id"]
        for rule in rules
        if rule["id"] in listed_ids and pathway_name in rule["pathways"]
        and any(re.search(pattern, question_text, re.IGNORECASE) for pattern in rule["patterns"])
    }
    return covered_ids == listed_ids


@neatlogs.span(kind="GUARDRAIL", name="rules_based_red_flag_checker", capture_input=False, capture_output=False)
def assess_urgency(history, patient_type):
    """Assess only user answers; uncertain/missing rules escalate to same-day care."""
    try:
        data = load_rules()
        pathway = data["pathways"].get(patient_type)
        if pathway is None:
            return {"urgency": UNCERTAIN_URGENCY, "matches": [], "message": "The patient pathway could not be safely assessed. Please contact a clinician today."}

        user_text = " ".join(
            item.get("content", "") for item in history
            if item.get("role") == "user" and isinstance(item.get("content"), str)
        ).lower()
        listed_ids = set(pathway["rule_ids"])
        matches = []
        for rule in data["rules"]:
            if rule["id"] not in listed_ids or patient_type not in rule["pathways"]:
                continue
            if any(
                (found := re.search(pattern, user_text, re.IGNORECASE)) is not None
                and not _is_negated(found.start(), user_text)
                for pattern in rule["patterns"]
            ):
                matches.append(rule)

        if not matches:
            if _complete_negative_screen(history, patient_type, pathway, data["rules"]):
                return {
                    "urgency": pathway["default_level"],
                    "matches": [],
                    "message": "No listed red flags were reported in response to the complete rules-based safety screen.",
                }
            # A ROUTINE default cannot establish safety from a partial history.
            return {"urgency": UNCERTAIN_URGENCY, "matches": [], "message": "No listed red flag was matched, but this limited check cannot rule out danger. Please contact a clinician today if there is any concern."}

        urgency = max(
            (rule["level"] for rule in matches),
            key={"ROUTINE": 0, "SEE_CLINICIAN_TODAY": 1, "EMERGENCY_NOW": 2}.get,
        )
        return {
            "urgency": urgency,
            "matches": [rule["id"] for rule in matches],
            "message": " ".join(dict.fromkeys(rule["message"] for rule in matches)),
        }
    except (RulesError, OSError, ValueError, TypeError, KeyError):
        return {"urgency": UNCERTAIN_URGENCY, "matches": [], "message": "The safety rules could not be safely assessed. Please contact a clinician today."}
