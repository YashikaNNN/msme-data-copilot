# Viva preparation

## One-line pitch

MSME Data Copilot cleans messy business spreadsheets, scores data quality, loads trusted data, and answers business questions from real metrics.

## Likely questions

**Why Bronze / Silver / Gold?**  
To keep the original upload immutable, store a cleaned working copy, and isolate analytics to trusted rows.

**How is the quality score calculated?**  
From completeness, uniqueness, validity, and consistency measured on actual cells. It is not hard-coded.

**How does the AI avoid hallucinations?**  
It only narrates facts already computed by analytics functions. Without an API key, the calculated answer still works.

**What happens to invalid rows?**  
Blocking validation failures are quarantined in Silver and excluded from Gold/analytics.

**What can the system do without Gemini?**  
Upload, profile, clean, validate, pipeline, analytics, exports, and metric-based copilot answers.

## Demo script

1. Load sample workspace
2. Open a sales quality report and show real issues
3. Preview cleaning changes
4. Show a pipeline run with six stages
5. Open analytics revenue chart
6. Ask: “Which products generated the highest revenue?”
