import os
import requests
import json
from dotenv import load_dotenv
from generate_svg import generate_svg
from statistics import mean

load_dotenv()

API_KEY = os.environ["MONKEYTYPE_API_KEY"]

API_KEY = os.environ["MONKEYTYPE_API_KEY"]
BASE_URL = "https://api.monkeytype.com"

headers = {
    "Authorization": f"ApeKey {API_KEY}"
}

def get_stats():
    response = requests.get(
        f"{BASE_URL}/users/stats",
        headers=headers,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["data"]

def get_recent_results(limit=30):
    response = requests.get(
        f"{BASE_URL}/results",
        headers=headers,
        params={"limit": limit},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["data"]

def calculate_metrics(stats, results):
    time_60 = [
        r for r in results
        if r.get("mode") == "time"
        and r.get("mode2") == "60"
    ]

    words_25 = [
        r for r in results
        if r.get("mode") == "words"
        and r.get("mode2") == "25"
    ]

    avg_wpm_60 = (
        mean(r["wpm"] for r in time_60)
        if time_60 else 0
    )

    avg_wpm_25 = (
        mean(r["wpm"] for r in words_25)
        if words_25 else 0
    )

    all_results = time_60 + words_25

    avg_accuracy = (
        mean(r["acc"] for r in all_results)
        if all_results else 0
    )

    time_typing_hours = stats["timeTyping"] / 3600

    # Approximation: standard WPM assumes 5 characters per word.
    estimated_words = round(
        avg_wpm_60 * (stats["timeTyping"] / 60)
    )

    return {
        "avg_wpm_60": round(avg_wpm_60, 2),
        "avg_wpm_25": round(avg_wpm_25, 2),
        "time_typing_hours": round(time_typing_hours, 2),
        "avg_accuracy": round(avg_accuracy, 2),
        "estimated_words_typed": estimated_words,
    }

def main():
    stats = get_stats()
    results = get_recent_results()

    metrics = calculate_metrics(stats, results)

    print("\n--- Monkeytype Dashboard Data ---\n")

    for key, value in metrics.items():
        if key != "history":
            print(f"{key}: {value}")

    print("\nWPM History:")
    print([item["wpm"] for item in metrics["history"]])

    generate_svg(metrics)


if __name__ == "__main__":
    main()
