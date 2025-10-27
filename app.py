import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv # Keep this for potential future use or other keys

# Removed Gemini Setup Block

# ====== DATA LOAD ======
@st.cache_data
def load_defaults():
    # Load the CSV file based on your project proposal name
    try:
        # Try proposal name first
        df = pd.read_csv("sector_defaults.csv", encoding='latin1')
    except FileNotFoundError:
        try:
            # Fallback in case the user has the old plural name
            df = pd.read_csv("sectors_defaults.csv", encoding='latin1')
        except Exception as e:
            st.error(f"Error loading data: {e}. Please ensure 'sector_defaults.csv' is in the same folder.")
            return None
    
    if df is not None:
        df = df.set_index("sector")
    return df

defaults = load_defaults()

# Stop execution if data isn't loaded
if defaults is None:
    st.stop()

st.set_page_config(
    page_title="Covalence", # Updated Page Title
    layout="wide"
)

# ====== SIDEBAR INPUT / PARAMS ======
# These inputs are universal for both personas
st.sidebar.header("Client / Export Inputs") # Capitalized

sector = st.sidebar.selectbox(
    "Sector",
    options=["steel", "aluminium"],
    help="Model is calibrated for Indian steel and aluminium exporters to the EU. (Watch the UI change!)"
)
row = defaults.loc[sector]

# ====== DEFINE DYNAMIC THEME COLORS ======
if sector == "steel":
    # New "Deep Indigo / Steel Blue" theme
    base_bg = "#1A202C"       # Very Dark Blue (Slate 900)
    card_bg = "#273344"       # Dark Blue (Slate 800)
    text_color = "#E2E8F0"    # Light Gray-Blue (Slate 200)
    light_text = "#94A3B8"    # Muted Gray (Slate 400)
    accent_color = "#38BDF8"  # Bright Steel Blue (Sky 400)
    border_color = "#475569"  # Dark Gray Border (Slate 600)
else:
    # "Midnight Blue" (dark) theme - HIGH CONTRAST
    base_bg = "#0F172A"       # Darkest Blue (Slate 900)
    card_bg = "#1E293B"       # Dark Blue (Slate 800)
    text_color = "#F1F5F9"    # Off-white (Slate 100)
    light_text = "#64748B"    # Muted Gray-Blue (Slate 500)
    accent_color = "#0EA5E9"  # Bright Sky Blue (Sky 500)
    border_color = "#334155"  # Subtle Border (Slate 700)

user_intensity = st.sidebar.number_input(
    "Plant emission intensity (tCO₂ / tonne product)",
    min_value=0.0,
    value=float(row["india_emission_intensity_tCO2_per_tonne"]),
    step=0.1
)

export_volume_tonnes = st.sidebar.number_input(
    "Annual EU export volume (tonnes/year)",
    min_value=0.0,
    value=39000.0,
    step=1000.0
)

selling_price = st.sidebar.number_input(
    "Average selling price (€/tonne)",
    min_value=0.0,
    value=float(row["typical_export_price_per_tonne_eur"]),
    step=10.0
)

pre_margin_pct = float(row["typical_pre_cbam_margin_pct"])

st.sidebar.divider()
st.sidebar.header("Decarbonisation Plan") # Capitalized

reduction_pct = st.sidebar.slider(
    "Target intensity reduction (%)",
    min_value=0,
    max_value=50,
    value=15,
    help="Your decarbonisation ambition over the next 24–36 months."
)

capex_per_pct_reduction_million_eur = st.sidebar.number_input(
    "Capex per 1% reduction (million €)",
    min_value=0.0,
    value=8.0 if sector == "steel" else 5.0,
    step=0.5,
    help="Ballpark: Steel retrofits (EAF, CCUS, H2-DRI) are more capital intensive than Aluminium's renewable power switch."
)

slb_rate_discount_bps = st.sidebar.number_input(
    "SLL / SLB incentive (bps)",
    min_value=0,
    max_value=300,
    value=75 if sector == "steel" else 60,
    step=5,
    help="Typical coupon/interest reduction if you hit CO₂ KPI."
)

# New input for Banker persona
deal_tenor_years = st.sidebar.number_input(
    "Loan Tenor (Years)",
    min_value=1,
    max_value=20,
    value=7,
    step=1,
    help="Typical loan period for structuring the deal."
)

st.sidebar.divider()
st.sidebar.header("Financial Assumptions") # Capitalized
EUR_to_INR_rate = st.sidebar.number_input("EUR to INR Exchange Rate", min_value=70.0, max_value=110.0, value=88.5, step=0.5) # Capitalized


# ====== CORE CALCULATIONS (Deterministic Layer A) ======

# Constants for INR conversion
LAKH = 100_000
CRORE = 10_000_000

# Extract benchmark values from the loaded data row
eu_benchmark = float(row["eu_benchmark_intensity_tCO2_per_tonne"])
ets_price = float(row["ets_price_eur_per_tCO2"])

# CBAM cost driver
excess_intensity = max(user_intensity - eu_benchmark, 0)
cbam_cost_per_tonne_calc = excess_intensity * ets_price
total_cbam_bill = cbam_cost_per_tonne_calc * export_volume_tonnes
total_cbam_bill_inr = total_cbam_bill * EUR_to_INR_rate

# Margin hit
cbam_hit_pct_of_price = (cbam_cost_per_tonne_calc / selling_price * 100) if selling_price > 0 else 0
post_margin_pct = max(pre_margin_pct - cbam_hit_pct_of_price, 0)
margin_delta = post_margin_pct - pre_margin_pct

if cbam_hit_pct_of_price <= 5:
    competitiveness = "GREEN – Broadly Aligned"
    competitiveness_class = "status-green"
elif cbam_hit_pct_of_price <= 15:
    competitiveness = "YELLOW – Cost Pressure"
    competitiveness_class = "status-yellow"
else:
    competitiveness = "RED – High Substitution Risk"
    competitiveness_class = "status-red"

# After decarbonisation scenario
reduced_intensity = user_intensity * (1 - reduction_pct/100)
excess_after = max(reduced_intensity - eu_benchmark, 0)
cbam_after_per_tonne = excess_after * ets_price
total_cbam_after = cbam_after_per_tonne * export_volume_tonnes

cbam_savings_total = max(total_cbam_bill - total_cbam_after, 0)
cbam_savings_total_inr = cbam_savings_total * EUR_to_INR_rate

# Finance sizing
total_transition_capex_million_eur = capex_per_pct_reduction_million_eur * reduction_pct
total_transition_capex_eur = total_transition_capex_million_eur * 1_000_000
total_transition_capex_inr = total_transition_capex_eur * EUR_to_INR_rate
annual_finance_relief_estimate_eur = (slb_rate_discount_bps / 10000) * total_transition_capex_eur
annual_finance_relief_estimate_inr = annual_finance_relief_estimate_eur * EUR_to_INR_rate

# Readiness score
# This calculation is correct. A high CBAM hit (e.g., 35% for Aluminium) vs. a low margin (10%)
# results in a 0.0 score, which is the intended financial warning.
score_raw = (cbam_hit_pct_of_price * 2) + (pre_margin_pct - post_margin_pct) * 5
readiness_score = max(min(100 - score_raw, 100), 0)

# Banker-specific calculations
annual_debt_service_eur = (total_transition_capex_eur / deal_tenor_years) if deal_tenor_years > 0 else 0
annual_debt_service_inr = annual_debt_service_eur * EUR_to_INR_rate
annual_cash_flow_gain_eur = cbam_savings_total + annual_finance_relief_estimate_eur
annual_cash_flow_gain_inr = annual_cash_flow_gain_eur * EUR_to_INR_rate
coverage_ratio = (annual_cash_flow_gain_eur / annual_debt_service_eur) if annual_debt_service_eur > 0 else 999 # Avoid divide by zero


# ====== SECTOR-SPECIFIC CONTEXT (for Layer B) ======
def sector_specific_decarb_levers(sec):
    if sec == "steel":
        return [
            "**Shift to EAF:** Move from Basic Oxygen Furnace (BOF) to scrap-based Electric Arc Furnace (EAF) or hydrogen-based Direct Reduced Iron (H2-DRI).",
            "**Pilot CCUS:** Implement Carbon Capture, Utilisation, and Storage (CCUS) on high-temperature process streams.",
            "**Electrification:** Use energy recovery and electrification in reheating and rolling processes."
        ]
    else:
        return [
            "**Renewable Power:** Shift captive power from coal to renewables via long-term Power Purchase Agreements (PPAs) or captive solar/wind farms. This is the single biggest lever.",
            "**Cell Efficiency:** Improve electrolytic cell efficiency and anode management to reduce process emissions.",
            "**Heat Recovery:** Implement heat recovery systems and electrify downstream rolling/extrusion."
        ]

def sector_specific_finance(sec):
    if sec == "steel":
        return [
            "**Sustainability-Linked Loans (SLLs):** KPI-linked loans tied to tCO₂/tonne reduction. *Precedent: Tata Steel, JSW Steel.*",
            "**Blended Finance:** Use of first-loss guarantees for high-capex tech like H₂-DRI or CCUS.",
            "**Policy Support:** Advocate for state-backed transition facilities or Contracts for Difference (CfD) for green steel."
        ]
    else:
        return [
            "**Green Bonds:** Issue bonds specifically to fund renewable PPAs or captive solar for smelters. *Precedent: Hindalco.*",
            "**Concessional Lines:** Access multilateral (World Bank, IFC) credit lines targeting electricity decarbonisation.",
            "**Pooled Guarantees:** For downstream MSMEs, use cluster-scale pooled guarantees to access affordable credit."
        ]

# ====== DYNAMIC STYLING (New Themes) ======
def get_custom_css(base_bg, card_bg, text_color, light_text, accent_color, border_color):
    # This function no longer defines colors, it receives them
    # Ensure consistent indentation within this f-string (using spaces)
    css = f"""
    <style>
        /* Base */
        .stApp {{
            background-color: {base_bg};
            color: {text_color};
        }}
        /* Updated: Style h2, etc. EXCEPT the main title */
        h2, h3, h4, h5, h6 {{
            color: {text_color};
        }}
        
        /* Main Title */
        .main-title {{
            color: {accent_color}; /* Use the bold accent color */
            font-weight: 700; /* Ensure it's bold */
            text-align: left; /* Keep alignment */
            padding-bottom: 0px; /* Adjust spacing if needed */
            margin-bottom: 0px; /* Adjust spacing if needed */
        }}
        
        /* Tagline */
        .tagline {{
            color: {light_text}; /* Use the lighter text color */
            font-size: 1.1rem;
            font-weight: 500;
            margin-top: -10px; /* Pull it closer to the title */
            margin-bottom: 10px;
        }}

        /* Persona Selector */
        [data-testid="stRadio"] label {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            padding: 8px 12px;
            border-radius: 8px;
            margin-right: 10px;
            color: {light_text};
        }}
        [data-testid="stRadio"] [aria-checked="true"] label {{
            background-color: {accent_color};
            color: #FFFFFF;
            border-color: {accent_color};
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {card_bg};
            border-right: 1px solid {border_color};
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
            color: {text_color};
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background-color: {base_bg};
            padding-bottom: 0px;
        }}
        .stTabs [data-baseweb="tab-list"] button {{
            color: {light_text};
            background-color: {base_bg};
            border-bottom: 2px solid {border_color};
            padding: 10px 15px;
        }}
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
            color: {accent_color};
            border-bottom: 2px solid {accent_color};
            background-color: {card_bg};
        }}

        /* Main Tab Content Containers */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 10px;
            padding: 24px;
            text-align: left;
            margin-bottom: 10px;
        }}

        /* --- Custom KPI Card Styles --- */
        .kpi-card {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 10px;
            padding: 24px;
            text-align: left;
            margin-bottom: 10px;
            height: 145px;
        }}
        .kpi-label {{
            font-size: 0.85rem;
            color: {light_text};
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        .kpi-value {{
            font-size: 2.25rem;
            font-weight: bold;
            color: {text_color};
            line-height: 1.2;
        }}
        .kpi-accent {{
            color: {accent_color};
        }}
        .kpi-subtext, .kpi-delta-pos, .kpi-delta-neg {{
            font-size: 0.95rem;
            color: {light_text};
            margin-top: 8px;
        }}
        .kpi-delta-pos {{
            color: #2ECC71 !important; /* Green */
        }}
        .kpi-delta-neg {{
            color: #E74C3C !important; /* Red */
        }}

        /* Status Text */
        .status-green {{ color: #2ECC71; font-weight: bold; }}
        .status-yellow {{ color: #F1C40F; font-weight: bold; }}
        .status-red {{ color: #E74C3C; font-weight: bold; }}

        /* List items in containers */
        [data-testid="stVerticalBlockBorderWrapper"] ul li {{
            margin-bottom: 8px;
            font-size: 0.95rem;
        }}

    </style>
    """
    return css

st.markdown(get_custom_css(base_bg, card_bg, text_color, light_text, accent_color, border_color), unsafe_allow_html=True)


# ====== LAYOUT START ======

# Updated Title and Tagline rendering
st.markdown(f'<h1 class="main-title">Covalence</h1>', unsafe_allow_html=True) # Capitalized Title
st.markdown(f'<p class="tagline">Bonding carbon, finance, and competitiveness</p>', unsafe_allow_html=True) # Capitalized Tagline
st.markdown(f"**Advisory dashboard for Indian {sector.title()} Exporters and their Financial Partners**") # Updated and Bolded Subtitle

# ====== PERSONA SELECTOR (Core new feature) ======
persona = st.radio(
    "Select Your View:",
    ["Exporter / Manufacturer", "Banker / Financial Institution"],
    horizontal=True,
    label_visibility="collapsed"
)
st.divider()

# ====== PERSONA 1: EXPORTER VIEW ======
if persona == "Exporter / Manufacturer":

    # 1.1: Exporter KPI Row
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    # --- Add helper text for 0.0 readiness score ---
    readiness_subtext = "Resilience to EU buyer pressure"
    if readiness_score == 0:
        readiness_subtext = "<span class='status-red'>High Risk: CBAM cost exceeds margin</span>"

    kpi_col1.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Readiness Score</div>
        <div class="kpi-value kpi-accent">{readiness_score:.1f} / 100</div>
        <div class="kpi-subtext">{readiness_subtext}</div>
    </div>
    """, unsafe_allow_html=True)
    
    kpi_col2.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Annual CBAM Bill (Est.)</div>
        <div class="kpi-value">€{total_cbam_bill:,.0f}</div>
        <div class="kpi-subtext">(Approx. ₹ {total_cbam_bill_inr / CRORE:,.1f} Cr)</div>
    </div>
    """, unsafe_allow_html=True)
    
    margin_delta_class = "kpi-delta-pos" if margin_delta >= 0 else "kpi-delta-neg"
    kpi_col3.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Post-CBAM Margin</div>
        <div class="kpi-value">{post_margin_pct:.1f}%</div>
        <div class="{margin_delta_class}">{margin_delta:.1f}% (from {pre_margin_pct:.1f}%)</div>
    </div>
    """, unsafe_allow_html=True)
    
    kpi_col4.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Annual CBAM Savings</div>
        <div class="kpi-value">€{cbam_savings_total:,.0f}</div>
        <div class="kpi-subtext">(Approx. ₹ {cbam_savings_total_inr / CRORE:,.1f} Cr)</div>
    </div>
    """, unsafe_allow_html=True)

    # 1.2: Exporter Tabs - REMOVED EMOJIS, Capitalized
    tab1, tab2, tab3 = st.tabs([
        "Exposure Analysis", 
        "Decarbonisation Plan", 
        "Policy & Market Levers"
    ])

    with tab1:
        with st.container(border=True):
            st.subheader("Competitiveness & Margin Erosion") # Capitalized
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="kpi-card" style="height: auto; text-align: center; padding: 30px; border: 1px solid {border_color}; border-radius: 10px;">
                    <div class="kpi-label">Competitiveness Rating</div>
                    <div class="kpi-value {competitiveness_class}" style="font-size: 1.8rem;">{competitiveness}</div>
                    <div class="{competitiveness_class}" style="margin-top: 10px; color: {light_text};">
                        CBAM adds {cbam_hit_pct_of_price:.1f}% to your per-tonne cost.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="kpi-card" style="height: auto;">
                    <div class="kpi-label">Current Plant Intensity</div>
                    <div class="kpi-value">{user_intensity:.2f} tCO₂/t</div>
                    <div class="kpi-subtext">
                        India baseline: {row['india_emission_intensity_tCO2_per_tonne']:.2f} | 
                        EU benchmark: {eu_benchmark:.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                <div class="kpi-card" style="height: auto; margin-top: 10px;">
                    <div class="kpi-label">CBAM Cost per Tonne</div>
                    <div class="kpi-value">€{cbam_cost_per_tonne_calc:,.2f}</div>
                    <div class="kpi-subtext">
                        (Approx. ₹ {cbam_cost_per_tonne_calc * EUR_to_INR_rate:,.0f})
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        with st.container(border=True):
            st.subheader(f"Quantifying the {reduction_pct}% Decarbonisation Plan") # Capitalized
            
            payback_period = (total_transition_capex_eur / annual_cash_flow_gain_eur) if annual_cash_flow_gain_eur > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"""
            <div class="kpi-card" style="height: auto;">
                <div class="kpi-label">Total Transition Capex</div>
                <div class="kpi-value">€{total_transition_capex_million_eur:,.1f}m</div>
                <div class="kpi-subtext">
                    (Approx. ₹ {total_transition_capex_inr / CRORE:,.1f} Cr)
                </div>
            </div>
            """, unsafe_allow_html=True)
            col2.markdown(f"""
            <div class="kpi-card" style="height: auto;">
                <div class="kpi-label">Annual Positive Cash Flow</div>
                <div class="kpi-value">€{annual_cash_flow_gain_eur:,.0f}</div>
                <div class="kpi-subtext">
                    (Approx. ₹ {annual_cash_flow_gain_inr / CRORE:,.2f} Cr / yr)
                </div>
            </div>
            """, unsafe_allow_html=True)
            col3.markdown(f"""
            <div class="kpi-card" style="height: auto;">
                <div class="kpi-label">Simple Payback Period</div>
                <div class="kpi-value kpi-accent">{payback_period:.1f} Yrs</div>
                <div class="kpi-subtext">
                    Compares Capex to annual cash flow gains.
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # REMOVED Exporter AI Copilot Tab 
    
    with tab3: # Renumbered from tab4
        with st.container(border=True):
            st.subheader("Policy Gaps & Market Levers") # Capitalized
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Key Decarbonisation Levers") # Capitalized
                lever_list = sector_specific_decarb_levers(sector)
                for item in lever_list:
                    st.markdown(f"- {item}")
            with col2:
                st.markdown("#### Policy & MRV Gaps") # Capitalized
                st.markdown(
                    """
                    - **Carbon Credit Recognition:** India's current CCTS / carbon credit schemes are not yet recognised by the EU. This creates a risk of 'double payment' (paying a carbon tax in India and again via CBAM).
                    - **MRV Standardization:** Lack of a standardized, EU-equivalent Monitoring, Reporting, and Verification (MRV) system complicates compliance and may lead to penalties based on default (higher) emissions values.
                    - **Domestic Revenue Recycling:** The proposal's core idea: advocate for a system to redirect domestic carbon receipts to fund exporter decarbonisation (e.g., via concessional finance).
                    """
                )

# ====== PERSONA 2: BANKER / FI VIEW ======
else: 
    
    # 2.1: Banker KPI Row
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    # --- Add helper text for 0.0 readiness score ---
    readiness_subtext = "Client's resilience to CBAM shock"
    if readiness_score == 0:
        readiness_subtext = "<span class='status-red'>High Risk: CBAM cost exceeds margin</span>"

    kpi_col1.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Client Risk Score</div>
        <div class="kpi-value kpi-accent">{readiness_score:.1f} / 100</div>
        <div class="kpi-subtext">{readiness_subtext}</div>
    </div>
    """, unsafe_allow_html=True)
    
    kpi_col2.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Client CBAM Liability</div>
        <div class="kpi-value">€{total_cbam_bill:,.0f} /yr</div>
        <div class="kpi-subtext">(Approx. ₹ {total_cbam_bill_inr / CRORE:,.1f} Cr / yr)</div>
    </div>
    """, unsafe_allow_html=True)

    kpi_col3.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Transition Deal Size</div>
        <div class="kpi-value">€{total_transition_capex_million_eur:,.1f}m</div>
        <div class="kpi-subtext">(Approx. ₹ {total_transition_capex_inr / CRORE:,.1f} Cr)</div>
    </div>
    """, unsafe_allow_html=True)
    
    coverage_class = "kpi-delta-pos" if coverage_ratio >= 1 else "kpi-delta-neg"
    kpi_col4.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Debt Service Coverage</div>
        <div class="kpi-value {coverage_class}">{coverage_ratio:.2f} x</div>
        <div class="kpi-subtext">Cash gains vs. debt service</div>
    </div>
    """, unsafe_allow_html=True)

    # 2.2: Banker Tabs - REMOVED EMOJIS, Capitalized
    tab1, tab2, tab3 = st.tabs([
        "Deal Structuring & ROI", 
        "Market Precedents", 
        "Client Risk Profile"
    ])

    with tab1:
        with st.container(border=True):
            st.subheader("Transition Finance Structuring") # Capitalized
            st.markdown(f"Structuring a **€{total_transition_capex_million_eur:,.1f}m (Approx. ₹ {total_transition_capex_inr / CRORE:,.1f} Cr)** transition loan over **{deal_tenor_years} years**.")
            
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"""
            <div class="kpi-card" style="height: auto;">
                <div class="kpi-label">Annual Debt Service (Est.)</div>
                <div class="kpi-value">€{annual_debt_service_eur:,.0f}</div>
                <div class="kpi-subtext">
                    (Approx. ₹ {annual_debt_service_inr / CRORE:,.2f} Cr / yr)
                </div>
            </div>
            """, unsafe_allow_html=True)
            col2.markdown(f"""
            <div class="kpi-card" style="height: auto;">
                <div class="kpi-label">Annual Client Cash Flow Gain</div>
                <div class="kpi-value">€{annual_cash_flow_gain_eur:,.0f}</div>
                <div class="kpi-subtext">
                    (Approx. ₹ {annual_cash_flow_gain_inr / CRORE:,.2f} Cr / yr)
                </div>
            </div>
            """, unsafe_allow_html=True)
            col3.markdown(f"""
            <div class="kpi-card" style="height: auto;">
                <div class="kpi-label">DSCR (Cash Gain / Debt)</div>
                <div class="kpi-value {coverage_class}">{coverage_ratio:.2f} x</div>
                <div class="kpi-subtext">
                    A ratio > 1.0x means the project's gains self-liquidate the new debt.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"**Conclusion:** The decarbonisation project is **bankable**. The annual positive cash flow of **€{annual_cash_flow_gain_eur:,.0f} (₹ {annual_cash_flow_gain_inr / CRORE:,.2f} Cr)** generated by the investment is sufficient to cover the new annual debt service of **€{annual_debt_service_eur:,.0f} (₹ {annual_debt_service_inr / CRORE:,.2f} Cr)** by a factor of **{coverage_ratio:.2f}x**. The SLL structure de-risks the client's export business, making them a stronger credit.")
            
    with tab2:
        with st.container(border=True):
            st.subheader("Market Precedents & Instrument Types") # Capitalized
            st.markdown("Use these case studies to inform your deal structuring:")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("#### Sustainability-Linked")
                st.markdown(
                    """
                    - **Instrument:** Sustainability-Linked Loans (SLLs) or Bonds (SLBs).
                    - **Structure:** General corporate purpose loan, but the interest rate (coupon) is tied to meeting a specific KPI (e.g., tCO₂/tonne).
                    - **Precedent:** **Tata Steel & JSW Steel** have both used SLBs, linking financing cost directly to decarbonisation milestones.
                    - **Use Case:** Ideal for large, credible clients like this one, where the {slb_rate_discount_bps} bps incentive is meaningful.
                    """
                )
            with col2:
                st.markdown("#### Green Use-of-Proceeds")
                st.markdown(
                    """
                    - **Instrument:** Green Bonds or Green Loans.
                    - **Structure:** Funds are earmarked *only* for specific green projects (e.g., building a new solar farm, an EAF, or a CCUS plant).
                    - **Precedent:** **Hindalco** issued Green Bonds specifically to finance its renewable energy projects to power its smelters.
                    - **Use Case:** Best if this client needs funding for a single, large, clearly-defined "green" asset.
                    """
                )
            with col3:
                st.markdown("#### Blended & Policy Finance")
                st.markdown(
                    """
                    - **Instrument:** Blended Finance (First-Loss Guarantees) or Concessional Lines.
                    - **Structure:** Using public or multilateral (World Bank, SIDBI) money to de-risk private bank lending.
                    - **Precedent:** **World Bank's MSME programs** often use pooled guarantees for energy efficiency.
                    - **Use Case:** Ideal for smaller clients in the {sector} supply chain who can't access capital markets alone.
                    """
                )
    
    # REMOVED Banker AI Copilot Tab

    with tab3: # Renumbered from tab4
        with st.container(border=True):
            # This is a simple duplication of the Exporter tab 1, framed for the banker
            st.subheader("Client Risk Profile & Exposure") # Capitalized
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="kpi-card" style="height: auto; text-align: center; padding: 30px; border: 1px solid {border_color}; border-radius: 10px;">
                    <div class="kpi-label">Client Competitiveness Rating</div>
                    <div class="kpi-value {competitiveness_class}" style="font-size: 1.8rem;">{competitiveness}</div>
                    <div class="{competitiveness_class}" style="margin-top: 10px; color: {light_text};">
                        CBAM adds {cbam_hit_pct_of_price:.1f}% to client's per-tonne cost.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="kpi-card" style="height: auto;">
                    <div class="kpi-label">Client Intensity vs. Benchmark</div>
                    <div class="kpi-value">{user_intensity:.2f} tCO₂/t</div>
                    <div class="kpi-subtext">
                        vs. EU benchmark of: {eu_benchmark:.2f} tCO₂/t
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                <div class="kpi-card" style="height: auto; margin-top: 10px;">
                    <div class="kpi-label">Client CBAM Cost per Tonne</div>
                    <div class="kpi-value">€{cbam_cost_per_tonne_calc:,.2f}</div>
                    <div class="kpi-subtext">
                        (Approx. ₹ {cbam_cost_per_tonne_calc * EUR_to_INR_rate:,.0f})
                    </div>
                </div>
                """, unsafe_allow_html=True)

