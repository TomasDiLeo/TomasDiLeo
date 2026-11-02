import os
from statistics import mean

import requests
from dotenv import load_dotenv

from generate_svg import generate_svg

# Configuration
load_dotenv()

BASE_URL = "https://api.monkeytype.com"
API_KEY = os.getenv("MONKEYTYPE_API_KEY")
RESULTS_LIMIT = 100
REQUEST_TIMEOUT = 15


class MonkeytypeAPIError(Exception):
    """Raised when a Monkeytype API request fails."""

def get_headers():
    """Return authentication headers for Monkeytype API."""
    if not API_KEY:
        raise MonkeytypeAPIError(
            "MONKEYTYPE_API_KEY is missing. Check your .env file."
        )

    return {
        "Authorization": f"ApeKey {API_KEY}"
    }


def api_get(endpoint, params=None):
    """Make an authenticated GET request to the Monkeytype API."""
    url = f"{BASE_URL}/{endpoint}"

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

    except requests.RequestException as error:
        raise MonkeytypeAPIError(
            f"API request failed ({endpoint}): {error}"
        ) from error

    try:
        return response.json()["data"]
    except (ValueError, KeyError, TypeError) as error:
        raise MonkeytypeAPIError(
            f"Unexpected API response from {endpoint}."
        ) from error


def get_stats():
    return api_get("users/stats")


def get_recent_results(limit=RESULTS_LIMIT):
    return api_get(
        "results",
        params={"limit": limit},
    )


def filter_results(results, mode, mode2):
    return [
        result
        for result in results
        if result.get("mode") == mode
        and str(result.get("mode2")) == str(mode2)
    ]


def calculate_average(results, field):
    values = [
        result[field]
        for result in results
        if isinstance(result.get(field), (int, float))
    ]

    return mean(values) if values else 0


def calculate_metrics(stats, results):
    time_60 = filter_results(results, "time", "60")
    words_25 = filter_results(results, "words", "25")

    avg_wpm_60 = calculate_average(time_60, "wpm")
    avg_wpm_25 = calculate_average(words_25, "wpm")

    accuracy_results = time_60 + words_25
    avg_accuracy = calculate_average(accuracy_results, "acc")

    time_typing_seconds = stats.get("timeTyping", 0)
    time_typing_hours = time_typing_seconds / 3600

    estimated_words = round(
        avg_wpm_60 * (time_typing_seconds / 60)
    )

    history = [
        {
            "wpm": result["wpm"],
            "timestamp": result["timestamp"],
        }
        for result in results
        if result.get("mode") == "time"
        and isinstance(result.get("wpm"), (int, float))
        and result.get("timestamp") is not None
    ]

    history.sort(key=lambda item: item["timestamp"])

    return {
        "avg_wpm_60": round(avg_wpm_60, 2),
        "avg_wpm_25": round(avg_wpm_25, 2),
        "time_typing_hours": round(time_typing_hours, 2),
        "avg_accuracy": round(avg_accuracy, 2),
        "estimated_words_typed": estimated_words,
        "history": history,
    }

def print_metrics(metrics):
    print("\n--- Monkeytype Dashboard Data ---\n")

    for key, value in metrics.items():
        if key != "history":
            print(f"{key}: {value}")

    print("\n--- WPM History ---\n")

    if metrics["history"]:
        for item in metrics["history"]:
            print(
                f'{item["timestamp"]}: {item["wpm"]} WPM'
            )
    else:
        print("No WPM history available.")


def main():
    try:
        stats = get_stats()
        results = get_recent_results()

        metrics = calculate_metrics(stats, results)

        print_metrics(metrics)

        generate_svg(metrics)

        print("\nMonkeytype SVG successfully generated.")

    except MonkeytypeAPIError as error:
        print(f"\nMonkeytype API error: {error}")
        raise

    except (KeyError, TypeError, ValueError) as error:
        print(f"\nData processing error: {error}")
        raise

if __name__ == "__main__":
    main()
