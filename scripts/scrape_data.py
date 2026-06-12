"""
Scrapes Pakistan tourism content from Wikipedia, Wikivoyage, and gov.pk.
Saves cleaned text to data/raw/<slug>.txt and writes sources_manifest.json.

Usage:
    python scripts/scrape_data.py
"""

import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import cfg
from src.utils import clean_text, ensure_dirs, setup_logger, slugify

logger = setup_logger("scraper")

SCRAPE_TARGETS = [
    # Wikipedia — tourism overview
    ("https://en.wikipedia.org/wiki/Tourism_in_Pakistan", "Wikipedia: Tourism in Pakistan"),
    # Wikipedia — major cities
    ("https://en.wikipedia.org/wiki/Lahore", "Wikipedia: Lahore"),
    ("https://en.wikipedia.org/wiki/Karachi", "Wikipedia: Karachi"),
    ("https://en.wikipedia.org/wiki/Islamabad", "Wikipedia: Islamabad"),
    ("https://en.wikipedia.org/wiki/Peshawar", "Wikipedia: Peshawar"),
    ("https://en.wikipedia.org/wiki/Quetta", "Wikipedia: Quetta"),
    ("https://en.wikipedia.org/wiki/Multan", "Wikipedia: Multan"),
    ("https://en.wikipedia.org/wiki/Rawalpindi", "Wikipedia: Rawalpindi"),
    ("https://en.wikipedia.org/wiki/Faisalabad", "Wikipedia: Faisalabad"),
    # Wikipedia — northern regions & valleys
    ("https://en.wikipedia.org/wiki/Gilgit-Baltistan", "Wikipedia: Gilgit-Baltistan"),
    ("https://en.wikipedia.org/wiki/Hunza_Valley", "Wikipedia: Hunza Valley"),
    ("https://en.wikipedia.org/wiki/Swat_District", "Wikipedia: Swat District"),
    ("https://en.wikipedia.org/wiki/Skardu", "Wikipedia: Skardu"),
    ("https://en.wikipedia.org/wiki/Naran,_Khyber_Pakhtunkhwa", "Wikipedia: Naran"),
    ("https://en.wikipedia.org/wiki/Chitral_District", "Wikipedia: Chitral"),
    ("https://en.wikipedia.org/wiki/Kalash_people", "Wikipedia: Kalash People"),
    # Wikipedia — natural wonders & peaks
    ("https://en.wikipedia.org/wiki/Fairy_Meadows", "Wikipedia: Fairy Meadows"),
    ("https://en.wikipedia.org/wiki/K2", "Wikipedia: K2"),
    ("https://en.wikipedia.org/wiki/Nanga_Parbat", "Wikipedia: Nanga Parbat"),
    ("https://en.wikipedia.org/wiki/Karakoram_Highway", "Wikipedia: Karakoram Highway"),
    ("https://en.wikipedia.org/wiki/Deosai_National_Park", "Wikipedia: Deosai National Park"),
    # Wikipedia — heritage & monuments
    ("https://en.wikipedia.org/wiki/Mohenjo-daro", "Wikipedia: Mohenjo-daro"),
    ("https://en.wikipedia.org/wiki/Taxila", "Wikipedia: Taxila"),
    ("https://en.wikipedia.org/wiki/Badshahi_Mosque", "Wikipedia: Badshahi Mosque"),
    ("https://en.wikipedia.org/wiki/Lahore_Fort", "Wikipedia: Lahore Fort"),
    ("https://en.wikipedia.org/wiki/Rohtas_Fort", "Wikipedia: Rohtas Fort"),
    ("https://en.wikipedia.org/wiki/Derawar_Fort", "Wikipedia: Derawar Fort"),
    ("https://en.wikipedia.org/wiki/Shalimar_Gardens,_Lahore", "Wikipedia: Shalimar Gardens"),
    # Wikipedia — culture & cuisine
    ("https://en.wikipedia.org/wiki/Pakistani_cuisine", "Wikipedia: Pakistani Cuisine"),
    ("https://en.wikipedia.org/wiki/Culture_of_Pakistan", "Wikipedia: Culture of Pakistan"),
    # Wikivoyage
    ("https://en.wikivoyage.org/wiki/Pakistan", "Wikivoyage: Pakistan"),
    ("https://en.wikivoyage.org/wiki/Lahore", "Wikivoyage: Lahore"),
    ("https://en.wikivoyage.org/wiki/Karachi", "Wikivoyage: Karachi"),
    ("https://en.wikivoyage.org/wiki/Islamabad", "Wikivoyage: Islamabad"),
    ("https://en.wikivoyage.org/wiki/Gilgit-Baltistan", "Wikivoyage: Gilgit-Baltistan"),
    ("https://en.wikivoyage.org/wiki/Hunza_Valley", "Wikivoyage: Hunza Valley"),
    ("https://en.wikivoyage.org/wiki/Skardu", "Wikivoyage: Skardu"),
    ("https://en.wikivoyage.org/wiki/Swat_Valley", "Wikivoyage: Swat Valley"),
    ("https://en.wikivoyage.org/wiki/Peshawar", "Wikivoyage: Peshawar"),
    ("https://en.wikivoyage.org/wiki/Khyber_Pass", "Wikivoyage: Khyber Pass"),
]


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": cfg.user_agent})
    return session


def fetch_page(url: str, session: requests.Session) -> str | None:
    try:
        resp = session.get(url, timeout=cfg.request_timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def extract_wiki(html: str) -> str:
    """Works for both Wikipedia and Wikivoyage — same MediaWiki DOM structure.
    Wikipedia now serves multiple mw-parser-output divs; pick the richest one."""
    soup = BeautifulSoup(html, "lxml")

    # Remove clutter
    for tag in soup.select(
        ".mw-editsection, table.infobox, .navbox, .navbox-styles, "
        ".sistersitebox, .reflist, .references, .mw-references-wrap, "
        ".hatnote, #toc, .toc, .mw-jump-link, sup, script, style, "
        ".thumb, .gallery"
    ):
        tag.decompose()

    # Wikipedia now renders multiple mw-parser-output divs — pick the one with most content
    candidates = soup.find_all("div", class_="mw-parser-output")
    if not candidates:
        return extract_generic(html)

    content = max(candidates, key=lambda d: len(d.find_all("p")))

    # Fallback: if no p tags found anywhere, try <main>
    if not content.find("p"):
        main_tag = soup.find("main")
        if main_tag:
            content = main_tag

    paragraphs = []
    for tag in content.find_all(["p", "li", "h2", "h3"]):
        text = tag.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)

    return "\n\n".join(paragraphs)


def extract_generic(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    return "\n\n".join(p for p in paragraphs if p)


def scrape_all():
    ensure_dirs(cfg.raw_data_dir)
    session = make_session()
    manifest = {}

    total = len(SCRAPE_TARGETS)
    for i, (url, label) in enumerate(SCRAPE_TARGETS, 1):
        slug = slugify(url)
        out_path = cfg.raw_data_dir / f"{slug}.txt"

        logger.info("[%d/%d] Scraping: %s", i, total, label)

        html = fetch_page(url, session)
        if html is None:
            logger.warning("Skipping %s (fetch failed)", url)
            continue

        is_wiki = "wikipedia.org" in url or "wikivoyage.org" in url
        raw_text = extract_wiki(html) if is_wiki else extract_generic(html)
        cleaned = clean_text(raw_text)

        if len(cleaned) < 200:
            logger.warning("Skipping %s (content too short: %d chars)", url, len(cleaned))
            continue

        out_path.write_text(cleaned, encoding="utf-8")
        manifest[slug] = {"url": url, "label": label, "chars": len(cleaned)}
        logger.info("  Saved %d chars → %s", len(cleaned), out_path.name)

        time.sleep(cfg.scrape_delay_seconds)

    manifest_path = cfg.raw_data_dir / "sources_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Manifest written: %s (%d sources)", manifest_path, len(manifest))
    return manifest


if __name__ == "__main__":
    manifest = scrape_all()
    print(f"\nScraping complete. {len(manifest)} pages saved to {cfg.raw_data_dir}")
