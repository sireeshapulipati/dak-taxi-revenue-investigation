# dak-taxi-revenue-investigation

An agent investigates why Chicago taxi revenue fell between 2019 and 2023. It works across three data sources, using Google Cloud's Data Agent Kit (DAK) in Antigravity IDE and a custom skill that tells it how to run the investigation.

This repo goes with the Towards Data Science article "I Let a Data Agent Investigate a Taxi Revenue Drop" (link coming once it's published).

## What the agent does

Given one business question, the agent pulls from three places and joins what it finds.

| Source | What's in it |
| --- | --- |
| BigQuery public data, `chicago_taxi_trips` | Taxi trips and fares |
| BigQuery public data, `noaa_gsod` | Daily weather |
| Cloud SQL for PostgreSQL | Synthetic driver profiles (Bronze, Silver and Gold tiers) |
| Local CSV | Monthly rideshare trip counts |

It writes a `findings_report.md` and a `charts/` folder. The versions from my run are in `sample-output/`, so you can compare them with yours.

## What's in the repo

```
.
├── .agent/
│   ├── skills/
│   │   └── taxi-revenue-investigator/
│   │       ├── SKILL.md
│   │       └── references/
│   │           └── data_sources.md
│   └── data/
│       └── rideshare_trips_by_month.csv
├── sample-output/
│   ├── charts/
│   ├── findings_report.md
│   └── investigate.py
├── driver_profiles.csv
└── README.md
```

The `.agent` folder is the only part you copy into your own project. `sample-output/` holds what the agent produced during my run, for comparison. Your run will produce similar files, but not identical ones. `driver_profiles.csv` is setup data.

`SKILL.md` is the custom skill. It sets the method and the output format and puts guardrails on the agent, such as read-only queries and no raw driver IDs in the output. `references/data_sources.md` lists the project, instance and table details the skill reads.

`sample-output/investigate.py` is the script the agent wrote during my run. It's here for reference only, and you don't run it. The skill doesn't contain a script, so your agent will write its own.

`driver_profiles.csv` holds the synthetic driver profiles. You import it into Cloud SQL (see below), and the agent reads it from there.

## What you need

- A Google Cloud project with BigQuery and Cloud SQL enabled
- A Cloud SQL for PostgreSQL instance with a database for the driver profiles
- Antigravity IDE (Claude Code or Codex also work with DAK)
- Data Agent Kit installed, with only the MCP servers this task uses turned on. I enabled BigQuery, Cloud SQL and the Knowledge Catalog. Keeping the list short keeps the agent's context small.

## Setup

1. Clone the repo, then copy the `.agent` folder into the folder you'll open in Antigravity.
2. Replace the placeholders in `.agent/skills/taxi-revenue-investigator/references/data_sources.md`. Use the same values in the Cloud SQL commands below.

   | Placeholder | Replace with |
   | --- | --- |
   | `YOUR_PROJECT_ID` | Your Google Cloud project ID |
   | `YOUR_INSTANCE` | Your Cloud SQL instance name |
   | `YOUR_DATABASE` | The database holding the driver profiles |
   | `YOUR_EMAIL` | The Google account you use with Google Cloud |

3. Set up Cloud SQL (see below) and import the driver profiles.
4. Connect the BigQuery and Cloud SQL MCP servers in DAK.

### Cloud SQL setup

Enable the Cloud SQL Admin API and the Dataplex integration, so the Knowledge Catalog can see the instance.

```bash
gcloud services enable sqladmin.googleapis.com --project=YOUR_PROJECT_ID

gcloud sql instances patch YOUR_INSTANCE \
  --enable-dataplex-integration
```

### Driver profiles

The profiles are synthetic. Each `taxi_id` from the public dataset has a tier (Bronze, Silver or Gold). The data is in `driver_profiles.csv` at the root of the repo, and you import it into your own Cloud SQL database. Connect as an admin user (Cloud SQL Studio in the console works, or `psql`) and create the table.

```sql
CREATE TABLE driver_profiles (
  taxi_id      TEXT PRIMARY KEY,
  driver_tier  TEXT,
  vehicle_type TEXT,
  company      TEXT,
  home_zone    TEXT,
  hire_date    DATE,
  active       BOOLEAN
);
```

Then load the CSV. With `psql`, this skips the header row.

```sql
\copy driver_profiles FROM 'driver_profiles.csv' WITH (FORMAT csv, HEADER true)
```

Check the load.

```sql
SELECT driver_tier, COUNT(*) FROM driver_profiles GROUP BY driver_tier;
```

Add your Google account as an IAM user on the instance. The instance also needs IAM database authentication turned on (the `cloudsql.iam_authentication` flag).

```bash
gcloud sql users create "YOUR_EMAIL" \
  --instance=YOUR_INSTANCE \
  --type=CLOUD_IAM_USER
```

Then, as the admin user, give that account read access. Do this after the table exists.

```sql
GRANT CONNECT ON DATABASE "YOUR_DATABASE" TO "YOUR_EMAIL";
GRANT USAGE ON SCHEMA public TO "YOUR_EMAIL";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "YOUR_EMAIL";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO "YOUR_EMAIL";
```

## Run it

In the agent chat, invoke the skill and give it the question.

```
/taxi-revenue-investigator Why did taxi revenue drop between 2019 and 2023, and which zones and driver tiers were hit hardest?
```

The skill leaves the answer open. Your numbers on the public data should match the report. If you load the included driver profiles, the tier results should match too.

## How the cross-system join works

The agent pulls the `taxi_id` list for each tier from Cloud SQL, then puts those IDs into an `IN (...)` filter on the BigQuery trips table. No federated query is involved. With a much larger driver table I'd switch to a federated query, so the whole join runs inside BigQuery and the IDs never pass through the agent.

## Results from my run

| Measure | 2019 | 2023 | Change |
| --- | --- | --- | --- |
| Taxi trips | 17.83M | 6.47M | -63.7% |
| Taxi revenue | $326.7M | $179.9M | about -45% |
| Rideshare trips | 104.76M | 76.15M | -27.3% |

Taxi share of combined trips fell from 14.6% to 7.9%. Rideshare recovered to 73% of its 2019 volume, while taxis reached 36%. The Loop and Near North Side account for $85.8M of the $146.8M revenue decline, and O'Hare revenue fell only 17.6%.

The tier breakdown shows Bronze, Silver and Gold all dropping, but those profiles are synthetic, so treat that part as a demo of the join and not as real driver behavior.

## Safety notes

- The skill only allows SELECT queries.
- It tells the agent not to print raw `taxi_id` values in its output, which keeps the report readable.

## License

This repo is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). You can share and adapt it, including for commercial use, as long as you give credit.

The Chicago taxi trips and NOAA weather data come from public datasets and keep their own terms. The rideshare CSV comes from the City of Chicago Data Portal. The driver profiles are synthetic.