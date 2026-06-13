# DWD Weather ETL Pipeline 🌤️

End-to-End ETL pipeline that extracts weather data from Germany's national weather service (DWD Open Data), transforms and validates it, and loads it into a Postgres data warehouse.

## Architecture

```
DWD Open Data API
       │
       ▼
   ┌────────┐     ┌───────────┐     ┌────────┐     ┌────────────┐
   │Extract │────▶│ Transform │────▶│  Load  │────▶│ Daily Mart │
   └────────┘     └───────────┘     └────────┘     └────────────┘
       │               │                │                │
   Download ZIP    Clean names      Upsert to       Aggregate
   Parse CSV      Validate data    raw + clean     hourly → daily
   Save Parquet   Handle nulls      Postgres         summaries
```

**Orchestrated by Apache Airflow | Data stored in PostgreSQL**

## Tech Stack

- **Orchestration:** Apache Airflow 2.9
- **Database:** PostgreSQL 16
- **Language:** Python 3.12
- **Data Processing:** pandas
- **Infrastructure:** Docker Compose
- **Data Source:** [DWD Open Data](https://opendata.dwd.de/)

## Data Model

| Layer | Table | Description |
|-------|-------|-------------|
| Raw | `raw_weather_observations` | Unmodified data, append-only |
| Clean | `clean_weather_observations` | Validated, deduped, upserted |
| Mart | `mart_daily_weather` | Daily aggregates per station |
| Dim | `dim_stations` | Station metadata |

## Stations

| ID | City |
|----|------|
| 00433 | Berlin-Tempelhof |
| 01443 | Frankfurt/Main |
| 02564 | Hamburg-Fuhlsbüttel |
| 04177 | München-Stadt |
| 02290 | Hannover |

## Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/dwd-etl-pipeline.git
cd dwd-etl-pipeline

# 2. Start containers
docker compose up airflow-init
docker compose up -d

# 3. Open Airflow UI
# http://localhost:8080
# Login: admin / admin

# 4. Activate the DAG "dwd_weather_etl" and trigger it
```

## Query Examples

```sql
-- Average temperature per city, last 7 days
SELECT s.station_name, d.date, d.avg_temperature
FROM mart_daily_weather d
JOIN dim_stations s ON d.station_id = s.station_id
WHERE d.date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY d.date DESC, d.avg_temperature;

-- Hottest day per station
SELECT station_id, date, max_temperature
FROM mart_daily_weather
WHERE max_temperature = (
    SELECT MAX(max_temperature)
    FROM mart_daily_weather m
    WHERE m.station_id = mart_daily_weather.station_id
);
```

## Next Steps

- [ ] Add more stations
- [ ] Add precipitation + wind data
- [ ] Build dbt transformation layer
- [ ] Add data quality checks (Great Expectations)
- [ ] Deploy to cloud (AWS/GCP)
- [ ] Build Streamlit dashboard

## Author

Luis Loeck
