# admin_app/app.py
import streamlit as st
import pandas as pd
import datetime
import gspread
import time
import json
from google.oauth2.service_account import Credentials

# ------------------------------
# CONFIG
# ------------------------------
page_bg = """
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("Artboard_itc.jpg"); /* Or use an online URL */
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}
[data-testid="stHeader"] {
    background: rgba(0,0,0,0); /* make header transparent */
</style>
"""
st.markdown(page_bg, unsafe_allow_html=True)

st.image("Capture d’écran 2025-10-31 112009.png", use_container_width=True)
st.set_page_config(page_title="ITC Club — Admin Dashboard", layout="wide")
st.title("🛠️ ITC Club — Admin Dashboard")
st.markdown("View submissions, filter, search and add notes.")

# ------------------------------
# Settings (same sheet id)
# ------------------------------
SHEET_ID = "1wpyHQf51TxG7mUM6MikyGBsz9maN471y1sO03BPOEUo"
# SHEET_ID = "1wpyHQf51TxG7mUM6MikyGBsz9maN471y1sO03BPOEUo" # itc sheet

CANONICAL_HEADERS = [
    "Name","Email","Department","Academic_Year","FB_Link","Discord_ID",
    "Domain_Interest","Areas","Programming_Languages","Self_Rate","Portfolio",
    "Tools","Domain_Extra","Why_Join","Motivation","Teamwork","Future_Goal",
    "Free_Time","Active_Events","How_Know_Us","Other_Team","Role","Team_Leader",
    "Extra","Score","Date"
]

# ------------------------------
# GSpread helper
# ------------------------------
def get_gspread_client():
    if "gcp_service_account" in st.secrets:
        info = st.secrets["gcp_service_account"]
        if isinstance(info, str):
            info = json.loads(info)
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    else:
        JSON_KEY_FILE = "last-f1197-42b004ea88d5 (1).json"
        creds = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

@st.cache_resource
def open_sheet():
    client = get_gspread_client()
    return client.open_by_key(SHEET_ID).sheet1

try:
    sheet = open_sheet()
except Exception as e:
    st.error("Could not connect to Google Sheets. Check credentials and sheet ID.")
    st.exception(e)
    st.stop()

# ------------------------------
# Admin password from secrets (fallback default)
# ------------------------------
ADMIN_PASSWORD = st.secrets.get("admin_password", "admin123")

pwd = st.text_input("Enter admin password:", type="password")
if pwd != ADMIN_PASSWORD:
    st.warning("Enter correct admin password to view submissions.")
    st.stop()

# ------------------------------
# Read data
# ------------------------------
try:
    raw = sheet.get_all_records()
    df = pd.DataFrame(raw)
    # ✅ Convert Score to numeric
    if "Score" in df.columns:
        df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0)
except Exception as e:
    st.error("Could not read data from Google Sheet.")
    st.exception(e)
    st.stop()

st.write(f"Total submissions: {len(df)}")

# ------------------------------
# Filters & search
# ------------------------------
col1, col2 = st.columns([1, 2])
with col1:
    domain_filter = st.multiselect("Filter by domain", options=sorted(df["Domain_Interest"].dropna().unique()) if "Domain_Interest" in df.columns else [])
    search = st.text_input("Search name or email")
with col2:
    st.metric("Average Score", round(df["Score"].mean(),2) if "Score" in df.columns and len(df) else "N/A")
    if "Domain_Interest" in df.columns:
        st.bar_chart(df["Domain_Interest"].value_counts())

df_shown = df.copy()
if domain_filter:
    df_shown = df_shown[df_shown["Domain_Interest"].isin(domain_filter)]
if search:
    mask = (df_shown.get("Name","").astype(str).str.contains(search, case=False, na=False)) | (df_shown.get("Email","").astype(str).str.contains(search, case=False, na=False))
    df_shown = df_shown[mask]

st.dataframe(df_shown, use_container_width=True)

# ------------------------------
# Download CSV
# ------------------------------
if not df.empty:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download submissions CSV", csv, "submissions.csv", "text/csv")

# ------------------------------
# Admin Notes (stored in second worksheet "admin_notes")
# ------------------------------
st.markdown("---")
st.subheader("📝 Notes for applicants (stored in sheet tab 'admin_notes')")
note_name = st.text_input("Applicant name (for note)")
note_text = st.text_area("Note text")
if st.button("Save Note"):
    try:
        try:
            notes_sheet = sheet.spreadsheet.worksheet("admin_notes")
        except gspread.WorksheetNotFound:
            notes_sheet = sheet.spreadsheet.add_worksheet(title="admin_notes", rows=1000, cols=5)
            notes_sheet.update("A1", [["Name","Note","Date"]])
        notes_sheet.append_row([note_name, note_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        st.success("Note saved.")
    except Exception as e:
        st.error(f"Could not save note: {e}")
