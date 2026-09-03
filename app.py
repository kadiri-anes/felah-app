import random
import re
from datetime import date
from io import BytesIO

import folium
import pandas as pd
import qrcode
import streamlit as st
from st_supabase_connection import SupabaseConnection
from streamlit_folium import st_folium

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="برنامج التخطيط والتنسيق الفلاحي 2026",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# GLOBAL CONSTANTS & TRANSLATIONS
# ---------------------------------------------------------
WILAYAS_48 = [
    "01 - Adrar",
    "02 - Chlef",
    "03 - Laghouat",
    "04 - Oum El Bouaghi",
    "05 - Batna",
    "06 - Béjaïa",
    "07 - Biskra",
    "08 - Béchar",
    "09 - Blida",
    "10 - Bouira",
    "11 - Tamanrasset",
    "12 - Tébessa",
    "13 - Tlemcen",
    "14 - Tiaret",
    "15 - Tizi Ouzou",
    "16 - Alger",
    "17 - Djelfa",
    "18 - Jijel",
    "19 - Sétif",
    "20 - Saïda",
    "21 - Skikda",
    "22 - Sidi Bel Abbès",
    "23 - Annaba",
    "24 - Guelma",
    "25 - Constantine",
    "26 - Médéa",
    "27 - Mostaganem",
    "28 - M'Sila",
    "29 - Mascara",
    "30 - Ouargla",
    "31 - Oran",
    "32 - El Bayadh",
    "33 - Illizi",
    "34 - Bordj Bou Arréridj",
    "35 - Boumerdès",
    "36 - El Tarf",
    "37 - Tindouf",
    "38 - Tissemsilt",
    "39 - El Oued",
    "40 - Khenchela",
    "41 - Souk Ahras",
    "42 - Tipaza",
    "43 - Mila",
    "44 - Aïn Defla",
    "45 - Naâma",
    "46 - Aïn Témouchent",
    "47 - Ghardaïa",
    "48 - Relizane",
]

DEFAULT_AGRI_LOCATIONS = [
    {
        "name": "سوق الجملة للخضر والفواكه - الكاليتوس",
        "wilaya": "16 - Alger",
        "category": "Wholesale Produce Market",
        "lat": 36.6572,
        "lon": 3.1294,
        "maps_link": "https://maps.google.com/?q=36.6572,3.1294",
    },
    {
        "name": "تعاونية الحبوب والخضر الجافة CCLS - شلغوم العيد",
        "wilaya": "43 - Mila",
        "category": "OAIC Cereal Silo (CCLS)",
        "lat": 36.1623,
        "lon": 6.1662,
        "maps_link": "https://maps.google.com/?q=36.1623,6.1662",
    },
    {
        "name": "نقطة توزيع الأسمدة أسميدال - وهران",
        "wilaya": "31 - Oran",
        "category": "ASMIDAL Fertilizer Depot",
        "lat": 35.6971,
        "lon": -0.6308,
        "maps_link": "https://maps.google.com/?q=35.6971,-0.6308",
    },
]

VEGETABLE_LIMITS = {
    "Potatoes (بطاطا)": 160000.0,
    "Tomatoes (طماطم)": 25000.0,
    "Onions (بصل)": 55000.0,
    "Garlic (ثوم)": 12000.0,
    "Carrots (جزر)": 20000.0,
}

FRUIT_LIST = [
    "Citrus / الموالح",
    "Apples / تفاح",
    "Dates / تمور",
    "Olives / زيتون",
    "Grapes / عنب",
    "Pomegranates / رمان",
]

SUPPORT_SECTORS = {
    "Geomembrane Basin (أحواض الجيوممبران)": [
        "Farmer Card (بطاقة الفلاح)",
        "Land Title / Lease (عقد الملكية أو الامتياز)",
        "Water Authorization (رخصة حفر/استغلال المياه)",
    ],
    "Well Digging (حفر الآبار الفلاحية)": [
        "Farmer Card (بطاقة الفلاح)",
        "Hydrogeological Study (دراسة هيدروجيولوجية)",
        "Water Resources Permit (ترخيص وزارة الموارد المائية)",
    ],
    "Solar Pumping (الطاقة الشمسية)": [
        "Farmer Card (بطاقة الفلاح)",
        "Technical Invoice (فاتورة شكلية للتجهيز)",
        "Land Title (عقد الملكية)",
    ],
    "Drip Irrigation (الري بالتقطير)": [
        "Farmer Card (بطاقة الفلاح)",
        "Topographical Map (مخطط الطبوغرافيا)",
        "Equipment Proforma Invoice (فاتورة شكلية)",
    ],
}

ALERT_STYLES = {
    "yellow": {
        "bg_color": "#fffbe6",
        "border_color": "#ffe58f",
        "text_color": "#d48806",
        "icon": "⚠️",
        "label": "يقظة - الأصفر",
        "badge_bg": "#ffe58f",
        "badge_text": "#8c6b00",
    },
    "orange": {
        "bg_color": "#fff2e8",
        "border_color": "#ffbb96",
        "text_color": "#d4380d",
        "icon": "🟠",
        "label": "تحذير - البرتقالي",
        "badge_bg": "#ffbb96",
        "badge_text": "#871400",
    },
    "red": {
        "bg_color": "#fff1f0",
        "border_color": "#ffa39e",
        "text_color": "#cf1322",
        "icon": "🚨",
        "label": "خطر - الأحمر",
        "badge_bg": "#ffa39e",
        "badge_text": "#820014",
    },
}

TEXTS = {
    "AR": {
        "title": "برنامج التخطيط والتنسيق الفلاحي 2026",
        "subtitle": "الجمهورية الجزائرية الديمقراطية الشعبية - وزارة الفلاحة والتنمية الريفية",
        "tab_home": "الرئيسية",
        "tab_card": "بطاقاتي",
        "tab_account": "حسابي وسجلاتي",
        "main_services": "الخدمات الإلكترونية الرئيسية",
        "crop": "نصائح الزراعة والتصريح (QR)",
        "news": "الأخبار والإعلانات الرسمية",
        "support": "طلب دعم الدولة (الدعم الفلاحي)",
        "weather": "الأحوال الجوية والتنبيهات",
        "pay": "تجديد بطاقة الفلاح (الذهبية/CIB)",
        "suppliers": "خريطة CCLS ونقاط الأسمدة وأسواق الجملة",
        "back_btn": "⬅️ العودة للخدمات الرئيسية",
    },
    "EN": {
        "title": "Agricultural Planning & Coordination Program 2026",
        "subtitle": "People's Democratic Republic of Algeria - Ministry of Agriculture",
        "tab_home": "Home Services",
        "tab_card": "Digital Farmer Card",
        "tab_account": "Account & History",
        "main_services": "Main E-Services",
        "crop": "Crop Declaration & Permit (QR)",
        "news": "Official News Releases",
        "support": "Ministry Subsidies Request",
        "weather": "Agri-Weather Alerts",
        "pay": "Carte Fellah Renewal",
        "suppliers": "Map: CCLS, Fertilizers & Markets",
        "back_btn": "⬅️ Back to Main Services",
    },
}

# ---------------------------------------------------------
# INITIALIZE SESSION STATE
# ---------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "AR"
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "home"
if "selected_service" not in st.session_state:
    st.session_state.selected_service = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "farmer_email" not in st.session_state:
    st.session_state.farmer_email = ""
if "farmer_name" not in st.session_state:
    st.session_state.farmer_name = "فلاح مسجل"
if "carte_num" not in st.session_state:
    st.session_state.carte_num = "DZ-2026-0000"
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "captcha_num1" not in st.session_state:
    st.session_state.captcha_num1 = random.randint(1, 9)
    st.session_state.captcha_num2 = random.randint(1, 9)

# ---------------------------------------------------------
# SUPABASE CONNECTION SETUP
# ---------------------------------------------------------
try:
    supabase_client = st.connection("supabase", type=SupabaseConnection)
except Exception:
    supabase_client = None

# ---------------------------------------------------------
# HELPER & UTILITY FUNCTIONS
# ---------------------------------------------------------


def sanitize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[<>]", "", str(text)).strip()


def get_admin_password() -> str:
    try:
        return st.secrets["ADMIN_SECRET_KEY"]
    except Exception:
        return "AlgeriaAgri2026"


def get_unread_notif_count() -> int:
    if not st.session_state.logged_in or not supabase_client:
        return 0
    try:
        res = (
            supabase_client.table("farmer_notifications")
            .select("id", count="exact")
            .eq("farmer_email", st.session_state.farmer_email)
            .eq("is_read", False)
            .execute()
        )
        return res.count if res.count else 0
    except Exception:
        return 0


def get_current_crop_area(crop_name: str) -> float:
    if not supabase_client:
        return 0.0
    try:
        res = (
            supabase_client.table("declarations")
            .select("area")
            .eq("crop", crop_name)
            .execute()
        )
        if res.data:
            return sum(float(item.get("area", 0)) for item in res.data)
    except Exception:
        pass
    return 0.0


# ---------------------------------------------------------
# DYNAMIC THEME & CSS INJECTION
# ---------------------------------------------------------
is_dark = st.session_state.theme_mode == "Dark"

bg_color = "#121820" if is_dark else "#f4f7f6"
card_bg = "#1b2430" if is_dark else "#ffffff"
text_color = "#e2e8f0" if is_dark else "#2d3748"
border_color = "#2d3748" if is_dark else "#e2e8f0"
subtext_color = "#a0aec0" if is_dark else "#4a5568"

st.markdown(
    f"""
    <style>
    @keyframes slideInUp {{
        0% {{
            opacity: 0;
            transform: translateY(18px);
        }}
        100% {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    /* Global Dark/Light Adaptation */
    @media (prefers-color-scheme: dark) {{
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
        }}
    }}

    .stApp {{
        background-color: {bg_color};
        color: {text_color};
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}

    /* Centered Header Banner */
    .header-banner {{
        background: linear-gradient(135deg, #0b8a62 0%, #1e5340 100%);
        color: white;
        padding: 22px 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }}
    .header-banner h2 {{
        margin: 0 0 6px 0;
        font-weight: 700;
        font-size: 1.7rem;
    }}
    .header-banner p {{
        margin: 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }}

    /* Centered Navigation Tabs Container */
    .nav-tabs-wrapper {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        margin-bottom: 25px;
        width: 100%;
    }}

    /* Dynamic Content Container with Keyframe Slide Transition */
    .animated-tab-content {{
        animation: slideInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 24px;
        margin-top: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}

    /* Main Services Section Title */
    .section-title {{
        text-align: center;
        color: #0b8a62;
        margin-bottom: 20px;
        font-size: 1.5rem;
        font-weight: 600;
    }}

    /* Custom Cards Styling */
    .news-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-left: 5px solid #0b8a62;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 14px;
    }}
    .notif-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-right: 5px solid #0b8a62;
        padding: 14px;
        border-radius: 8px;
        margin-bottom: 10px;
    }}

    /* Streamlit Widget Customization */
    div[data-testid="stSidebar"] {{
        background-color: {card_bg};
        border-right: 1px solid {border_color};
    }}
    .stButton>button {{
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }}
    .stButton>button:hover {{
        border-color: #0b8a62;
        color: #0b8a62;
        transform: translateY(-1px);
    }}
    </style>
""",
    unsafe_allow_html=True,
)

t = TEXTS[st.session_state.lang]

# ---------------------------------------------------------
# SIDEBAR CONTROL PANEL & AUTH
# ---------------------------------------------------------
with st.sidebar:
    st.title("⚙️ MENU / القائمة")

    # Language Switcher
    lang_choice = st.radio(
        "اللغة / Language",
        ["العربية", "English"],
        index=0 if st.session_state.lang == "AR" else 1,
    )
    st.session_state.lang = "AR" if lang_choice == "العربية" else "EN"

    # Smooth Dark / Light Mode Switch
    theme_choice = st.radio(
        "المظهر / Theme Mode",
        ["Dark 🌙", "Light ☀️"],
        index=0 if st.session_state.theme_mode == "Dark" else 1,
    )
    new_theme = "Dark" if "Dark" in theme_choice else "Light"
    if new_theme != st.session_state.theme_mode:
        st.session_state.theme_mode = new_theme
        st.rerun()

    st.divider()

    # User Account / Auth Workflow
    st.subheader("👤 Account / تسجيل الدخول")
    if not st.session_state.logged_in:
        auth_mode = st.radio(
            "Action:",
            ["Log In (دخول)", "Register (إنشاء حساب)", "Forgot Password"],
        )

        email_input = st.text_input("Email / البريد الإلكتروني")
        pass_input = st.text_input("Password / كلمة السر", type="password")

        if auth_mode == "Register (إنشاء حساب)":
            name_input = st.text_input("Full Name / الاسم الكامل")
            carte_input = st.text_input(
                "Carte Fellah N° / رقم بطاقة الفلاح", placeholder="DZ-2026-XXXX"
            )

            # CAPTCHA Guard
            captcha_ans = st.number_input(
                f"Security Check: {st.session_state.captcha_num1} + {st.session_state.captcha_num2} = ?",
                step=1,
                value=0,
            )

            if st.button("Submit Registration", type="primary"):
                if (
                    captcha_ans
                    != st.session_state.captcha_num1
                    + st.session_state.captcha_num2
                ):
                    st.error("Incorrect CAPTCHA answer.")
                elif email_input and pass_input and supabase_client:
                    try:
                        res = supabase_client.auth.sign_up(
                            {
                                "email": email_input,
                                "password": pass_input,
                                "options": {
                                    "data": {
                                        "full_name": name_input,
                                        "carte_num": carte_input,
                                    }
                                },
                            }
                        )
                        st.success(
                            "Account created successfully! You may now log in."
                        )
                    except Exception as e:
                        st.error(f"Registration Error: {e}")

        elif auth_mode == "Log In (دخول)":
            if st.button("Login", type="primary"):
                if email_input and pass_input and supabase_client:
                    try:
                        res = supabase_client.auth.sign_in_with_password(
                            {"email": email_input, "password": pass_input}
                        )
                        st.session_state.logged_in = True
                        st.session_state.farmer_email = email_input
                        user_metadata = (
                            res.user.user_metadata if res.user else {}
                        )
                        st.session_state.farmer_name = user_metadata.get(
                            "full_name", email_input.split("@")[0]
                        )
                        st.session_state.carte_num = user_metadata.get(
                            "carte_num", "DZ-2026-1088"
                        )
                        st.success("Logged in successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication Failed: {e}")
                else:
                    st.error("Please enter email and password.")

        elif auth_mode == "Forgot Password":
            if st.button("Send Reset Link"):
                if email_input and supabase_client:
                    try:
                        supabase_client.auth.reset_password_for_email(
                            email_input
                        )
                        st.info("Password reset link sent to your email.")
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        unread_count = get_unread_notif_count()
        st.success(f"Logged in: {st.session_state.farmer_name}")
        st.caption(f"Carte N°: {st.session_state.carte_num}")
        if unread_count > 0:
            st.warning(f"🔔 You have {unread_count} unread notifications!")

        if st.button("Log Out / خروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.farmer_email = ""
            st.session_state.admin_authenticated = False
            st.rerun()

# ---------------------------------------------------------
# HEADER BANNER (CENTERED)
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="header-banner">
        <h2>{t['title']}</h2>
        <p>{t['subtitle']}</p>
    </div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# CENTERED TOP SLIDING NAVIGATION TABS
# ---------------------------------------------------------
c_left, c_mid, c_right = st.columns([1, 4, 1])

with c_mid:
    t_col1, t_col2, t_col3 = st.columns(3)

    unread_badge = f" ({get_unread_notif_count()})" if st.session_state.logged_in and get_unread_notif_count() > 0 else ""

    with t_col1:
        is_home = st.session_state.active_tab == "home"
        if st.button(
            f"🏠 {t['tab_home']}",
            use_container_width=True,
            type="primary" if is_home else "secondary",
        ):
            st.session_state.active_tab = "home"
            st.rerun()

    with t_col2:
        is_card = st.session_state.active_tab == "card"
        if st.button(
            f"🪪 {t['tab_card']}",
            use_container_width=True,
            type="primary" if is_card else "secondary",
        ):
            st.session_state.active_tab = "card"
            st.rerun()

    with t_col3:
        is_acc = st.session_state.active_tab == "account"
        if st.button(
            f"🔔 {t['tab_account']}{unread_badge}",
            use_container_width=True,
            type="primary" if is_acc else "secondary",
        ):
            st.session_state.active_tab = "account"
            st.rerun()

# ---------------------------------------------------------
# TAB 1: MAIN SERVICES VIEW (ANIMATED)
# ---------------------------------------------------------
if st.session_state.active_tab == "home":
    st.markdown(
        '<div class="animated-tab-content">', unsafe_allow_html=True
    )

    if st.session_state.selected_service is None:
        st.markdown(
            f"<h3 class='section-title'>{t['main_services']}</h3>",
            unsafe_allow_html=True,
        )

        # Centered Grid Layout for Main Services Icons
        srv_col1, srv_col2 = st.columns(2)

        with srv_col1:
            if st.button(
                f"🌾 {t['crop']}",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.selected_service = "crop"
                st.rerun()
            if st.button(
                f"📑 {t['support']}",
                use_container_width=True,
            ):
                st.session_state.selected_service = "support"
                st.rerun()
            if st.button(
                f"💳 {t['pay']}",
                use_container_width=True,
            ):
                st.session_state.selected_service = "pay"
                st.rerun()

        with srv_col2:
            if st.button(
                f"📢 {t['news']}",
                use_container_width=True,
            ):
                st.session_state.selected_service = "news"
                st.rerun()
            if st.button(
                f"🌤️ {t['weather']}",
                use_container_width=True,
            ):
                st.session_state.selected_service = "weather"
                st.rerun()
            if st.button(
                f"🗺️ {t['suppliers']}",
                use_container_width=True,
            ):
                st.session_state.selected_service = "suppliers"
                st.rerun()

    else:
        if st.button(t["back_btn"], use_container_width=True):
            st.session_state.selected_service = None
            st.rerun()

        st.divider()

        # SERVICE 1: SUPPORT DEMAND
        if st.session_state.selected_service == "support":
            st.subheader(t["support"])
            st.write(
                "Submit official requests for Ministry subsidies (Geomembrane basins, well digging, solar, drip irrigation)."
            )

            if not st.session_state.logged_in:
                st.warning(
                    "⚠️ Please log in from the left menu ↗ to submit a support demand."
                )
            else:
                selected_w_sup = st.selectbox(
                    "Wilaya / الولاية", WILAYAS_48, key="sup_w"
                )
                selected_sector = st.selectbox(
                    "Select Subsidized Sector / اختر مجال الدعم",
                    list(SUPPORT_SECTORS.keys()),
                )

                st.markdown(
                    f"#### 📄 Required Documents for `{selected_sector}`:"
                )
                req_docs = SUPPORT_SECTORS[selected_sector]
                for doc in req_docs:
                    st.write(f"• **{doc}**")

                st.divider()
                st.write(
                    "### Attach Your Files & Papers (رفع الملفات والوثائق)"
                )
                uploaded_files = {}

                for idx, doc in enumerate(req_docs):
                    up_file = st.file_uploader(
                        f"Upload: {doc}",
                        type=["pdf", "jpg", "jpeg", "png"],
                        key=f"file_{idx}",
                    )
                    if up_file:
                        uploaded_files[doc] = up_file

                additional_notes = st.text_area(
                    "Additional Notes / ملاحظات إضافية",
                    placeholder="Describe your farm capacity or specific project details...",
                )

                if st.button(
                    "Submit Support Demand (إرسال طلب الدعم)",
                    type="primary",
                    use_container_width=True,
                ):
                    if len(uploaded_files) < len(req_docs):
                        st.error(
                            f"Please upload all {len(req_docs)} required documents before submitting."
                        )
                    else:
                        uploaded_links = {}
                        try:
                            with st.spinner(
                                "Uploading documents securely to Supabase Storage..."
                            ):
                                for (
                                    doc_name,
                                    file_obj,
                                ) in uploaded_files.items():
                                    clean_filename = f"{st.session_state.carte_num}_{random.randint(1000,9999)}_{file_obj.name}"
                                    file_path = f"support_docs/{clean_filename}"
                                    file_bytes = file_obj.read()

                                    supabase_client.storage.from_(
                                        "agricultural-docs"
                                    ).upload(file_path, file_bytes)
                                    public_url = f"{st.secrets['connections']['supabase']['SUPABASE_URL']}/storage/v1/object/public/agricultural-docs/{file_path}"
                                    uploaded_links[doc_name] = public_url

                                supabase_client.table(
                                    "support_requests"
                                ).insert({
                                    "farmer_name": st.session_state.farmer_name,
                                    "carte_num": st.session_state.carte_num,
                                    "wilaya": selected_w_sup,
                                    "sector": selected_sector,
                                    "description": sanitize(
                                        additional_notes
                                    ),
                                    "files_json": uploaded_links,
                                }).execute()

                                st.success(
                                    "🎉 Your Agricultural Support demand has been submitted successfully!"
                                )
                        except Exception as e:
                            st.error(f"Error submitting request: {e}")

        # SERVICE 2: NEWS
        elif st.session_state.selected_service == "news":
            st.subheader(t["news"])
            try:
                res_news = (
                    supabase_client.table("portal_news")
                    .select("*")
                    .order("id", desc=True)
                    .execute()
                )
                news_items = res_news.data if res_news.data else []
            except Exception:
                news_items = []

            if news_items:
                for n in news_items:
                    st.markdown(
                        f"""
                        <div class="news-card">
                            <span style="background: #0b8a62; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8em;">{sanitize(n.get("category",""))}</span>
                            <h4 style="margin: 8px 0 5px 0; color: #0b8a62;">📢 {sanitize(n.get("title",""))}</h4>
                            <p style="margin: 0;">{sanitize(n.get("content",""))}</p>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("📰 No official news releases published today.")

        # SERVICE 3: CROP DECLARATION & QUOTA PERMIT
        elif st.session_state.selected_service == "crop":
            st.subheader(t["crop"])
            selected_w = st.selectbox(
                "Wilaya / الولاية (48 Wilayas)", WILAYAS_48
            )
            cat_choice = st.radio(
                "Category / الصنف:", ["Vegetables (خضروات)", "Fruits (فواكه)"]
            )
            area_ha = st.number_input(
                "Your Farming Area (Hectares / هكتار)",
                min_value=0.1,
                value=5.0,
                max_value=10000.0,
            )
            start_date = st.date_input(
                "Date of Starting Cultivation / تاريخ بداية الزراعة",
                value=date.today(),
            )

            if cat_choice == "Fruits (فواكه)":
                selected_c = st.selectbox(
                    "Select Fruit / اختر الفاكهة", FRUIT_LIST
                )
                st.success(
                    "Unlimited Capacity / بدون حد أقصى — Fruit cultivation is open without national hectare restrictions."
                )
            else:
                selected_c = st.selectbox(
                    "Select Vegetable / اختر الخضار",
                    list(VEGETABLE_LIMITS.keys()),
                )
                limit = VEGETABLE_LIMITS[selected_c]
                current_total = get_current_crop_area(selected_c)
                projected_total = current_total + area_ha
                percentage = min((projected_total / limit), 1.0)

                st.write(
                    f"**National Area Quota Status ({selected_c}):**"
                )
                st.progress(percentage)
                st.caption(
                    f"Currently Registered: {current_total:.1f} Ha | Your Input: {area_ha:.1f} Ha | Target Limit: {limit:.0f} Ha"
                )

            if st.button(
                "Submit & Generate QR Permit", type="primary"
            ):
                if st.session_state.logged_in:
                    try:
                        supabase_client.table("declarations").insert({
                            "farmer_name": st.session_state.farmer_name,
                            "carte_num": st.session_state.carte_num,
                            "wilaya": selected_w,
                            "category": cat_choice,
                            "crop": selected_c,
                            "area": area_ha,
                            "start_date": str(start_date),
                        }).execute()

                        st.success("Declaration registered successfully!")
                        qr_payload = f"FELAH-PERMIT|{st.session_state.farmer_name}|{st.session_state.carte_num}|{selected_w}|{selected_c}|{area_ha}HA|START:{start_date}"
                        qr = qrcode.make(qr_payload)
                        buf = BytesIO()
                        qr.save(buf, format="PNG")
                        st.image(
                            buf.getvalue(),
                            caption=f"Official QR Permit (Start Date: {start_date})",
                            width=220,
                        )
                    except Exception as e:
                        st.error(f"Failed to record declaration: {e}")
                else:
                    st.warning("Please log in first from sidebar.")

        # SERVICE 4: WEATHER ALERTS
        elif st.session_state.selected_service == "weather":
            st.subheader(t["weather"])
            try:
                res = (
                    supabase_client.table("weather_alerts")
                    .select("*")
                    .order("id", desc=True)
                    .execute()
                )
                alerts = res.data if res.data else []
            except Exception:
                alerts = []

            if alerts:
                for item in alerts:
                    title = sanitize(
                        item.get("title", "Weather Notice")
                    )
                    region = sanitize(
                        item.get("region", "All Wilayas")
                    )
                    message = sanitize(item.get("message", ""))
                    raw_level = (
                        str(item.get("severity", "yellow"))
                        .lower()
                        .strip()
                    )
                    style = ALERT_STYLES.get(
                        raw_level, ALERT_STYLES["yellow"]
                    )

                    st.markdown(
                        f"""
                        <div style="background-color: {style['bg_color']}; border-left: 6px solid {style['border_color']}; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px; color: {style['text_color']};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-weight: bold; font-size: 1.05em;">{style['icon']} {title} — <small style="font-weight: normal;">({region})</small></span>
                                <span style="background-color: {style['badge_bg']}; color: {style['badge_text']}; padding: 3px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold;">{style['label']}</span>
                            </div>
                            <p style="margin: 0; font-size: 0.95em;">{message}</p>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info(
                    "🟢 No severe weather warnings active across the 48 wilayas."
                )

        # SERVICE 5: PAYMENTS
        elif st.session_state.selected_service == "pay":
            st.subheader(t["pay"])
            st.write("Annual Subscription Fee: **2,500 DZD**")
            st.radio(
                "Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"]
            )
            st.text_input(
                "Card Number:", placeholder="6037 XXXX XXXX XXXX"
            )
            if st.button("Confirm Payment", type="primary"):
                st.success("Carte Fellah renewed for season 2026/2027!")

        # SERVICE 6: MAPS DIRECTORY
        elif st.session_state.selected_service == "suppliers":
            st.subheader(
                "🗺️ خريطة الموزعين وأسوق الجملة ونقاط CCLS"
            )
            try:
                res = (
                    supabase_client.table("suppliers_directory")
                    .select("*")
                    .execute()
                )
                db_locations = res.data if res.data else []
            except Exception:
                db_locations = []

            all_locations = DEFAULT_AGRI_LOCATIONS + db_locations
            selected_cat = st.selectbox(
                "Filter Points by Type / تصفية حسب النوع:",
                [
                    "All",
                    "Wholesale Produce Market",
                    "OAIC Cereal Silo (CCLS)",
                    "ASMIDAL Fertilizer Depot",
                ],
            )

            filtered_locs = (
                all_locations
                if selected_cat == "All"
                else [
                    loc
                    for loc in all_locations
                    if loc.get("category") == selected_cat
                ]
            )

            m = folium.Map(
                location=[34.5000, 3.2000],
                zoom_start=6,
                tiles="OpenStreetMap",
            )
            color_map = {
                "Wholesale Produce Market": "green",
                "OAIC Cereal Silo (CCLS)": "cadetblue",
                "ASMIDAL Fertilizer Depot": "orange",
            }

            for loc in filtered_locs:
                lat, lon = float(loc.get("lat", 36.7323)), float(
                    loc.get("lon", 3.1678)
                )
                name, wilaya, cat = (
                    loc.get("name", "Agricultural Point"),
                    loc.get("wilaya", ""),
                    loc.get("category", ""),
                )
                maps_url = loc.get(
                    "maps_link", f"https://maps.google.com/?q={lat},{lon}"
                )

                popup_html = f"""
                <div style="font-family: Arial; width: 200px;">
                    <h4 style="margin:0; color:#0b8a62;">{name}</h4>
                    <p style="margin:0; font-size:12px;"><b>Cat:</b> {cat}</p>
                    <a href="{maps_url}" target="_blank" style="display:inline-block; margin-top:5px; background:#4285F4; color:white; padding:4px 8px; border-radius:4px; font-size:11px; text-decoration:none;">🗺️ Open Google Maps</a>
                </div>
                """
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=220),
                    tooltip=name,
                    icon=folium.Icon(color=color_map.get(cat, "blue")),
                ).add_to(m)

            st_folium(m, width=700, height=450)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: DIGITAL CARTE FELLAH (ANIMATED)
# ---------------------------------------------------------
elif st.session_state.active_tab == "card":
    st.markdown(
        '<div class="animated-tab-content">', unsafe_allow_html=True
    )
    st.subheader("Digital Carte Fellah - البطاقة الفلاحية الرقمية")

    if st.session_state.logged_in:
        st.markdown(
            f"""
            <div style="border: 2px solid #0b8a62; border-radius: 15px; padding: 20px; background: {card_bg}; text-align: center;">
                <h3 style="color: #0b8a62; margin-top:0;">الجمهورية الجزائرية الديمقراطية الشعبية</h3>
                <p><b>وزارة الفلاحة والتنمية الريفية</b></p>
                <hr style="border-color: {border_color};">
                <div style="text-align: right; display: inline-block;">
                    <p><b>Farmer Name / الاسم:</b> {st.session_state.farmer_name}</p>
                    <p><b>Email / البريد:</b> {st.session_state.farmer_email}</p>
                    <p><b>Card N° / رقم البطاقة:</b> {st.session_state.carte_num}</p>
                    <p><b>Status / الحالة:</b> <span style="color: #0b8a62; font-weight: bold;">ACTIVE / 2026 Valid</span></p>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("Please log in to view your digital card.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 3: PERSONAL HUB & OWNER ADMIN CONSOLE (ANIMATED)
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
    st.markdown(
        '<div class="animated-tab-content">', unsafe_allow_html=True
    )

    # PART 1: FARMER'S PERSONAL HUB
    if st.session_state.logged_in:
        st.subheader(f"👋 Welcome, {st.session_state.farmer_name}")
        st.caption(
            f"Connected Email: `{st.session_state.farmer_email}` | Card N°: `{st.session_state.carte_num}`"
        )

        acc_tab1, acc_tab2, acc_tab3 = st.tabs([
            "🔔 Notifications",
            "📜 My Crop Declarations",
            "📄 My Subsidies Requests",
        ])

        with acc_tab1:
            st.subheader("Your Official Notifications")
            try:
                res_notif = (
                    supabase_client.table("farmer_notifications")
                    .select("*")
                    .eq("farmer_email", st.session_state.farmer_email)
                    .order("id", desc=True)
                    .execute()
                )
                notifs = res_notif.data if res_notif.data else []

                if notifs:
                    for n in notifs:
                        st.markdown(
                            f"""
                            <div class="notif-card">
                                <b>📩 {sanitize(n.get('title',''))}</b>
                                <p style="margin:4px 0;">{sanitize(n.get('message',''))}</p>
                                <small style="color:gray;">{n.get('created_at','')[:10]}</small>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )

                    if st.button("Mark All Notifications as Read"):
                        supabase_client.table(
                            "farmer_notifications"
                        ).update({"is_read": True}).eq(
                            "farmer_email",
                            st.session_state.farmer_email,
                        ).execute()
                        st.success("Notifications updated.")
                        st.rerun()
                else:
                    st.info(
                        "No personal notifications at this moment."
                    )
            except Exception as e:
                st.error(f"Error reading notifications: {e}")

        with acc_tab2:
            st.subheader("Submitted Crop Declarations")
            try:
                res_dec = (
                    supabase_client.table("declarations")
                    .select("*")
                    .eq("carte_num", st.session_state.carte_num)
                    .execute()
                )
                if res_dec.data:
                    df_dec = pd.DataFrame(res_dec.data)
                    st.dataframe(
                        df_dec[[
                            "crop",
                            "category",
                            "area",
                            "wilaya",
                            "start_date",
                        ]],
                        use_container_width=True,
                    )
                else:
                    st.info("No crop declarations on file.")
            except Exception as e:
                st.error(f"Error fetching declarations: {e}")

        with acc_tab3:
            st.subheader("Subsidies & Equipment Applications")
            try:
                res_sup = (
                    supabase_client.table("support_requests")
                    .select("*")
                    .eq("carte_num", st.session_state.carte_num)
                    .execute()
                )
                if res_sup.data:
                    df_sup = pd.DataFrame(res_sup.data)
                    st.dataframe(
                        df_sup[[
                            "sector",
                            "wilaya",
                            "status",
                            "created_at",
                        ]],
                        use_container_width=True,
                    )
                else:
                    st.info("No active subsidy applications on file.")
            except Exception as e:
                st.error(f"Error fetching subsidy demands: {e}")

        st.divider()

    else:
        st.info(
            "👈 Please log in from the left sidebar menu to see your personal records and notifications."
        )
        st.divider()

    # PART 2: OWNER ADMIN DASHBOARD MANAGEMENT
    st.subheader(
        "🔐 Owner / Portal Admin Management Console"
    )

    if not st.session_state.admin_authenticated:
        admin_input_pass = st.text_input(
            "Enter Admin Security Secret Code",
            type="password",
            key="admin_pwd",
        )
        if st.button("Unlock Admin Panel", type="primary"):
            if admin_input_pass == get_admin_password():
                st.session_state.admin_authenticated = True
                st.success("Access Granted to Portal Admin Console.")
                st.rerun()
            else:
                st.error("Invalid Secret Key.")
    else:
        st.success("🔓 Authenticated as System Administrator")

        adm_tab1, adm_tab2, adm_tab3, adm_tab4 = st.tabs([
            "📢 Post News & Alerts",
            "📨 Send Farmer Notifications",
            "📍 Add Map Location",
            "📊 View All Database Records",
        ])

        # ADMIN TAB 1: NEWS AND ALERTS
        with adm_tab1:
            st.markdown("#### Post Weather Alert")
            al_title = st.text_input(
                "Alert Title", placeholder="e.g. Sirocco Heatwave Warning"
            )
            al_region = st.selectbox(
                "Target Wilaya", ["All Wilayas"] + WILAYAS_48
            )
            al_severity = st.selectbox(
                "Severity Level", ["yellow", "orange", "red"]
            )
            al_msg = st.text_area("Alert Message Body")

            if st.button("Broadcast Weather Alert"):
                try:
                    supabase_client.table("weather_alerts").insert({
                        "title": sanitize(al_title),
                        "region": al_region,
                        "severity": al_severity,
                        "message": sanitize(al_msg),
                    }).execute()
                    st.success("Weather Alert Published!")
                except Exception as e:
                    st.error(f"Failed to post alert: {e}")

            st.divider()
            st.markdown("#### Post Portal News Release")
            news_title = st.text_input("Article Title")
            news_cat = st.selectbox(
                "News Category",
                ["General", "Subsidies", "Weather", "Market Prices"],
            )
            news_body = st.text_area("Article Content Body")

            if st.button("Publish News Release"):
                try:
                    supabase_client.table("portal_news").insert({
                        "title": sanitize(news_title),
                        "category": news_cat,
                        "content": sanitize(news_body),
                    }).execute()
                    st.success("Official News Article Published!")
                except Exception as e:
                    st.error(f"Failed to publish news: {e}")

        # ADMIN TAB 2: DIRECT NOTIFICATIONS
        with adm_tab2:
            st.markdown("#### Send Targeted Notification to Farmer")
            target_email = st.text_input(
                "Target Farmer Email", placeholder="farmer@domain.dz"
            )
            notif_title = st.text_input("Notification Subject Title")
            notif_body = st.text_area("Message Body Text")

            if st.button("Dispatch Direct Notification"):
                try:
                    supabase_client.table(
                        "farmer_notifications"
                    ).insert({
                        "farmer_email": sanitize(target_email),
                        "title": sanitize(notif_title),
                        "message": sanitize(notif_body),
                        "is_read": False,
                    }).execute()
                    st.success(
                        f"Notification dispatched to {target_email}!"
                    )
                except Exception as e:
                    st.error(f"Dispatch failed: {e}")

        # ADMIN TAB 3: ADD DIRECTORY LOCATION
        with adm_tab3:
            st.markdown("#### Add Location to Map Directory")
            loc_name = st.text_input("Facility Name")
            loc_wilaya = st.selectbox(
                "Wilaya Location", WILAYAS_48, key="adm_w_dir"
            )
            loc_cat = st.selectbox(
                "Facility Type",
                [
                    "Wholesale Produce Market",
                    "OAIC Cereal Silo (CCLS)",
                    "ASMIDAL Fertilizer Depot",
                ],
            )
            loc_lat = st.number_input(
                "Latitude coordinate", value=36.7323, format="%.4f"
            )
            loc_lon = st.number_input(
                "Longitude coordinate", value=3.1678, format="%.4f"
            )
            loc_address = st.text_input("Address details")
            loc_maps = st.text_input("Google Maps URL link")

            if st.button("Save New Location"):
                try:
                    supabase_client.table(
                        "suppliers_directory"
                    ).insert({
                        "name": sanitize(loc_name),
                        "wilaya": loc_wilaya,
                        "category": loc_cat,
                        "lat": loc_lat,
                        "lon": loc_lon,
                        "address": sanitize(loc_address),
                        "maps_link": sanitize(loc_maps),
                    }).execute()
                    st.success("Location added to public directory!")
                except Exception as e:
                    st.error(f"Failed to insert map point: {e}")

        # ADMIN TAB 4: DATABASE TABLES INSPECTION
        with adm_tab4:
            st.markdown("#### System Database Inspector")
            table_choice = st.selectbox(
                "Select Database Table to Inspect",
                [
                    "farmer_profiles",
                    "declarations",
                    "support_requests",
                    "farmer_notifications",
                    "weather_alerts",
                    "portal_news",
                    "suppliers_directory",
                ],
            )

            try:
                res_all = (
                    supabase_client.table(table_choice)
                    .select("*")
                    .execute()
                )
                if res_all.data:
                    st.dataframe(
                        pd.DataFrame(res_all.data),
                        use_container_width=True,
                    )
                else:
                    st.info(
                        f"Table `{table_choice}` is currently empty."
                    )
            except Exception as e:
                st.error(f"Failed to query table: {e}")

        if st.button("🔒 Lock Admin Console"):
            st.session_state.admin_authenticated = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
