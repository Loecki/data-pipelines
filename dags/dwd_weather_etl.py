"""
DWD Weather ETL Pipeline
========================
Extracts hourly weather observations from DWD Open Data,
cleans and validates, loads into Postgres warehouse.

Source: https://opendata.dwd.de/climate_environment/CDC/
"""

from datetime import datetime, timedelta
import pandas as pd
import requests
import zipfile
import io
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine


# ---- Config ----
POSTGRES_CONN = "postgresql+psycopg2://etl_user:etl_password@postgres/dwd_warehouse"
DATA_DIR = "/opt/airflow/data"

# DWD station IDs: pick a few German cities
STATIONS = {
    "00433": "Berlin-Tempelhof",
    "01443": "Frankfurt/Main",
    "02564": "Hamburg-Fuhlsbüttel",
    "04177": "München-Stadt",
    "02290": "Hannover",
}

# Base URL for DWD recent hourly air temperature data
DWD_BASE_URL = (
    "https://opendata.dwd.de/climate_environment/CDC/"
    "observations_germany/climate/hourly/air_temperature/recent/"
)


def extract_weather_data(**context):
    """Extract: Download weather CSVs from DWD Open Data."""

    all_data = []

    for station_id, station_name in STATIONS.items():
        filename = f"stundenwerte_TU_{station_id}_akt.zip"
        url = f"{DWD_BASE_URL}{filename}"

        print(f"Downloading {station_name} ({station_id})...")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # Find the data file (starts with 'produkt_')
                data_files = [f for f in z.namelist() if f.startswith("produkt_")]
                if not data_files:
                    print(f"  No data file found for {station_id}")
                    continue

                with z.open(data_files[0]) as csv_file:
                    df = pd.read_csv(csv_file, sep=";", encoding="latin-1")
                    df["station_name"] = station_name
                    all_data.append(df)
                    print(f"  {len(df)} rows extracted")

        except Exception as e:
            print(f"  Error for {station_id}: {e}")
            continue

    if not all_data:
        raise ValueError("No data extracted from any station!")

    combined = pd.concat(all_data, ignore_index=True)

    # Save raw extract as parquet
    os.makedirs(DATA_DIR, exist_ok=True)
    raw_path = os.path.join(DATA_DIR, "raw_extract.parquet")
    combined.to_parquet(raw_path, index=False)
    print(f"Saved {len(combined)} total rows to {raw_path}")

    return raw_path


def transform_weather_data(**context):
    """Transform: Clean, rename, validate weather data."""

    raw_path = context["ti"].xcom_pull(task_ids="extract")
    df = pd.read_parquet(raw_path)

    # Rename DWD columns to clean names
    column_map = {
        "STATIONS_ID": "station_id",
        "MESS_DATUM": "timestamp",
        "TT_TU": "temperature_c",      # Air temperature 2m height
        "RF_TU": "humidity_pct",        # Relative humidity
    }

    # Keep only columns we have mappings for
    available = {k: v for k, v in column_map.items() if k in df.columns}
    df = df.rename(columns=available)
    df = df[list(available.values()) + ["station_name"]]

    # Parse timestamp (DWD format: YYYYMMDDHH)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y%m%d%H")

    # Station ID as string, zero-padded
    df["station_id"] = df["station_id"].astype(str).str.zfill(5)

    # Remove invalid readings (DWD uses -999 as missing)
    numeric_cols = ["temperature_c", "humidity_pct"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] < -900, col] = None

    # Drop full duplicates
    df = df.drop_duplicates(subset=["station_id", "timestamp"])

    # Sort
    df = df.sort_values(["station_id", "timestamp"])

    # Save cleaned data
    clean_path = os.path.join(DATA_DIR, "clean_extract.parquet")
    df.to_parquet(clean_path, index=False)
    print(f"Cleaned: {len(df)} rows, columns: {list(df.columns)}")

    return clean_path


def load_weather_data(**context):
    """Load: Write cleaned data to Postgres warehouse."""

    clean_path = context["ti"].xcom_pull(task_ids="transform")
    df = pd.read_parquet(clean_path)

    engine = create_engine(POSTGRES_CONN)

    # Load to raw table (append)
    df_raw = df.drop(columns=["station_name"], errors="ignore")
    df_raw["loaded_at"] = datetime.now()
    df_raw.to_sql("raw_weather_observations", engine, if_exists="append", index=False)
    print(f"Loaded {len(df_raw)} rows to raw_weather_observations")

    # Load to clean table (upsert via temp table)
    df_raw.to_sql("_temp_clean", engine, if_exists="replace", index=False)
    with engine.connect() as conn:
        conn.execute("""
            INSERT INTO clean_weather_observations
                (station_id, timestamp, temperature_c, humidity_pct, loaded_at)
            SELECT station_id, timestamp, temperature_c, humidity_pct, loaded_at
            FROM _temp_clean
            ON CONFLICT (station_id, timestamp)
            DO UPDATE SET
                temperature_c = EXCLUDED.temperature_c,
                humidity_pct = EXCLUDED.humidity_pct,
                loaded_at = EXCLUDED.loaded_at;
        """)
        conn.execute("DROP TABLE IF EXISTS _temp_clean;")
        conn.commit()
    print("Upserted to clean_weather_observations")


def build_daily_mart(**context):
    """Mart: Aggregate hourly → daily summaries."""

    engine = create_engine(POSTGRES_CONN)

    query = """
        INSERT INTO mart_daily_weather
            (station_id, date, avg_temperature, min_temperature, max_temperature,
             avg_humidity, total_precipitation, avg_wind_speed, observation_count, loaded_at)
        SELECT
            station_id,
            DATE(timestamp) as date,
            ROUND(AVG(temperature_c)::numeric, 2),
            ROUND(MIN(temperature_c)::numeric, 2),
            ROUND(MAX(temperature_c)::numeric, 2),
            ROUND(AVG(humidity_pct)::numeric, 2),
            NULL,  -- no precipitation in this dataset
            NULL,  -- no wind in this dataset
            COUNT(*),
            NOW()
        FROM clean_weather_observations
        GROUP BY station_id, DATE(timestamp)
        ON CONFLICT (station_id, date)
        DO UPDATE SET
            avg_temperature = EXCLUDED.avg_temperature,
            min_temperature = EXCLUDED.min_temperature,
            max_temperature = EXCLUDED.max_temperature,
            avg_humidity = EXCLUDED.avg_humidity,
            observation_count = EXCLUDED.observation_count,
            loaded_at = EXCLUDED.loaded_at;
    """

    with engine.connect() as conn:
        conn.execute(query)
        conn.commit()
    print("Daily mart rebuilt")


# ---- DAG Definition ----
default_args = {
    "owner": "luis",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="dwd_weather_etl",
    default_args=default_args,
    description="ETL pipeline: DWD weather data → Postgres warehouse",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["etl", "weather", "dwd"],
) as dag:

    extract = PythonOperator(
        task_id="extract",
        python_callable=extract_weather_data,
    )

    transform = PythonOperator(
        task_id="transform",
        python_callable=transform_weather_data,
    )

    load = PythonOperator(
        task_id="load",
        python_callable=load_weather_data,
    )

    mart = PythonOperator(
        task_id="build_daily_mart",
        python_callable=build_daily_mart,
    )

    # Pipeline: Extract → Transform → Load → Build Mart
    extract >> transform >> load >> mart
