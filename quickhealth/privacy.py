"""Privacy mask applied to neatlogs span data before export."""


def redact_trace_content(span_data):
    """Keep trace structure while redacting free text and credentials."""
    attributes = span_data.get("attributes", {})
    for key in list(attributes):
        lowered = str(key).lower()
        if any(part in lowered for part in (
            "input_messages.", "output_messages.", ".content", ".arguments",
            ".definition", ".description", ".input_schema", "prompt", "completion",
            "exception", "error.message", "stacktrace", "api_key", "authorization",
            "secret", "password", "patient_name", "phone", "email",
        )):
            attributes[key] = "[redacted]"
    return span_data
