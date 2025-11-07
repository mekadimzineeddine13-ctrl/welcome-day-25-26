import streamlit as st
import pandas as pd
import datetime
import gspread
import json
import time
from google.oauth2.service_account import Credentials

# ------------------------------
# PAGE CONFIG & STYLES
# ------------------------------
st.set_page_config(page_title="**ITC Club — Admin Dashboard**", layout="wide", page_icon="🛠️")
st.image("IMG_20251102_204411_811.png", use_container_width=True)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("Artboard_itc.jpg");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
         
}
[data-testid="stHeader"] {
    background: rgba(0,0,0,0);
}
section[data-testid="stSidebar"] {
    background-color: rgba(0, 0, 0, 0.4);
}
div[data-testid="stMetricValue"] {
    color: #FF4B4B !important;
    font-weight: 450 !important; 
             
}
.dataframe tbody tr:hover {
    background-color: rgba(0, 255, 255, 0.2) !important;
}
.stDataFrame {
    background-color: rgba(255,255,255,0.1);
    border-radius: 10px;
}
.big-title {
    font-size: 60px;
    font-weight: 950;
    text-align: center;
    color: #E40D0D;
}
.metric-card {
    padding: 1.5rem;
    background-color: rgba(0,0,0,0.3);
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🛠️ ITC Club — Admin Dashboard</div>', unsafe_allow_html=True)

# ------------------------------
# SHEET CONNECTION
# ------------------------------
SHEET_ID_form = "1wpyHQf51TxG7mUM6MikyGBsz9maN471y1sO03BPOEUo"
SHEET_ID_Reviews = "18uodDjMAL3_haYUwoBEbM1cNtvsQKIcldAjjZKnQJd8"

def get_gspread_client():
    try:
        info = st.secrets["gcp_service_account"]["key"]
        info = json.loads(info)
        creds = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Error creating GSpread client: {e}")
        st.stop()


# -------------------------------
# FORM SHEET (user responses)
# -------------------------------
@st.cache_resource
def open_form_sheet(sheet_id):
    client = get_gspread_client()
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Could not connect to Form Sheet: {e}")
        st.stop()
 
form_sheet = open_form_sheet(SHEET_ID_form)

# -------------------------------
# REVIEWS SHEET (admin evaluations)
# -------------------------------
@st.cache_resource
def open_reviews_sheet(sheet_id):
    client = get_gspread_client()
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Could not connect to Form Sheet: {e}")
        st.stop()
 
review_sheet = open_reviews_sheet(SHEET_ID_Reviews)

# ------------------------------
# ADMIN LOGIN
# ------------------------------
ADMIN_PASSWORD = st.secrets.get("admin_password", "abdesami3")

col1, col2 = st.columns([2, 1])
with col1:
    admin_name = st.text_input("👤 Enter your admin name")
with col2:
    pwd = st.text_input("🔒 Enter admin password", type="password")

if pwd != ADMIN_PASSWORD or not admin_name.strip():
    st.warning("Please enter the correct admin password and your name.")
    st.stop()

# ------------------------------
# LOAD DATA
# ------------------------------
df = pd.DataFrame(form_sheet.get_all_records())
if "Total_Score" in df.columns:
    df["Total_Score"] = pd.to_numeric(df["Total_Score"], errors="coerce").fillna(0)

# ------------------------------
# TABS
# ------------------------------
# Inject CSS to center tabs
st.markdown(
    """
    <style>
    div[data-baseweb="tab-list"] {
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)
tab1, tab2, tab3 = st.tabs(["📊 **Dashboard**", "📋 **Submissions**", "📝 **Review**"])

# ------------------------------
# 📊 DASHBOARD TAB
# ------------------------------
with tab1:
    st.subheader("Overview Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'><h3>👥 Total Applicants</h3><h1>{len(df)+1}</h1></div>", unsafe_allow_html=True)
    with col2:
        avg = round(df['Total_Score'].mean(), 2) if 'Total_Score' in df.columns else 0
        st.markdown(f"<div class='metric-card'><h3>⭐ Average Score</h3><h1>{avg}</h1></div>", unsafe_allow_html=True)
    with col3:
        if "Department" in df.columns:
            dept_count = df["Department"].nunique()
        else:
            dept_count = 0
        st.markdown(f"<div class='metric-card'><h3>🏛 Departments</h3><h1>{dept_count}</h1></div>", unsafe_allow_html=True)

    st.divider()
    if "Domain_Interest_Order" in df.columns:
        st.subheader("📈 Applicants per Domain")
        st.bar_chart(df["Domain_Interest_Order"].value_counts())

# ------------------------------
# 📋 SUBMISSIONS TAB
# ------------------------------
with tab2:
    st.subheader("All Submissions")
    col1, col2 = st.columns([2, 1])
    with col1:
        domain_filter = st.multiselect(
            "Filter by Domain",
            sorted(df["Domain_Interest_Order"].dropna().astype(str).unique()) if "Domain_Interest_Order" in df.columns else []
        )
        search = st.text_input("Search name or email")
    with col2:
        dept_filter = st.multiselect(
        "Filter by Department",
        sorted(df["Department"].dropna().astype(str).unique()) if "Department" in df.columns else []
    )

    df_filtered = df.copy()
    if domain_filter:
        df_filtered = df_filtered[df_filtered["Domain_Interest_Order"].isin(domain_filter)]
    if dept_filter:
        df_filtered = df_filtered[df_filtered["Department"].isin(dept_filter)]
    if search:
        mask = (
            df_filtered["Name"].astype(str).str.contains(search, case=False, na=False)
            | df_filtered["Email"].astype(str).str.contains(search, case=False, na=False)
        )
        df_filtered = df_filtered[mask]

    st.dataframe(df_filtered, use_container_width=True, height=500)

    if not df_filtered.empty:
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "submissions.csv", "text/csv")

# ------------------------------
# 📝 REVIEW TAB
# ------------------------------
with tab3:
    st.subheader("Review and Add Notes")

    candidate = st.selectbox("Select Candidate", options=df["Name"].unique() if "Name" in df.columns else [])
    if candidate:
        row = df[df["Name"] == candidate].iloc[0]

        # --- Get existing data from form sheet ---
        tech_score = float(row.get("Tech_Score", 0))
        media_score = float(row.get("Media_Score", 0))
        sponsor_score = float(row.get("Sponsor_Score", 0))
        total_score = float(row.get("Total_Score", 0))
        final_score_of_domains = total_score * 3 + 2
        domain_order = row.get("Domain_Interest_Order", "N/A")

        # --- Display student info summary ---
        st.markdown("### 👤 Candidate Information")
        c1, c2, c3 = st.columns(3)
        c1.metric("💻 **Tech Score**", tech_score)
        c2.metric("🎨 **Media Score**", media_score)
        c3.metric("💰 **Sponsor Score**", sponsor_score)
        st.metric("🧩 Final Score of Domains",  round(final_score_of_domains, 2))
        st.markdown(f"**Domain Order:** {domain_order}")

        st.divider()

        if st.button("📄 View Full Candidate Info "):
            st.write("### Candidate Info")
            st.json(row.to_dict())
        
        st.divider()

        st.markdown("### ✍️ Add Review")
        note = st.text_area("🗒️ Note / Feedback", placeholder="Write your observations here...")
        motivation_score = st.slider("🔥 Motivation Score", 0, 100, 10)
        skills_score = st.slider("🧠 Skills Score", 0, 100, 10)
        
        
        computed_total = final_score_of_domains # Default value
        
        if st.button("### Calculate Final Total Score"):
            computed_total = round(((final_score_of_domains + skills_score) / 2) * 0.6 + (motivation_score * 0.4), 2)

        st.markdown("### 📈 Evaluation Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("🎯 **Domain Avg**", round(final_score_of_domains, 2))
        col2.metric("💪 **Motivation**", motivation_score)
        col3.metric("✅ **Final Total**", round(computed_total, 2))

        if st.button("💾 Save Review"):
            try:
                client = get_gspread_client()
                try:
                    review_sheet = client.open_by_key(SHEET_ID_Reviews).worksheet("Admin_Reviews")
                except:
                    # Create sheet if missing
                    review_sheet = client.open_by_key(SHEET_ID_Reviews).add_worksheet("Admin_Reviews", rows=1000, cols=12)
                    review_sheet.append_row([
                        "Admin_Name", "Student_Name", "Tech_Score", "Media_Score",
                        "Sponsor_Score", "Domain_Order", "Final_Score_of_Domains",
                        "Motivation_Score", "Skills_Score", "Computed_Total",
                        "Note", "Date"
                    ])
                
                date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                review_data = [
                    admin_name, candidate, tech_score, media_score, sponsor_score,
                    domain_order, final_score_of_domains, motivation_score, skills_score,
                    computed_total, note, date_now
                ]

                review_sheet.append_row(review_data)

                st.success(f"✅ Review saved successfully for {candidate}")

            except Exception as e:
                st.error(f"⚠️ Error saving review: {e}")
