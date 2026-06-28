"""
China AI Policy Corpus Builder v2
===================================
Fixes from v1:
  - DigiChina sitemap is a sitemap index → recurse into sub-sitemaps
  - Brookings RSS gives summaries; follow link to fetch full article
  - CSET Georgetown added (best primary doc translations)
  - ORF, War on the Rocks, Lawfare: fixed RSS URLs
  - Suppress XML-parsed-as-HTML warnings
  - Stopword list expanded to remove URL artifacts
  - lxml used for sitemap parsing if available

Usage:
  pip install requests beautifulsoup4 pymupdf feedparser lxml --break-system-packages
  python3 china_ai_scraper_v2.py
"""

import requests, feedparser, json, time, re, os, hashlib, warnings
from datetime import datetime
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from urllib.parse import urljoin, urlparse
import fitz

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ── Config ────────────────────────────────────────────────────────────────────
HEADERS     = {"User-Agent": "China-AI-Policy-Research-Bot/1.0 (academic; joyboseroy@github)"}
TIMEOUT     = 25
DELAY       = 2.5
OUTPUT_DIR  = "china_ai_corpus"
PDF_DIR     = os.path.join(OUTPUT_DIR, "pdfs")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "corpus.json")

os.makedirs(PDF_DIR, exist_ok=True)

CHINA_AI_KEYWORDS = re.compile(
    r"china|chinese|beijing|prc|artificial intelligence|\bai\b|machine learning"
    r"|technology policy|five.year|made in china|miit|semiconductor|algorithm"
    r"|foundation model|llm|compute|chip|digital economy|cyber|data governance"
    r"|surveillance|huawei|baidu|alibaba|tencent|deepseek|cac\b|autonomous"
    r"|robotics|dual.use|military.civil|tech competition|strategic competition",
    re.IGNORECASE
)

# ── RSS sources (corrected URLs) ──────────────────────────────────────────────
RSS_SOURCES = [
    {
        "org": "Brookings",
        "rss": "https://www.brookings.edu/feed/?s=china+artificial+intelligence",
        "fetch_full": True,   # follow link to get full article, not just summary
    },
    {
        "org": "Carnegie Endowment",
        "rss": "https://carnegieendowment.org/rss/solr/?fa=topic&q=china+artificial+intelligence",
        "fetch_full": True,
    },
    {
        "org": "ORF India",
        "rss": "https://www.orfonline.org/feed/?s=china+artificial+intelligence",
        "fetch_full": True,
        "filter_keywords": True,
    },
    {
        "org": "War on the Rocks",
        "rss": "https://warontherocks.com/feed/",
        "fetch_full": True,
        "filter_keywords": True,
    },
    {
        "org": "Lawfare",
        "rss": "https://www.lawfaremedia.org/feed",
        "fetch_full": True,
        "filter_keywords": True,
    },
    {
        "org": "Nikkei Asia (AI/China)",
        "rss": "https://asia.nikkei.com/rss/feed/section/China",
        "fetch_full": False,   # paywalled full text, summaries only
        "filter_keywords": True,
    },
    {
        "org": "MIT Technology Review",
        "rss": "https://www.technologyreview.com/feed/",
        "fetch_full": True,
        "filter_keywords": True,
    },
    {
        "org": "CSIS",
        "rss": "https://www.csis.org/rss.xml",
        "fetch_full": True,
        "filter_keywords": True,
    },
]

# ── Sitemap sources ───────────────────────────────────────────────────────────
# DigiChina has a sitemap INDEX (links to sub-sitemaps) — handle separately
DIGICHINA_SITEMAP_INDEX = "https://digichina.stanford.edu/sitemap.xml"

# CSET Georgetown — best primary doc translations
CSET_SITEMAP = "https://cset.georgetown.edu/sitemap.xml"

# ── Direct high-value URLs (verified working) ─────────────────────────────────
DIRECT_URLS = [
    # DigiChina — use correct current URLs from their site
    ("DigiChina (Stanford)", "https://digichina.stanford.edu/work/full-translation-chinas-new-generation-artificial-intelligence-development-plan-2017/"),
    ("DigiChina (Stanford)", "https://digichina.stanford.edu/work/chinas-ai-governance-principles-and-related-documents/"),
    ("DigiChina (Stanford)", "https://digichina.stanford.edu/work/decoding-chinas-ai-dream/"),

    # CSET translations (Georgetown) — primary docs
    ("CSET Georgetown", "https://cset.georgetown.edu/publication/chinas-new-generation-ai-development-plan/"),
    ("CSET Georgetown", "https://cset.georgetown.edu/publication/ai-safety-in-china/"),
    ("CSET Georgetown", "https://cset.georgetown.edu/publication/chinas-approach-to-ai-safety/"),
    ("CSET Georgetown", "https://cset.georgetown.edu/publication/chinas-ai-chip-policy/"),

    # China Law Translate — regulations in English
    ("China Law Translate", "https://www.chinalawtranslate.com/en/generative-ai-regulation/"),
    ("China Law Translate", "https://www.chinalawtranslate.com/en/algorithm-recommendations/"),
    ("China Law Translate", "https://www.chinalawtranslate.com/en/deep-synthesis/"),

    # ASPI ICPC China reports (try alternate URLs)
    ("ASPI", "https://www.aspi.org.au/report/artificial-intelligence-chinas-national-strategy"),

    # RAND (open access reports — no PDF auth needed for HTML versions)
    ("RAND", "https://www.rand.org/pubs/research_reports/RRA400-1.html"),

    # Atlantic Council
    ("Atlantic Council", "https://www.atlanticcouncil.org/programs/geotech-center/"),
    ("Atlantic Council", "https://www.atlanticcouncil.org/insight-impact/reports/china-ai-strategy/"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  [WARN] {url[:70]}: {e}")
        return None

def is_relevant(text):
    return bool(CHINA_AI_KEYWORDS.search(text))

def clean_text(text):
    text = re.sub(r"https?://\S+", " ", text)          # strip URLs from text
    text = re.sub(r"\b\w{1,2}\b", " ", text)           # strip very short tokens
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()[:25000]

def extract_html_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style","nav","footer","header","aside","form",
                     "figure","figcaption",".sidebar",".related",".ad"]):
        tag.decompose()
    # Prefer article/main content blocks
    for selector in ["article", "main", ".entry-content", ".post-content",
                     ".article-body", ".content-body", '[class*="article"]',
                     '[class*="content"]']:
        block = soup.select_one(selector)
        if block and len(block.get_text()) > 200:
            return clean_text(block.get_text(separator="\n", strip=True))
    return clean_text(soup.get_text(separator="\n", strip=True))

def extract_pdf_text(pdf_bytes, url):
    fname = hashlib.md5(url.encode()).hexdigest()[:10] + ".pdf"
    fpath = os.path.join(PDF_DIR, fname)
    with open(fpath, "wb") as f:
        f.write(pdf_bytes)
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n\n".join(page.get_text() for page in doc)
        return clean_text(text), fpath
    except Exception as e:
        return f"[PDF error: {e}]", fpath

def infer_year(url, text):
    for pattern in [r"/(20[12]\d)/", r"\b(201[5-9]|202\d)\b"]:
        m = re.search(pattern, url + " " + text[:1000])
        if m:
            return int(m.group(1))
    return None

def make_record(org, url, title, text, doc_type, extra=None):
    rec = {
        "title":      title.strip()[:200],
        "url":        url,
        "org":        org,
        "year":       infer_year(url, text),
        "doc_type":   doc_type,
        "scraped_at": datetime.utcnow().isoformat(),
        "word_count": len(text.split()),
        "text":       text,
    }
    if extra:
        rec.update(extra)
    return rec

def scrape_url(org, url, min_words=150):
    """Fetch article or PDF, return record or None."""
    time.sleep(DELAY)
    r = safe_get(url)
    if not r:
        return None
    ct = r.headers.get("Content-Type", "")
    if "pdf" in ct or url.lower().endswith(".pdf"):
        text, pdf_path = extract_pdf_text(r.content, url)
        title = urlparse(url).path.split("/")[-1].replace("-"," ").replace(".pdf","").title()
        if not is_relevant(title + text):
            return None
        rec = make_record(org, url, title, text, "pdf", {"pdf_path": pdf_path})
    else:
        soup  = BeautifulSoup(r.text, "html.parser")
        h1    = soup.find("h1")
        title_tag = soup.find("title")
        title = (h1.get_text(strip=True) if h1
                 else (title_tag.string if title_tag else url))
        text  = extract_html_text(r.text)
        if len(text.split()) < min_words:
            return None
        if not is_relevant(title + " " + text[:2000]):
            return None
        rec = make_record(org, url, title, text, "html")
    return rec

# ── Sitemap recursion ─────────────────────────────────────────────────────────

def parse_sitemap(url, depth=0):
    """Return all <loc> URLs from a sitemap or sitemap index."""
    if depth > 2:
        return []
    r = safe_get(url)
    if not r:
        return []
    try:
        soup = BeautifulSoup(r.text, "lxml-xml")
    except Exception:
        soup = BeautifulSoup(r.text, "html.parser")

    # Sitemap index: contains <sitemap><loc>...</loc></sitemap>
    sub_sitemaps = soup.find_all("sitemap")
    if sub_sitemaps:
        all_urls = []
        for s in sub_sitemaps:
            loc = s.find("loc")
            if loc:
                time.sleep(0.5)
                all_urls.extend(parse_sitemap(loc.text.strip(), depth+1))
        return all_urls

    # Regular sitemap: contains <url><loc>...</loc></url>
    return [loc.text.strip() for loc in soup.find_all("loc")]


def scrape_sitemap_source(org, sitemap_url, url_filter_re=None, cap=40):
    print(f"\n  Sitemap: {org}")
    all_urls = parse_sitemap(sitemap_url)
    print(f"  Total URLs in sitemap tree: {len(all_urls)}")

    if url_filter_re:
        candidates = [u for u in all_urls if re.search(url_filter_re, u, re.I)]
    else:
        candidates = [u for u in all_urls
                      if re.search(r"china|ai|artific|tech|digit|policy|translat", u, re.I)]
    print(f"  Candidates after filter: {len(candidates)}")

    records = []
    for url in candidates[:cap]:
        rec = scrape_url(org, url)
        if rec:
            records.append(rec)
            print(f"    ✓ [{rec['year']}] {rec['title'][:60]} ({rec['word_count']}w)")
    return records

# ── RSS scraping ──────────────────────────────────────────────────────────────

def scrape_rss(source):
    print(f"\n  RSS: {source['org']}")
    feed = feedparser.parse(source["rss"])
    if not feed.entries:
        print(f"  [WARN] No entries found")
        return []

    records = []
    for entry in feed.entries[:30]:
        title   = entry.get("title","")
        url     = entry.get("link","")
        summary = entry.get("summary","") + entry.get("content",[{"value":""}])[0].get("value","")

        if source.get("filter_keywords") and not is_relevant(title + " " + summary):
            continue

        print(f"    → {title[:65]}")

        if source.get("fetch_full") and url:
            rec = scrape_url(source["org"], url)
        else:
            # Use summary text only
            text = clean_text(BeautifulSoup(summary, "html.parser").get_text())
            if len(text.split()) < 50:
                rec = None
            else:
                rec = make_record(source["org"], url, title, text, "rss_summary")

        if rec:
            records.append(rec)
            print(f"      ✓ [{rec['year']}] {rec['word_count']} words")
        else:
            print(f"      ✗ skipped (too short or irrelevant)")

    print(f"  {source['org']}: {len(records)} documents kept")
    return records

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    corpus    = []
    seen_urls = set()

    def add(records):
        for r in (records or []):
            if r and r["url"] not in seen_urls:
                corpus.append(r)
                seen_urls.add(r["url"])

    print("=" * 65)
    print("CHINA AI POLICY CORPUS BUILDER v2")
    print("=" * 65)

    # Phase 1: RSS
    print("\n[PHASE 1] RSS feeds")
    for source in RSS_SOURCES:
        add(scrape_rss(source))

    # Phase 2: DigiChina sitemap (sitemap index → recurse)
    print("\n[PHASE 2] DigiChina sitemap (recursive)")
    add(scrape_sitemap_source(
        "DigiChina (Stanford)",
        DIGICHINA_SITEMAP_INDEX,
        url_filter_re=r"digichina\.stanford\.edu/work/",
        cap=60,
    ))

    # Phase 2b: CSET Georgetown sitemap
    print("\n[PHASE 2b] CSET Georgetown sitemap")
    add(scrape_sitemap_source(
        "CSET Georgetown",
        CSET_SITEMAP,
        url_filter_re=r"cset\.georgetown\.edu/publication/",
        cap=40,
    ))

    # Phase 3: Direct URLs
    print("\n[PHASE 3] Direct high-value URLs")
    for org, url in DIRECT_URLS:
        print(f"  → {url[:70]}")
        rec = scrape_url(org, url)
        if rec:
            add([rec])
            print(f"    ✓ [{rec['year']}] {rec['title'][:55]} ({rec['word_count']}w)")
        else:
            print(f"    ✗ skipped")

    # Save
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    # Summary
    from collections import Counter
    by_org = Counter(r["org"] for r in corpus)
    years  = sorted(set(r["year"] for r in corpus if r["year"]))

    print(f"\n{'='*65}")
    print(f"CORPUS COMPLETE")
    print(f"  Total documents : {len(corpus)}")
    print(f"  Total words     : {sum(r['word_count'] for r in corpus):,}")
    print(f"  Year range      : {years[0] if years else 'N/A'}–{years[-1] if years else 'N/A'}")
    print(f"  Saved to        : {OUTPUT_JSON}")
    print("\nBy organisation:")
    for org, n in by_org.most_common():
        print(f"  {n:3d}  {org}")
    print(f"\nNext: python3 china_ai_analyze.py")

if __name__ == "__main__":
    main()
