"""LMP-based estimates; these are not confirmed pregnancy dates."""

from datetime import date, timedelta
import re


LMP_ESTIMATE_NOTICE = (
    "LMP-based dates are estimates, not confirmed facts. They may be inaccurate, "
    "especially with irregular cycles or an uncertain LMP."
)


def calculate_obstetric_dates(lmp, *, today=None, is_certain=True):
    """Calculate EDD as LMP + 280 days and completed gestational weeks/days.

    The 280-day convention (40 weeks from the first day of the last menstrual
    period) follows ACOG's Methods for Estimating the Due Date guidance:
    https://www.acog.org/clinical/clinical-guidance/committee-opinion/articles/2017/05/methods-for-estimating-the-due-date
    Invalid or future dates produce no estimate; callers should never present
    estimates as confirmed dates.
    """
    if not is_certain:
        return {"status": "uncertain", "edd": None, "weeks": None, "days": None}
    if not isinstance(lmp, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", lmp) is None:
        return {"status": "invalid", "edd": None, "weeks": None, "days": None}
    try:
        lmp_date = date.fromisoformat(lmp)
    except ValueError:
        return {"status": "invalid", "edd": None, "weeks": None, "days": None}

    current_date = today or date.today()
    if lmp_date > current_date:
        return {"status": "future", "edd": None, "weeks": None, "days": None}

    elapsed_days = (current_date - lmp_date).days
    estimated_due_date = lmp_date + timedelta(days=280)
    weeks, days = divmod(elapsed_days, 7)
    return {
        "status": "estimated",
        "edd": estimated_due_date.isoformat(),
        "weeks": weeks,
        "days": days,
    }


def find_lmp_estimate(history, *, today=None):
    """Find a certain ISO LMP only when it answers an explicit LMP question."""
    for index, item in enumerate(history[:-1]):
        if item.get("role") != "assistant" or not re.search(
            r"\b(?:LMP|last menstrual period)\b", item.get("content", ""), re.IGNORECASE
        ):
            continue
        answer = history[index + 1]
        if answer.get("role") != "user":
            continue
        answer_text = answer.get("content", "")
        if re.search(r"\b(?:uncertain|unsure|unknown|don't know|not sure|not certain)\b", answer_text, re.IGNORECASE):
            return calculate_obstetric_dates(None, today=today, is_certain=False)
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", answer_text)
        certainty = re.search(r"\b(certain|sure|yes)\b", answer_text, re.IGNORECASE)
        if date_match is None or certainty is None:
            return {"status": "uncertain", "edd": None, "weeks": None, "days": None}
        return calculate_obstetric_dates(date_match.group(1), today=today)
    return None
