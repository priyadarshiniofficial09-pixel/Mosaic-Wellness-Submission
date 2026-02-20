import streamlit as st
import pandas as pd
from datetime import datetime
import warnings

import plotly.graph_objects as go
import plotly.express as px
warnings.filterwarnings('ignore')

# Page Configuration
st.set_page_config(page_title="Competitor Ad Intelligence", layout="wide", initial_sidebar_state="expanded")

# Load Data
@st.cache_data
def load_data():
    df = pd.read_csv('meta_ad_library_dataset.csv')
    return df

df = load_data()

# Data Preprocessing
def preprocess_data(df):
    df['ad_creation_time'] = pd.to_datetime(df['ad_creation_time'])
    df['ad_date'] = df['ad_creation_time'].dt.date
    df['week'] = df['ad_creation_time'].dt.isocalendar().week
    df['month'] = df['ad_creation_time'].dt.month
    df['year'] = df['ad_creation_time'].dt.year
    df['year_month'] = df['ad_creation_time'].dt.to_period('M').astype(str)
    df['spend_midpoint'] = (df['spend_lower_inr'] + df['spend_upper_inr']) / 2
    df['impressions_midpoint'] = (df['impressions_lower'] + df['impressions_upper']) / 2
    
    # Keyword flags
    keywords = ['discount', 'offer', 'clinical', 'free', 'limited', 'sale']
    df['keywords_found'] = df['ad_creative_body'].str.lower().apply(
        lambda x: [kw for kw in keywords if kw in str(x).lower()]
    )
    
    # New ad flag (last 7 days)
    max_date = df['ad_creation_time'].max()
    df['is_new_ad'] = (max_date - df['ad_creation_time']).dt.days <= 7
    
    return df

def format_inr(value):
    if value >= 1_000_000:
        return f"₹{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"₹{value/1_000:.0f}K"
    else:
        return f"₹{value:.0f}"

df = preprocess_data(df)

# Sidebar Filters
st.sidebar.title("🎛 Filters")
st.sidebar.markdown("---")

# Primary Filters
brand_filter = st.sidebar.multiselect(
    "Brand Category",
    options=df['brand_category'].unique(),
    default=df['brand_category'].unique()
)

competitor_filter = st.sidebar.multiselect(
    "Competitor Page",
    options=df['competitor_page'].unique(),
    default=df['competitor_page'].unique()[:10]
)

month_filter = st.sidebar.multiselect(
    "Select Months",
    options=sorted(df['year_month'].unique()),
    default=sorted(df['year_month'].unique())
)

platform_filter = st.sidebar.multiselect(
    "Platform",
    options=df['publisher_platform'].unique(),
    default=df['publisher_platform'].unique()
)

region_filter = st.sidebar.multiselect(
    "Region",
    options=df['region_distribution'].unique(),
    default=df['region_distribution'].unique()[:10]
)

age_filter = st.sidebar.multiselect(
    "Age Group",
    options=df['target_age_group'].unique(),
    default=df['target_age_group'].unique()
)

active_filter = st.sidebar.multiselect(
    "Active Status",
    options=[True, False],
    default=[True, False]
)

# Advanced Filters
st.sidebar.markdown("---")
st.sidebar.subheader("Advanced Filters")

spend_range = st.sidebar.slider(
    "Spend Range (INR)",
    min_value=float(df['spend_midpoint'].min()),
    max_value=float(df['spend_midpoint'].max()),
    value=(float(df['spend_midpoint'].min()), float(df['spend_midpoint'].max()))
)

impressions_range = st.sidebar.slider(
    "Impressions Range",
    min_value=float(df['impressions_midpoint'].min()),
    max_value=float(df['impressions_midpoint'].max()),
    value=(float(df['impressions_midpoint'].min()), float(df['impressions_midpoint'].max()))
)

cta_filter = st.sidebar.multiselect(
    "CTA Type",
    options=df['cta_type'].unique(),
    default=df['cta_type'].unique()
)

keyword_search = st.sidebar.text_input("Search Keywords in Ad Text")

# Apply Filters
filtered_df = df[
    (df['brand_category'].isin(brand_filter)) &
    (df['competitor_page'].isin(competitor_filter)) &
    (df['year_month'].isin(month_filter)) &
    (df['publisher_platform'].isin(platform_filter)) &
    (df['region_distribution'].isin(region_filter)) &
    (df['target_age_group'].isin(age_filter)) &
    (df['is_active'].isin(active_filter)) &
    (df['spend_midpoint'] >= spend_range[0]) &
    (df['spend_midpoint'] <= spend_range[1]) &
    (df['impressions_midpoint'] >= impressions_range[0]) &
    (df['impressions_midpoint'] <= impressions_range[1]) &
    (df['cta_type'].isin(cta_filter))
]

if filtered_df.empty:
    st.warning("No data available for selected filters. Please adjust filters.")
    st.stop()
    
if keyword_search:
    filtered_df = filtered_df[filtered_df['ad_creative_body'].str.contains(keyword_search, case=False, na=False)]

# Dashboard Title
st.title("📊 Competitor Ad Intelligence Dashboard")
st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==== 1. EXECUTIVE MARKET OVERVIEW ====
st.markdown("---")
st.header("1. 📈 Executive Market Overview")

# Row 1 → 3 KPIs
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Active Ads", filtered_df[filtered_df['is_active']].shape[0])

with col2:
    st.metric("Total Ads", filtered_df.shape[0])

with col3:
    st.metric("Total Spend (INR)", format_inr(filtered_df['spend_midpoint'].sum()))


# Row 2 → 3 KPIs
col4, col5, col6 = st.columns(3)

with col4:
    top_competitor = (
        filtered_df['competitor_page'].value_counts().index[0]
        if len(filtered_df) > 0 else "N/A"
    )
    st.metric("Most Active Competitor", top_competitor)

with col5:
    dominant_platform = (
        filtered_df['publisher_platform'].mode()[0]
        if len(filtered_df) > 0 else "N/A"
    )
    st.metric("Dominant Platform", dominant_platform)

with col6:
    top_region = (
        filtered_df['region_distribution'].mode()[0]
        if len(filtered_df) > 0 else "N/A"
    )
    st.metric("Most Targeted Region", top_region)
col1, col2 = st.columns(2)

with col1:
    # Ad Volume Over Time
    ad_volume = filtered_df.groupby('year_month').size().sort_index()

    fig_volume = px.line(
        x=ad_volume.index,
        y=ad_volume.values,
        title="Monthly Ad Volume",
        labels={'x': 'Month', 'y': 'Number of Ads'}
    )
    st.plotly_chart(fig_volume, use_container_width=True)

with col2:
    # Ads by Brand Category
    brand_counts = filtered_df['brand_category'].value_counts()
    fig_brand = px.bar(x=brand_counts.index, y=brand_counts.values, title="Ads by Brand Category", labels={'x': 'Brand Category', 'y': 'Count'})
    st.plotly_chart(fig_brand, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    # Platform Share
    platform_counts = filtered_df['publisher_platform'].value_counts()
    fig_platform = px.pie(values=platform_counts.values, names=platform_counts.index, title="Platform Share")
    st.plotly_chart(fig_platform, use_container_width=True)

with col2:
    # Top Competitors
    competitor_counts = filtered_df['competitor_page'].value_counts().head(10)
    fig_competitors = px.bar(x=competitor_counts.values, y=competitor_counts.index, orientation='h', title="Top 10 Competitors by Ad Count")
    st.plotly_chart(fig_competitors, use_container_width=True)

# ==== 2. BRAND COMPETITION VIEW ====
st.markdown("---")
st.header("2. 🏆 Brand Competition View")

brand_selected = st.selectbox("Select Brand Category", options=filtered_df['brand_category'].unique(), key="brand_comp")
brand_df = filtered_df[filtered_df['brand_category'] == brand_selected]

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Competitor Ads", brand_df.shape[0])
with col2:
    st.metric("Active Competitors", brand_df['competitor_page'].nunique())
with col3:
    top_spender = brand_df.groupby('competitor_page')['spend_midpoint'].sum().idxmax() if len(brand_df) > 0 else "N/A"
    st.metric("Top Spender", top_spender)
with col4:
    st.metric("Avg Spend/Ad", format_inr(brand_df['spend_midpoint'].mean()))
with col5:
    st.metric("Avg Impressions/Ad", format_inr(brand_df['impressions_midpoint'].mean()))

col1, col2, col3 = st.columns(3)

with col1:
    competitor_ads = brand_df['competitor_page'].value_counts().head(10)
    fig_comp_ads = px.bar(x=competitor_ads.index, y=competitor_ads.values, title="Ads per Competitor", labels={'x': 'Competitor', 'y': 'Count'})
    fig_comp_ads.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_comp_ads, use_container_width=True)

with col2:
    competitor_spend = brand_df.groupby('competitor_page')['spend_midpoint'].sum().sort_values(ascending=False).head(10)
    fig_comp_spend = px.bar(x=competitor_spend.index, y=competitor_spend.values, title="Spend per Competitor", labels={'x': 'Competitor', 'y': 'Spend (INR)'})
    fig_comp_spend.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_comp_spend, use_container_width=True)

with col3:
    sov = brand_df.groupby('competitor_page')['spend_midpoint'].sum().sort_values(ascending=False).head(10)
    fig_sov = px.pie(values=sov.values, names=sov.index, title="Share of Voice (Top 10)")
    st.plotly_chart(fig_sov, use_container_width=True)

# ==== 3. COMPETITOR DEEP DIVE ====
st.markdown("---")
st.header("3. 🔍 Competitor Deep Dive")

competitor_selected = st.selectbox("Select Competitor", options=filtered_df['competitor_page'].unique(), key="competitor_dive")
comp_df = filtered_df[filtered_df['competitor_page'] == competitor_selected]

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Ads", comp_df.shape[0])
with col2:
    st.metric("Active %", f"{(comp_df['is_active'].sum() / len(comp_df) * 100):.1f}%" if len(comp_df) > 0 else "0%")
with col3:
    st.metric("Avg Spend", format_inr(comp_df['spend_midpoint'].mean()))
with col4:
    st.metric("Avg Impressions", format_inr(comp_df['impressions_midpoint'].mean()))
with col5:
    st.metric("Dominant Platform", comp_df['publisher_platform'].mode()[0] if len(comp_df) > 0 else "N/A")

col1, col2 = st.columns(2)

with col1:
    comp_timeline = comp_df.groupby('year_month').size().sort_index()

    fig_comp_timeline = px.line(
        x=comp_timeline.index,
        y=comp_timeline.values,
        title="Monthly Ad Activity Timeline",
        labels={'x': 'Month', 'y': 'Ad Count'}
    )

    st.plotly_chart(fig_comp_timeline, use_container_width=True)

with col2:
    fig_spend_hist = px.histogram(comp_df, x='spend_midpoint', nbins=30, title="Spend Distribution", labels={'spend_midpoint': 'Spend (INR)'})
    st.plotly_chart(fig_spend_hist, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    cta_freq = comp_df['cta_type'].value_counts()
    fig_cta = px.bar(x=cta_freq.index, y=cta_freq.values, title="CTA Frequency", labels={'x': 'CTA Type', 'y': 'Count'})
    st.plotly_chart(fig_cta, use_container_width=True)

with col2:
    platform_dist = comp_df['publisher_platform'].value_counts()
    fig_platform_comp = px.pie(values=platform_dist.values, names=platform_dist.index, title="Platform Distribution")
    st.plotly_chart(fig_platform_comp, use_container_width=True)

# ==== 4. CREATIVE & MESSAGING INTELLIGENCE ====
st.markdown("---")
st.header("4. 💡 Creative & Messaging Intelligence")

all_keywords = []
for keywords_list in filtered_df['keywords_found']:
    all_keywords.extend(keywords_list)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Most Common Keyword", max(set(all_keywords), key=all_keywords.count) if all_keywords else "N/A")
with col2:
    st.metric("New Messaging %", f"{(filtered_df['is_new_ad'].sum() / len(filtered_df) * 100):.1f}%" if len(filtered_df) > 0 else "0%")
with col3:
    discount_ads = filtered_df[filtered_df['keywords_found'].apply(lambda x: 'discount' in x)]
    st.metric("Discount Ads %", f"{(len(discount_ads) / len(filtered_df) * 100):.1f}%" if len(filtered_df) > 0 else "0%")
with col4:
    st.metric("Creative Variations", filtered_df['ad_creative_body'].nunique())

col1, col2 = st.columns(2)

with col1:
    keyword_counts = pd.Series(all_keywords).value_counts()
    fig_keywords = px.bar(x=keyword_counts.index, y=keyword_counts.values, title="Keyword Frequency", labels={'x': 'Keyword', 'y': 'Count'})
    st.plotly_chart(fig_keywords, use_container_width=True)

with col2:
    messaging_trend = (
    filtered_df
    .groupby(['year_month', 'is_new_ad'])
    .size()
    .reset_index(name='count')
    .sort_values('year_month')
)

    fig_messaging = px.area(
        messaging_trend,
        x='year_month',
        y='count',
        color='is_new_ad',
        title="Monthly Messaging Trend"
    )

    st.plotly_chart(fig_messaging, use_container_width=True)

# ==== 5. SPEND & SCALE ANALYSIS ====
st.markdown("---")
st.header("5. 💰 Spend & Scale Analysis")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Market Spend", format_inr(filtered_df['spend_midpoint'].sum()))
with col2:
    spend_growth = filtered_df.groupby(filtered_df['ad_creation_time'].dt.isocalendar().week)['spend_midpoint'].sum()
    growth_rate = ((spend_growth.iloc[-1] - spend_growth.iloc[0]) / spend_growth.iloc[0] * 100) if len(spend_growth) > 1 else 0
    st.metric("WoW Spend Growth", f"{growth_rate:.1f}%")
with col3:
    top_3_spend = filtered_df.groupby('competitor_page')['spend_midpoint'].sum().nlargest(3).sum()
    concentration = (top_3_spend / filtered_df['spend_midpoint'].sum() * 100) if filtered_df['spend_midpoint'].sum() > 0 else 0
    st.metric("Top 3 Concentration", f"{concentration:.1f}%")

col1, col2 = st.columns(2)

with col1:
    spend_timeline = filtered_df.groupby('year_month')['spend_midpoint'].sum().sort_index()

    fig_spend_timeline = px.line(
        x=spend_timeline.index,
        y=spend_timeline.values,
        title="Monthly Spend Over Time",
        labels={'x': 'Month', 'y': 'Spend'}
    )

    st.plotly_chart(fig_spend_timeline, use_container_width=True)

with col2:
    fig_scatter = px.scatter(filtered_df, x='spend_midpoint', y='impressions_midpoint', color='competitor_page', title="Spend vs Impressions")
    st.plotly_chart(fig_scatter, use_container_width=True)

# Spend Distribution by Competitor
spend_by_comp = filtered_df.groupby('competitor_page')['spend_midpoint'].apply(list)
fig_box = go.Figure()
for competitor in spend_by_comp.index:
    fig_box.add_trace(go.Box(y=spend_by_comp[competitor], name=competitor))
fig_box.update_layout(title="Spend Distribution by Competitor", height=500)
st.plotly_chart(fig_box, use_container_width=True)

# ==== 6. TARGETING INTELLIGENCE ====
st.markdown("---")
st.header("6. 🎯 Targeting Intelligence")

col1, col2 = st.columns(2)
with col1:
    st.metric("Most Targeted Age Group", filtered_df['target_age_group'].mode()[0] if len(filtered_df) > 0 else "N/A")
with col2:
    st.metric("Most Targeted Region", filtered_df['region_distribution'].mode()[0] if len(filtered_df) > 0 else "N/A")

col1, col2 = st.columns(2)

with col1:
    age_dist = filtered_df['target_age_group'].value_counts()
    fig_age = px.bar(x=age_dist.index, y=age_dist.values, title="Age Group Distribution", labels={'x': 'Age Group', 'y': 'Count'})
    st.plotly_chart(fig_age, use_container_width=True)

with col2:
    region_dist = filtered_df['region_distribution'].value_counts().head(15)
    fig_region = px.bar(y=region_dist.index, x=region_dist.values, orientation='h', title="Top 15 Regions", labels={'x': 'Count', 'y': 'Region'})
    st.plotly_chart(fig_region, use_container_width=True)

# Platform vs Age Group Heatmap
platform_age = pd.crosstab(filtered_df['publisher_platform'], filtered_df['target_age_group'])
fig_heatmap = px.imshow(platform_age, title="Platform vs Age Group Heatmap", labels=dict(color="Ad Count"))
st.plotly_chart(fig_heatmap, use_container_width=True)

# ==== 7. TREND MONITORING ====
st.markdown("---")
st.header("7. 📊 Trend Monitoring")

col1, col2, col3 = st.columns(3)
with col1:
    weekly_growth = filtered_df.groupby(filtered_df['ad_creation_time'].dt.isocalendar().week).size()
    wow_growth = ((weekly_growth.iloc[-1] - weekly_growth.iloc[-2]) / weekly_growth.iloc[-2] * 100) if len(weekly_growth) > 1 else 0
    st.metric("WoW Ad Growth", f"{wow_growth:.1f}%")
with col2:
    new_ads = filtered_df['is_new_ad'].sum()
    st.metric("New Ads (7 days)", new_ads)
with col3:
    stopped_ads = filtered_df[~filtered_df['is_active']].shape[0]
    st.metric("Stopped Ads", stopped_ads)

col1, col2 = st.columns(2)

with col1:
    weekly_counts = filtered_df.groupby('week').size().sort_index()
    fig_weekly = px.line(x=weekly_counts.index, y=weekly_counts.values, title="Weekly Ad Count", labels={'x': 'Week', 'y': 'Count'})
    st.plotly_chart(fig_weekly, use_container_width=True)

with col2:
    new_vs_stopped = pd.DataFrame({
        'New': [filtered_df['is_new_ad'].sum()],
        'Stopped': [stopped_ads]
    })
    fig_new_stopped = px.bar(new_vs_stopped, title="New vs Stopped Ads", labels={'value': 'Count'})
    st.plotly_chart(fig_new_stopped, use_container_width=True)

st.markdown("---")
st.caption("Dashboard created with Streamlit | Data powered by Meta Ad Library")