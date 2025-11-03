# form_app/app.py
import streamlit as st
import pandas as pd
import datetime
import yagmail
import gspread
import threading
import time
import datetime
import json
from google.oauth2.service_account import Credentials
import base64

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config(page_title="ITC Club — Application Form", layout="centered")

# Put your Logo file name in same folder or use a URL
st.image("IMG_20251102_204411_811.png", use_container_width=True,)

# st.markdown("""
# <style>
# [data-testid="stAppViewContainer"] {
#     background: linear-gradient(135deg, #e61707 10%, #03002e 70%);
#     color: white;
# }
# [data-testid="stHeader"] { background: rgba(0,0,0,0); }
# </style>
# """, unsafe_allow_html=True)

page_bg = """
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("Capture d’écran 2025-10-31 112009.png"); /* Or use an online URL */
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}
[data-testid="stHeader"] {
    background: rgba(0,0,0,0); /* make header transparent */
</style>
"""
# st.markdown(page_bg, unsafe_allow_html=True)

# Function to set background
def add_bg_from_local(image_file):
    """Add background image, transparent header, and dark form style."""
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>
        /* Background image */
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            color: white !important;
        }}

        /* Transparent header */
        [data-testid="stHeader"] {{
            background: rgba(0,0,0,0);
        }}

        /* Optional transparent sidebar */
        [data-testid="stSidebar"] > div:first-child {{
            background: rgba(0,0,0,0);
        }}

        /* Dark glass effect for form */
        div[data-testid="stForm"] {{
            background-color: rgba(0, 0, 0, 0.9);
            backdrop-filter: blur(10px);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            color: white !important;
        }}

        /* Ensure all text inside the form is white */
        div[data-testid="stForm"] * {{
            color: white !important;
        }}

        /* Make input boxes and selects readable */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select,
        .stTextArea textarea {{
            background-color: rgba(255,255,255,0.15);
            color: white !important;
            border: 1px solid rgba(255,255,255,0.3);
        }}

        /* Change placeholder color */
        ::placeholder {{
            color: rgba(255,255,255,0.7);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# 🖼️ Call it
add_bg_from_local("IMG.jpg")

# ------------------------------
# Settings - same sheet id as you provided
# ------------------------------
SHEET_ID = "1wpyHQf51TxG7mUM6MikyGBsz9maN471y1sO03BPOEUo"

CANONICAL_HEADERS = [
    # --- Basic Info ---
    "Name", "Email", "Phone","Student_ID", "Department", "Academic_Year",
    "FB_Link", "Discord_ID", "Date_Birth",

    # --- Domain Preferences ---
    "Domain_Interest_Order",

    # --- Tech Domain ---
    "Tech_Areas",
    "Tech_Programming_Languages",
    "Tech_Project_Desc",
    "Tech_Portfolio",
    "Tech_Tools",
    "Tech_Self_Rate",
    "Tech_Score",

    # --- Media Domain ---
    "Media_Areas",
    "Media_Tools",
    "Media_Freelance",
    "Media_Tasks",
    "Media_Editing_Tools",
    "Media_Equipment",
    "Media_Portfolio",
    "Media_Project_Desc",
    "Media_DesignRate",
    "Media_EditingRate",
    "Media_Score",

    # --- Sponsoring Domain ---
    "Sponsor_Areas",
    "Sponsor_Exp_Desc",
    "Sponsor_Event_Participation",
    "Sponsor_Connections",
    "Sponsor_Public_Speaking",
    "Sponsor_Represent_Club",
    "Sponsor_Comm_Rate",
    "Sponsor_Score",

    # --- Motivation & Availability ---
    "Why_Join",
    "Motivation",
    "Teamwork",
    "Future_Goal",
    "Free_Time",
    "Active_Events",
    "How_Know_Us",
    "Other_Club",
    "Role",
    "Team_Leader",
    "Extra",

    # --- Final Scoring & Meta ---
    "Total_Score",
    "Submission_Date"
]



# ------------------------------
# Helpers: GSpread client (secrets fallback)
# ------------------------------
def get_gspread_client():
    info = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        info, 
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    return client

@st.cache_resource
def open_sheet():
    client = get_gspread_client()
    return client.open_by_key(SHEET_ID).sheet1

try:
    sheet = open_sheet()
except Exception as e:
    st.error("Could not connect to Google Sheets — check credentials and SHEET_ID.")
    st.exception(e)
    st.stop()

# ensure header row exists and matches canonical headers
def ensure_headers():
    try:
        current = sheet.row_values(1)
        if current[:len(CANONICAL_HEADERS)] != CANONICAL_HEADERS:
            sheet.update("A1", [CANONICAL_HEADERS])
    except Exception as e:
        st.warning(f"Could not ensure headers: {e}")

ensure_headers()

# Append with retry
def append_row_with_retry(row, retries=3, backoff=0.4):
    last_exc = None
    for i in range(retries):
        try:
            sheet.append_row(row, value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            last_exc = e
            time.sleep(backoff * (i + 1))
    raise last_exc

# Set your global closing time (UTC or local)
CLOSING_TIME = datetime.datetime(2025, 11, 5, 23, 59)  # 

# Compute remaining time
now = datetime.datetime.now()
remaining = CLOSING_TIME - now
if remaining.total_seconds() > 0:
    # Convert to mm:ss
    mins, secs = divmod(int(remaining.total_seconds()), 60)
    hours, mins = divmod(mins, 60)
    days = remaining.days
        
    # ------------------------------
    # FORM UI
    # ------------------------------

    # Initialize page state
    if "page" not in st.session_state:
        st.session_state.page = "form"

    # Function to go to info page
    def go_to_info():
        st.session_state.page = "info"
    
    # --------------------------
    # PAGE 1: The Form
    # --------------------------
    if st.session_state.page == "form":
                
        st.title("🚀 ITC Club — Application Form")
        st.markdown("Please complete required fields. After submit the data is stored and you'll receive a confirmation email (if configured).")
        st.markdown("---")
        
        #st.markdown(
        #    f"### Time remaining: **{days} days, {hours:02d}:{mins:02d}:{secs:02d}**"
        #)

        # session duplicate prevention
        if "submitted" not in st.session_state:
            st.session_state.submitted = False

        st.markdown("""
            <style>
            /* Target Streamlit forms */
            div[data-testid="stForm"] {
                background-color: rgba(200, 200, 200, 0.2);
                backdrop-filter: blur(10px);
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
            }
            </style>
        """, unsafe_allow_html=True)

        with st.form("application_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("👤 Full Name *")
                email = st.text_input("📧 Email Address *")
                Phone = st.text_input("📞 Phone Number")
                department = st.text_input("🏫 Department")
                academic_year = st.selectbox("🎓 Academic Year", ["L1/ING1","L2/ING2","L3/ING3","M1/ING4","M2/ING5"])
            with col2:
                Student_id = st.text_input("🆔 Student ID")
                fb_link = st.text_input("🔗 Facebook Link")
                discord_id = st.text_input("💬 Discord ID")
                Date_Birth = st.text_input("📅 Date of Birth (DD/MM/YYYY)")
                st.caption("Fields marked * are required")
            
            st.markdown("---")

            st.subheader("📊 Domain Preference Order — Rank all three (no duplicates)")

            options = ["Tech", "Media", "Sponsor"]

            first = st.selectbox("1️⃣ First Choice", options, key="first_domain")
            second = st.selectbox("2️⃣ Second Choice", options, key="second_domain")
            third = st.selectbox("3️⃣ Third Choice", options, key="third_domain")
            st.info("Tip: choose three different domains — duplicates will be rejected on submit.")
        
            st.markdown("---")
        
            st.subheader("💻 Tech Domain")
            tech_areas = st.multiselect("💡 Which areas interest you?", ["Robotics","AI/ML","Security","Front-End","Back-End","Mobile","Game Dev","UI/UX"])
            tech_languages = st.multiselect("💻 Programming languages ", ["Python","C/C++","Java","JavaScript /TypeScript","C#","Dart (Flutter)","PHP","SQL","None yet, but I’m learning"])
            tech_project_desc = st.multiselect("🧠 Describe a project / competition / experience", ["Participated in national or international competitions","Designed (alone or in a team) the UI/UX of an app or website","Built a fully functional robot","Developed a responsive website","Trained an AI model","Created a game","Modeled or implemented a security system","Developed a fully functional mobile application","Created an original project or innovative solution", "Modified or improved existing ideas or systems", "Conduct practical experiments or hands-on technical tests occasionally","Not yet, but excited to start"])
            tech_portfolio = st.selectbox("🌐 Do you have a portfolio?", ["yes","no"])
            tech_tools = st.multiselect("🧰 Tools", ["Arduino / ESP32 / Raspberry Pi /sensors","Unity","Figma","Java","Git/GitHub","Linux","Database(SQL / MongoDB)","Docker/VM","VS Code / IntelliJ / PyCharm","APIs / Postman","Cloud Services (AWS, Firebase, etc.)","Flutter","No, but I’d like to try"])
            tech_self_rate = st.slider("Rate yourself (1–5)", 1, 5, 3)

            st.markdown("---")
            st.subheader("🎨 Design & Media Section")
            media_areas = st.multiselect("💡 Which design areas?", ["Graphic Design","UI UX","Illustration","Motion Graphics","3D Modeling"]) # 2 pts per selected (max 5) , max = 10 
            media_tools = st.multiselect("🎨 Which tools or software do you use?", ["Adobe Illustrator","Photoshop","Figma","Canva","InDesign","Other","None, but I’d like to learn"]) # 2	Tools/software used	Multiple choice	2 pts per selected (max 5)	10 , max = 10
            media_freelance_exp = st.selectbox("Have you worked as a freelancer or with a company before?", ["Yes","No","Not yet, but I’d like to"]) #Yes 10 / Want 3/ No 0
            media_tasks = st.multiselect("Which media tasks do you enjoy most? ", ["Photography","Videography","Video Editing","Script / Caption Writing","Social Media Management","Voice Recording / Narration","Acting"])# 3 pts per selected (max 6) , max = 18
            media_editing_tools = st.multiselect("Which tools do you use for editing?", ["Adobe Premiere Pro","CapCut","DaVinci Resolve","Adobe Audition","Audacity","None"]) # 2 pts per selected (max 6)
            media_deep_tools = st.multiselect("Have you ever explored or owned any of these tools/resources?", ["Camera","Smartphone with good camera","Microphone","Lighting Setup","Tripod / Stabilizer","SD cards / External storage","None"]) # 2 pt per selected (max 6)
            media_portfolio = st.selectbox("🌐 Do you have a portfolio ?", ["yes","no"],key=1)# 0
            media_project_desc = st.multiselect("🧠 Describe a media-related project or experience",["Participated in a design competition = 1pt", "Created a complete project (poster, logo, UI/UX, 3D model, etc.) = 2pt", "Designed for real events, clients, or organizations = 2pt", "Tried taking professional photos=1pt", "Created a short film or video project = 2pt", "Managed media coverage or promotional content = 1pt", "Made a marketing strategy / understand social media algorithms = 2pt", "Tried or currently doing content creation=1pt", "Good at voice acting or acting = 2pt"])
            media_designrate = st.slider("Rate experience (1–5)",1,5,3) # 12 / 24 / 36 / 48 / 510
            media_editingrate = st.slider("Rate your editing skills (1–5)",1,5,3) # 11 / 22 / 33 / 45 / 57

            st.markdown("---")
            st.subheader("💼 Sponsoring Domain")
            sponsor_areas = st.multiselect("💡 Which type of activities interest you? ", ["Searching for sponsors","Writing emails","Negotiation & Partnerships","Marketing and promotion","Communication and network","Other"]) # 1	Activities of interest	Multiple choice	8 pts per selected (max 5)	40
            sponsor_exp = st.multiselect("Do you have prior experience in any of these?", ["Contacting or negotiating with sponsors","Writing partnership proposals", "Managing event logistics (venue, materials, setup…)", "Communicating with partners or companies", "Handling budgets or sponsorship funds", "None"]) # 2ptc per choice (max 5) , if none = o
            sponsor_event_participation = st.selectbox("Have you ever participated in organizing an event or project?", ["Yes, many times","Yes, once or twice","No, but I'd like to learn"]) # None0 / Once4 / Many10
            sponsor_connections = st.selectbox("Do you have connections that could help find sponsors?", ["Yes","Maybe","No"]) # Yes10 / Maybe5 / No0
            sponsor_public_speaking = st.selectbox("Are you comfortable speaking or presenting in front of others?", ["Yes, confidently","Sometimes","Not really, but I’d like to get better","No, I prefer working behind the scenes"]) # No0 / Not really2 / Sometimes5 / Yes
            sponsor_represent_club = st.selectbox("Are you interested in representing the club externally (meetings, sponsors, events)?", ["Yes, definitely","Maybe","Not really"]) # Yes8 / Maybe4 / No0
            sponsor_comm_rate = st.slider("Rate your confidence in communication & negotiation",1,5,3) # 12 / 24 / 36 / 49 / 512

            st.markdown("---")
            st.subheader("Motivation & Availability")
            why_join = st.text_area("Why do you want to join the club? *")
            motivation = st.text_area("What motivates you? *")
            teamwork = st.text_area("Describe a teamwork experience")
            future_goal = st.text_area("What do you hope to learn this year?")
            free_time = st.text_input("Hours per week you can dedicate")
            active_events = st.selectbox("Ready to participate outside class?", ["Yes,often","Sometimes","Rarely"])
            how_know = st.selectbox("How did you hear about us?", ["Media","Friend","University","Other"])
            other_club = st.selectbox("Have you been part of other clubs?", ["No","Yes"])
            role = st.text_input("If yes, your role") 
            team_leader = st.selectbox("Leadership interest?", ["Yes, I’m interested","Maybe later","Not for now"])
            extra = st.text_area("Anything to add?")

            submitted = st.form_submit_button("✅ Submit My Application")

        # handle submit
        if submitted:
            if st.session_state.submitted:
                st.warning("You have already submitted this session. Refresh the page to submit again.")
            else:
                # basic validation
                if not (name and email and why_join and motivation):
                    st.error("Please fill required fields: Name, Email, Why join, Motivation.")
                else:
                    # prevent duplicate by email (check sheet)
                    try:
                        rows = sheet.get_all_records()
                        existing_emails = {
                            str(r.get("Email", "")).strip().lower()
                            for r in rows
                            if str(r.get("Email", "")).strip()
                        }
                        if email.strip().lower() in existing_emails:
                            st.warning("An application with this email already exists. If this is an error, contact the admin.")
                        else:

                            a = st.session_state.get("first_domain")
                            b = st.session_state.get("second_domain")
                            c = st.session_state.get("third_domain")

                            if len({a, b, c}) != 3:
                                st.error("Please make sure all three choices are different before submitting.")
                            else:
                                domain_order = [a, b, c]
                                st.session_state["domain_order"] = domain_order

                                # compute score (same logic as earlier; keep consistent)
                                def compute_domain_score(domain, dd):
                                    if domain == "Tech":
                                        # Areas: 3 pts per selected, max 8, max = 24
                                        s = min(len(dd.get("areas", [])), 8) * 3

                                        # Languages: 2 pts per selected, max 8, max = 16
                                        s += min(len(dd.get("languages", [])), 8) * 2

                                        # Project description: each 2 pts except special cases
                                        project_descs = dd.get("project_desc", [])
                                        project_pts = 0
                                        for p in project_descs:
                                            if p in [
                                                "Modified or improved existing ideas or systems",
                                                "Conduct practical experiments or hands-on technical tests occasionally",
                                            ]:
                                                project_pts += 1
                                            elif p == "Not yet, but excited to start":
                                                project_pts += 0
                                            else:
                                                project_pts += 2
                                        s += project_pts

                                        # Tools: 3 pts per selected, max 10, max = 30 (exclude "No, but I’d like to try")
                                        tools = dd.get("tools", [])
                                        tool_pts = sum(3 for t in tools if t != "No, but I’d like to try")
                                        s += min(tool_pts, 30)

                                        # Portfolio: always 0 pts
                                        s += 0

                                        # Self rate: scale 1→2 / 2→5 / 3→7 / 4→9 / 5→12
                                        s += {1: 2, 2: 5, 3: 7, 4: 9, 5: 12}.get(dd.get("self_rate", 3), 7)

                                        return s

                                    elif domain == "Media":
                                        s = 0

                                        # 🎨 Areas: 2 pts per selected (max 5), max = 10
                                        s += min(len(dd.get("areas", [])), 5) * 2

                                        # 🧰 Tools: 2 pts per selected (max 5), max = 10
                                        tools = dd.get("tools", [])
                                        tool_pts = sum(2 for t in tools if t != "None, but I’d like to learn")
                                        s += min(tool_pts, 10)

                                        # 💼 Freelance experience: Yes = 10 / Want = 3 / No = 0
                                        freelance_exp = dd.get("freelance_exp", "")
                                        if freelance_exp == "Yes":
                                            s += 10
                                        elif freelance_exp == "Not yet, but I’d like to":
                                            s += 3
                                        else:
                                            s += 0

                                        # 🎬 Media tasks: 3 pts per selected (max 6), max = 18
                                        s += min(len(dd.get("media_tasks", [])), 6) * 3

                                        # ✂️ Editing tools: 2 pts per selected (max 6), max = 12
                                        s += min(len(dd.get("editing_tools", [])), 6) * 2

                                        # 🎥 Deep tools: 2 pts per selected (max 6), max = 12
                                        s += min(len(dd.get("deep_tools", [])), 6) * 2

                                        # 🌐 Portfolio: 0 pts
                                        s += 0

                                        # 🧠 Media project desc — each has custom point value
                                        project_descs = dd.get("project_desc", [])
                                        project_pts = 0
                                        for p in project_descs:
                                            if "= 2pt" in p:
                                                project_pts += 2
                                            elif "= 1pt" in p:
                                                project_pts += 1
                                        s += project_pts

                                        # 🧑‍🎨 Design rate: 1→2 / 2→4 / 3→6 / 4→8 / 5→10
                                        s += {1: 2, 2: 4, 3: 6, 4: 8, 5: 10}.get(dd.get("designrate", 3), 6)

                                        # ✂️ Editing rate: 1→1 / 2→2 / 3→3 / 4→5 / 5→7
                                        s += {1: 1, 2: 2, 3: 3, 4: 5, 5: 7}.get(dd.get("editingrate", 3), 3)

                                        return s

                                    else:
                                        s = 0

                                        # 💡 Activities of interest: 8 pts per selected (max 5), max = 25
                                        s += min(len(dd.get("areas", [])), 5) * 5

                                        # 🧠 Experience: 2 pts per selected (max 5), 'None' = 0
                                        exp = dd.get("exp", [])
                                        if "None" in exp:
                                            s += 0
                                        else:
                                            s += min(len(exp), 5) * 5

                                        # 🎟️ Event participation: Many=10 / Once=4 / Want=0
                                        s += {
                                            "Yes, many times": 10,
                                            "Yes, once or twice": 4,
                                            "No, but I'd like to learn": 0,
                                        }.get(dd.get("event_participation"), 0)

                                        # 🤝 Connections: Yes=10 / Maybe=5 / No=0
                                        s += {
                                            "Yes": 10,
                                            "Maybe": 5,
                                            "No": 0,
                                        }.get(dd.get("connections"), 0)

                                        # 🎤 Public speaking: Yes=10 / Sometimes=5 / Not really=2 / No=0
                                        s += {
                                            "Yes, confidently": 10,
                                            "Sometimes": 5,
                                            "Not really, but I’d like to get better": 2,
                                            "No, I prefer working behind the scenes": 0,
                                        }.get(dd.get("public_speaking"), 0)

                                        # 🏛️ Represent club externally: Yes=8 / Maybe=4 / Not really=0
                                        s += {
                                            "Yes, definitely": 8,
                                            "Maybe": 4,
                                            "Not really": 0,
                                        }.get(dd.get("represent_club"), 0)

                                        # 💬 Communication & negotiation rate: 1→2 / 2→4 / 3→6 / 4→9 / 5→12
                                        s += {1: 2, 2: 4, 3: 6, 4: 9, 5: 12}.get(dd.get("comm_rate", 3), 6)

                                        return s


                                # 💻 TECH DOMAIN
                                tech_data = {
                                    "areas": tech_areas,
                                    "languages": tech_languages,
                                    "project_desc": tech_project_desc,
                                    "portfolio": tech_portfolio,
                                    "tools": tech_tools,
                                    "self_rate": tech_self_rate
                                }

                                # 🎨 DESIGN & MEDIA SECTION
                                media_data = {
                                    "areas": media_areas,
                                    "tools": media_tools,
                                    "freelance_exp": media_freelance_exp,
                                    "media_tasks": media_tasks,
                                    "editing_tools": media_editing_tools,
                                    "deep_tools": media_deep_tools,
                                    "portfolio": media_portfolio,
                                    "project_desc": media_project_desc,
                                    "designrate": media_designrate,
                                    "editingrate": media_editingrate
                                }

                                # 💼 SPONSORING DOMAIN
                                sponsor_data = {
                                    "areas": sponsor_areas,
                                    "exp_desc": sponsor_exp, 
                                    "event_participation": sponsor_event_participation,
                                    "connections": sponsor_connections,
                                    "public_speaking": sponsor_public_speaking,
                                    "represent_club": sponsor_represent_club,
                                    "comm_rate": sponsor_comm_rate
                                }

                                # --- Domain Weights Based on Order ---
                                weights = {}
                                if isinstance(domain_order, list):
                                    # Normalize domain names (capitalize first letter for matching)
                                    domain_order = [d.strip().capitalize() for d in domain_order]
                                else:
                                    domain_order = [d.strip().capitalize() for d in str(domain_order).split(",")]

                                # Default weight
                                weights = {d: 0 for d in ["Tech", "Media", "Sponsoring"]}

                                for i, d in enumerate(domain_order):
                                    if i == 0:
                                        weights[d] = 0.6
                                    elif i == 1:
                                        weights[d] = 0.25
                                    elif i == 2:
                                        weights[d] = 0.15

                                # --- Compute domain scores individually ---
                                domain_scores = {
                                    "Tech": compute_domain_score("Tech", tech_data),
                                    "Media": compute_domain_score("Media", media_data),
                                    "Sponsoring": compute_domain_score("Sponsoring", sponsor_data)
                                }

                                # --- Weighted total domain score ---
                                domain_score = (
                                    (domain_scores.get(domain_order[0], 0) * 0.6) +
                                    (domain_scores.get(domain_order[1], 0) * 0.25) +
                                    (domain_scores.get(domain_order[2], 0) * 0.15)
                                ) / 3

                                domain_score = round(domain_score, 2)

                                # ✅ Final total = only domain score (no motivation yet)
                                total_score = domain_score

                                # date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                # domain_extra = domain_data.get("project_desc","") or domain_data.get("exp_desc","") or ""

                                # build row
                                # Build the row to save in Google Sheet
                                row = [
                                    # --- Personal info ---
                                    name, email, Phone, Student_id, department, academic_year, fb_link,
                                    discord_id, Date_Birth, 

                                    # --- Domain order ---
                                    ", ".join(domain_order),

                                    # --- Tech domain ---
                                    ", ".join(tech_data["areas"]),
                                    ", ".join(tech_data["languages"]),
                                    ", ".join(tech_data["project_desc"]),
                                    ", ".join(tech_data["portfolio"]),
                                    ", ".join(tech_data["tools"]),
                                    tech_data["self_rate"],
                                    domain_scores["Tech"],  # individual Tech domain score

                                    # --- Media domain ---
                                    ", ".join(media_data["areas"]),
                                    ", ".join(media_data["tools"]),
                                    media_data["freelance_exp"],
                                    ", ".join(media_data["media_tasks"]),
                                    ", ".join(media_data["editing_tools"]),
                                    ", ".join(media_data["deep_tools"]),
                                    media_data["portfolio"],
                                    ", ".join(media_data["project_desc"]),
                                    media_data["designrate"],
                                    media_data["editingrate"],
                                    domain_scores["Media"],  # individual Media domain score

                                    # --- Sponsoring domain ---
                                    ", ".join(sponsor_data["areas"]),
                                    ", ".join(sponsor_data["exp_desc"]),
                                    sponsor_data["event_participation"],
                                    sponsor_data["connections"],
                                    sponsor_data["public_speaking"],
                                    sponsor_data["represent_club"],
                                    sponsor_data["comm_rate"],
                                    domain_scores["Sponsoring"],  # individual Sponsoring domain score

                                    # --- Motivation / other info (optional to keep) ---
                                    why_join, motivation, teamwork, future_goal, free_time,
                                    active_events, how_know, other_club, role, team_leader, extra,

                                    # --- Final total score ---
                                    total_score,

                                    # --- Timestamp ---
                                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                ]


                                # append with retry
                                try:
                                    append_row_with_retry(row)
                                    
                                    # st.balloons()
                                    st.session_state.submitted = True
                                    st.session_state.name = name
                                    st.session_state["selected_first_domain"] = domain_order[0]

                                    if domain_order[0] == "Tech":
                                        st.session_state["selected_first_domain_areas"] = tech_data["areas"]
                                    elif domain_order[0] == "Media":
                                        st.session_state["selected_first_domain_areas"] = media_data["areas"]
                                    elif domain_order[0] == "Sponsoring":
                                        st.session_state["selected_first_domain_areas"] = sponsor_data["areas"]
                                    
                                    st.success(f" one more Click to finish, {name}! 🎉")
                                    go_to_info()

                                except Exception as e:
                                    st.error(f"❌ Failed to save application: {e}")
                                
                    except Exception as e:
                        st.error(f"Unexpected error validating duplicates: {e}")
    # --------------------------
    # PAGE 2: Information Page
    # --------------------------
    elif st.session_state.page == "info":
        st.title("✅ Thank you for submitting!")

        st.success(f"Welcome {st.session_state.name} 👋")
        st.subheader("Here’s a summary of your top domain:")

        first_domain = st.session_state.get("selected_first_domain", "N/A")
        domain_areas = st.session_state.get("selected_first_domain_areas", [])

        areas_text = "\n".join([f"- {a}" for a in domain_areas]) if domain_areas else "No areas selected."

        st.info(f"**Your top domain:** {first_domain}\n\n**Selected areas:**\n{areas_text}")
        st.warning("📌 Please take a screenshot of your domain and criterias and bring it with you to the interview on the welcome day ,Thank you")
        # st.markdown(
        #     f"""
        #     <div style="
        #         border: 2px solid #4B9CD3;
        #         border-radius: 10px;
        #         padding: 15px;
        #         background-color: #F0F8FF;
        #         margin-top: 10px;
        #     ">
        #         <h4>📊 Summary of Your Top Domain</h4>
        #         <b>Your top domain:</b> {first_domain}<br><br>
        #         <b>Your selected areas:</b><br>
        #         {areas_text}
        #     </div>
        #     """,
        #     unsafe_allow_html=True
        # )

        st.button("⬅️ Back to Form", on_click=lambda: st.session_state.update(page="form"))
else:   
    # ------------------------------
    # TIMER EXPIRED — DISABLE FORM
    # ------------------------------
    st.error("⏰ The form is now closed. Deadline has passed.")
    st.stop()