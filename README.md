# China AI Policy Corpus (CAPC)

**Accompanying repository for:**
> Joy Bose, "Toward an Indian Sovereign AI Strategy: Lessons from China's Coordinated AI Ecosystem," SSRN Working Paper, June 2026.

[![SSRN](https://img.shields.io/badge/SSRN-Working%20Paper-blue)](https://ssrn.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What this repository contains

| File | Description |
|------|-------------|
| `corpus_metadata.csv` | Metadata for 118 collected documents: title, organisation, year, document type, word count, URL, topic tags. No full text (copyright). |
| `scraper/china_ai_scraper_v2.py` | Python script to reproduce the corpus collection |
| `scraper/china_ai_analyze_v2.py` | Corpus analysis: keyword trends, topic clustering, temporal distribution |
| `scraper/requirements.txt` | Python dependencies |
| `docs/primary_sources.md` | Direct download URLs for the 17 primary Chinese policy documents (CSET Georgetown and China Law Translate translations) |

**Full document text is not included** for copyright reasons. Run the scraper to reproduce the corpus, or download primary source PDFs directly from the URLs in `docs/primary_sources.md`.

---

## Corpus overview

| Statistic | Value |
|-----------|-------|
| Total documents | 118 |
| Total words | ~191,000 |
| Year range | 2016 to 2026 |
| Organisations | 8 |
| Primary Chinese policy documents (translated) | 17 |

### Documents by organisation

| Organisation | Documents |
|-------------|-----------|
| DigiChina (Stanford University) | 60 |
| CSET Georgetown | 39 |
| War on the Rocks | 8 |
| MIT Technology Review | 6 |
| CSIS | 2 |
| Brookings Institution | 1 |
| China Law Translate | 1 |
| Atlantic Council | 1 |

### Topic coverage

Topics were tagged using keyword cluster matching across eleven policy domains: Compute and Hardware, Foundation Models and LLMs, Governance and Regulation, Military and Dual-Use, Talent and Education, Semiconductor Policy, Data and Surveillance, Industrial Policy and Five-Year Plans, Open Source and Ecosystem, India and South Asia, US-China Competition.

---

## How the corpus was collected

Collection used three complementary strategies:

**1. News feeds (RSS)**
Think tanks including Brookings, CSIS, War on the Rocks, MIT Technology Review, and Carnegie Endowment publish structured publication lists called RSS feeds. The scraper subscribes to these and retrieves full article text, bypassing JavaScript-heavy search pages that block simple scrapers.

**2. Website index files (sitemaps)**
Sites like DigiChina at Stanford and CSET Georgetown publish XML sitemaps listing all their pages. DigiChina uses a two-level sitemap index requiring recursive traversal. CSET's sitemap listed 4,138 pages; 678 matched the keyword filter for China AI policy content.

**3. Direct document download**
Seventeen known high-value primary policy documents, already translated into English by expert translators at CSET Georgetown and China Law Translate, were downloaded directly as PDFs. These form the empirical core of the paper's Chapter 3 analysis.

All requests used a 2.5-second pause between downloads and identified the research purpose in the request headers. Text extraction used BeautifulSoup for HTML and PyMuPDF for PDFs.

---

## Reproducing the corpus

```bash
# Install dependencies
pip install -r scraper/requirements.txt

# Run the scraper (takes 20-40 minutes, creates china_ai_corpus/)
python3 scraper/china_ai_scraper_v2.py

# Run the analyser
python3 scraper/china_ai_analyze_v2.py
```

Output: `china_ai_corpus/corpus.json` and `china_ai_corpus/corpus_summary.md`

For the 17 primary source PDFs, download them directly from the URLs in `docs/primary_sources.md` and place them in `china_ai_corpus/pdfs/`.

---

## Extending the corpus

The most important sources not yet systematically included:

- **CSET Translation Catalogue** — 200+ expert translations of Chinese primary documents: https://cset.georgetown.edu/publications/?fq[]=type:Translations
- **Jeffrey Ding's AI Policy Newsletter**: https://jeffrey-ding.ghost.io
- **NPC Observer** — National People's Congress legislation: https://npcobserver.com
- **DigiChina translation archive**: https://digichina.stanford.edu/work/
- **ORF India China Monitor**: https://www.orfonline.org
- **MERICS China AI Tracker**: https://merics.org/en/tracker/china-ai-tracker

---

## Citation

If you use this corpus or code, please cite:

```bibtex
@misc{bose2026india,
  title     = {Toward an Indian Sovereign AI Strategy: Lessons from China's Coordinated AI Ecosystem},
  author    = {Bose, Joy},
  year      = {2026},
  month     = {June},
  publisher = {SSRN},
  url       = {https://ssrn.com/abstract=XXXXXX},
  note      = {Working Paper}
}
```

---

## Related work by the author

- **darshana-graph** — Knowledge graph of Hindu, Buddhist, and Jain philosophical traditions (28,322 edges): https://huggingface.co/datasets/joyboseroy/darshana-graph
- **bengal-dharma-corpus** — Bengali devotional text corpus (75 texts): https://huggingface.co/datasets/joyboseroy/bengal-dharma-corpus
- **falkor-irac** — Legal reasoning system using knowledge graphs: https://github.com/joyboseroy/falkor-irac
- **telekg-agent** — Telecom knowledge graph agent: https://github.com/joyboseroy/telekg-agent

---

## License

Code (scraper scripts): MIT License

Corpus metadata CSV: CC BY 4.0

Document text is not included and remains under the copyright of the original publishers.

---

## Contact

Joy Bose | joy.bose@ieee.org | GitHub: joyboseroy | HuggingFace: joyboseroy
