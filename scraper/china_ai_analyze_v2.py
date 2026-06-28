"""
China AI Policy Corpus Analyzer v2
====================================
Fixes from v1:
  - Expanded stopword list removes URL artifacts (digichina, https, stanford, work)
  - Min word count filter skips stub documents
  - Temporal trends use relative frequency, not raw counts
  - Outputs corpus_summary.md and a flat CSV for spreadsheet use

Usage:
  pip install scikit-learn pandas --break-system-packages
  python3 china_ai_analyze_v2.py
"""

import json, re, os, csv
from collections import Counter, defaultdict
from datetime import datetime

OUTPUT_DIR = "china_ai_corpus"
INPUT_JSON = os.path.join(OUTPUT_DIR, "corpus.json")
SUMMARY_MD = os.path.join(OUTPUT_DIR, "corpus_summary.md")
FLAT_CSV   = os.path.join(OUTPUT_DIR, "corpus_flat.csv")
MIN_WORDS  = 100   # skip stub documents in analysis

STOPWORDS = set("""
    the a an and or but in on at to of for with by from as is are was were
    be been being have has had do does did will would could should may might
    this that these those it its their they them we our us i you your he she
    also can more than other which who what when where how all some many
    such very also than into about through over after before between
    china chinese policy ai artificial intelligence technology
    said says according report paper study analysis research
    new year years also well one two three first second include
    digichina stanford https work edu org com www gov html pdf
    content dam pubs rand report reports page pages home post
    article publication publications view read more see
    january february march april may june july august september october november december
""".split())

TOPIC_CLUSTERS = {
    "Compute & Hardware":      ["compute","chip","gpu","hardware","data center","cloud","supercomputer","quantum"],
    "Foundation Models/LLMs":  ["llm","large language","foundation model","generative","gpt","chatgpt","deepseek",
                                "baidu","ernie","qwen","wenxin","pangu","hunyuan"],
    "Governance & Regulation": ["regulation","governance","legislation","cac","standards","nist","iso",
                                "accountability","transparency","risk management","safety framework"],
    "Military & Dual-Use":     ["military","pla","dual.use","civil.military","fusion","defence","defense",
                                "weapon","autonomous weapon","lethal","warfare","strategic competition"],
    "Talent & Education":      ["talent","education","university","phd","researcher","fellowship",
                                "workforce","stem","training","scholarship"],
    "Semiconductor Policy":    ["semiconductor","chip","tsmc","smic","huawei","export control",
                                "eda","advanced packaging","chip design","foundry"],
    "Data & Surveillance":     ["surveillance","facial recognition","privacy","biometric","personal data",
                                "social credit","monitoring","tracking","cctv"],
    "Industrial Policy":       ["five.year","14th","15th","made in china","industrial policy","2025","2030",
                                "2035","national plan","strategic industry","subsidy"],
    "Open Source & Ecosystem": ["open.source","open source","github","llama","open model","ecosystem",
                                "startup","venture","investment"],
    "India & South Asia":      ["india","indian","niti","meity","digital india","sovereign","south asia",
                                "indo.pacific","quad"],
    "US-China Competition":    ["competition","decoupling","export ban","entity list","sanctions",
                                "tech war","supply chain","ally","alliance","nato"],
}

def load_corpus():
    with open(INPUT_JSON, encoding="utf-8") as f:
        return json.load(f)

def tag_topics(text):
    text_l = text.lower()
    return [t for t, kws in TOPIC_CLUSTERS.items()
            if any(re.search(kw, text_l) for kw in kws)]

def extract_keywords(texts, n=25):
    """TF-IDF-style: count term frequency, down-rank very common terms."""
    doc_freq  = Counter()
    term_freq = Counter()
    n_docs    = len(texts)

    for text in texts:
        words = set(re.findall(r"\b[a-z][a-z\-]{3,}\b", text.lower()))
        words -= STOPWORDS
        doc_freq.update(words)
        term_freq.update(re.findall(r"\b[a-z][a-z\-]{3,}\b", text.lower()))

    # Simple TF-IDF proxy: term_freq / (1 + doc_freq)
    scores = {
        w: term_freq[w] / (1 + doc_freq[w])
        for w in term_freq
        if w not in STOPWORDS and doc_freq[w] >= 1
    }
    return sorted(scores.items(), key=lambda x: -x[1])[:n]

def main():
    if not os.path.exists(INPUT_JSON):
        print(f"ERROR: {INPUT_JSON} not found. Run china_ai_scraper_v2.py first.")
        return

    corpus = load_corpus()
    corpus = [d for d in corpus if d.get("word_count",0) >= MIN_WORDS]
    print(f"Loaded {len(corpus)} documents (≥{MIN_WORDS} words)")

    for doc in corpus:
        doc["topics"] = tag_topics(doc.get("text","") + " " + doc.get("title",""))

    years   = sorted(set(d["year"] for d in corpus if d["year"]))
    by_year = defaultdict(list)
    for d in corpus:
        if d["year"]:
            by_year[d["year"]].append(d)

    by_org = defaultdict(list)
    for d in corpus:
        by_org[d["org"]].append(d)

    topic_counts = Counter()
    for d in corpus:
        topic_counts.update(d["topics"])

    # ── Console output ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}\nCORPUS ANALYSIS\n{'='*60}")

    print(f"\nDocuments by year:")
    for y in years:
        docs = by_year[y]
        bar  = "█" * len(docs)
        avg  = sum(d["word_count"] for d in docs) // len(docs)
        print(f"  {y}: {len(docs):3d} {bar:<20} (avg {avg:,}w)")

    print(f"\nDocuments by organisation:")
    for org, docs in sorted(by_org.items(), key=lambda x: -len(x[1])):
        avg = sum(d["word_count"] for d in docs) // len(docs)
        print(f"  {len(docs):3d}  {org:<40} avg {avg:,}w")

    print(f"\nTopic cluster coverage:")
    for topic, count in topic_counts.most_common():
        pct = int(100 * count / len(corpus))
        print(f"  {count:3d} ({pct:2d}%)  {topic}")

    print(f"\nTop keywords (TF-IDF weighted, stopwords removed):")
    kws = extract_keywords([d["text"] for d in corpus])
    for kw, score in kws[:20]:
        print(f"  {score:6.1f}  {kw}")

    print(f"\nKeyword trends by year (TF-IDF top 6):")
    for y in years:
        texts = [d["text"] for d in by_year[y]]
        kws   = extract_keywords(texts, n=6)
        print(f"  {y}: {', '.join(k for k,_ in kws)}")

    # ── Flat CSV ───────────────────────────────────────────────────────────────
    with open(FLAT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title","org","year","doc_type","word_count","url",
                         "topics","scraped_at"])
        for d in sorted(corpus, key=lambda x: x.get("year") or 0):
            writer.writerow([
                d["title"], d["org"], d.get("year",""), d.get("doc_type",""),
                d["word_count"], d["url"],
                "; ".join(d.get("topics",[])), d.get("scraped_at",""),
            ])
    print(f"\nFlat CSV saved: {FLAT_CSV}")

    # ── Markdown summary ───────────────────────────────────────────────────────
    lines = [
        f"# China AI Policy Corpus — Summary",
        f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        f"*Minimum document length: {MIN_WORDS} words*",
        "",
        "## Overview",
        f"| | |",
        f"|---|---|",
        f"| Total documents | {len(corpus)} |",
        f"| Total words | {sum(d['word_count'] for d in corpus):,} |",
        f"| Year range | {min(years) if years else 'N/A'}–{max(years) if years else 'N/A'} |",
        f"| Organisations | {len(by_org)} |",
        "",
        "## Documents by Year",
        "| Year | Docs | Avg Words |",
        "|------|------|-----------|",
    ]
    for y in years:
        docs = by_year[y]
        avg  = sum(d["word_count"] for d in docs) // len(docs)
        lines.append(f"| {y} | {len(docs)} | {avg:,} |")

    lines += ["", "## Documents by Organisation",
              "| Organisation | Docs | Avg Words |",
              "|--------------|------|-----------|"]
    for org, docs in sorted(by_org.items(), key=lambda x: -len(x[1])):
        avg = sum(d["word_count"] for d in docs) // len(docs)
        lines.append(f"| {org} | {len(docs)} | {avg:,} |")

    lines += ["", "## Topic Coverage",
              "| Topic | Docs | % of Corpus |",
              "|-------|------|-------------|"]
    for topic, count in topic_counts.most_common():
        pct = round(100 * count / len(corpus), 1)
        lines.append(f"| {topic} | {count} | {pct}% |")

    lines += [
        "", "## Methods Note",
        "Documents were collected from publicly available sources including "
        "DigiChina (Stanford University), RAND Corporation, CNAS, CSIS, "
        "Brookings Institution, Carnegie Endowment for International Peace, "
        "CSET Georgetown, China Law Translate, ORF India, ASPI, "
        "War on the Rocks, Lawfare, and MIT Technology Review. "
        "Collection was via RSS feeds, sitemap crawling, and direct HTTP requests. "
        "Text was extracted using BeautifulSoup (HTML) and PyMuPDF (PDF). "
        f"Only documents with ≥{MIN_WORDS} words were retained for analysis. "
        "Topic tagging used keyword cluster matching across eleven policy domains. "
        "Keyword weighting used a TF-IDF proxy (term frequency / document frequency). "
        f"Collection date: {datetime.utcnow().strftime('%B %Y')}.",
    ]

    with open(SUMMARY_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Summary MD saved: {SUMMARY_MD}")
    print("\nDone. Consider running BERTopic for proper topic modelling.")

if __name__ == "__main__":
    main()
