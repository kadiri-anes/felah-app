import streamlit as st
import pandas as pd
import qrcode
import random
import html
import hashlib
from datetime import date
from io import BytesIO
from st_supabase_connection import SupabaseConnection
import folium
from streamlit_folium import st_folium

# ---------------------------------------------------------
# Security & Helper Functions
# ---------------------------------------------------------
def sanitize(text: str) -> str:
    """Sanitize user input to prevent XSS attacks."""
    if not isinstance(text, str):
        return str(text)
    return html.escape(text.strip())

def hash_password(password: str) -> str:
    """Hash password using SHA-256 for local checks."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_admin_password() -> str:
    return st.secrets.get("ADMIN_PASSWORD", "greatdz")

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="بوابة الفلاح - 48 ولاية",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# CSS Styling (RTL Layout, Centering & Modern Theme)
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* Full Page RTL Layout */
    html, body, [class*="css"], .stApp {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .main, [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }

    /* Top Main Title (Upper Centered Area) */
    .centered-main-title {
        text-align: center;
        color: #1A1A1A;
        font-size: 34px;
        font-weight: 800;
        margin-top: -30px;
        margin-bottom: 25px;
    }

    /* Central Green Banner Header */
    .header-banner {
        background: linear-gradient(135deg, #0d5c3a 0%, #157a4f 100%);
        color: white;
        padding: 25px 15px;
        border-radius: 14px;
        text-align: center;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.15);
        margin-bottom: 25px;
    }
    .header-banner h2 {
        margin: 0;
        font-size: 28px;
        font-weight: 700;
        color: #FFFFFF !important;
    }
    .header-banner p {
        margin-top: 10px;
        margin-bottom: 0;
        font-size: 15px;
        opacity: 0.95;
    }

    /* Red Primary Highlight Button (for QR Service) */
    div.stButton > button[kind="primary"] {
        background-color: #ff4d4d !important;
        border-color: #ff4d4d !important;
        color: white !important;
        font-weight: bold;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #e63939 !important;
        border-color: #e63939 !important;
    }

    /* Standard Grid & Service Buttons */
    div.stButton > button {
        border-radius: 8px;
        padding: 12px 10px;
        font-size: 15px;
        font-weight: 600;
        border: 1px solid #E0E0E0;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.03);
    }

    /* Cards and Notifications */
    .mobile-sidebar-notice {
        background-color: #e6f4ea;
        border: 2px dashed #0b8a62;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 12px;
        font-weight: bold;
        color: #0b8a62;
    }
    .news-card {
        background-color: #ffffff;
        border-left: 5px solid #0b8a62;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }

    /* Dark Mode Overrides */
    @media (prefers-color-scheme: dark) {
        .stApp { background-color: #12181f !important; color: #e2e8f0 !important; }
        .mobile-sidebar-notice { background-color: #1a3328 !important; border-color: #0b8a62 !important; color: #6ee7b7 !important; }
        .news-card { background-color: #1e2631 !important; border-color: #0b8a62 !important; color: #f1f5f9 !important; }
        .news-card p, .news-card h4 { color: #e2e8f0 !important; }
        .centered-main-title { color: #ffffff !important; }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Database Client Initializer
# ---------------------------------------------------------
try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["SUPABASE_URL"],
        key=st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    )
except Exception:
    conn = st.connection("supabase", type=SupabaseConnection)

supabase_client = conn.client

# ---------------------------------------------------------
# PRESET DATA & CONSTANTS
# ---------------------------------------------------------
DEFAULT_AGRI_LOCATIONS = [
    {"name": "Wholesale Market (EPLFM MAGRO)", "wilaya": "16 - Alger", "category": "Wholesale Produce Market", "lat": 36.7323, "lon": 3.1678, "maps_link": "https://maps.google.com/?q=36.7323,3.1678"},
    {"name": "CCLS Silo & Grain Point", "wilaya": "19 - Sétif", "category": "OAIC Cereal Silo (CCLS)", "lat": 36.1911, "lon": 5.4137, "maps_link": "https://maps.google.com/?q=36.1911,5.4137"},
    {"name": "Asmidal Fertilizer Depot", "wilaya": "23 - Annaba", "category": "ASMIDAL Fertilizer Depot", "lat": 36.9000, "lon": 7.7667, "maps_link": "https://maps.google.com/?q=36.9000,7.7667"},
    {"name": "Wholesale Market (Attaf)", "wilaya": "44 - Aïn Defla", "category": "Wholesale Produce Market", "lat": 36.2238, "lon": 1.9682, "maps_link": "https://maps.google.com/?q=36.2238,1.9682"},
    {"name": "CCLS Cereal Storage Depot", "wilaya": "14 - Tiaret", "category": "OAIC Cereal Silo (CCLS)", "lat": 35.3710, "lon": 1.3169, "maps_link": "https://maps.google.com/?q=35.3710,1.3169"},
    {"name": "Wholesale Dates Market", "wilaya": "07 - Biskra", "category": "Wholesale Produce Market", "lat": 34.8502, "lon": 5.7281, "maps_link": "https://maps.google.com/?q=34.8502,5.7281"}
]

WILAYAS_48 = [
    "01 - Adrar", "02 - Chlef", "03 - Laghouat", "04 - Oum El Bouaghi", "05 - Batna", 
    "06 - Béjaïa", "07 - Biskra", "08 - Béchar", "09 - Blida", "10 - Bouira", 
    "11 - Tamanrasset", "12 - Tébessa", "13 - Tlemcen", "14 - Tiaret", "15 - Tizi Ouzou", 
    "16 - Alger", "17 - Djelfa", "18 - Jijel", "19 - Sétif", "20 - Saïda", 
    "21 - Skikda", "22 - Sidi Bel Abbès", "23 - Annaba", "24 - Guelma", "25 - Constantine", 
    "26 - Médéa", "27 - Mostaganem", "28 - M'Sila", "29 - Mascara", "30 - Ouargla", 
    "31 - Oran", "32 - El Bayadh", "33 - Illizi", "34 - Bordj Bou Arréridj", "35 - Boumerdès", 
    "36 - El Tarf", "37 - Tindouf", "38 - Tissemsilt", "39 - El Oued", "40 - Khenchela", 
    "41 - Souk Ahras", "42 - Tipaza", "43 - Mila", "44 - Aïn Defla", "45 - Naâma", 
    "46 - Aïn Témouchent", "47 - Ghardaïa", "48 - Relizane"
]

VEGETABLE_LIMITS = {
    "Potato (بطاطس)": 1700.0, "Tomato (طماطم)": 1000.0, "Pepper (فلفل)": 800.0,
    "Carrot (جزر)": 700.0, "Onion (بصل)": 650.0, "Garlic (ثوم)": 600.0,
    "Wheat / Cereal (قمح)": 400.0, "Beans (فاصولياء)": 400.0, "Lettuce (خس)": 300.0, "Cucumber (خيار)": 200.0
}

FRUIT_LIST = [
    "Dates Deglet Nour (تمور دقلة نور)", "Citrus / Oranges (حمضيات / برتقال)",
    "Apples (تفاح)", "Grapes (عنب)", "Olives (زيتون)", "Figs (تين)", "Watermelon / Melon (بطيخ)"
]

SUPPORT_SECTORS = {
    "Geomembrane Water Basin (حوض الجيو-ممبران)": ["Fellah Card (بطاقة الفلاح)", "Land Ownership or Lease Contract (عقد الملكية أو الامتياز)", "Technical Study / Supplier Proforma Invoice (دراسة تقنية / فاتورة شكلية)"],
    "Well & Water Drilling (حفر الآبار الفلاحية)": ["Fellah Card (بطاقة الفلاح)", "Water Drilling Authorization Permit (رخصة حفر البئر من الموارد المائية)", "Land Title / Lease Agreement (عقد الملكية أو الامتياز)"],
    "Modern Drip/Sprinkler Irrigation (أنظمة الري الحديثة)": ["Fellah Card (بطاقة الفلاح)", "Proforma Invoice for Equipment (فاتورة شكلية للعتاد)", "Land Topography Plan (مخطط طبوغرافي للأرض)"],
    "Solar Energy for Agricultural Pumps (الطاقة الشمسية للمزارع)": ["Fellah Card (بطاقة الفلاح)", "Solar Installation Technical Quote (عرض سعر للنظام الشمسي)", "Well Authorization / Water Source Proof (اثبات وجود مورد مائي)"],
    "Tractors & Farm Machinery (الجرارات والعتاد الفلاحي)": ["Fellah Card (بطاقة الفلاح)", "Proforma Invoice from Certified Dealer (فاتورة شكلية من موزع معتمد)", "Exploitation Certificate (شهادة استغلال فلاحي)"]
}

ALERT_STYLES = {
    "yellow": {"bg_color": "#fff9c4", "border_color": "#fbc02d", "text_color": "#574200", "icon": "⚠️"},
    "orange": {"bg_color": "#ffe0b2", "border_color": "#f57c00", "text_color": "#4a2400", "icon": "🍊"},
    "red": {"bg_color": "#ffcdd2", "border_color": "#d32f2f", "text_color": "#490c0c", "icon": "🚨"}
}

def get_current_crop_area(crop_name: str) -> float:
    try:
        res = supabase_client.table("declarations").select("area").eq("crop", crop_name).execute()
        if res and res.data:
            return sum(item["area"] for item in res.data if item.get("area") is not None)
    except Exception:
        return 0.0
    return 0.0

def get_unread_notif_count(email: str) -> int:
    if not email:
        return 0
    try:
        res = supabase_client.table("farmer_notifications").select("id").eq("farmer_email", email).eq("is_read", False).execute()
        return len(res.data) if res and res.data else 0
    except Exception:
        return 0

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if 'lang' not in st.session_state: st.session_state.lang = 'AR'
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'farmer_name' not in st.session_state: st.session_state.farmer_name = ""
if 'farmer_email' not in st.session_state: st.session_state.farmer_email = ""
if 'carte_num' not in st.session_state: st.session_state.carte_num = ""
if 'current_page' not in st.session_state: st.session_state.current_page = "home"
if 'selected_service' not in st.session_state: st.session_state.selected_service = None

if 'captcha_num1' not in st.session_state: st.session_state.captcha_num1 = random.randint(1, 9)
if 'captcha_num2' not in st.session_state: st.session_state.captcha_num2 = random.randint(1, 9)

# ---------------------------------------------------------
# SIDEBAR ( القائمة / Language / Account )
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ القائمة / MENU")
    
    st.markdown("#### 🌐 Language / اللغة")
    lang_choice = st.radio(
        label="Language",
        options=["العربية", "English"],
        index=0 if st.session_state.lang == 'AR' else 1,
        label_visibility="collapsed"
    )
    st.session_state.lang = 'AR' if lang_choice == "العربية" else 'EN'
    
    st.markdown("---")
    
    st.markdown("#### 👤 تسجيل الدخول / Account")
    if not st.session_state.logged_in:
        auth_action = st.radio(
            label="Action:",
            options=["Log In (دخول)", "Register (إنشاء حساب)", "Forgot Password (نسيان كلمة السر)"],
            index=0
        )
        
        if "Log In" in auth_action:
            login_email = st.text_input("البريد الإلكتروني / Email", placeholder="example@domain.com")
            login_pass = st.text_input("كلمة السر / Password", type="password")
            
            n1 = st.session_state.captcha_num1
            n2 = st.session_state.captcha_num2
            correct_sum = n1 + n2
            st.markdown(f"**🤖 Human Verification:** What is `{n1} + {n2}`?")
            user_captcha = st.number_input("Solve math challenge:", min_value=0, max_value=20, step=1, value=0)
            
            if st.button("تأكيد / Submit", use_container_width=True, type="secondary"):
                if user_captcha != correct_sum:
                    st.error("❌ CAPTCHA Error")
                    st.session_state.captcha_num1 = random.randint(1, 9)
                    st.session_state.captcha_num2 = random.randint(1, 9)
                elif login_email and login_pass:
                    try:
                        auth_res = supabase_client.auth.sign_in_with_password({
                            "email": login_email.strip(),
                            "password": login_pass
                        })
                        if auth_res.user:
                            user_id = auth_res.user.id
                            res = supabase_client.table("farmer_profiles").select("*").eq("id", user_id).execute()
                            if res and res.data:
                                profile = res.data[0]
                                st.session_state.logged_in = True
                                st.session_state.farmer_name = profile.get("full_name", "Farmer")
                                st.session_state.farmer_email = profile.get("email", login_email.strip())
                                st.session_state.carte_num = profile.get("carte_num", "N/A")
                                st.success("تم تسجيل الدخول بنجاح")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")

        elif "Register" in auth_action:
            reg_name = st.text_input("Full Name / الاسم الكامل")
            reg_email = st.text_input("Email / البريد الإلكتروني")
            reg_card = st.text_input("Carte Fellah N°", placeholder="DZ-2026-XXXXX")
            reg_pass = st.text_input("Create Password", type="password")
            
            if st.button("Register Account", use_container_width=True):
                if reg_name and reg_email and reg_card and reg_pass:
                    try:
                        clean_email = sanitize(reg_email)
                        clean_name = sanitize(reg_name)
                        clean_card = sanitize(reg_card)
                        auth_response = supabase_client.auth.sign_up({"email": clean_email, "password": reg_pass})
                        if auth_response.user:
                            supabase_client.table("farmer_profiles").insert({
                                "id": auth_response.user.id, "email": clean_email, "full_name": clean_name, "carte_num": clean_card
                            }).execute()
                            st.success("Registration completed! Please log in.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            rec_email = st.text_input("Enter registered email:")
            if st.button("Send Recovery Link", use_container_width=True):
                if rec_email:
                    try:
                        supabase_client.auth.reset_password_for_email(rec_email.strip())
                        st.success("Recovery link sent!")
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.success(f"🟢 Connected:\n**{st.session_state.farmer_name}**")
        st.caption(f"Card N°: `{st.session_state.carte_num}`")
        if st.button("🔒 Log Out / خروج", use_container_width=True):
            try:
                supabase_client.auth.sign_out()
            except Exception:
                pass
            st.session_state.logged_in = False
            st.session_state.farmer_name = ""
            st.session_state.farmer_email = ""
            st.session_state.carte_num = ""
            st.rerun()

# ---------------------------------------------------------
# MAIN CONTENT AREA
# ---------------------------------------------------------

# 1. UPPER CENTERING: Main Page Title
st.markdown("<div class='centered-main-title'>بوابة الفلاح - 48 ولاية</div>", unsafe_allow_html=True)

# 2. CENTERED BANNER: Program Banner Header
st.markdown("""
    <div class="header-banner">
        <h2>برنامج التخطيط والتنسيق الفلاحي 2026</h2>
        <p>الجمهورية الجزائرية الديمقراطية الشعبية - وزارة الفلاحة والتنمية الريفية</p>
    </div>
""", unsafe_allow_html=True)

# 3. CENTERED NAVIGATION BUTTONS
nav_margin_left, nav_col1, nav_col2, nav_col3, nav_margin_right = st.columns([1.5, 2, 2, 2.5, 1.5])

with nav_col1:
    if st.button("🏠 الرئيسية", use_container_width=True):
        st.session_state.current_page = "home"
        st.session_state.selected_service = None

with nav_col2:
    if st.button("💳 بطاقاتي", use_container_width=True):
        st.session_state.current_page = "cards"

with nav_col3:
    if st.button("👨‍🌾 حسابي وسجلاتي", use_container_width=True):
        st.session_state.current_page = "account_records"

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PAGE ROUTING
# ---------------------------------------------------------

# --- PAGE 1: HOME & SERVICES ---
if st.session_state.current_page == "home":
    if st.session_state.selected_service is None:
        st.markdown("<h2 style='text-align: center; font-size: 26px; margin-bottom: 25px;'>الخدمات الإلكترونية / Main Services</h2>", unsafe_allow_html=True)

        # Row 1
        col_r1_1, col_r1_2 = st.columns(2)
        with col_r1_1:
            if st.button("الأخبار والإعلانات الرسمية", use_container_width=True, key="btn_news"):
                st.session_state.selected_service = "news"
                st.rerun()
        with col_r1_2:
            if st.button("نصائح الزراعة والتصريح (QR)", use_container_width=True, type="primary", key="btn_qr"):
                st.session_state.selected_service = "crop"
                st.rerun()

        # Row 2
        col_r2_1, col_r2_2 = st.columns(2)
        with col_r2_1:
            if st.button("الأحوال الجوية والتنبيهات", use_container_width=True, key="btn_weather"):
                st.session_state.selected_service = "weather"
                st.rerun()
        with col_r2_2:
            if st.button("طلب دعم الدولة (الدعم الفلاحي)", use_container_width=True, key="btn_support"):
                st.session_state.selected_service = "support"
                st.rerun()

        # Row 3
        col_r3_1, col_r3_2 = st.columns(2)
        with col_r3_1:
            if st.button("خريطة أسوق الجملة، نقاط CCLS والأسمدة", use_container_width=True, key="btn_map"):
                st.session_state.selected_service = "suppliers"
                st.rerun()
        with col_r3_2:
            if st.button("تجديد بطاقة الفلاح (الذهبية/CIB)", use_container_width=True, key="btn_renew"):
                st.session_state.selected_service = "pay"
                st.rerun()

    else:
        # Inline Back Button
        if st.button("🔙 العودة / Back"):
            st.session_state.selected_service = None
            st.rerun()

        # SERVICE VIEW: CROP DECLARATION & QR PERMIT
        if st.session_state.selected_service == "crop":
            st.subheader("نصائح الزراعة والتصريح (QR)")
            selected_w = st.selectbox("Wilaya / الولاية", WILAYAS_48)
            cat_choice = st.radio("Category / الصنف:", ["Vegetables (خضروات)", "Fruits (فواكه)"])
            area_ha = st.number_input("Farming Area (Hectares)", min_value=0.1, value=5.0, max_value=10000.0)
            start_date = st.date_input("Cultivation Date", value=date.today())
            
            if cat_choice == "Fruits (فواكه)":
                selected_c = st.selectbox("Select Fruit", FRUIT_LIST)
                st.success("Unlimited Capacity — Fruit cultivation has no national area restrictions.")
            else:
                selected_c = st.selectbox("Select Vegetable", list(VEGETABLE_LIMITS.keys()))
                limit = VEGETABLE_LIMITS[selected_c]
                current_total = get_current_crop_area(selected_c)
                percentage = min(((current_total + area_ha) / limit), 1.0)
                st.write(f"**National Area Quota Status ({selected_c}):**")
                st.progress(percentage)
                st.caption(f"Registered: {current_total:.1f} Ha | Your Input: {area_ha:.1f} Ha | Limit: {limit:.0f} Ha")

            if st.button("Submit & Generate QR Permit", type="primary"):
                if st.session_state.logged_in:
                    try:
                        supabase_client.table("declarations").insert({
                            "farmer_name": st.session_state.farmer_name,
                            "carte_num": st.session_state.carte_num,
                            "wilaya": selected_w,
                            "category": cat_choice,
                            "crop": selected_c,
                            "area": area_ha,
                            "start_date": str(start_date)
                        }).execute()
                        st.success("Declaration registered successfully!")
                        qr_payload = f"FELAH-PERMIT|{st.session_state.farmer_name}|{st.session_state.carte_num}|{selected_w}|{selected_c}|{area_ha}HA"
                        qr = qrcode.make(qr_payload)
                        buf = BytesIO()
                        qr.save(buf, format="PNG")
                        st.image(buf.getvalue(), caption="Official QR Permit", width=200)
                    except Exception as e:
                        st.error(f"Failed to record declaration: {e}")
                else:
                    st.warning("Please log in first from sidebar.")

        # SERVICE VIEW: SUPPORT REQUEST
        elif st.session_state.selected_service == "support":
            st.subheader("طلب دعم الدولة (الدعم الفلاحي)")
            if not st.session_state.logged_in:
                st.warning("⚠️ Please log in from the left menu ↗ to submit a support demand.")
            else:
                selected_w_sup = st.selectbox("Wilaya / الولاية", WILAYAS_48)
                selected_sector = st.selectbox("Select Subsidized Sector", list(SUPPORT_SECTORS.keys()))
                
                st.markdown(f"#### Required Documents for `{selected_sector}`:")
                req_docs = SUPPORT_SECTORS[selected_sector]
                for doc in req_docs:
                    st.write(f"• **{doc}**")
                
                uploaded_files = {}
                for idx, doc in enumerate(req_docs):
                    up_file = st.file_uploader(f"Upload: {doc}", type=["pdf", "jpg", "jpeg", "png"], key=f"file_{idx}")
                    if up_file:
                        uploaded_files[doc] = up_file
                
                additional_notes = st.text_area("Additional Notes / ملاحظات إضافية")

                if st.button("Submit Support Demand", type="primary", use_container_width=True):
                    if len(uploaded_files) < len(req_docs):
                        st.error(f"Please upload all {len(req_docs)} required documents.")
                    else:
                        try:
                            with st.spinner("Uploading documents..."):
                                uploaded_links = {}
                                for doc_name, file_obj in uploaded_files.items():
                                    clean_filename = f"{st.session_state.carte_num}_{random.randint(1000,9999)}_{file_obj.name}"
                                    file_path = f"support_docs/{clean_filename}"
                                    supabase_client.storage.from_("agricultural-docs").upload(file_path, file_obj.read())
                                    public_url = f"{st.secrets['connections']['supabase']['SUPABASE_URL']}/storage/v1/object/public/agricultural-docs/{file_path}"
                                    uploaded_links[doc_name] = public_url

                                supabase_client.table("support_requests").insert({
                                    "farmer_name": st.session_state.farmer_name,
                                    "carte_num": st.session_state.carte_num,
                                    "wilaya": selected_w_sup,
                                    "sector": selected_sector,
                                    "description": sanitize(additional_notes),
                                    "files_json": uploaded_links
                                }).execute()

                                st.success("🎉 Support demand submitted successfully!")
                        except Exception as e:
                            st.error(f"Error submitting request: {e}")

        # SERVICE VIEW: NEWS
        elif st.session_state.selected_service == "news":
            st.subheader("الأخبار والإعلانات الرسمية")
            try:
                res_news = supabase_client.table("portal_news").select("*").order("id", desc=True).execute()
                news_items = res_news.data if res_news.data else []
            except Exception:
                news_items = []

            if news_items:
                for n in news_items:
                    st.markdown(f"""
                        <div class="news-card">
                            <span style="background: #0b8a62; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8em;">{sanitize(n.get("category",""))}</span>
                            <h4 style="margin: 8px 0 5px 0;">📢 {sanitize(n.get("title",""))}</h4>
                            <p style="margin: 0;">{sanitize(n.get("content",""))}</p>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📰 No official news releases published today.")

        # SERVICE VIEW: WEATHER
        elif st.session_state.selected_service == "weather":
            st.subheader("الأحوال الجوية والتنبيهات")
            try:
                res = supabase_client.table("weather_alerts").select("*").order("id", desc=True).execute()
                alerts = res.data if res.data else []
            except Exception: 
                alerts = []
            
            if alerts:
                for item in alerts:
                    style = ALERT_STYLES.get(str(item.get("severity", "yellow")).lower(), ALERT_STYLES["yellow"])
                    st.markdown(f"""
                        <div style="background-color: {style['bg_color']}; border-left: 6px solid {style['border_color']}; border-radius: 8px; padding: 14px; margin-bottom: 12px; color: {style['text_color']};">
                            <b>{style['icon']} {sanitize(item.get('title',''))}</b> — ({sanitize(item.get('region',''))})
                            <p style="margin:4px 0 0 0;">{sanitize(item.get('message',''))}</p>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("🟢 No severe weather warnings active across the 48 wilayas.")

        # SERVICE VIEW: PAYMENTS / RENEWAL
        elif st.session_state.selected_service == "pay":
            st.subheader("تجديد بطاقة الفلاح (الذهبية/CIB)")
            st.write("Annual Subscription Fee: **2,500 DZD**")
            st.radio("Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"])
            st.text_input("Card Number:", placeholder="6037 XXXX XXXX XXXX")
            if st.button("Confirm Payment", type="primary"): 
                st.success("Carte Fellah renewed for season 2026/2027!")

        # SERVICE VIEW: SUPPLIERS & MAPS
        elif st.session_state.selected_service == "suppliers":
            st.subheader("خريطة أسوق الجملة، نقاط CCLS والأسمدة")
            try:
                res = supabase_client.table("suppliers_directory").select("*").execute()
                db_locations = res.data if res.data else []
            except Exception:
                db_locations = []
                
            all_locations = DEFAULT_AGRI_LOCATIONS + db_locations
            selected_cat = st.selectbox("Filter Points by Type:", ["All", "Wholesale Produce Market", "OAIC Cereal Silo (CCLS)", "ASMIDAL Fertilizer Depot"])
            filtered_locs = all_locations if selected_cat == "All" else [loc for loc in all_locations if loc.get("category") == selected_cat]

            m = folium.Map(location=[34.5000, 3.2000], zoom_start=6)
            color_map = {"Wholesale Produce Market": "green", "OAIC Cereal Silo (CCLS)": "cadetblue", "ASMIDAL Fertilizer Depot": "orange"}

            for loc in filtered_locs:
                lat, lon = float(loc.get("lat", 36.7323)), float(loc.get("lon", 3.1678))
                name, cat = loc.get("name", "Point"), loc.get("category", "")
                maps_url = loc.get("maps_link", f"https://maps.google.com/?q={lat},{lon}")

                popup_html = f"<b>{name}</b><br><small>{cat}</small><br><a href='{maps_url}' target='_blank'>Open Maps</a>"
                folium.Marker(location=[lat, lon], popup=folium.Popup(popup_html, max_width=200), icon=folium.Icon(color=color_map.get(cat, "blue"))).add_to(m)

            st_folium(m, width=700, height=450)

# --- PAGE 2: CARTE FELLAH ---
elif st.session_state.current_page == "cards":
    st.subheader("💳 بطاقتي الفلاحية الرقمية / Digital Carte Fellah")
    if st.session_state.logged_in:
        st.markdown(f"""
            <div style="border: 2px solid #0b8a62; border-radius: 15px; padding: 20px; background-color: #f9fbf9;">
                <h3 style="color: #0b8a62; margin-top:0;">الجمهورية الجزائرية الديمقراطية الشعبية</h3>
                <p><b>وزارة الفلاحة والتنمية الريفية</b></p>
                <hr>
                <p><b>Farmer Name:</b> {st.session_state.farmer_name}</p>
                <p><b>Email:</b> {st.session_state.farmer_email}</p>
                <p><b>Card N°:</b> {st.session_state.carte_num}</p>
                <p><b>Status:</b> <span style="color: green; font-weight: bold;">ACTIVE / 2026 Valid</span></p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Please log in from the sidebar to view your digital card.")

# --- PAGE 3: ACCOUNT & RECORDS ---
elif st.session_state.current_page == "account_records":
    st.subheader("👨‍🌾 حسابي وسجلاتي / My Account & Records")
    if st.session_state.logged_in:
        st.write(f"**Welcome, {st.session_state.farmer_name}!**")
        st.write("Here you can inspect past declarations and filed support requests.")
        
        tab_dec, tab_sup = st.tabs(["Declarations / التصريحات", "Support Demands / طلبات الدعم"])
        
        with tab_dec:
            try:
                res_d = supabase_client.table("declarations").select("*").eq("carte_num", st.session_state.carte_num).execute()
                if res_d and res_d.data:
                    st.dataframe(pd.DataFrame(res_d.data))
                else:
                    st.info("No crop declarations recorded.")
            except Exception as e:
                st.error(f"Could not retrieve declarations: {e}")
                
        with tab_sup:
            try:
                res_s = supabase_client.table("support_requests").select("*").eq("carte_num", st.session_state.carte_num).execute()
                if res_s and res_s.data:
                    st.dataframe(pd.DataFrame(res_s.data))
                else:
                    st.info("No support demands submitted.")
            except Exception as e:
                st.error(f"Could not retrieve support requests: {e}")
    else:
        st.warning("Please log in from the sidebar to access your account records.")
