"""
Sports Nutrition & Bio-Metrics Dashboard
=========================================
Analyzes the impact of Creatine and Mass Gainers on
body weight and strength gains across different demographics.

Data: Kaggle - Sports Nutrition & Bio-Metrics | Supplement Cycles
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---- Page Config ----
st.set_page_config(
    page_title="Supplement Impact Analysis",
    page_icon="💪",
    layout="wide",
)

# ---- Custom Styling ----
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    [data-testid="stMetricDelta"] { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ---- Color Palette ----
COLORS = {
    "Creatine Monohydrate": "#636EFA",
    "Mass Gainer": "#EF553B",
    "Both": "#00CC96",
}
GENDER_COLORS = {
    "Male": "#636EFA",
    "Female": "#EF553B",
    "Non-Binary": "#00CC96",
}


@st.cache_data
def load_data():
    """Load and prepare the supplement dataset."""
    df = pd.read_csv("data/supplement_impact_data.csv")

    # Parse Strength_Gain from "8%" to 8.0
    df["Strength_Gain_Pct"] = (
        df["Strength_Gain"].str.replace("%", "").astype(float)
    )

    # Calculate weight change
    df["Weight_Change_kg"] = (df["Final_WT"] - df["Initial_WT"]).round(2)
    df["Weight_Change_Pct"] = (
        (df["Weight_Change_kg"] / df["Initial_WT"]) * 100
    ).round(2)

    # Age groups
    bins = [17, 25, 35, 45, 55, 66]
    labels = ["18-25", "26-35", "36-45", "46-55", "56-65"]
    df["Age_Group"] = pd.cut(df["Age"], bins=bins, labels=labels)

    # Duration groups
    df["Duration_Group"] = pd.cut(
        df["Weeks"],
        bins=[3, 8, 12, 16, 25],
        labels=["4-8 Wo.", "9-12 Wo.", "13-16 Wo.", "17-24 Wo."],
    )

    return df


df = load_data()

# ---- Sidebar Filters ----
st.sidebar.title("🔍 Filter")

selected_supplements = st.sidebar.multiselect(
    "Supplement",
    options=df["Supplement"].unique(),
    default=df["Supplement"].unique(),
)

selected_genders = st.sidebar.multiselect(
    "Geschlecht",
    options=df["Gender"].unique(),
    default=df["Gender"].unique(),
)

age_range = st.sidebar.slider(
    "Alter",
    min_value=int(df["Age"].min()),
    max_value=int(df["Age"].max()),
    value=(int(df["Age"].min()), int(df["Age"].max())),
)

weeks_range = st.sidebar.slider(
    "Einnahmedauer (Wochen)",
    min_value=int(df["Weeks"].min()),
    max_value=int(df["Weeks"].max()),
    value=(int(df["Weeks"].min()), int(df["Weeks"].max())),
)

# Apply filters
filtered = df[
    (df["Supplement"].isin(selected_supplements))
    & (df["Gender"].isin(selected_genders))
    & (df["Age"].between(age_range[0], age_range[1]))
    & (df["Weeks"].between(weeks_range[0], weeks_range[1]))
]

# ---- Header ----
st.title("💪 Supplement Impact Analysis")
st.markdown(
    f"Analyse von **{len(filtered):,}** Teilnehmern "
    f"(von {len(df):,} gesamt) — Wirkung von Kreatin & Mass Gainern "
    f"auf Körpergewicht und Kraftzuwachs."
)

if len(filtered) == 0:
    st.warning("Keine Daten für diese Filterauswahl. Bitte Filter anpassen.")
    st.stop()

# ---- KPI Row ----
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Ø Kraftzuwachs",
        f"{filtered['Strength_Gain_Pct'].mean():.1f}%",
    )
with col2:
    st.metric(
        "Ø Gewichtsveränderung",
        f"{filtered['Weight_Change_kg'].mean():.1f} kg",
    )
with col3:
    st.metric(
        "Ø Einnahmedauer",
        f"{filtered['Weeks'].mean():.0f} Wochen",
    )
with col4:
    st.metric(
        "Ø Alter",
        f"{filtered['Age'].mean():.0f} Jahre",
    )

st.markdown("---")

# ============================================================
# Section 1: Supplement-Vergleich
# ============================================================
st.header("📊 Welches Supplement bringt am meisten?")

col_left, col_right = st.columns(2)

with col_left:
    # Strength Gain by Supplement
    strength_by_supp = (
        filtered.groupby("Supplement")["Strength_Gain_Pct"]
        .agg(["mean", "median", "std", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )

    fig_strength = px.bar(
        strength_by_supp,
        x="Supplement",
        y="mean",
        color="Supplement",
        color_discrete_map=COLORS,
        text=strength_by_supp["mean"].apply(lambda x: f"{x:.1f}%"),
        title="Durchschnittlicher Kraftzuwachs",
    )
    fig_strength.update_traces(textposition="outside")
    fig_strength.update_layout(
        yaxis_title="Kraftzuwachs (%)",
        xaxis_title="",
        showlegend=False,
        height=400,
    )
    st.plotly_chart(fig_strength, use_container_width=True)

with col_right:
    # Weight Change by Supplement
    weight_by_supp = (
        filtered.groupby("Supplement")["Weight_Change_kg"]
        .agg(["mean", "median", "std", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )

    fig_weight = px.bar(
        weight_by_supp,
        x="Supplement",
        y="mean",
        color="Supplement",
        color_discrete_map=COLORS,
        text=weight_by_supp["mean"].apply(lambda x: f"{x:.1f} kg"),
        title="Durchschnittliche Gewichtsveränderung",
    )
    fig_weight.update_traces(textposition="outside")
    fig_weight.update_layout(
        yaxis_title="Gewichtsveränderung (kg)",
        xaxis_title="",
        showlegend=False,
        height=400,
    )
    st.plotly_chart(fig_weight, use_container_width=True)

# Distribution violin plot
fig_violin = px.violin(
    filtered,
    x="Supplement",
    y="Strength_Gain_Pct",
    color="Supplement",
    color_discrete_map=COLORS,
    box=True,
    points="outliers",
    title="Verteilung des Kraftzuwachses pro Supplement",
)
fig_violin.update_layout(
    yaxis_title="Kraftzuwachs (%)",
    xaxis_title="",
    showlegend=False,
    height=400,
)
st.plotly_chart(fig_violin, use_container_width=True)

st.markdown("---")

# ============================================================
# Section 2: Einnahmedauer vs. Wirkung
# ============================================================
st.header("⏱️ Wie hängt die Einnahmedauer mit der Wirkung zusammen?")

col_left2, col_right2 = st.columns(2)

with col_left2:
    # Scatter: Weeks vs Strength Gain
    fig_scatter = px.scatter(
        filtered,
        x="Weeks",
        y="Strength_Gain_Pct",
        color="Supplement",
        color_discrete_map=COLORS,
        opacity=0.5,
        trendline="ols",
        title="Einnahmedauer vs. Kraftzuwachs",
    )
    fig_scatter.update_layout(
        xaxis_title="Wochen",
        yaxis_title="Kraftzuwachs (%)",
        height=450,
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_right2:
    # Scatter: Weeks vs Weight Change
    fig_scatter2 = px.scatter(
        filtered,
        x="Weeks",
        y="Weight_Change_kg",
        color="Supplement",
        color_discrete_map=COLORS,
        opacity=0.5,
        trendline="ols",
        title="Einnahmedauer vs. Gewichtsveränderung",
    )
    fig_scatter2.update_layout(
        xaxis_title="Wochen",
        yaxis_title="Gewichtsveränderung (kg)",
        height=450,
    )
    st.plotly_chart(fig_scatter2, use_container_width=True)

# Grouped bar by duration
duration_stats = (
    filtered.groupby(["Duration_Group", "Supplement"])
    .agg(
        avg_strength=("Strength_Gain_Pct", "mean"),
        avg_weight=("Weight_Change_kg", "mean"),
        count=("ID", "count"),
    )
    .reset_index()
)

fig_duration = px.bar(
    duration_stats,
    x="Duration_Group",
    y="avg_strength",
    color="Supplement",
    color_discrete_map=COLORS,
    barmode="group",
    text=duration_stats["avg_strength"].apply(lambda x: f"{x:.1f}%"),
    title="Kraftzuwachs nach Einnahmedauer und Supplement",
)
fig_duration.update_traces(textposition="outside")
fig_duration.update_layout(
    xaxis_title="Einnahmedauer",
    yaxis_title="Ø Kraftzuwachs (%)",
    height=400,
)
st.plotly_chart(fig_duration, use_container_width=True)

st.markdown("---")

# ============================================================
# Section 3: Altersunterschiede
# ============================================================
st.header("🎂 Gibt es Altersunterschiede in der Wirkung?")

col_left3, col_right3 = st.columns(2)

with col_left3:
    age_stats = (
        filtered.groupby(["Age_Group", "Supplement"])
        .agg(
            avg_strength=("Strength_Gain_Pct", "mean"),
            count=("ID", "count"),
        )
        .reset_index()
    )

    fig_age = px.bar(
        age_stats,
        x="Age_Group",
        y="avg_strength",
        color="Supplement",
        color_discrete_map=COLORS,
        barmode="group",
        title="Kraftzuwachs nach Altersgruppe",
    )
    fig_age.update_layout(
        xaxis_title="Altersgruppe",
        yaxis_title="Ø Kraftzuwachs (%)",
        height=450,
    )
    st.plotly_chart(fig_age, use_container_width=True)

with col_right3:
    age_weight = (
        filtered.groupby(["Age_Group", "Supplement"])
        .agg(avg_weight=("Weight_Change_kg", "mean"))
        .reset_index()
    )

    fig_age_wt = px.bar(
        age_weight,
        x="Age_Group",
        y="avg_weight",
        color="Supplement",
        color_discrete_map=COLORS,
        barmode="group",
        title="Gewichtsveränderung nach Altersgruppe",
    )
    fig_age_wt.update_layout(
        xaxis_title="Altersgruppe",
        yaxis_title="Ø Gewichtsveränderung (kg)",
        height=450,
    )
    st.plotly_chart(fig_age_wt, use_container_width=True)

# Heatmap: Age Group x Supplement → Strength
heatmap_data = (
    filtered.groupby(["Age_Group", "Supplement"])["Strength_Gain_Pct"]
    .mean()
    .unstack(fill_value=0)
)

fig_heat = px.imshow(
    heatmap_data.values,
    x=heatmap_data.columns.tolist(),
    y=heatmap_data.index.tolist(),
    color_continuous_scale="YlOrRd",
    text_auto=".1f",
    title="Heatmap: Ø Kraftzuwachs (%) nach Alter und Supplement",
    labels=dict(x="Supplement", y="Altersgruppe", color="Kraftzuwachs (%)"),
)
fig_heat.update_layout(height=350)
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("---")

# ============================================================
# Section 4: Gender-Analyse
# ============================================================
st.header("👥 Unterschiede nach Geschlecht")

col_left4, col_right4 = st.columns(2)

with col_left4:
    gender_stats = (
        filtered.groupby(["Gender", "Supplement"])
        .agg(
            avg_strength=("Strength_Gain_Pct", "mean"),
            avg_weight=("Weight_Change_kg", "mean"),
        )
        .reset_index()
    )

    fig_gender = px.bar(
        gender_stats,
        x="Gender",
        y="avg_strength",
        color="Supplement",
        color_discrete_map=COLORS,
        barmode="group",
        title="Kraftzuwachs nach Geschlecht",
    )
    fig_gender.update_layout(
        xaxis_title="",
        yaxis_title="Ø Kraftzuwachs (%)",
        height=400,
    )
    st.plotly_chart(fig_gender, use_container_width=True)

with col_right4:
    fig_gender_wt = px.bar(
        gender_stats,
        x="Gender",
        y="avg_weight",
        color="Supplement",
        color_discrete_map=COLORS,
        barmode="group",
        title="Gewichtsveränderung nach Geschlecht",
    )
    fig_gender_wt.update_layout(
        xaxis_title="",
        yaxis_title="Ø Gewichtsveränderung (kg)",
        height=400,
    )
    st.plotly_chart(fig_gender_wt, use_container_width=True)

st.markdown("---")

# ============================================================
# Section 5: Primary Benefit Breakdown
# ============================================================
st.header("🎯 Welchen Hauptnutzen berichten die Teilnehmer?")

col_left5, col_right5 = st.columns(2)

with col_left5:
    benefit_counts = (
        filtered.groupby(["Primary_Benefit", "Supplement"])
        .size()
        .reset_index(name="count")
    )

    fig_benefit = px.bar(
        benefit_counts,
        x="Primary_Benefit",
        y="count",
        color="Supplement",
        color_discrete_map=COLORS,
        barmode="stack",
        title="Gemeldeter Hauptnutzen nach Supplement",
    )
    fig_benefit.update_layout(
        xaxis_title="",
        yaxis_title="Anzahl Teilnehmer",
        height=400,
    )
    st.plotly_chart(fig_benefit, use_container_width=True)

with col_right5:
    # Sunburst: Supplement → Benefit
    fig_sun = px.sunburst(
        filtered,
        path=["Supplement", "Primary_Benefit"],
        color="Supplement",
        color_discrete_map=COLORS,
        title="Supplement → Hauptnutzen (Anteil)",
    )
    fig_sun.update_layout(height=400)
    st.plotly_chart(fig_sun, use_container_width=True)

# Benefit vs actual results
benefit_results = (
    filtered.groupby("Primary_Benefit")
    .agg(
        avg_strength=("Strength_Gain_Pct", "mean"),
        avg_weight_change=("Weight_Change_kg", "mean"),
        count=("ID", "count"),
    )
    .reset_index()
    .sort_values("avg_strength", ascending=False)
)

fig_benefit_result = make_subplots(
    rows=1, cols=2,
    subplot_titles=(
        "Ø Kraftzuwachs nach Hauptnutzen",
        "Ø Gewichtsveränderung nach Hauptnutzen",
    ),
)

fig_benefit_result.add_trace(
    go.Bar(
        x=benefit_results["Primary_Benefit"],
        y=benefit_results["avg_strength"],
        marker_color="#636EFA",
        text=benefit_results["avg_strength"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
    ),
    row=1, col=1,
)

fig_benefit_result.add_trace(
    go.Bar(
        x=benefit_results["Primary_Benefit"],
        y=benefit_results["avg_weight_change"],
        marker_color="#EF553B",
        text=benefit_results["avg_weight_change"].apply(lambda x: f"{x:.1f} kg"),
        textposition="outside",
    ),
    row=1, col=2,
)

fig_benefit_result.update_layout(height=400, showlegend=False)
st.plotly_chart(fig_benefit_result, use_container_width=True)

st.markdown("---")

# ============================================================
# Section 6: Rohdaten
# ============================================================
with st.expander("📋 Gefilterte Rohdaten anzeigen"):
    display_cols = [
        "ID", "Age", "Gender", "Supplement", "Weeks",
        "Initial_WT", "Final_WT", "Weight_Change_kg",
        "Strength_Gain_Pct", "Primary_Benefit",
    ]
    st.dataframe(
        filtered[display_cols].sort_values("Strength_Gain_Pct", ascending=False),
        use_container_width=True,
        height=400,
    )

# ---- Footer ----
st.markdown("---")
st.caption(
    "Datenquelle: Kaggle — Sports Nutrition & Bio-Metrics | Supplement Cycles · "
    "Dashboard erstellt mit Streamlit & Plotly"
)
