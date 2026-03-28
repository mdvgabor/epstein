import csv
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

rows = []
for page in range(1, 100):
    req = Request(
        f"https://jmail.world/person?page={page}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    soup = BeautifulSoup(urlopen(req).read(), "html.parser")
    cards = soup.select('a.email-row[href^="/person/"]')
    if not cards:
        break
    for card in cards:
        slug = card["href"].removeprefix("/person/")
        name = card.select_one(".sender-name").get_text(strip=True)
        desc = card.select_one(".preview").get_text(strip=True)
        count = int(card.select_one(".email-date")["title"].split()[0].replace(",", ""))
        rows.append({
            "slug": slug,
            "name": name,
            "description": desc,
            "email_count": count,
            "url": f"https://jmail.world/person/{slug}",
        })
    print(f"Page {page}: {len(cards)} people")

print(f"Total: {len(rows)} people")

with open("data/jmail_people.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["slug", "name", "description", "email_count", "url"])
    w.writeheader()
    w.writerows(rows)

print("Saved to data/jmail_people.csv")
