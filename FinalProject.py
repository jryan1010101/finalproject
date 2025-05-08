"""
Name: Jack Ryan
CS230: Section 001
Data: Forbes Global 2000 — Top2000_Companies_Globally_Fixed.csv
URL: <add‑your‑Streamlit‑Cloud‑link‑here>

Description:
Interactive Streamlit dashboard that lets users explore the Forbes Global 2000 data.
Filters: continent, country, and minimum market value. Visuals: bar chart (top 10
market caps), bubble chart (sales vs. profits, bubble=assets), box plot of
market‑value distributions, and an interactive PyDeck map of company HQs. The
app also provides a pivot table (average market value per continent) and a
sortable data table of the filtered results. All required widgets, charts, data
analytics tasks, and Python features are included per the CS230 final‑project
rubric.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pydeck as pdk
from typing import Tuple


# [ST4] Page‑level config + simple colour tweaks

st.set_page_config(
    page_title="Top 2000 Global Companies",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Quick CSS: dark sidebar & blue headings
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {background-color: #1f2833;}
        h1, h2, h3 {color: #45b6fe;}
        div[data-testid="stMetric"] label {color: #c5c6c7;}
    </style>
    """,
    unsafe_allow_html=True,
)

sns.set_style("darkgrid")
BAR_PALETTE = sns.color_palette("mako", 10)


# Data loading and cleaning


@st.cache_data(show_spinner=False)
# [PY1] multi‑param func used twice
# [PY2] returns two dfs
# [PY3] try/except
# [DA1] clean data
def load_data(csv_path: str = "Top2000_Companies_Globally_Fixed.csv",
              drop_na_geo: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
    try:
        raw_df = pd.read_csv(csv_path)
    except FileNotFoundError:
        st.error("CSV not found – check the path.")
        st.stop()

    tidy_df = raw_df.rename(columns={
        "Sales ($billion)": "Sales",
        "Profits ($billion)": "Profits",
        "Assets ($billion)": "Assets",
        "Market Value ($billion)": "MarketValue",
    }).copy()

    # [PY4] list comp -> numeric coercion
    num_cols = [c for c in ["Sales", "Profits", "Assets", "MarketValue",
                            "Latitude_final", "Longitude_final"]]
    tidy_df[num_cols] = tidy_df[num_cols].apply(pd.to_numeric, errors="coerce")

    if drop_na_geo:
        tidy_df = tidy_df.dropna(subset=["Latitude_final", "Longitude_final"])

    return raw_df, tidy_df

# two calls for PY1
_, df = load_data()
raw_df, _ = load_data(drop_na_geo=False)


# Filtering helper


@st.cache_data(show_spinner=False)
# [PY2] returns two values
# [DA4] one condition | [DA5] two conditions
def filter_data(data: pd.DataFrame, *, continent: str = "All", country: str = "All") -> Tuple[pd.DataFrame, pd.DataFrame]:
    continent_df = data if continent == "All" else data[data["Continent"] == continent]
    country_df = continent_df if country == "All" else continent_df[continent_df["Country"] == country]
    return continent_df, country_df

# [PY5] dict‑comp KPI
continent_counts = {c: int(raw_df[raw_df["Continent"] == c].shape[0])
                    for c in raw_df["Continent"].dropna().unique()}

# Sidebar UI


st.sidebar.header("Filters")

continents = ["All"] + sorted(df["Continent"].dropna().unique())
continent_choice = st.sidebar.selectbox("Continent", continents)  # [ST1]

continent_df, _ = filter_data(df, continent=continent_choice)

countries = ["All"] + sorted(continent_df["Country"].dropna().unique())
country_choice = st.sidebar.selectbox("Country", countries)       # [ST2]

min_mv = st.sidebar.slider("Min Market Value (B USD)",            # [ST3]
                           0.0, float(df["MarketValue"].max()), 0.0, 10.0)

# use keyword args so *‑only params are respected
continent_df, country_df = filter_data(df, continent=continent_choice, country=country_choice)
country_df = country_df[country_df["MarketValue"] >= min_mv]       # [DA2]



st.title("Top 2000 Global Companies Dashboard")

# KPI row
cols = st.columns(len(continent_counts))
for i, (cont, cnt) in enumerate(continent_counts.items()):
    cols[i].metric(cont, cnt)

# [VIZ1] Bar – Top 10 by Market Value
if not continent_df.empty:
    st.subheader("Top 10 by Market Value")
    top10 = continent_df.nlargest(10, "MarketValue").sort_values("MarketValue")  # [DA3]
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    sns.barplot(data=top10, x="MarketValue", y="Company", palette=BAR_PALETTE, ax=ax1)
    ax1.set_xlabel("Market Value (B USD)")
    st.pyplot(fig1)

# [VIZ2] Scatter – Sales vs Profits
if not country_df.empty:
    st.subheader("Sales vs Profits (bubble = Assets, color = Market Value)")
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    size = (country_df["Assets"] / country_df["Assets"].max()) * 2000
    scatter = ax2.scatter(
        country_df["Sales"], country_df["Profits"],
        s=size, c=country_df["MarketValue"], cmap="plasma", alpha=0.7, edgecolors="w"
    )
    ax2.set_xlabel("Sales (B USD)")
    ax2.set_ylabel("Profits (B USD)")
    fig2.colorbar(scatter).set_label("Market Value (B USD)")
    st.pyplot(fig2)

# [VIZ3] Box – Market Value by Continent
st.subheader("Market Value by Continent")
fig3, ax3 = plt.subplots(figsize=(8, 5))
sns.boxplot(data=df, x="Continent", y="MarketValue", palette="Set2", ax=ax3)
ax3.set_ylabel("Market Value (B USD)")
plt.xticks(rotation=45)
st.pyplot(fig3)

# [MAP] HQ map
if not continent_df.empty:
    st.subheader("Company Headquarters Map")
    mid = {"lat": continent_df["Latitude_final"].mean(),
           "lon": continent_df["Longitude_final"].mean()}
    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/dark-v10",
            initial_view_state=pdk.ViewState(latitude=mid["lat"], longitude=mid["lon"], zoom=2, pitch=45),
            layers=[pdk.Layer(
                "ScatterplotLayer",
                data=continent_df,
                get_position="[Longitude_final, Latitude_final]",
                get_fill_color="[180,45,129,160]",
                get_radius=70000,
                pickable=True,
            )],
            tooltip={"html": "<b>{Company}</b><br>{Country}<br>Market: ${MarketValue} B"},
        )
    )

# [DA6] Pivot table – average market value per continent
st.subheader("Average Market Value per Continent")
pivot_df = df.pivot_table(index="Continent", values="MarketValue", aggfunc="mean")
st.dataframe(pivot_df.style.format("{:.2f}"))

# Full table of filtered results
st.subheader("Companies Matching Current Filters")
st.dataframe(
    country_df[["Global Rank", "Company", "Country", "Sales", "Profits", "Assets", "MarketValue"]]
    .sort_values("MarketValue", ascending=False)
    .reset_index(drop=True)
)
