"""
Running Analytics Dashboard
--------------------------------
Personal training analysis based on Garmin data.
Tracking progress towards a sub-4-hour marathon goal.

Data: Garmin Connect export (Activities.csv)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta

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

# ---- Color Palette ----
RUN_TYPE_COLORS = {
    "Kurz (<8 km)": "#2E86AB",
    "Mittel (8–15 km)": "#F18F01",
    "Lang (>15 km)": "#A23B72",
    "Marathon": "#3B1F2B",
}


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
    """Extract location from title like 'Hamburg Laufen' or 'Hamburg - Basis'."""
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

    # Parse pace (M:SS → seconds)
    df["Pace_sec"] = df["Ø Pace"].apply(parse_pace)
    df["Best_Pace_sec"] = df["Beste Pace"].apply(parse_pace)

    # Parse duration to minutes
    df["Dauer_min"] = df["Zeit"].apply(parse_time)

    # Classify run type by distance, and extract location
    df["Lauftyp"] = df.apply(classify_run, axis=1)
    df["Ort"] = df["Titel"].apply(extract_location)

    # Sort by date
    df = df.sort_values("Datum").reset_index(drop=True)

    return df


df = load_data()

# ---- Sidebar ----
st.sidebar.title("🔍 Filter")

selected_types = st.sidebar.multiselect(
    "Lauftyp",
    options=sorted(df["Lauftyp"].unique()),
    default=sorted(df["Lauftyp"].unique()),
)

date_range = st.sidebar.date_input(
    "Zeitraum",
    value=(df["Datum"].min().date(), df["Datum"].max().date()),
    min_value=df["Datum"].min().date(),
    max_value=df["Datum"].max().date(),
)

min_distance = st.sidebar.slider(
    "Mindestdistanz (km)",
    min_value=0.0,
    max_value=float(df["Distanz_km"].max()),
    value=0.0,
    step=1.0,
)

# Apply filters
if len(date_range) == 2:
    filtered = df[
        (df["Lauftyp"].isin(selected_types))
        & (df["Datum"].dt.date >= date_range[0])
        & (df["Datum"].dt.date <= date_range[1])
        & (df["Distanz_km"] >= min_distance)
    ]
else:
    filtered = df[
        (df["Lauftyp"].isin(selected_types))
        & (df["Distanz_km"] >= min_distance)
    ]

# ---- Header ----
st.title("🏃 Running Analytics")
st.markdown("Persönliche Trainingsanalyse auf Basis von Garmin-Daten — Weg zum Sub-4-Marathon.")

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
    # Weekly volume
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
    # Monthly volume
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
# Section 2: Pace-Entwicklung
# ============================================================
st.header("⏱️ Pace-Entwicklung")

col_left2, col_right2 = st.columns(2)

with col_left2:
    # Pace over time by run type
    pace_data = filtered.dropna(subset=["Pace_sec"]).copy()

    fig_pace = px.scatter(
        pace_data,
        x="Datum",
        y="Pace_sec",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        size="Distanz_km",
        hover_data={
            "Pace_sec": False,
            "Distanz_km": ":.1f",
            "Avg_HR": ":.0f",
            "Titel": True,
        },
        title="Pace über Zeit (kleiner = schneller)",
    )

    # Add sub-4 marathon pace line (5:41/km)
    fig_pace.add_hline(
        y=341, line_dash="dash", line_color="red", opacity=0.7,
        annotation_text="Sub-4 Pace (5:41/km)",
        annotation_position="top left",
    )

    # Format y-axis as M:SS
    pace_ticks = [300, 320, 340, 360, 380, 400]
    fig_pace.update_layout(
        yaxis=dict(
            autorange="reversed",
            tickvals=pace_ticks,
            ticktext=[pace_seconds_to_str(p) for p in pace_ticks],
        ),
        yaxis_title="Pace (min/km)",
        xaxis_title="",
        height=450,
    )
    st.plotly_chart(fig_pace, use_container_width=True)

with col_right2:
    # Pace by run type (box plot)
    fig_pace_box = px.box(
        pace_data,
        x="Lauftyp",
        y="Pace_sec",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        title="Pace-Verteilung nach Lauftyp",
    )
    pace_ticks2 = [280, 300, 320, 340, 360, 380, 400, 420]
    fig_pace_box.update_layout(
        yaxis=dict(
            autorange="reversed",
            tickvals=pace_ticks2,
            ticktext=[pace_seconds_to_str(p) for p in pace_ticks2],
        ),
        yaxis_title="Pace (min/km)",
        xaxis_title="",
        showlegend=False,
        height=450,
    )
    st.plotly_chart(fig_pace_box, use_container_width=True)

st.markdown("---")

# ============================================================
# Section 3: Herzfrequenz-Analyse
# ============================================================
st.header("❤️ Herzfrequenz-Analyse")

col_left3, col_right3 = st.columns(2)

with col_left3:
    # HR over time
    hr_data = filtered.dropna(subset=["Avg_HR"]).copy()

    fig_hr = px.scatter(
        hr_data,
        x="Datum",
        y="Avg_HR",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        size="Distanz_km",
        trendline="ols",
        title="Ø Herzfrequenz über Zeit",
    )
    fig_hr.update_layout(
        yaxis_title="Herzfrequenz (bpm)",
        xaxis_title="",
        height=450,
    )
    st.plotly_chart(fig_hr, use_container_width=True)

with col_right3:
    # HR vs Pace (fitness indicator)
    hr_pace = filtered.dropna(subset=["Avg_HR", "Pace_sec"]).copy()

    fig_hr_pace = px.scatter(
        hr_pace,
        x="Avg_HR",
        y="Pace_sec",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        size="Distanz_km",
        trendline="ols",
        title="Herzfrequenz vs. Pace (Effizienz)",
        hover_data={"Datum": True, "Distanz_km": ":.1f"},
    )

    pace_ticks3 = [300, 320, 340, 360, 380, 400]
    fig_hr_pace.update_layout(
        yaxis=dict(
            autorange="reversed",
            tickvals=pace_ticks3,
            ticktext=[pace_seconds_to_str(p) for p in pace_ticks3],
        ),
        xaxis_title="Ø Herzfrequenz (bpm)",
        yaxis_title="Pace (min/km)",
        height=450,
    )
    st.plotly_chart(fig_hr_pace, use_container_width=True)

# Cardiac drift: for long runs, how does pace hold up?
st.markdown("---")

# ============================================================
# Section 4: Lauftyp-Analyse
# ============================================================
st.header("🏋️ Trainingsstruktur")

col_left4, col_right4 = st.columns(2)

with col_left4:
    # Distribution of run types (km)
    type_km = (
        filtered.groupby("Lauftyp")["Distanz_km"]
        .sum()
        .reset_index()
        .sort_values("Distanz_km", ascending=False)
    )

    fig_type_km = px.pie(
        type_km,
        values="Distanz_km",
        names="Lauftyp",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        title="Kilometer-Verteilung nach Lauftyp",
        hole=0.4,
    )
    fig_type_km.update_layout(height=400)
    st.plotly_chart(fig_type_km, use_container_width=True)

with col_right4:
    # Stats table by run type
    type_stats = (
        filtered.groupby("Lauftyp")
        .agg(
            Läufe=("Distanz_km", "count"),
            Gesamt_km=("Distanz_km", "sum"),
            Avg_km=("Distanz_km", "mean"),
            Avg_Pace=("Pace_sec", "mean"),
            Avg_HR=("Avg_HR", "mean"),
        )
        .reset_index()
    )
    type_stats["Avg_Pace"] = type_stats["Avg_Pace"].apply(pace_seconds_to_str)
    type_stats["Avg_HR"] = type_stats["Avg_HR"].apply(
        lambda x: f"{x:.0f}" if pd.notna(x) else "—"
    )
    type_stats["Gesamt_km"] = type_stats["Gesamt_km"].apply(lambda x: f"{x:.1f}")
    type_stats["Avg_km"] = type_stats["Avg_km"].apply(lambda x: f"{x:.1f}")

    type_stats.columns = [
        "Lauftyp", "Läufe", "Gesamt (km)", "Ø Distanz (km)",
        "Ø Pace", "Ø HR",
    ]

    st.markdown("#### Statistik nach Lauftyp")
    st.dataframe(type_stats, use_container_width=True, hide_index=True)

    # Location breakdown
    st.markdown("#### Lauforte")
    loc_stats = (
        filtered.groupby("Ort")
        .agg(Läufe=("Distanz_km", "count"), km=("Distanz_km", "sum"))
        .reset_index()
        .sort_values("km", ascending=False)
    )
    loc_stats["km"] = loc_stats["km"].apply(lambda x: f"{x:.1f}")
    st.dataframe(loc_stats, use_container_width=True, hide_index=True)

st.markdown("---")

# ============================================================
# Section 5: Laufeffizienz
# ============================================================
st.header("⚙️ Laufeffizienz & Biomechanik")

col_left5, col_right5 = st.columns(2)

with col_left5:
    # Cadence over time
    cad_data = filtered.dropna(subset=["Cadence"]).copy()
    fig_cad = px.scatter(
        cad_data,
        x="Datum",
        y="Cadence",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        trendline="ols",
        title="Schrittfrequenz über Zeit",
    )
    fig_cad.update_layout(
        yaxis_title="Schritte/min",
        xaxis_title="",
        height=400,
    )
    st.plotly_chart(fig_cad, use_container_width=True)

with col_right5:
    # Ground contact time over time
    gct_data = filtered.dropna(subset=["Ground_Contact"]).copy()
    fig_gct = px.scatter(
        gct_data,
        x="Datum",
        y="Ground_Contact",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        trendline="ols",
        title="Bodenkontaktzeit über Zeit (kürzer = effizienter)",
    )
    fig_gct.update_layout(
        yaxis_title="Bodenkontaktzeit (ms)",
        xaxis_title="",
        height=400,
    )
    st.plotly_chart(fig_gct, use_container_width=True)

# Power vs Pace
col_left6, col_right6 = st.columns(2)

with col_left6:
    power_data = filtered.dropna(subset=["Avg_Power", "Pace_sec"]).copy()
    fig_power = px.scatter(
        power_data,
        x="Avg_Power",
        y="Pace_sec",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        trendline="ols",
        title="Leistung (Watt) vs. Pace",
    )
    pace_ticks4 = [300, 320, 340, 360, 380, 400]
    fig_power.update_layout(
        yaxis=dict(
            autorange="reversed",
            tickvals=pace_ticks4,
            ticktext=[pace_seconds_to_str(p) for p in pace_ticks4],
        ),
        xaxis_title="Ø Leistung (Watt)",
        yaxis_title="Pace (min/km)",
        height=400,
    )
    st.plotly_chart(fig_power, use_container_width=True)

with col_right6:
    # Stride length vs pace
    stride_data = filtered.dropna(subset=["Stride_Length", "Pace_sec"]).copy()
    fig_stride = px.scatter(
        stride_data,
        x="Stride_Length",
        y="Pace_sec",
        color="Lauftyp",
        color_discrete_map=RUN_TYPE_COLORS,
        title="Schrittlänge vs. Pace",
    )
    fig_stride.update_layout(
        yaxis=dict(
            autorange="reversed",
            tickvals=pace_ticks4,
            ticktext=[pace_seconds_to_str(p) for p in pace_ticks4],
        ),
        xaxis_title="Ø Schrittlänge (m)",
        yaxis_title="Pace (min/km)",
        height=400,
    )
    st.plotly_chart(fig_stride, use_container_width=True)

st.markdown("---")

# ============================================================
# Section 6: Marathon-Analyse
# ============================================================
st.header("🏅 Marathon-Analyse")

if len(marathon) > 0:
    m = marathon.iloc[0]

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Finish-Zeit", str(m["Zeit"])[:7])
    with col_m2:
        st.metric("Distanz", f"{m['Distanz_km']:.2f} km")
    with col_m3:
        st.metric("Ø Pace", str(m["Ø Pace"]))
    with col_m4:
        gap_sec = parse_pace(str(m["Ø Pace"])) - 341  # 5:41 = sub4
        st.metric(
            "Gap zu Sub-4",
            f"+{gap_sec} sec/km" if gap_sec > 0 else f"{gap_sec} sec/km",
        )

    st.markdown("")

    # Compare long runs leading up to marathon
    long_runs = filtered[filtered["Distanz_km"] >= 15].sort_values("Datum")

    if len(long_runs) > 1:
        fig_long = go.Figure()

        fig_long.add_trace(
            go.Scatter(
                x=long_runs["Datum"],
                y=long_runs["Pace_sec"],
                mode="lines+markers+text",
                text=long_runs["Distanz_km"].apply(lambda x: f"{x:.0f}km"),
                textposition="top center",
                marker=dict(
                    size=long_runs["Distanz_km"] * 0.6,
                    color="#A23B72",
                ),
                line=dict(color="#A23B72", width=2),
                name="Lange Läufe",
            )
        )

        fig_long.add_hline(
            y=341, line_dash="dash", line_color="red", opacity=0.7,
            annotation_text="Sub-4 Pace (5:41/km)",
        )

        pace_ticks5 = [340, 350, 360, 370, 380, 390]
        fig_long.update_layout(
            title="Lange Läufe (>15 km) — Pace-Entwicklung bis zum Marathon",
            yaxis=dict(
                autorange="reversed",
                tickvals=pace_ticks5,
                ticktext=[pace_seconds_to_str(p) for p in pace_ticks5],
            ),
            yaxis_title="Pace (min/km)",
            xaxis_title="",
            height=400,
        )
        st.plotly_chart(fig_long, use_container_width=True)
else:
    st.info("Kein Marathon in den Daten gefunden.")

st.markdown("---")

# ============================================================
# Section 7: Rohdaten
# ============================================================
with st.expander("📋 Alle Aktivitäten anzeigen"):
    display_cols = [
        "Datum", "Titel", "Lauftyp", "Distanz_km", "Zeit",
        "Avg_HR", "Max_HR", "Cadence", "Aerober_TE", "Anstieg",
    ]
    display_df = filtered[display_cols].copy()
    display_df["Datum"] = display_df["Datum"].dt.strftime("%d.%m.%Y")
    display_df.columns = [
        "Datum", "Titel", "Typ", "km", "Zeit",
        "Ø HR", "Max HR", "Kadenz", "Aer. TE", "Anstieg (m)",
    ]
    st.dataframe(
        display_df.sort_index(ascending=False),
        use_container_width=True,
        height=500,
    )

# ---- Footer ----
st.markdown("---")
st.caption(
    "Datenquelle: Garmin Connect Export · "
    "Dashboard erstellt mit Streamlit & Plotly"
)