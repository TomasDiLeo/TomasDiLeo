import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.hardcover.app/v1/graphql"
API_KEY = os.getenv("HARDCOVER_API_KEY")

QUERY = """
query {
    me {
        user_books(where: {status_id: {_eq: 2}}) {
            book {
                title
                pages
                image {
                    url
                }
                contributions {
                    author {
                        name
                    }
                }
            }
            user_book_reads(order_by: {id: desc}, limit: 1) {
                progress_pages
                progress_seconds
            }
        }
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
        },
        json={"query": QUERY},
        timeout=20,
    )

    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")

    books = data["data"]["me"][0]["user_books"]
    print(json.dumps(books, indent=2))


if __name__ == "__main__":
    main()
