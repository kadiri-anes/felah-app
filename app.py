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
# Page Configuration & Modern Theme Styling
# ---------------------------------------------------------
st.set_page_config(page_title="Felah Mobile Portal - Algeria", page_icon="🌾", layout="centered")

st.markdown("""
    <style>
    /* Dark Mode Compatible Theme System */
    @media (prefers-color-scheme: dark) {
        .stApp { background-color: #12181f !important; color: #e2e8f0 !important; }
        .mobile-sidebar-notice { background-color: #1a3328 !important; border-color: #0b8a62 !important; color: #6ee7b7 !important; }
        .promo-banner { background: linear-gradient(135deg, #0b8a62 0%, #134e3a 100%) !important; color: #ffffff !important; }
        .news-card, .notif-card, .market-card { background-color: #1e2631 !important; border-color: #0b8a62 !important; color: #f1f5f9 !important; }
        .news-card p, .news-card h4 { color: #e2e8f0 !important; }
    }

    /* Layout Elements */
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
    .promo-banner {
        background: linear-gradient(135deg, #0b8a62 0%, #1e5340 100%);
        color: white;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 20px;
        border: 2px solid #d4af37;
    }
    .news-card {
        background-color: #ffffff;
        border-left: 5px solid #0b8a62;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .notif-card {
        background-color: #ffffff;
        border-left: 5px solid #1a73e8;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* CENTERED, WIDE & ENLARGED MAIN TOP TABS */
    div[data-baseweb="tab-list"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        gap: 8px !important;
        background-color: transparent !important;
        margin-bottom: 20px !important;
    }
    div[data-baseweb="tab"] {
        flex: 1 1 0% !important;
        text-align: center !important;
        padding: 12px 16px !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        background-color: #f0f2f5 !important;
        border-radius: 10px !important;
        border: 1px solid #dcdfe6 !important;
        color: #2c3e50 !important;
        justify-content: center !important;
    }
    div[data-baseweb="tab"][aria-selected="true"] {
        background-color: #e6f4ea !important;
        border-color: #0b8a62 !important;
        color: #0b8a62 !important;
    }

    /* Tight service area */
    .service-container {
        margin-top: 0px !important;
        padding-top: 0px !important;
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
# PRESET DATA & WILAYAS
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
    "yellow": {"bg_color": "#fff9c4", "border_color": "#fbc02d", "text_color": "#574200", "badge_bg": "#fbc02d", "badge_text": "#000000", "icon": "⚠️", "label": "Yellow / Vigilance (يقظة)"},
    "orange": {"bg_color": "#ffe0b2", "border_color": "#f57c00", "text_color": "#4a2400", "badge_bg": "#f57c00", "badge_text": "#ffffff", "icon": "🍊", "label": "Orange / High Alert (حذر شديد)"},
    "red": {"bg_color": "#ffcdd2", "border_color": "#d32f2f", "text_color": "#490c0c", "badge_bg": "#d32f2f", "badge_text": "#ffffff", "icon": "🚨", "label": "Red / Extreme Danger (خطر أقصى)"}
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
# Session State Initializer
# ---------------------------------------------------------
if 'lang' not in st.session_state: st.session_state.lang = 'AR'
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'farmer_name' not in st.session_state: st.session_state.farmer_name = ""
if 'farmer_email' not in st.session_state: st.session_state.farmer_email = ""
if 'carte_num' not in st.session_state: st.session_state.carte_num = ""
if 'selected_service' not in st.session_state: st.session_state.selected_service = None
if 'admin_authenticated' not in st.session_state: st.session_state.admin_authenticated = False

if 'captcha_num1' not in st.session_state: st.session_state.captcha_num1 = random.randint(1, 9)
if 'captcha_num2' not in st.session_state: st.session_state.captcha_num2 = random.randint(1, 9)

TEXTS = {
    'AR': {
        'title': "بوابة الفلاح - 48 ولاية",
        'banner': "برنامج التخطيط والتنسيق الفلاحي 2026",
        'home': "🏠 الرئيسية",
        'card': "💳 بطاقتي",
        'account': "👤 حسابي وسجلاتي",
        'weather': "الأحوال الجوية والتنبيهات",
        'crop': "نصائح الزراعة والتصريح (QR)",
        'pay': "تجديد بطاقة الفلاح (CIB/الذهبية)",
        'suppliers': "خريطة أسوق الجملة، نقاط CCLS والأسمدة",
        'support': "طلب دعم الدولة (الدعم الفلاحي)",
        'news': "الأخبار والإعلانات الرسمية",
        'back_btn': "🔙 العودة"
    },
    'EN': {
        'title': "Felah Farmer Portal - 48 Wilayas",
        'banner': "Agricultural Planning & Coordination Program 2026",
        'home': "🏠 Home",
        'card': "💳 My Card",
        'account': "👤 My Account",
        'weather': "Weather & Ag-Alerts",
        'crop': "Cultivation & QR Permit",
        'pay': "Carte Fellah Subscription",
        'suppliers': "Wholesale Markets & Fertilizer Map",
        'support': "Government Agricultural Support",
        'news': "News & Official Announcements",
        'back_btn': "🔙 Back"
    }
}

def on_lang_change():
    selected = st.session_state.sb_lang
    st.session_state.lang = 'AR' if selected == "العربية" else 'EN'

t = TEXTS[st.session_state.lang]

# ---------------------------------------------------------
# SIDEBAR NAVIGATION & AUTHENTICATION
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="background-color: #0b8a62; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px;">
            ⚙️ MENU / القائمة
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🌐 Language / اللغة")
    default_idx = 0 if st.session_state.lang == 'AR' else 1
    st.radio("Choose Language", ["العربية", "English"], index=default_idx, key="sb_lang", on_change=on_lang_change, label_visibility="collapsed")
    st.divider()
    
    st.markdown("### 👤 Account / تسجيل الدخول")
    if not st.session_state.logged_in:
        auth_choice = st.radio("Action:", ["Log In (دخول)", "Register (إنشاء حساب)", "Forgot Password (نسيان كلمة السر)"], key="sb_auth_choice")
        
        if "Log In" in auth_choice:
            login_email = st.text_input("Email / البريد الإلكتروني", key="sb_l_email")
            login_pass = st.text_input("Password / كلمة السر", type="password", key="sb_l_pass")
            
            n1 = st.session_state.captcha_num1
            n2 = st.session_state.captcha_num2
            correct_sum = n1 + n2
            
            st.markdown(f"**🤖 Human Verification:** What is `{n1} + {n2}`?")
            user_captcha = st.number_input("Solve math challenge:", min_value=0, max_value=20, step=1, value=0, key="sb_captcha_val")
            
            if st.button("🔓 Log In / دخول", use_container_width=True, type="primary"):
                if user_captcha != correct_sum:
                    st.error("❌ Incorrect CAPTCHA answer!")
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
                                user_profile = res.data[0]
                                st.session_state.logged_in = True
                                st.session_state.farmer_name = user_profile.get("full_name", "Farmer")
                                st.session_state.farmer_email = user_profile.get("email", login_email.strip())
                                st.session_state.carte_num = user_profile.get("carte_num", "N/A")
                                st.success("Successfully logged in!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")
                else:
                    st.warning("Please fill all fields.")
        
        elif "Register" in auth_choice:
            reg_name = st.text_input("Full Name / الاسم الكامل", key="sb_r_name")
            reg_email = st.text_input("Email / البريد الإلكتروني", key="sb_r_email")
            reg_card = st.text_input("Carte Fellah N°", placeholder="DZ-2026-XXXXX", key="sb_r_card")
            reg_pass = st.text_input("Create Password", type="password", key="sb_r_pass")
            
            if st.button("📝 Register Account", use_container_width=True, type="primary"):
                if reg_name and reg_email and reg_card and reg_pass:
                    try:
                        clean_email = sanitize(reg_email)
                        clean_name = sanitize(reg_name)
                        clean_card = sanitize(reg_card)

                        auth_response = supabase_client.auth.sign_up({"email": clean_email, "password": reg_pass})
                        
                        if auth_response.user:
                            user_id = auth_response.user.id
                            supabase_client.table("farmer_profiles").insert({
                                "id": user_id, "email": clean_email, "full_name": clean_name, "carte_num": clean_card
                            }).execute()

                            if auth_response.session is None:
                                st.info(f"📩 Confirmation Email Sent to `{clean_email}`!")
                            else:
                                st.session_state.logged_in = True
                                st.session_state.farmer_name = clean_name
                                st.session_state.farmer_email = clean_email
                                st.session_state.carte_num = clean_card
                                st.success("Registration completed!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Error registering account: {e}")

        else:
            rec_email = st.text_input("Enter your registered email:", key="sb_rec_email")
            if st.button("📧 Send Recovery Link", use_container_width=True):
                if rec_email:
                    try:
                        supabase_client.auth.reset_password_for_email(rec_email.strip())
                        st.success(f"Recovery email dispatched to `{rec_email}`!")
                    except Exception as e:
                        st.error(f"Failed to dispatch link: {e}")
    else:
        st.success(f"🟢 Connected:\n**{st.session_state.farmer_name}**")
        st.caption(f"Email: `{st.session_state.farmer_email}`")
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
# TOP STATUS HEADER WITH NOTIFICATION BELL
# ---------------------------------------------------------
unread_count = get_unread_notif_count(st.session_state.farmer_email)
mobile_status = f"🟢 Connected: {st.session_state.farmer_name}" if st.session_state.logged_in else "🔴 Not Logged In — Use left menu ↗ to login"
st.markdown(f'<div class="mobile-sidebar-notice">👉 {mobile_status}</div>', unsafe_allow_html=True)

col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.markdown(f"<h2 style='margin:0;'>{t['title']}</h2>", unsafe_allow_html=True)
with col_head2:
    st.button(f"🔔 {unread_count}", help="Notifications")

st.markdown(f"""
    <div class="promo-banner">
        <h4 style="margin:0;">{t['banner']}</h4>
        <small>الجمهورية الجزائرية الديمقراطية الشعبية - وزارة الفلاحة والتنمية الريفية</small>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MAIN 3 TOP SLIDING TABS (EXACT CENTERED & LARGE FORMAT)
# ---------------------------------------------------------
tab_home, tab_card, tab_account = st.tabs([t['home'], t['card'], t['account']])

# =========================================================
# TAB 1: HOME & MAIN SERVICES
# =========================================================
with tab_home:
    if st.session_state.selected_service is None:
        st.subheader("الخدمات الإلكترونية / Main Services")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(t['crop'], use_container_width=True, type="primary"):
                st.session_state.selected_service = "crop"
                st.rerun()
            if st.button(t['support'], use_container_width=True):
                st.session_state.selected_service = "support"
                st.rerun()
            if st.button(t['pay'], use_container_width=True):
                st.session_state.selected_service = "pay"
                st.rerun()
        
        with col2:
            if st.button(t['news'], use_container_width=True):
                st.session_state.selected_service = "news"
                st.rerun()
            if st.button(t['weather'], use_container_width=True):
                st.session_state.selected_service = "weather"
                st.rerun()
            if st.button(t['suppliers'], use_container_width=True):
                st.session_state.selected_service = "suppliers"
                st.rerun()

    else:
        # Compact Inline Back Button
        b_col1, b_col2 = st.columns([1, 4])
        with b_col1:
            if st.button(t['back_btn'], key="back_sm"):
                st.session_state.selected_service = None
                st.rerun()

        st.markdown('<div class="service-container">', unsafe_allow_html=True)

        # SERVICE 1: SUPPORT DEMAND
        if st.session_state.selected_service == "support":
            st.subheader(t['support'])
            if not st.session_state.logged_in:
                st.warning("⚠️ Please log in from the left menu ↗ to submit a support demand.")
            else:
                selected_w_sup = st.selectbox("Wilaya / الولاية", WILAYAS_48, key="sup_w")
                selected_sector = st.selectbox("Select Subsidized Sector", list(SUPPORT_SECTORS.keys()))
                
                st.markdown(f"#### 📄 Required Documents for `{selected_sector}`:")
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

        # SERVICE 2: NEWS
        elif st.session_state.selected_service == "news":
            st.subheader(t['news'])
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

        # SERVICE 3: DECLARATION & QUOTA SYSTEM
        elif st.session_state.selected_service == "crop":
            st.subheader(t['crop'])
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

        # SERVICE 4: WEATHER ALERTS
        elif st.session_state.selected_service == "weather":
            st.subheader(t['weather'])
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

        # SERVICE 5: PAYMENTS
        elif st.session_state.selected_service == "pay":
            st.subheader(t['pay'])
            st.write("Annual Subscription Fee: **2,500 DZD**")
            st.radio("Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"])
            st.text_input("Card Number:", placeholder="6037 XXXX XXXX XXXX")
            if st.button("Confirm Payment", type="primary"): 
                st.success("Carte Fellah renewed for season 2026/2027!")

        # SERVICE 6: MAPS DIRECTORY
        elif st.session_state.selected_service == "suppliers":
            st.subheader("🗺️ خريطة الموزعين وأسوق الجملة ونقاط CCLS")
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

        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# TAB 2: CARTE FELLAH
# =========================================================
with tab_card:
    st.subheader("Digital Carte Fellah - البطاقة الفلاحية الرقمية")
    if st.session_state.logged_in:
        st.markdown(f"""
            <div style="border: 2px solid #0b8a62; border-radius: 15px; padding: 20px;">
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
        st.warning("Please log in from the left menu to view your digital card.")

# =========================================================
# TAB 3: MY ACCOUNT & ADMIN CONSOLE (WITH SLIDING SUB-TABS)
# =========================================================
with tab_account:
    if st.session_state.logged_in:
        st.subheader(f"👋 Welcome, {st.session_state.farmer_name}")
        
        user_tab1, user_tab2, user_tab3 = st.tabs(["🔔 Notifications", "📜 My Crop Declarations", "📄 My Subsidies Requests"])
        
        with user_tab1:
            try:
                res_notif = supabase_client.table("farmer_notifications").select("*").eq("farmer_email", st.session_state.farmer_email).order("id", desc=True).execute()
                notifs = res_notif.data if res_notif.data else []
                
                if notifs:
                    for n in notifs:
                        st.markdown(f"""
                            <div class="notif-card">
                                <b>📩 {sanitize(n.get('title',''))}</b>
                                <p style="margin:4px 0;">{sanitize(n.get('message',''))}</p>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No personal notifications.")
            except Exception as e:
                st.error(f"Error fetching notifications: {e}")

        with user_tab2:
            try:
                res_dec = supabase_client.table("declarations").select("*").eq("carte_num", st.session_state.carte_num).execute()
                if res_dec.data:
                    st.dataframe(pd.DataFrame(res_dec.data)[["crop", "category", "area", "wilaya", "start_date"]], use_container_width=True)
                else:
                    st.info("No crop declarations found.")
            except Exception as e:
                st.error(f"Error: {e}")

        with user_tab3:
            try:
                res_sup = supabase_client.table("support_requests").select("*").eq("carte_num", st.session_state.carte_num).execute()
                if res_sup.data:
                    st.dataframe(pd.DataFrame(res_sup.data)[["sector", "wilaya", "status", "created_at"]], use_container_width=True)
                else:
                    st.info("No subsidy applications found.")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("👈 Please log in from the sidebar menu to view your personal account records.")

    st.divider()

    # RESTORED ADMIN PANEL WITH FULL FEATURED SUB-TABS (SLIDES)
    st.subheader("🔐 Admin Management Portal")
    admin_input_pass = st.text_input("Enter Admin Secret Key", type="password", key="admin_pwd_full")
    
    if admin_input_pass == get_admin_password():
        st.success("🔓 Authenticated as Portal Administrator")
        
        # Sub-tabs/Slides for Admin Tasks
        adm_alerts, adm_news, adm_notifs, adm_locs, adm_db = st.tabs([
            "⚠️ Weather Alerts", 
            "📰 News", 
            "📨 Notifications", 
            "📍 Add Location", 
            "📊 Full Database"
        ])

        with adm_alerts:
            st.markdown("### 📢 Broadcast Weather Alert")
            al_title = st.text_input("Alert Title / العنوان", key="ad_alt_t")
            al_region = st.selectbox("Target Region / الولاية", ["All Wilayas"] + WILAYAS_48, key="ad_alt_r")
            al_severity = st.selectbox("Severity Level", ["yellow", "orange", "red"], key="ad_alt_s")
            al_msg = st.text_area("Content / المحتوى", key="ad_alt_m")
            if st.button("Broadcast Weather Alert", type="primary"):
                supabase_client.table("weather_alerts").insert({
                    "title": sanitize(al_title), "region": al_region, "severity": al_severity, "message": sanitize(al_msg)
                }).execute()
                st.success("Alert Broadcasted Successfully!")

        with adm_news:
            st.markdown("### 📰 Publish Official Announcement")
            news_title = st.text_input("News Title", key="ad_nw_t")
            news_cat = st.selectbox("Category", ["Official Statement", "Ministry Announcement", "Market Update", "General Advisory"], key="ad_nw_c")
            news_content = st.text_area("News Body Content", key="ad_nw_m")
            if st.button("Publish News"):
                supabase_client.table("portal_news").insert({
                    "title": sanitize(news_title), "category": news_cat, "content": sanitize(news_content)
                }).execute()
                st.success("News Announcement Published!")

        with adm_notifs:
            st.markdown("### 📨 Send Direct Farmer Notification")
            target_email = st.text_input("Target Farmer Email", key="ad_nt_e")
            notif_title = st.text_input("Subject", key="ad_nt_t")
            notif_body = st.text_area("Message Body", key="ad_nt_b")
            if st.button("Send Direct Message"):
                supabase_client.table("farmer_notifications").insert({
                    "farmer_email": sanitize(target_email), "title": sanitize(notif_title), "message": sanitize(notif_body), "is_read": False
                }).execute()
                st.success("Notification Dispatched!")

        with adm_locs:
            st.markdown("### 📍 Register Map Directory Location")
            loc_name = st.text_input("Location / Facility Name", key="ad_lc_n")
            loc_wilaya = st.selectbox("Wilaya Location", WILAYAS_48, key="ad_lc_w")
            loc_cat = st.selectbox("Facility Type", ["Wholesale Produce Market", "OAIC Cereal Silo (CCLS)", "ASMIDAL Fertilizer Depot"], key="ad_lc_c")
            loc_lat = st.number_input("Latitude", value=36.7323, format="%.4f", key="ad_lc_lt")
            loc_lon = st.number_input("Longitude", value=3.1678, format="%.4f", key="ad_lc_ln")
            if st.button("Add Map Point"):
                maps_url = f"https://maps.google.com/?q={loc_lat},{loc_lon}"
                supabase_client.table("suppliers_directory").insert({
                    "name": sanitize(loc_name), "wilaya": loc_wilaya, "category": loc_cat, "lat": loc_lat, "lon": loc_lon, "maps_link": maps_url
                }).execute()
                st.success("New Map Location Saved!")

        with adm_db:
            st.markdown("### 📊 Live Crop Quotas & System Database")
            
            # Crop Area Usage Analytics Overview
            st.write("#### 🌾 National Vegetable Quotas & Used Areas")
            quota_data = []
            for crop, limit in VEGETABLE_LIMITS.items():
                used = get_current_crop_area(crop)
                avail = max(0.0, limit - used)
                quota_data.append({"Crop": crop, "Used (Ha)": used, "Available (Ha)": avail, "Total Quota (Ha)": limit})
            st.dataframe(pd.DataFrame(quota_data), use_container_width=True)

            st.divider()
            
            # Full DB Inspector
            table_choice = st.selectbox("Inspect Database Table Records:", ["declarations", "support_requests", "farmer_profiles", "farmer_notifications", "weather_alerts", "portal_news", "suppliers_directory"])
            res_all = supabase_client.table(table_choice).select("*").execute()
            if res_all.data:
                st.dataframe(pd.DataFrame(res_all.data), use_container_width=True)
            else:
                st.info("Table is empty.")
