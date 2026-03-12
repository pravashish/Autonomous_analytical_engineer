# Autonomous Analytics Engineer

A local SQL analysis tool for Snowflake, built with Streamlit and Ollama. No API keys. No cost per call. Everything runs on your machine.

---

## What it does

**Query Analyzer** runs rule checks against your SQL first — SELECT *, missing date filters, cartesian joins, functions on join columns — then passes the query to a local model for deeper interpretation. The severity score is purely rule-based, so the same query always gets the same score. The LLM adds context, it doesn't control the score.

**Table Explainer** is for warehouses with no documentation. Pick a table, it fetches the schema and a handful of sample rows, then takes a guess at the business purpose, grain, candidate primary key, and what tests probably make sense. Useful when you inherit someone else's warehouse.

**dbt Generator** takes a source table and a plain-English description of what you want to build. Returns model SQL, a schema.yml, and a list of assumptions the model made. Read the assumptions — they tell you where the output is likely wrong.

---

## How the analysis works

SQL doesn't go straight to the model:

```
SQL Input
    │
    ├── Rule engine (instant, no model calls)
    │       SELECT *              →  HIGH
    │       No WHERE filter       →  HIGH
    │       CROSS JOIN            →  HIGH
    │       Function on join col  →  MEDIUM
    │       Ambiguous aliases     →  LOW
    │
    └── LLM (Ollama, local)
            intent
            performance risks
            recommendations
            rewritten SQL
```

Rule flags and LLM output render side by side. The severity score is computed from rule flags only — deterministic, repeatable, not subject to model mood.

---

## Setup

Python 3.10+, a Snowflake account, and Ollama installed.

```bash
git clone <repo>
cd autonomous-analytics-engineer
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Snowflake credentials:

```
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=ANALYTICS_DEMO
SNOWFLAKE_SCHEMA=MARTS
```

Pull a model. No GPU means start with the smaller one:

```bash
ollama pull qwen2.5-coder:1.5b   # 1GB download, runs fine on CPU
ollama pull qwen2.5-coder:7b     # 4.7GB, noticeably better, needs a GPU
```

```bash
streamlit run app.py
```

---

## Project structure

```
├── app.py                     # Streamlit UI, 3 tabs
├── src/
│   ├── config.py              # env vars, model names, token caps
│   ├── snowflake_client.py    # all Snowflake queries in one place
│   ├── claude_client.py       # Ollama wrapper with timing and logging
│   ├── prompts.py             # prompt templates
│   ├── rules.py               # deterministic SQL rule checks
│   └── utils/
│       ├── sql_utils.py       # clean and trim SQL before sending to model
│       └── formatting.py      # Streamlit render helpers
├── analytics_project/         # dbt project with staging and mart models
└── examples/
    └── sample_queries.sql     # a few bad queries to test the analyzer
```

---

## Demo data

A small synthetic ARR dataset — three tables, shaped like a SaaS revenue warehouse:

| Table | Rows | What it contains |
|---|---|---|
| `PROGRAMS_DIM` | 5 | programs with region |
| `DATES_DIM` | 730 | two years of dates |
| `ARR_PROGRAM_FACT` | 14 | ARR movements by program and period |

---

## Logging

Every model request is timed and written to the terminal and `logs/llm.log`:

```
22:40:54 | INFO  | REQUEST  caller=analyze_query model=qwen2.5-coder:1.5b max_tokens=800
22:40:54 | DEBUG |   prompt_chars: 842
22:41:02 | INFO  | RESPONSE elapsed=8.12s response_chars=703
```

The sidebar shows a live Ollama ping on every page load. If the model isn't running, it fails loudly rather than hanging.

---

## What's next

- Batch-pull the 20 slowest queries and analyze them in one run
- Severity dashboard over query history
- PDF export of analysis results
