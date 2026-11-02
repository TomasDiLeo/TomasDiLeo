import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.hardcover.app/v1/graphql"
API_KEY = os.getenv("HARDCOVER_API_KEY")

QUERY = """
query {
    me {
        id
        username
        name
    }
}
"""


def main():
    if not API_KEY:
        raise RuntimeError("HARDCOVER_API_KEY is missing from .env")

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "TomasDiLeo-GitHub-README/1.0",
        },
        json={"query": QUERY},
        timeout=20,
    )

    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")

    print("Hardcover API connection successful!")
    print(data["data"]["me"])


if __name__ == "__main__":
    main()

