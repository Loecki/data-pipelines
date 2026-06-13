"""
Running Analytics Dashboard
--------------------------------
Personal training analysis based on Garmin data.
Tracking progress towards a sub-4-hour marathon goal.

Data: Garmin Connect export (Activities.csv)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta, datetime
 
# ---- Page Config ----
st.set_page_config(
    page_title="Running Analytics",
    page_icon="🏃",
    layout="wide",
)
 
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
</style>
""", unsafe_allow_html=True)
 
 
# ---- Helper Functions ----
 
def parse_pace(pace_str):
    """Convert pace string 'M:SS' to total seconds per km."""
    if not pace_str or pace_str == "--":
        return None
    try:
        parts = pace_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None
 
 
def pace_seconds_to_str(seconds):
    """Convert seconds per km back to 'M:SS' string."""
    if seconds is None or pd.isna(seconds):
        return "--"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"
 
 
def parse_time(time_str):
    """Convert time string 'HH:MM:SS' to total minutes."""
    if not time_str or time_str == "--":
        return None
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
    except (ValueError, IndexError):
        return None
 
 
def classify_run(row):
    """Classify run type by distance."""
    title = str(row.get("Titel", "")).lower()
    dist = row.get("Distanz_km", 0)
    if "marathon" in title and dist > 40:
        return "Marathon"
    elif dist > 15:
        return "Lang (>15 km)"
    elif dist >= 8:
        return "Mittel (8–15 km)"
    else:
        return "Kurz (<8 km)"
 
 
def extract_location(title):
    """Extract location from title."""
    if " - " in title:
        return title.split(" - ")[0].strip()
    elif " " in title:
        return title.split(" ")[0].strip()
    return title
 
 
@st.cache_data
def load_data():
    """Load and prepare Garmin activities data."""
    df = pd.read_csv("data/Activities.csv")
 
    # Parse date
    df["Datum"] = pd.to_datetime(df["Datum"])
    df["Date_only"] = df["Datum"].dt.date
    df["Monat"] = df["Datum"].dt.to_period("M").astype(str)
    df["Woche"] = df["Datum"].dt.to_period("W").apply(lambda x: x.start_time)
    df["Wochentag"] = df["Datum"].dt.day_name()
 
    # Parse numeric fields
    df["Distanz_km"] = pd.to_numeric(
        df["Distanz"].astype(str).str.replace(",", ""), errors="coerce"
    )
    df["Kalorien"] = pd.to_numeric(
        df["Kalorien"].astype(str).str.replace(",", ""), errors="coerce"
    )
    df["Avg_HR"] = pd.to_numeric(df["Ø Herzfrequenz"], errors="coerce")
    df["Max_HR"] = pd.to_numeric(df["Maximale Herzfrequenz"], errors="coerce")
    df["Cadence"] = pd.to_numeric(
        df["Ø Schrittfrequenz (Laufen)"], errors="coerce"
    )
    df["Stride_Length"] = pd.to_numeric(df["Ø Schrittlänge"], errors="coerce")
    df["Ground_Contact"] = pd.to_numeric(
        df["Ø Bodenkontaktzeit"], errors="coerce"
    )
    df["Aerober_TE"] = pd.to_numeric(df["Aerober TE"], errors="coerce")
    df["Anstieg"] = pd.to_numeric(df["Anstieg gesamt"], errors="coerce")
    df["Avg_Power"] = pd.to_numeric(df["Ø Leistung"], errors="coerce")
    df["Schritte"] = pd.to_numeric(
        df["Schritte"].astype(str).str.replace(",", ""), errors="coerce"
    )
 
    # Parse pace and duration
    df["Pace_sec"] = df["Ø Pace"].apply(parse_pace)
    df["Best_Pace_sec"] = df["Beste Pace"].apply(parse_pace)
    df["Dauer_min"] = df["Zeit"].apply(parse_time)
 
    # Classify run type and location
    df["Lauftyp"] = df.apply(classify_run, axis=1)
    df["Ort"] = df["Titel"].apply(extract_location)
 
    # HR Zones (based on estimated max HR)
    # Zone 1-2: Easy/Aerobic (<150 bpm) — the "80%" runs
    # Zone 3+: Tempo/Threshold/Hard (>=150 bpm) — the "20%" runs
    df["HR_Zone"] = df["Avg_HR"].apply(
        lambda x: "Locker (< 150 bpm)" if pd.notna(x) and x < 150
        else ("Intensiv (≥ 150 bpm)" if pd.notna(x) else None)
    )
 
    # Days since previous run
    df = df.sort_values("Datum").reset_index(drop=True)
    df["Prev_Run_Date"] = df["Datum"].shift(1)
    df["Ruhetage"] = (df["Datum"] - df["Prev_Run_Date"]).dt.days - 1
    df.loc[0, "Ruhetage"] = None  # first run has no previous
 
    return df
 
 
df = load_data()
 
# ---- Sidebar ----
st.sidebar.title("🔍 Filter")
 
date_range = st.sidebar.date_input(
    "Zeitraum",
    value=(df["Datum"].min().date(), df["Datum"].max().date()),
    min_value=df["Datum"].min().date(),
    max_value=df["Datum"].max().date(),
)
 
# Apply filters
if len(date_range) == 2:
    filtered = df[
        (df["Datum"].dt.date >= date_range[0])
        & (df["Datum"].dt.date <= date_range[1])
    ]
else:
    filtered = df.copy()
 
# ---- Header ----
st.title("🏃 Running Analytics")
st.markdown("Persönliche Trainingsanalyse — Weg zum Sub-4-Marathon.")
 
if len(filtered) == 0:
    st.warning("Keine Daten für diese Filterauswahl.")
    st.stop()
 
# ============================================================
# KPI Row
# ============================================================
st.markdown("---")
 
marathon = df[df["Lauftyp"] == "Marathon"]
marathon_time = marathon["Zeit"].values[0] if len(marathon) > 0 else None
 
col1, col2, col3, col4, col5 = st.columns(5)
 
with col1:
    st.metric("Gesamtdistanz", f"{filtered['Distanz_km'].sum():.0f} km")
with col2:
    st.metric("Läufe", f"{len(filtered)}")
with col3:
    avg_pace = filtered["Pace_sec"].mean()
    st.metric("Ø Pace", pace_seconds_to_str(avg_pace))
with col4:
    st.metric("Ø Herzfrequenz", f"{filtered['Avg_HR'].mean():.0f} bpm")
with col5:
    if marathon_time:
        st.metric("Marathon", str(marathon_time)[:7])
    else:
        st.metric("Marathon", "—")
 
st.markdown("---")
 
# ============================================================
# Section 1: Trainingsvolumen
# ============================================================
st.header("📈 Trainingsvolumen über Zeit")
 
col_left, col_right = st.columns(2)
 
with col_left:
    weekly = (
        filtered.groupby("Woche")
        .agg(
            km=("Distanz_km", "sum"),
            runs=("Distanz_km", "count"),
            minutes=("Dauer_min", "sum"),
        )
        .reset_index()
    )
 
    fig_weekly = go.Figure()
    fig_weekly.add_trace(
        go.Bar(
            x=weekly["Woche"],
            y=weekly["km"],
            name="Kilometer",
            marker_color="#2E86AB",
            text=weekly["km"].apply(lambda x: f"{x:.0f}"),
            textposition="outside",
        )
    )
    fig_weekly.update_layout(
        title="Wöchentliche Kilometer",
        xaxis_title="",
        yaxis_title="km",
        height=400,
    )
    st.plotly_chart(fig_weekly, use_container_width=True)
 
with col_right:
    monthly = (
        filtered.groupby("Monat")
        .agg(
            km=("Distanz_km", "sum"),
            runs=("Distanz_km", "count"),
            hours=("Dauer_min", lambda x: x.sum() / 60),
        )
        .reset_index()
    )
 
    fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])
    fig_monthly.add_trace(
        go.Bar(
            x=monthly["Monat"],
            y=monthly["km"],
            name="Kilometer",
            marker_color="#2E86AB",
            text=monthly["km"].apply(lambda x: f"{x:.0f}"),
            textposition="outside",
        ),
        secondary_y=False,
    )
    fig_monthly.add_trace(
        go.Scatter(
            x=monthly["Monat"],
            y=monthly["runs"],
            name="Anzahl Läufe",
            mode="lines+markers",
            marker_color="#F18F01",
            line=dict(width=2),
        ),
        secondary_y=True,
    )
    fig_monthly.update_layout(
        title="Monatliche Übersicht",
        height=400,
    )
    fig_monthly.update_yaxes(title_text="km", secondary_y=False)
    fig_monthly.update_yaxes(title_text="Anzahl Läufe", secondary_y=True)
    st.plotly_chart(fig_monthly, use_container_width=True)
 
st.markdown("---")
 
# ============================================================
# Section 2: 80/20 Intensitätsverteilung
# ============================================================
st.header("💓 80/20-Regel: Läufst du locker genug?")
st.markdown(
    "Die effektivste Marathon-Vorbereitung folgt der 80/20-Regel: "
    "**80% der Kilometer locker** (HR < 150 bpm), nur **20% intensiv**. "
    "Die meisten Hobbyläufer laufen zu oft zu schnell."
)
 
hr_data = filtered.dropna(subset=["Avg_HR", "Distanz_km"]).copy()
 
if len(hr_data) > 0:
    col_left2, col_right2 = st.columns(2)
 
    with col_left2:
        # Km by HR zone
        zone_km = (
            hr_data.groupby("HR_Zone")["Distanz_km"]
            .sum()
            .reset_index()
        )
        total_km = zone_km["Distanz_km"].sum()
        zone_km["Anteil"] = (zone_km["Distanz_km"] / total_km * 100).round(1)
 
        zone_colors = {
            "Locker (< 150 bpm)": "#2E86AB",
            "Intensiv (≥ 150 bpm)": "#C73E1D",
        }
 
        fig_zone = px.pie(
            zone_km,
            values="Distanz_km",
            names="HR_Zone",
            color="HR_Zone",
            color_discrete_map=zone_colors,
            title="Kilometer-Verteilung nach Intensität",
            hole=0.45,
        )
        fig_zone.update_traces(
            textinfo="percent+label",
            textposition="outside",
        )
        fig_zone.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_zone, use_container_width=True)
 
        # Verdict
        locker_row = zone_km[zone_km["HR_Zone"] == "Locker (< 150 bpm)"]
        locker_pct = locker_row["Anteil"].values[0] if len(locker_row) > 0 else 0
 
        if locker_pct >= 75:
            st.success(f"✅ {locker_pct}% locker — gute Verteilung!")
        elif locker_pct >= 60:
            st.warning(f"⚠️ {locker_pct}% locker — etwas mehr Easy Runs einbauen.")
        else:
            st.error(f"🔴 {locker_pct}% locker — deutlich zu viel Intensität!")
 
    with col_right2:
        # Monthly 80/20 trend
        monthly_zones = (
            hr_data.groupby(["Monat", "HR_Zone"])["Distanz_km"]
            .sum()
            .reset_index()
        )
 
        fig_zone_trend = px.bar(
            monthly_zones,
            x="Monat",
            y="Distanz_km",
            color="HR_Zone",
            color_discrete_map=zone_colors,
            barmode="stack",
            title="Intensitätsverteilung pro Monat",
        )
        fig_zone_trend.update_layout(
            xaxis_title="",
            yaxis_title="km",
            height=400,
            legend_title="",
        )
        st.plotly_chart(fig_zone_trend, use_container_width=True)
 
st.markdown("---")
 
# ============================================================
# Section 3: Konsistenz-Kalender
# ============================================================
st.header("📅 Konsistenz: Wie regelmäßig läufst du?")
st.markdown(
    "Regelmäßigkeit ist der stärkste Prädiktor für Marathon-Erfolg. "
    "Ziel: **3–4 Läufe pro Woche**, ohne lange Lücken."
)
 
# Build a full date range and mark run days
min_date = filtered["Datum"].min().date()
max_date = filtered["Datum"].max().date()
all_dates = pd.date_range(min_date, max_date, freq="D")
 
# Create calendar dataframe
cal_df = pd.DataFrame({"Datum": all_dates})
cal_df["Date_only"] = cal_df["Datum"].dt.date
cal_df["Wochentag_Nr"] = cal_df["Datum"].dt.weekday  # 0=Mo, 6=So
cal_df["KW"] = cal_df["Datum"].dt.isocalendar().week.astype(int)
cal_df["Jahr"] = cal_df["Datum"].dt.year
cal_df["KW_Label"] = cal_df["Datum"].dt.strftime("KW%V %Y")
 
# Merge with runs
run_dates = filtered.groupby("Date_only").agg(
    km=("Distanz_km", "sum"),
    runs=("Distanz_km", "count"),
).reset_index()
 
cal_df = cal_df.merge(run_dates, on="Date_only", how="left")
cal_df["km"] = cal_df["km"].fillna(0)
 
# Create week index for y-axis (continuous)
cal_df["Week_Start"] = cal_df["Datum"] - pd.to_timedelta(cal_df["Wochentag_Nr"], unit="D")
week_starts = sorted(cal_df["Week_Start"].unique())
week_map = {ws: i for i, ws in enumerate(week_starts)}
cal_df["Week_Idx"] = cal_df["Week_Start"].map(week_map)
 
day_labels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
 
fig_cal = go.Figure()
 
fig_cal.add_trace(
    go.Heatmap(
        x=cal_df["Wochentag_Nr"],
        y=cal_df["Week_Idx"],
        z=cal_df["km"],
        colorscale=[
            [0, "#ebedf0"],       # no run
            [0.01, "#9be9a8"],    # light
            [0.3, "#40c463"],     # medium
            [0.6, "#30a14e"],     # good
            [1.0, "#216e39"],     # long run
        ],
        showscale=True,
        colorbar=dict(title="km"),
        text=cal_df.apply(
            lambda r: f"{r['Date_only']}\n{r['km']:.1f} km" if r["km"] > 0
            else str(r["Date_only"]),
            axis=1,
        ),
        hoverinfo="text",
        xgap=3,
        ygap=3,
    )
)
 
# Add month labels
cal_df["Month_Start"] = cal_df["Datum"].dt.day == 1
month_labels = cal_df[cal_df["Month_Start"]]
 
fig_cal.update_layout(
    title="Laufkalender (grüner = mehr Kilometer)",
    xaxis=dict(
        tickvals=list(range(7)),
        ticktext=day_labels,
        side="top",
    ),
    yaxis=dict(
        autorange="reversed",
        showticklabels=False,
    ),
    height=max(300, len(week_starts) * 18),
)
st.plotly_chart(fig_cal, use_container_width=True)
 
# Weekly frequency stats
weekly_runs = filtered.groupby("Woche").size().reset_index(name="runs_per_week")
avg_runs_week = weekly_runs["runs_per_week"].mean()
weeks_3plus = (weekly_runs["runs_per_week"] >= 3).sum()
total_weeks = len(weekly_runs)
 
col_c1, col_c2, col_c3 = st.columns(3)
with col_c1:
    st.metric("Ø Läufe/Woche", f"{avg_runs_week:.1f}")
with col_c2:
    st.metric("Wochen mit 3+ Läufen", f"{weeks_3plus} von {total_weeks}")
with col_c3:
    longest_gap = filtered["Ruhetage"].max()
    st.metric("Längste Pause", f"{longest_gap:.0f} Tage" if pd.notna(longest_gap) else "—")
 
st.markdown("---")
 
# ============================================================
# Section 4: Wochenkilometer-Progression (10%-Regel)
# ============================================================
st.header("📊 Aufbau: Steigerst du sicher?")
st.markdown(
    "Die **10%-Regel**: das wöchentliche Volumen sollte maximal 10% gegenüber "
    "der Vorwoche steigen. Zu schnelle Steigerung ist die Hauptursache für Verletzungen."
)
 
weekly_vol = (
    filtered.groupby("Woche")["Distanz_km"]
    .sum()
    .reset_index()
    .sort_values("Woche")
)
weekly_vol.columns = ["Woche", "km"]
weekly_vol["Vorwoche_km"] = weekly_vol["km"].shift(1)
weekly_vol["Steigerung_pct"] = (
    (weekly_vol["km"] - weekly_vol["Vorwoche_km"]) / weekly_vol["Vorwoche_km"] * 100
).round(1)
weekly_vol["Über_10pct"] = weekly_vol["Steigerung_pct"] > 10
 
fig_prog = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.08,
    row_heights=[0.55, 0.45],
    subplot_titles=("Wöchentliche Kilometer", "Steigerung zur Vorwoche (%)"),
)
 
# Top: weekly km bars
fig_prog.add_trace(
    go.Bar(
        x=weekly_vol["Woche"],
        y=weekly_vol["km"],
        marker_color="#2E86AB",
        text=weekly_vol["km"].apply(lambda x: f"{x:.0f}"),
        textposition="outside",
        name="km",
        showlegend=False,
    ),
    row=1, col=1,
)
 
# Bottom: percentage change
colors = weekly_vol["Steigerung_pct"].apply(
    lambda x: "#C73E1D" if pd.notna(x) and x > 10
    else ("#F18F01" if pd.notna(x) and x > 0 else "#2E86AB")
)
 
fig_prog.add_trace(
    go.Bar(
        x=weekly_vol["Woche"],
        y=weekly_vol["Steigerung_pct"],
        marker_color=colors,
        text=weekly_vol["Steigerung_pct"].apply(
            lambda x: f"{x:+.0f}%" if pd.notna(x) else ""
        ),
        textposition="outside",
        name="Steigerung",
        showlegend=False,
    ),
    row=2, col=1,
)
 
# 10% line
fig_prog.add_hline(
    y=10, line_dash="dash", line_color="#C73E1D", opacity=0.7,
    annotation_text="10%-Grenze",
    row=2, col=1,
)
 
fig_prog.update_layout(height=600)
fig_prog.update_yaxes(title_text="km", row=1, col=1)
fig_prog.update_yaxes(title_text="%", row=2, col=1)
st.plotly_chart(fig_prog, use_container_width=True)
 
# Stats
over_10 = weekly_vol["Über_10pct"].sum()
total_w = len(weekly_vol.dropna(subset=["Steigerung_pct"]))
if total_w > 0:
    if over_10 / total_w < 0.2:
        st.success(f"✅ Nur {over_10} von {total_w} Wochen über 10% Steigerung — solider Aufbau!")
    else:
        st.warning(f"⚠️ {over_10} von {total_w} Wochen über 10% — Verletzungsrisiko beachten.")
 
st.markdown("---")
 
# ============================================================
# Section 5: Aerobe Effizienz
# ============================================================
st.header("🫀 Aerobe Effizienz: Wirst du fitter?")
st.markdown(
    "Der wichtigste Fortschrittsindikator: **gleiche Pace bei niedrigerem Puls** "
    "(oder schnellere Pace bei gleichem Puls). Hier sehen wir nur lockere Läufe "
    "(HR < 150 bpm), um den Vergleich fair zu halten."
)
 
easy_runs = filtered[
    (filtered["Avg_HR"] < 150)
    & (filtered["Avg_HR"].notna())
    & (filtered["Pace_sec"].notna())
    & (filtered["Distanz_km"] >= 5)  # mindestens 5km für stabilen Vergleich
].copy()
 
if len(easy_runs) >= 3:
    col_left5, col_right5 = st.columns(2)
 
    with col_left5:
        # Pace at easy HR over time
        fig_eff = px.scatter(
            easy_runs,
            x="Datum",
            y="Pace_sec",
            size="Distanz_km",
            color="Avg_HR",
            color_continuous_scale="RdYlGn_r",
            trendline="ols",
            hover_data={
                "Pace_sec": False,
                "Distanz_km": ":.1f",
                "Avg_HR": ":.0f",
            },
            title="Pace bei lockeren Läufen (HR < 150)",
        )
 
        pace_ticks = [320, 340, 360, 380, 400]
        fig_eff.update_layout(
            yaxis=dict(
                autorange="reversed",
                tickvals=pace_ticks,
                ticktext=[pace_seconds_to_str(p) for p in pace_ticks],
            ),
            yaxis_title="Pace (min/km)",
            xaxis_title="",
            height=450,
            coloraxis_colorbar=dict(title="HR"),
        )
        st.plotly_chart(fig_eff, use_container_width=True)
 
    with col_right5:
        # HR at easy pace over time
        fig_hr_trend = px.scatter(
            easy_runs,
            x="Datum",
            y="Avg_HR",
            size="Distanz_km",
            color="Pace_sec",
            color_continuous_scale="RdYlGn",
            trendline="ols",
            hover_data={
                "Pace_sec": False,
                "Distanz_km": ":.1f",
            },
            title="Herzfrequenz bei lockeren Läufen",
        )
        fig_hr_trend.update_layout(
            yaxis_title="Ø Herzfrequenz (bpm)",
            xaxis_title="",
            height=450,
            coloraxis_colorbar=dict(title="Pace (s)"),
        )
        st.plotly_chart(fig_hr_trend, use_container_width=True)
 
    # Trend summary
    first_half = easy_runs.head(len(easy_runs) // 2)
    second_half = easy_runs.tail(len(easy_runs) // 2)
 
    pace_change = second_half["Pace_sec"].mean() - first_half["Pace_sec"].mean()
    hr_change = second_half["Avg_HR"].mean() - first_half["Avg_HR"].mean()
 
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        direction = "schneller" if pace_change < 0 else "langsamer"
        st.metric(
            "Pace-Trend (Easy Runs)",
            f"{abs(pace_change):.0f} sec/km {direction}",
            delta=f"{-pace_change:.0f} sec",
            delta_color="normal",
        )
    with col_e2:
        direction = "niedriger" if hr_change < 0 else "höher"
        st.metric(
            "HR-Trend (Easy Runs)",
            f"{abs(hr_change):.0f} bpm {direction}",
            delta=f"{-hr_change:.0f} bpm",
            delta_color="normal",
        )
else:
    st.info("Zu wenige lockere Läufe (≥5 km, HR < 150) für eine Trendanalyse.")
 
st.markdown("---")
 
# ============================================================
# Section 6: Erholungstage
# ============================================================
st.header("😴 Erholung: Gönnst du dir genug Pause?")
st.markdown(
    "Ausreichend Erholung zwischen den Läufen ist entscheidend für Anpassung und "
    "Verletzungsprävention. **1–2 Ruhetage** zwischen den Läufen sind ideal."
)
 
rest_data = filtered.dropna(subset=["Ruhetage"]).copy()
 
if len(rest_data) > 0:
    col_left6, col_right6 = st.columns(2)
 
    with col_left6:
        fig_rest = px.histogram(
            rest_data,
            x="Ruhetage",
            nbins=int(rest_data["Ruhetage"].max()) + 1,
            title="Verteilung der Ruhetage zwischen Läufen",
            color_discrete_sequence=["#2E86AB"],
        )
        fig_rest.update_layout(
            xaxis_title="Ruhetage",
            yaxis_title="Häufigkeit",
            height=400,
            bargap=0.1,
        )
        st.plotly_chart(fig_rest, use_container_width=True)
 
    with col_right6:
        # Rest days over time
        fig_rest_time = px.scatter(
            rest_data,
            x="Datum",
            y="Ruhetage",
            size="Distanz_km",
            color="Ruhetage",
            color_continuous_scale=["#2E86AB", "#F18F01", "#C73E1D"],
            title="Ruhetage über Zeit",
        )
        fig_rest_time.add_hline(
            y=2, line_dash="dash", line_color="#F18F01", opacity=0.7,
            annotation_text="2 Tage Empfehlung",
        )
        fig_rest_time.update_layout(
            xaxis_title="",
            yaxis_title="Ruhetage",
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig_rest_time, use_container_width=True)
 
    # Stats
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric("Ø Ruhetage", f"{rest_data['Ruhetage'].mean():.1f}")
    with col_r2:
        back_to_back = (rest_data["Ruhetage"] == 0).sum()
        st.metric("Back-to-Back Läufe", f"{back_to_back}")
    with col_r3:
        long_breaks = (rest_data["Ruhetage"] >= 5).sum()
        st.metric("Pausen ≥ 5 Tage", f"{long_breaks}")
 
# ---- Footer ----
st.markdown("---")
st.caption(
    "Datenquelle: Garmin Connect Export · "
    "Dashboard erstellt mit Streamlit & Plotly"
)