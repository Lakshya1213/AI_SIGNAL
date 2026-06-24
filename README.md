# GraphOne Venture Ecosystem Ingestion Pipeline

This repository implements a highly concurrent, scalable, and fault-tolerant ingestion pipeline designed to extract, normalize, enrich, and canonicalize multi-dimensional datasets for the AI and venture ecosystem.

## Key Evaluation Areas Handled
*   **Massive Bulk Ingestion**: Handles one-time fetches of thousands of records without bottlenecks using concurrent network requests.
*   **Robust LLM fallback chain**: Implements a multi-tier API extraction sequence (`Gemini Flash` -> `Groq Llama 3` -> `DeepSeek`) with exponential backoff for `429` rate limits and intelligent chunking for `413` context limit handling.
*   **Extreme Freshness tracking**: Pulls news articles and job opportunities published in the last 24 hours, normalizing disparate dates to UTC ISO-8601.
*   **Fuzzy Entity Resolution**: Normalizes messy string startup names against a target seed database of 50 prominent AI startups (using space-insensitive RapidFuzz token sorting) and logs mappings.
*   **Asynchronous Parallel Scraping**: Resolves GitHub repository star counts concurrently via `ThreadPoolExecutor`.

---

## Directory Structure

```
graphone-trial/
├── src/
│   ├── main.py                     # Pipeline driver and CLI entry point
│   ├── crawlers/
│   │   ├── startup_crawler.py      # YC startup directory fetcher
│   │   ├── product_crawler.py      # YC product pricing classifier
│   │   ├── paper_crawler.py        # HF papers crawler & concurrent GitHub star scraper
│   │   ├── news_crawler.py         # 5 News RSS parser & body scraper
│   │   └── job_crawler.py          # 5 Job boards aggregator & classifier
│   ├── llm/
│   │   ├── chunking.py             # HTML cleaning and payload truncation
│   │   ├── retry_handler.py        # Exponential backoff with random jitter decorator
│   │   ├── gemini_provider.py      # Gemini Flash API wrapper
│   │   ├── groq_provider.py        # Groq Llama 3 API wrapper
│   │   ├── deepseek_provider.py    # DeepSeek API wrapper
│   │   └── llm_orchestrator.py     # Fallback chain & mock local parser
│   ├── entity_resolution/
│   │   ├── canonical_db.py         # 50 known AI startups seed list
│   │   └── resolver.py             # Fuzzy string matching & resolution mapping
│   ├── schemas/
│   │   ├── startup_schema.py       # Startup Entity model
│   │   ├── product_schema.py       # Product Entity model
│   │   ├── paper_schema.py         # Research Paper Entity model
│   │   ├── job_schema.py           # Job Entity model
│   │   └── news_schema.py          # News Entity model
│   ├── storage/
│   │   └── export_csv.py           # Excel compiler exporting 6 sheets
│   └── utils/
│       └── logger.py               # Colored console logger
├── tests/
│   ├── test_date_parsing.py        # Unit tests for date parser
│   ├── test_entity_resolution.py   # Unit tests for fuzzy resolver
│   └── test_llm_fallback.py        # Unit tests for LLM pricing classifier
├── requirements.txt                # Project dependencies
├── .env                            # Environment variables (API keys)
└── README.md                       # Documentation
```

---

## Setup & Installation

### 1. Prerequisites
*   Python 3.8 or higher.
*   Pip package manager.

### 2. Installation
Clone this repository and navigate to the directory:
```bash
git clone <repository-link>
cd graphone-trial
```
Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
# Optional API Keys (Required only for production LLM fallback chain mode)
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```
*Note: If no API keys are provided, the pipeline will run in `mock` mode utilizing a deterministic local rule-based extractor to classify pricing models and clean company names, ensuring zero API costs.*

---

## Running the Pipeline

### 1. Run Unit Tests
To verify date parsing, entity resolution, and orchestrator rule heuristics, run:
```bash
python -m pytest
```

### 2. Fast Pipeline Dry Run
To run a fast verification run (processing 5 items per category) using mock LLM mode:
```bash
python -m src.main --limit 5 --mock
```
This will instantly crawl the sources and compile a test spreadsheet under `outputs/graphone_data.xlsx`.

### 3. Full Production Pipeline Run
To scrape the full dataset (1,000+ startups, products, papers, news, jobs, and mappings):
*   **Using Heuristic Mode (Free)**:
    ```bash
    python -m src.main --limit 1000 --mock
    ```
*   **Using LLM fallback chain (Paid - requires API keys)**:
    ```bash
    python -m src.main --limit 1000
    ```

---

## Target Output Spreadsheet Structure
The output is saved as a multi-tab spreadsheet in `outputs/graphone_data.xlsx` containing:
1.  **Startups**: 1,000+ rows of normalized YC companies.
2.  **Products**: 1,000+ rows classifying pricing models (`FREE`, `FREEMIUM`, `PAID`, `ENTERPRISE`).
3.  **Research Papers**: 1,000+ rows of Hugging Face Machine Learning papers with code URLs and concurrent GitHub star counts.
4.  **Jobs**: Fresh jobs from the last 24 hours aggregated across Greenhouse, Remotive, and ai-jobs.net.
5.  **News**: Fresh articles from the last 24 hours from TechCrunch, VentureBeat, Nvidia, AWS, and KDnuggets containing scraped full-text contents.
6.  **Entity Mapping Log**: Logs of raw startup names resolved to our target seed database.
