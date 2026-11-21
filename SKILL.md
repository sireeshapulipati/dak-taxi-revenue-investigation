---
name: taxi-revenue-investigator
description: >
  Use this skill to investigate Chicago taxi revenue trends, anomalies, or business performance questions. The skill queries across BigQuery, Cloud SQL, and local data files to produce a structured investigation report with supporting charts.
---

# Taxi Revenue Investigator

## Goal

Investigate the user's question about Chicago taxi revenue by autonomously exploring and reasoning across all available data sources. Form hypotheses, test them with data, and synthesize findings into a clear report.

## Data Sources

Refer to `references/data_sources.md` for data source details.

You have access to:
- BigQuery: historical trip data and weather data
- Cloud SQL PostgreSQL: operational driver data
- Local CSV: rideshare competition data

Use DAK's catalog to understand the available schemas and relationships before querying. Let the data guide the investigation.

## Investigation Approach

- Start by understanding the scope of the question
- Explore the data before drawing conclusions
- Form hypotheses and test them
- Cross-reference findings across data sources when the question requires it
- Rule out explanations with data before accepting them
- Let patterns in the data surface naturally — don't assume where the answer will come from

## Output

Once the investigation is complete, produce:

1. **Executive Summary** — what you found, in 3-4 sentences
2. **Root Cause Finding** — the most supported explanation
3. **Affected Segments** — which zones, time periods, driver cohorts were most impacted
4. **Supporting Evidence** — key finding from each data source used
5. **Charts** — visualizations that support the findings
6. **Caveats** — any data limitations or assumptions

Save the following to the project folder:
- `findings_report.md` — the full report
- `charts/` — all generated chart images

## Constraints

- Only run SELECT queries — no INSERT, UPDATE, DELETE, or DROP
- Do not expose raw taxi_id values in output
- If a data source is unavailable, note it and continue with what is available