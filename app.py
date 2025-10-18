
"""
Streamlit dashboard for Lulu UAE — Pricing, Discount & Demographic Sales Analysis

Place this file (app.py) in the same folder as `lulu_uae_master_2000.csv` and run:
    streamlit run app.py

This dashboard includes:
- Filters for demographic fields and loyalty program
- KPIs: Unit price, Discount price, Net sales, Gross sales, VAT amount
- Several charts and below each chart a short business insight and recommendation
- Exports: filtered data CSV download

Note: the app attempts to detect common column names automatically. If your CSV uses different names,
edit the "COLUMN MAPPING" section below accordingly.
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(layout="wide", page_title="Lulu UAE — Pricing & Discount Dashboard")

# === Load data ===
@st.cache_data
def load_data(path="lulu_uae_master_2000.csv"):
    df = pd.read_csv(path, parse_dates=[col for col in ["order_datetime","order_date"] if col in pd.read_csv(path, nrows=0).columns and col])
    return df

df = load_data()

st.title("Lulu UAE — Pricing, Discount & Demographic Sales Dashboard")
st.markdown("Interactive dashboard showing sales metrics by demographic & loyalty segments. Below each chart you'll find a concise business insight and a recommendation.")

# === COLUMN MAPPING (adjust here if needed) ===
# Common column names found in many Lulu exports. Edit if your CSV differs.
col_map = {
    "base_unit_price": None,
    "unit_price_after_discount": None,
    "quantity": None,
    "vat_amount": None,
    "vat_percent": None,
    "gender": None,
    "age": None,
    "age_group": None,
    "city": None,
    "loyalty_tier": None,
    "loyalty_id": None,
    "customer_id": None
}
cols = set(df.columns.str.lower())
for c in df.columns:
    lc = c.lower()
    if "base_unit" in lc or ("unit" in lc and "base" in lc) or "base_unit_price" in lc or "base_price" in lc:
        col_map["base_unit_price"] = c
    if "after_discount" in lc or "unit_price_after" in lc or ("unit" in lc and "after" in lc):
        col_map["unit_price_after_discount"] = c
    if "quantity" in lc:
        col_map["quantity"] = c
    if "vat_amount" in lc or "vat" in lc and "amount" in lc:
        col_map["vat_amount"] = c
    if lc == "vat_percent" or "vat_percent" in lc or "vat_rate" in lc:
        col_map["vat_percent"] = c
    if "gender" in lc:
        col_map["gender"] = c
    if "age_group" in lc:
        col_map["age_group"] = c
    if lc == "age":
        col_map["age"] = c
    if "city" in lc or "location" in lc:
        col_map["city"] = c
    if "loyal" in lc or "tier" in lc:
        col_map["loyalty_tier"] = c
    if "loyalty_id" in lc:
        col_map["loyalty_id"] = c
    if "customer" in lc and "id" in lc:
        col_map["customer_id"] = c

# Show mapping to user
st.subheader("Detected column mapping")
st.write(col_map)

# Basic derived columns with safe fallbacks
df_proc = df.copy()

# unit price (base unit price)
if col_map["base_unit_price"] and col_map["base_unit_price"] in df_proc.columns:
    df_proc["unit_price"] = pd.to_numeric(df_proc[col_map["base_unit_price"]], errors="coerce")
else:
    # fallback: try unit_price if exists
    if "unit_price" in df_proc.columns:
        df_proc["unit_price"] = pd.to_numeric(df_proc["unit_price"], errors="coerce")
    else:
        st.warning("Could not find a base unit price column automatically. Please update the COLUMN MAPPING section in the app.")
        df_proc["unit_price"] = 0.0

# unit price after discount
if col_map["unit_price_after_discount"] and col_map["unit_price_after_discount"] in df_proc.columns:
    df_proc["unit_price_after_discount"] = pd.to_numeric(df_proc[col_map["unit_price_after_discount"]], errors="coerce")
else:
    # if not present, assume unit_price * (1 - discount_pct) if discount_pct present
    # or set equal to unit_price
    if "unit_price_after_discount" not in df_proc.columns:
        df_proc["unit_price_after_discount"] = df_proc["unit_price"]

# quantity
if col_map["quantity"] and col_map["quantity"] in df_proc.columns:
    df_proc["quantity"] = pd.to_numeric(df_proc[col_map["quantity"]], errors="coerce").fillna(1)
else:
    if "quantity" not in df_proc.columns:
        df_proc["quantity"] = 1

# gross sales = base unit price * quantity
df_proc["gross_sales_aed"] = (df_proc["unit_price"].fillna(0) * df_proc["quantity"].fillna(1)).round(2)

# net sales = unit_price_after_discount * quantity
df_proc["net_sales_aed"] = (df_proc["unit_price_after_discount"].fillna(df_proc["unit_price"]) * df_proc["quantity"]).round(2)

# discount amount per unit and total
df_proc["discount_per_unit"] = (df_proc["unit_price"] - df_proc["unit_price_after_discount"]).fillna(0)
df_proc["discount_total_aed"] = (df_proc["discount_per_unit"] * df_proc["quantity"]).round(2)

# VAT: prefer existing vat_amount; else compute if vat_percent present
if col_map["vat_amount"] and col_map["vat_amount"] in df_proc.columns:
    try:
        df_proc["vat_amount_aed"] = pd.to_numeric(df_proc[col_map["vat_amount"]], errors="coerce").fillna(0)
    except Exception:
        df_proc["vat_amount_aed"] = 0.0
elif col_map["vat_percent"] and col_map["vat_percent"] in df_proc.columns:
    df_proc["vat_amount_aed"] = ((df_proc["net_sales_aed"] * pd.to_numeric(df_proc[col_map["vat_percent"]], errors="coerce").fillna(0))/100).round(2)
else:
    # assume 5% VAT if not present (adjust if needed)
    DEFAULT_VAT = 5.0
    df_proc["vat_amount_aed"] = (df_proc["net_sales_aed"] * DEFAULT_VAT / 100).round(2)

# Demographic fields
gender_col = col_map["gender"] if col_map["gender"] in df_proc.columns else None
age_col = col_map["age"] if col_map["age"] in df_proc.columns else None
age_group_col = col_map["age_group"] if col_map["age_group"] in df_proc.columns else None
city_col = col_map["city"] if col_map["city"] in df_proc.columns else None
loyalty_col = col_map["loyalty_tier"] if col_map["loyalty_tier"] in df_proc.columns else None

# Create age groups if only age present
if age_col and age_col in df_proc.columns and not age_group_col:
    try:
        df_proc["age"] = pd.to_numeric(df_proc[age_col], errors="coerce")
        bins = [0,18,25,35,45,60,120]
        labels = ["<18","18-24","25-34","35-44","45-59","60+"]
        df_proc["age_group"] = pd.cut(df_proc["age"], bins=bins, labels=labels)
        age_group_col = "age_group"
    except Exception:
        pass

# === Sidebar filters ===
st.sidebar.header("Filters")
# Gender filter
if gender_col:
    genders = ["All"] + sorted(df_proc[gender_col].dropna().unique().tolist())
    sel_gender = st.sidebar.selectbox("Gender", genders, index=0)
else:
    sel_gender = "All"

# Age group filter
if age_group_col:
    age_groups = ["All"] + sorted(df_proc[age_group_col].dropna().unique().astype(str).tolist())
    sel_age_group = st.sidebar.selectbox("Age group", age_groups, index=0)
else:
    sel_age_group = "All"

# City filter
if city_col:
    cities = ["All"] + sorted(df_proc[city_col].dropna().unique().tolist())
    sel_city = st.sidebar.selectbox("City", cities, index=0)
else:
    sel_city = "All"

# Loyalty filter
if loyalty_col:
    loyalty_vals = ["All"] + sorted(df_proc[loyalty_col].dropna().unique().tolist())
    sel_loyalty = st.sidebar.selectbox("Loyalty tier", loyalty_vals, index=0)
else:
    sel_loyalty = "All"

# Date range filter if order date exists
date_cols = [c for c in df_proc.columns if "date" in c.lower() or "datetime" in c.lower()]
date_col = date_cols[0] if date_cols else None
if date_col:
    try:
        df_proc[date_col] = pd.to_datetime(df_proc[date_col], errors="coerce")
        min_date = df_proc[date_col].min()
        max_date = df_proc[date_col].max()
        sel_date = st.sidebar.date_input("Date range", value=(min_date, max_date))
    except Exception:
        date_col = None

# Apply filters
df_filtered = df_proc.copy()
if sel_gender != "All" and gender_col:
    df_filtered = df_filtered[df_filtered[gender_col] == sel_gender]
if sel_age_group != "All" and age_group_col:
    df_filtered = df_filtered[df_filtered[age_group_col].astype(str) == sel_age_group]
if sel_city != "All" and city_col:
    df_filtered = df_filtered[df_filtered[city_col] == sel_city]
if sel_loyalty != "All" and loyalty_col:
    df_filtered = df_filtered[df_filtered[loyalty_col] == sel_loyalty]
if date_col and isinstance(sel_date, tuple) and len(sel_date) == 2:
    df_filtered = df_filtered[(df_filtered[date_col] >= pd.to_datetime(sel_date[0])) & (df_filtered[date_col] <= pd.to_datetime(sel_date[1]))]

# === KPI cards ===
st.header("Top-level KPIs (filtered)")
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Avg Unit Price (AED)", f"{df_filtered['unit_price'].mean():.2f}")
kpi2.metric("Avg Discount per Unit (AED)", f"{df_filtered['discount_per_unit'].mean():.2f}")
kpi3.metric("Net Sales (AED)", f"{df_filtered['net_sales_aed'].sum():.2f}")
kpi4.metric("Gross Sales (AED)", f"{df_filtered['gross_sales_aed'].sum():.2f}")
kpi5.metric("VAT Amount (AED)", f"{df_filtered['vat_amount_aed'].sum():.2f}")

# === Charts ===

# 1) Unit price distribution by loyalty tier
st.subheader("Unit price distribution by Loyalty Tier")
fig1, ax1 = plt.subplots(figsize=(8,4))
if loyalty_col:
    grouped = df_filtered.groupby(df_filtered[loyalty_col])["unit_price"].median().sort_values(ascending=False)
    ax1.bar(grouped.index.astype(str), grouped.values)
    ax1.set_ylabel("Median Unit Price (AED)")
    ax1.set_xlabel("Loyalty Tier")
    ax1.set_title("Median Unit Price by Loyalty Tier")
else:
    ax1.hist(df_filtered["unit_price"].dropna(), bins=30)
    ax1.set_xlabel("Unit Price (AED)")
    ax1.set_title("Unit Price Distribution")
st.pyplot(fig1)
st.markdown("**Business insight:** Median unit price varies across loyalty tiers indicating different purchasing behaviors. \n\n**Recommendation:** Create tier-specific promotions (e.g., bundle offers for lower-tier customers, premium upsell bundles for higher-tier customers) to increase AOV.")

# 2) Discount amount by age group
st.subheader("Average Discount per Unit by Age Group")
fig2, ax2 = plt.subplots(figsize=(8,4))
if "age_group" in df_filtered.columns:
    disc_by_age = df_filtered.groupby("age_group")["discount_per_unit"].mean().sort_index()
    ax2.plot(disc_by_age.index.astype(str), disc_by_age.values, marker='o')
    ax2.set_xlabel("Age Group")
    ax2.set_ylabel("Average Discount per Unit (AED)")
    ax2.set_title("Average Discount per Unit by Age Group")
else:
    ax2.text(0.5,0.5,"Age group data not available", ha='center')
st.pyplot(fig2)
st.markdown("**Business insight:** Certain age groups receive/claim higher discounts, showing sensitivity to price reductions. \n\n**Recommendation:** Target discount-led campaigns at price-sensitive age groups and use A/B testing to find the optimal discount that increases conversion without eroding margin.")

# 3) Net sales trend over time
st.subheader("Net Sales Trend Over Time")
fig3, ax3 = plt.subplots(figsize=(10,4))
if date_col:
    timeseries = df_filtered.set_index(date_col).resample("W")["net_sales_aed"].sum()
    ax3.plot(timeseries.index, timeseries.values)
    ax3.set_xlabel("Date")
    ax3.set_ylabel("Net Sales (AED)")
    ax3.set_title("Weekly Net Sales Trend")
else:
    ax3.text(0.5,0.5,"Date data not available", ha='center')
st.pyplot(fig3)
st.markdown("**Business insight:** Weekly net sales trend reveals peaks and troughs that may correspond to promotions or seasonality. \n\n**Recommendation:** Align marketing spend with historical peaks and run targeted uplift campaigns during low periods to smooth revenue.")

# 4) Gross vs Net sales by city (top cities)
st.subheader("Gross vs Net Sales by City (Top 10)")
fig4, ax4 = plt.subplots(figsize=(10,5))
if city_col:
    city_sales = df_filtered.groupby(city_col)[["gross_sales_aed","net_sales_aed"]].sum().sort_values("net_sales_aed", ascending=False).head(10)
    x = np.arange(len(city_sales))
    ax4.bar(x - 0.15, city_sales["gross_sales_aed"], width=0.3, label="Gross")
    ax4.bar(x + 0.15, city_sales["net_sales_aed"], width=0.3, label="Net")
    ax4.set_xticks(x)
    ax4.set_xticklabels(city_sales.index.astype(str), rotation=45, ha='right')
    ax4.set_ylabel("Sales (AED)")
    ax4.legend()
else:
    ax4.text(0.5,0.5,"City data not available", ha='center')
st.pyplot(fig4)
st.markdown("**Business insight:** Some cities have higher gross but proportionally lower net sales, indicating larger discounts or promotion activity. \n\n**Recommendation:** Audit city-specific promotional effectiveness and consider localized pricing strategies where net margin is low.")

# 5) VAT contribution by loyalty tier
st.subheader("VAT Amount Contribution by Loyalty Tier")
fig5, ax5 = plt.subplots(figsize=(8,4))
if loyalty_col:
    vat_by_loyal = df_filtered.groupby(df_filtered[loyalty_col])["vat_amount_aed"].sum().sort_values(ascending=False)
    ax5.pie(vat_by_loyal.values, labels=vat_by_loyal.index.astype(str), autopct='%1.1f%%', startangle=140)
    ax5.set_title("VAT Contribution by Loyalty Tier")
else:
    ax5.text(0.5,0.5,"Loyalty tier data not available", ha='center')
st.pyplot(fig5)
st.markdown("**Business insight:** VAT contributions highlight which loyalty tiers generate the most taxable sales. \n\n**Recommendation:** For high-VAT tiers, consider targeted loyalty offers that encourage higher-margin purchases (private label, add-ons) rather than blanket discounts.")

# 6) Discount vs Net sales scatter (price sensitivity)
st.subheader("Discount per Unit vs Net Sales (scatter)")
fig6, ax6 = plt.subplots(figsize=(8,5))
ax6.scatter(df_filtered["discount_per_unit"], df_filtered["net_sales_aed"])
ax6.set_xlabel("Discount per Unit (AED)")
ax6.set_ylabel("Net Sales (AED)")
ax6.set_title("Discount vs Net Sales (each transaction)")
st.pyplot(fig6)
st.markdown("**Business insight:** High discounts do not always correlate with higher net sales — discounts can erode margin without driving enough volume. \n\n**Recommendation:** Use targeted discounts (coupon codes, loyalty-only discounts) and measure incremental lift vs control groups to ensure discounts are profitable.")

# === Additional analysis: Average spend by gender and order count by channel if channel exists ===
st.header("Demographic cross-tabs & tables")
cols_to_show = ["gender","age_group", city_col, loyalty_col, "quantity", "net_sales_aed"]
available = [c for c in cols_to_show if c in df_filtered.columns or c in df_filtered.columns]
if "gender" in df_filtered.columns:
    gender_tab = df_filtered.groupby("gender").agg(orders=("quantity","count"), avg_spend=("net_sales_aed","mean"), total_net=("net_sales_aed","sum"))
    st.subheader("By Gender")
    st.write(gender_tab)
    st.markdown("**Insight:** Use gender-level avg spend to tailor assortments and targeted communication.\n\n**Recommendation:** Personalize promotions and product recommendations by gender segments.")

# Export filtered data
st.markdown("### Export filtered dataset")
def convert_df_to_csv_bytes(df):
    return df.to_csv(index=False).encode('utf-8')

csv_bytes = convert_df_to_csv_bytes(df_filtered)
st.download_button("Download filtered data (CSV)", data=csv_bytes, file_name="lulu_filtered.csv", mime="text/csv")

st.markdown("---")
st.caption("Dashboard created for Lulu UAE — adjust COLUMN MAPPING at the top of this file if any metric appears incorrect due to differing column names.")
