# Data Sources

## BigQuery
- Project: `bigquery-public-data`
- Dataset: `chicago_taxi_trips` — historical Chicago taxi trip data
- Dataset: `noaa_gsod` — daily weather data; use O'Hare airport station

## Cloud SQL PostgreSQL
- Instance: `YOUR_INSTANCE` 
- Database: `YOUR_DATABASE`
- Table: `driver_profiles` — operational driver data 

Replace the instance and database names with your own.

## Local CSV
- Path: `.agent/data/rideshare_trips_by_month.csv`
- Monthly TNP rideshare trip volumes by community area
- Source: City of Chicago Data Portal