# MSME Data Copilot — Detailed Report Content Draft

Use this as source material for the final dissertation. Adapt wording to your college template. Do not invent metrics; the numerical results below come from the implemented system’s sample-data run.

**Project title (suggested):**  
MSME Data Copilot: From Messy Business Data to Data Quality and Business Intelligence

**Repository:** https://github.com/YashikaNNN/msme-data-copilot

---

## Preliminary pages (what to write)

### Abstract (draft)

Micro, Small and Medium Enterprises (MSMEs) commonly store operational information in spreadsheets such as sales, customer, inventory and expense files. These files frequently contain missing values, duplicates, inconsistent identifiers, mixed date formats and invalid numeric amounts. Direct use of such data for reporting leads to unreliable business insights.

This project presents **MSME Data Copilot**, an end-to-end web-based data engineering and analytics platform. Users upload CSV/XLSX/JSON files; the system profiles datasets, calculates a real data-quality score, allows preview-based cleaning, validates records using configurable rules, and stores data in Bronze, Silver and Gold layers in PostgreSQL. Trusted Gold data is used for business dashboards. An AI Business Copilot answers natural-language questions using calculated metrics rather than unrestricted model guessing. If an LLM API key is unavailable, the system still returns evidence-based answers from analytics functions.

The system was implemented using Next.js, FastAPI, Pandas, SQLAlchemy and PostgreSQL, containerized with Docker Compose, and deployed using Render (API/database) and Vercel (frontend).

### Keywords

Data quality, ETL, MSME analytics, Bronze-Silver-Gold, FastAPI, Next.js, PostgreSQL, AI Copilot

### Acknowledgement

Thank guide, department, university, and any open-source tools used.

---

# Chapter 1 — Introduction

## 1.1 Background

MSMEs form a major part of the Indian and global economy. Their day-to-day records—orders, customers, stock and expenses—are often maintained in Excel or CSV exports from billing software, accounting tools or manual entry. Unlike large enterprises, MSMEs rarely have dedicated data engineers or analysts.

As a result, business owners face three practical difficulties:

1. **Unreliable source files** — missing cells, duplicate rows, inconsistent IDs (`C-001` vs `c 001`), ambiguous dates (`15/01/2024` vs `01/15/2024`), and invalid amounts.
2. **No repeatable cleaning process** — spreadsheet cleaning is manual, error-prone and hard to audit.
3. **Untrusted dashboards and AI answers** — if analytics or chatbots read messy files directly, they may produce plausible but incorrect numbers.

Modern data platforms address similar problems using layered architectures (raw → cleaned → curated) and data-quality monitoring. This project adapts those ideas to a practical MSME-oriented product.

## 1.2 Overview

**MSME Data Copilot** is a full-stack platform that converts messy business spreadsheets into trusted analytical data and insights.

**Product flow:**

Upload → Profile/Quality diagnosis → Clean (preview + approval) → Validate/Quarantine → Load trusted data → Analytics dashboard → AI Copilot

**Major modules:**

| Module | Purpose |
| --- | --- |
| Dataset Upload | CSV/XLSX/JSON ingestion with validation |
| Dataset Explorer | Schema, profile, preview, pagination |
| Data Quality Center | Real quality score and issue report |
| Cleaning Workspace | Preview/apply/reject cleaning without overwriting originals |
| Validation Engine | Rules, pass/fail/warning, quarantine |
| Pipeline Monitor | Extract–Profile–Clean–Validate–Transform–Load |
| Business Intelligence | Sales, customers, inventory, expenses KPIs |
| AI Copilot | Question → analytics facts → optional LLM narration |
| Lineage & Exports | Traceability and downloadable reports |

## 1.3 Applications of the proposed system

1. **Retail / wholesale shops** — clean sales and inventory files before monthly review.
2. **Small manufacturers** — standardize product/customer IDs across orders and stock.
3. **Service MSMEs** — expense vs revenue comparison from uploaded sheets.
4. **Student / academic demonstration** — end-to-end data engineering with measurable quality improvement.
5. **Pre-BI preparation** — produce trusted CSV/XLSX exports for Excel or other tools.

## 1.4 Tools and Technology

| Layer | Technology | Role |
| --- | --- | --- |
| Frontend | Next.js 15, React, TypeScript, Tailwind CSS, Recharts | UI, charts, copilot chat |
| Backend | Python, FastAPI, Pydantic | REST APIs, orchestration |
| Data processing | Pandas, openpyxl | File reading, profiling, cleaning |
| ORM / DB | SQLAlchemy, Alembic, PostgreSQL | Persistence, migrations |
| AI | Gemini / OpenRouter (optional) | Natural-language explanation of verified facts |
| Infra | Docker Compose, Render, Vercel | Local and cloud deployment |

## 1.5 Organization of Dissertation

- **Chapter 1** introduces the problem domain and proposed system.
- **Chapter 2** surveys related work and identifies research gaps.
- **Chapter 3** presents problem statement, methodology and objectives.
- **Chapter 4** reports experimental results, observations and limitations.
- **Chapter 5** concludes and outlines future work.

---

# Chapter 2 — Literature Survey

## 2.1 Introduction

This chapter reviews concepts underlying the project: spreadsheet-centric MSME data practice, ETL/ELT architectures, data-quality dimensions, analytics dashboards, and grounded LLM usage.

## 2.2 Significance of the main concept/technology

### Data quality

Common quality dimensions used in literature and industry include:

- **Completeness** — proportion of non-missing values
- **Uniqueness** — absence of unwanted duplicates
- **Validity** — values conform to expected type/format/domain
- **Consistency** — same real-world entity represented uniformly

A single “quality score” is often a weighted combination of these dimensions. In this project, the score is computed from uploaded cells, not hard-coded.

### Bronze / Silver / Gold

Widely used in lakehouse architectures:

- **Bronze** — raw ingested data
- **Silver** — cleaned/standardized data
- **Gold** — business-ready aggregates/entities

This separation protects originals and makes analytics reproducible.

### Grounded AI

Large Language Models can hallucinate numbers if asked to “read” messy files freely. Safer designs:

1. compute facts with deterministic code/SQL
2. pass only those facts to the LLM for explanation

## 2.3 Evolution of relevant techniques

1. Manual spreadsheet cleaning
2. Scripted ETL jobs (Python/SQL)
3. Visual ETL tools and data warehouses
4. Data observability / quality platforms
5. Analytics + conversational interfaces over curated data

MSME Data Copilot sits between (2) and (5): a lightweight, student-implementable stack with quality, pipeline visibility and grounded Q&A.

## 2.4 Overview of Prior Research / Related systems

Discuss in your own words with citations you actually read. Suggested themes:

- ETL/ELT process models
- Data profiling algorithms
- Rule-based data validation
- MSME digitization challenges
- BI dashboards for SMEs
- Retrieval-augmented / tool-using LLMs for analytics

Also note the project’s foundation: an earlier AI-powered ETL analytics prototype focused on event pipelines, which lacked multi-entity MSME quality workflows.

## 2.5 Research Gaps

1. Many academic demos show dashboards with **hard-coded or synthetic KPIs**.
2. Cleaning tools often **overwrite source data** without an immutable raw layer.
3. Chatbot demos frequently let LLMs invent business numbers.
4. MSME-focused systems rarely combine **quality scoring + quarantine + lineage + grounded Q&A** in one student-scale product.

**Gap addressed by this project:**  
An integrated, auditable path from messy MSME spreadsheets to trusted analytics and evidence-based AI answers.

---

# Chapter 3 — Problem Statement and Methodology

## 3.1 Problem Statement

MSMEs possess business data in files, but lack a systematic, transparent way to:

1. ingest multi-format datasets,
2. measure and explain data-quality issues,
3. clean data with user preview/approval,
4. validate and quarantine bad records,
5. store raw and trusted versions separately,
6. generate business KPIs only when required fields exist,
7. ask natural-language questions answered from verified metrics.

Therefore, there is a need for a platform that treats data engineering as the core contribution, with analytics and AI as layers on top of trusted data.

## 3.2 Methodology

### 3.2.1 Overall approach

The system follows a layered ETL methodology with explicit user control at cleaning time.

### Methodology flowchart (describe/draw vertically)

```
Start
  ↓
Upload business file(s) (CSV/XLSX/JSON)
  ↓
Store original file + Bronze rows
  ↓
Profile columns + compute quality score/issues
  ↓
Preview cleaning changes
  ↓
User Apply / Reject
  ↓
Write Silver copy (original Bronze unchanged)
  ↓
Run validation rules
  ↓
Quarantine blocking failures
  ↓
Map columns → Load Gold entities
  ↓
Record pipeline stages + lineage
  ↓
Serve Dashboard / Analytics / Copilot / Exports
  ↓
End
```

### 3.2.2 System architecture

Four layers:

1. Presentation (Next.js)
2. API (FastAPI)
3. Services (ingest, quality, cleaning, validation, pipeline, analytics, copilot)
4. Storage (files + PostgreSQL)

### 3.2.3 Quality scoring method

Dimensions calculated from actual data:

- Completeness
- Validity
- Uniqueness
- Consistency

Overall score is a weighted combination (implemented in code). Issues include category, column, affected count, severity, explanation, suggested resolution, auto-fixability and manual-review flag.

### 3.2.4 Cleaning method

Standard operations include:

- trim strings
- normalize IDs
- normalize dates
- coerce numbers
- standardize categories
- drop exact duplicates

Cleaning always runs on a copy. Apply writes Silver; Reject removes cleaned copy.

### 3.2.5 Validation and quarantine

Rules such as not-null, unique, numeric, non-negative, positive integer, valid date, no future date, email format. Blocking failures quarantine rows out of Gold.

### 3.2.6 AI Copilot method

```
User question
  → intent detection
  → call analytics/quality function
  → verified metrics
  → optional LLM narration (facts only)
  → answer + sources/metrics
```

No free-form SQL execution by the LLM.

### 3.2.7 Implementation strategy

1. Inspect existing ETL prototype
2. Create new repository (`msme-data-copilot`) without modifying original
3. Reuse stack patterns; implement MSME-specific modules
4. Test with deliberately messy sample datasets
5. Containerize and deploy

## 3.3 Objectives

1. Design and implement a web platform for MSME spreadsheet ingestion.
2. Automatically profile datasets and generate a real data-quality report.
3. Provide preview-based cleaning without overwriting originals.
4. Validate cleaned data and quarantine failing records.
5. Persist Bronze/Silver/Gold layers in PostgreSQL.
6. Generate business analytics from trusted Gold data only.
7. Provide an AI Copilot grounded in calculated metrics.
8. Expose pipeline monitoring, lineage and exports.
9. Demonstrate the system with sample messy datasets and deployment.

---

# Chapter 4 — Result Analysis

## 4.1 Result Analysis

### 4.1.1 Experimental setup

- Local: Docker Compose (Postgres + FastAPI + Next.js)
- Backend tests: `pytest` upload → quality → pipeline → analytics → copilot
- Sample datasets: sales, customers, products, inventory, expenses (intentionally messy)
- Cloud: GitHub repo; Render API/DB; Vercel frontend

### 4.1.2 Functional modules delivered

All core modules listed in Chapter 1 were implemented and integrated (see project checklist).

### 4.1.3 Sample pipeline outcomes (measured)

After **Load sample workspace** on the running system:

| Dataset | Pipeline status | Loaded (Gold) | Rejected (quarantine) |
| --- | --- | ---: | ---: |
| Sample products | success | 8 | 1 |
| Sample customers | success | 5 | 1 |
| Sample inventory | success | 9 | 0 |
| Sample expenses | success | 8 | 2 |
| Sample sales | success | 10 | 2 |

**Observation:** Invalid/negative/incomplete rows were rejected from Gold while valid rows remained available for analytics.

### 4.1.4 Quality and dashboard metrics (measured)

From dashboard after sample load:

| Metric | Observed value |
| --- | --- |
| Total datasets | 5 |
| Aggregate quality score | ~89.4% |
| Successful pipeline runs | 5 |

Sales analytics (Gold):

| Metric | Observed value |
| --- | --- |
| Available | True |
| Orders used | 10 |
| Revenue | ₹7,628.00 |

**Observation:** Revenue is computed only from rows with usable amounts; invalid amounts in source files do not silently become zero in the quality philosophy (invalid values are flagged; quarantine prevents untrusted rows from entering KPIs).

### 4.1.5 Copilot behaviour

Question: “Which month had the highest sales?”

- System returned a calculated answer from dated Gold sales (example observed: 2024-03 with ₹3,695.00 across 3 orders).
- With `LLM_PROVIDER=none`, narration note stated that AI explanation was unavailable and metrics-only mode was used.

**Observation:** Copilot remains useful without an LLM key; with a key it can narrate the same facts.

### 4.1.6 Screenshots to include in report

Capture and label:

1. Landing page  
2. Dashboard with live counts  
3. Upload page (multi-file)  
4. Dataset explorer (schema/profile)  
5. Data Quality Center (score + issues)  
6. Cleaning preview diff  
7. Validation results  
8. Pipeline run with 6 stages  
9. Analytics charts  
10. AI Copilot conversation  
11. Lineage view  
12. Exports page  
13. Sample data page  

### 4.1.7 Comparison: before vs after processing (qualitative table)

| Aspect | Before (raw spreadsheet) | After (platform) |
| --- | --- | --- |
| Missing values | Hidden in cells | Counted and explained |
| Duplicates | Easy to miss | Detected; removable via cleaning |
| Invalid amounts/dates | May break reports | Flagged / quarantined |
| Original file safety | Often overwritten | Bronze immutable |
| KPI trust | Uncertain | Based on Gold only |
| AI answers | Risk of hallucination | Grounded in metrics |

### 4.1.8 Limitations observed

1. Single-tenant workspace (no full multi-user authentication).
2. Column mapping is heuristic; unusual headers may need renaming.
3. Copilot supports a fixed set of business intents.
4. Free-tier cloud services may cold-start slowly.
5. Uploaded file storage on free PaaS disks may be ephemeral unless persistent disk is configured.

---

# Chapter 5 — Conclusions and Future Work

## 5.1 Conclusion

The project successfully designed and implemented **MSME Data Copilot**, a practical platform that transforms messy business spreadsheets into trusted analytical data. The core contribution is the data-engineering pipeline—profiling, quality scoring, preview-based cleaning, validation/quarantine, and Bronze–Silver–Gold storage—rather than a standalone chatbot or static dashboard.

Verified sample runs demonstrated that invalid rows can be quarantined while trusted rows produce real sales KPIs and grounded copilot answers. The application was packaged with Docker and prepared for deployment on Render and Vercel.

## 5.2 Scope for Future Work

1. Authentication and multi-user workspaces  
2. Rich interactive lineage graph  
3. More cleaning recipes and industry-specific rule packs  
4. Scheduled / incremental pipelines  
5. Broader copilot intents with safe query builders  
6. Persistent object storage for uploaded files in production  
7. Deeper reference integrity across many related datasets  

---

# References (starter list — replace with your actual citations)

1. Kimball, R., & Ross, M. — *The Data Warehouse Toolkit* (dimensional modeling / ETL concepts).  
2. Inmon, W. H. — data warehousing fundamentals.  
3. ISO/IEC 25012 — Data quality model (completeness, consistency, etc.).  
4. Papers/articles on SME digitalization and spreadsheet risks (add local library sources).  
5. FastAPI, Next.js, PostgreSQL, Pandas official documentation.  
6. Literature on lakehouse medallion architecture (Bronze/Silver/Gold).  
7. Papers on LLM hallucination and tool-augmented question answering over databases.

---

# Appendix suggestions

A. Sample data schema and intentionally injected errors  
B. API endpoint list (`/api/v1/...`)  
C. Database tables list  
D. Deployment steps (Render + Vercel)  
E. Test cases executed  

---

# One-page viva summary

**What is the project?**  
A data-quality + ETL + BI + grounded AI platform for MSME spreadsheets.

**What is new vs a normal dashboard?**  
Immutable raw layer, calculated quality scores, cleaning preview, quarantine, lineage, and AI that cannot invent KPIs.

**How do you prove it works?**  
Sample messy files → pipeline rejects bad rows → Gold analytics show real revenue → Copilot answers from those metrics.
