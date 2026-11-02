import os
import base64
import mimetypes
import requests

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.hardcover.app/v1/graphql"
API_KEY = os.getenv("HARDCOVER_API_KEY")

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUTPUT = ASSETS / "hardcover.svg"

QUERY = """
query {
    me {
        currently_reading: user_books(
            where: {status_id: {_eq: 2}}
        ) {
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
            }
        }

        read_books: user_books(
            where: {status_id: {_eq: 3}}
        ) {
            user_book_reads {
                finished_at
            }
        }
    }
}
"""


def fetch_hardcover_data():
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "TomasDiLeo-GitHub-README/1.0",
        },
        json={"query": QUERY},
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise RuntimeError(f"Hardcover API error: {data['errors']}")

    return data["data"]["me"][0]


def get_reading_data(user):
    current_year = str(datetime.now().year)

    read_books = user.get("read_books") or []

    # Count distinct books marked as read.
    lifetime_count = len(read_books)

    # Count books with at least one completion date in the current year.
    year_count = sum(
        1
        for book in read_books
        if any(
            (read.get("finished_at") or "").startswith(current_year)
            for read in (book.get("user_book_reads") or [])
        )
    )

    candidates = []

    for entry in user.get("currently_reading") or []:
        book = entry.get("book") or {}
        reads = entry.get("user_book_reads") or []

        if not reads:
            continue

        pages = book.get("pages")
        progress = reads[0].get("progress_pages")

        if pages is None or progress is None or pages <= 0:
            continue

        candidates.append({
            "book": book,
            "progress": progress,
            "pages": pages,
            "percentage": min(progress / pages * 100, 100),
        })

    # Select the book with the highest recorded progress percentage.
    selected = (
        max(candidates, key=lambda item: item["percentage"])
        if candidates
        else None
    )

    return selected, year_count, lifetime_count


def get_cover_data(url):
    if not url:
        return None

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type", ""
    ).split(";")[0]

    if not content_type.startswith("image/"):
        content_type = (
            mimetypes.guess_type(url)[0] or "image/jpeg"
        )

    encoded = base64.b64encode(response.content).decode("ascii")

    return f"data:{content_type};base64,{encoded}"


def generate_svg(item, year_count, lifetime_count):
    stats = f"""
    <text x="164" y="181" fill="#8bac0f"
    font-family="monospace" font-size="11">
    READ THIS YEAR: {year_count}
    </text>

    <text x="490" y="181" fill="#8bac0f"
    font-family="monospace" font-size="11">
    READ IN LIFETIME: {lifetime_count}
    </text>
    """

    if item is None:
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg"
        width="900" height="200" viewBox="0 0 900 200">

            <rect width="900" height="200" fill="#11110f"/>

            <text x="24" y="45" fill="#8bac0f"
            font-family="monospace" font-size="12"
            letter-spacing="2">
            CURRENTLY READING
            </text>

            <text x="24" y="85" fill="#a5a398"
            font-family="monospace" font-size="16">
            NO READING PROGRESS RECORDED
            </text>

            {stats}

        </svg>
        """

        OUTPUT.write_text(svg, encoding="utf-8")
        return

    book = item["book"]

    title = escape(book.get("title") or "Untitled")

    authors = [
        contribution["author"]["name"]
        for contribution in book.get("contributions", [])
        if contribution.get("author")
        and contribution["author"].get("name")
    ]

    author = escape(", ".join(authors) or "Unknown author")

    progress = item["progress"]
    pages = item["pages"]
    percentage = item["percentage"]

    cover_url = (book.get("image") or {}).get("url")
    cover = get_cover_data(cover_url)

    if cover:
        cover_element = f"""
        <image href="{cover}"
        x="24" y="20" width="112" height="140"
        preserveAspectRatio="xMidYMid meet"/>
        """
    else:
        cover_element = """
        <rect x="24" y="20" width="112" height="140"
        fill="#25251f"/>
        """

    bar_width = 690 * percentage / 100

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg"
    width="900" height="200" viewBox="0 0 900 200">

        <rect width="900" height="200" fill="#11110f"/>

        {cover_element}

        <text x="164" y="37" fill="#8bac0f"
        font-family="monospace" font-size="12"
        letter-spacing="2">
        CURRENTLY READING
        </text>

        <text x="164" y="75" fill="#f0eee5"
        font-family="monospace" font-size="24">
        {title}
        </text>

        <text x="164" y="101" fill="#a5a398"
        font-family="monospace" font-size="14">
        {author}
        </text>

        <rect x="164" y="122" width="690"
        height="5" fill="#34342d"/>

        <rect x="164" y="122" width="{bar_width:.2f}"
        height="5" fill="#8bac0f"/>

        <text x="164" y="151" fill="#a5a398"
        font-family="monospace" font-size="12">
        {progress:,} / {pages:,} PAGES
        </text>

        <text x="854" y="151" fill="#8bac0f"
        font-family="monospace" font-size="12"
        text-anchor="end">
        {percentage:.1f}%
        </text>

        {stats}

    </svg>
    """

    OUTPUT.write_text(svg, encoding="utf-8")


def main():
    if not API_KEY:
        raise RuntimeError(
            "HARDCOVER_API_KEY is missing from .env"
        )

    ASSETS.mkdir(exist_ok=True)

    user = fetch_hardcover_data()

    item, year_count, lifetime_count = get_reading_data(user)

    generate_svg(item, year_count, lifetime_count)

    print(f"Books read this year: {year_count}")
    print(f"Books read in lifetime: {lifetime_count}")

    if item:
        print(
            f"Currently reading: {item['book']['title']} "
            f"({item['percentage']:.1f}%)"
        )
    else:
        print("No book with recorded reading progress found.")

    print(f"SVG generated: {OUTPUT}")


if __name__ == "__main__":
    main()

