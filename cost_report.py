"""Print privacy-safe token, estimated cost, and latency averages for completed sessions."""

import argparse
from pathlib import Path

from dotenv import dotenv_values

from quickhealth.storage import completed_usage_totals


ROOT = Path(__file__).resolve().parent
PRICES_PER_MILLION = {
    # USD per 1M uncached input / output tokens, standard API rates.
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o": (2.50, 10.00),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-price", type=float, help="Override input USD per 1M tokens for an unlisted model")
    parser.add_argument("--output-price", type=float, help="Override output USD per 1M tokens for an unlisted model")
    args = parser.parse_args()

    config = dotenv_values(ROOT / ".env")
    model = (config.get("OPENAI_MODEL") or "").strip()
    if not model:
        parser.error("OPENAI_MODEL is missing from .env; the report cannot select model pricing")
    prices = PRICES_PER_MILLION.get(model)
    if prices is None:
        if args.input_price is None or args.output_price is None:
            parser.error("No built-in rate for this model. Supply both --input-price and --output-price in USD per 1M tokens.")
        prices = (args.input_price, args.output_price)

    totals = completed_usage_totals()
    if totals["sessions"] == 0:
        print(f"Model: {model}")
        print("Completed sessions with token usage: 0")
        print("No completed clerking sessions with recorded model usage are available yet.")
        return

    count = totals["sessions"]
    average_input = totals["input_tokens"] / count
    average_output = totals["output_tokens"] / count
    average_latency_seconds = totals["latency_ms"] / count / 1000
    average_cost = (average_input * prices[0] + average_output * prices[1]) / 1_000_000
    print(f"Model: {model}")
    print(f"Completed clerking sessions: {count}")
    print(f"Average input tokens/session: {average_input:.1f}")
    print(f"Average output tokens/session: {average_output:.1f}")
    print(f"Estimated average model cost/session: ${average_cost:.8f} USD")
    print(f"Average model latency/session: {average_latency_seconds:.2f} seconds")
    print("Rates: standard uncached token rates, USD per million tokens; excludes non-token fees and cached-input discounts.")


if __name__ == "__main__":
    main()
