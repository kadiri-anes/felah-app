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
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_admin_password() -> str:
    """Retrieve admin password securely from secrets or fallback."""
    return st.secrets.get("ADMIN_PASSWORD", "greatdz")

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(page_title="Felah Mobile Portal - Algeria", page_icon="🌾", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .mobile-sidebar-notice {
        background-color: #e6f4ea;
        border: 2px dashed #0b8a62;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 15px;
        font-weight: bold;
        color: #0b8a62;
    }
    .promo-banner {
        background: linear-gradient(135deg, #0b8a62 0%, #1e5340 100%);
        color: white;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 12px;
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
    .market-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 10px; padding: 12px; margin-bottom: 10px; }
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
# PRESET ALGERIAN AGRICULTURAL LOCATIONS & DATA
# ---------------------------------------------------------
DEFAULT_AGRI_LOCATIONS = [
    {"name": "Wholesale Market (EPLFM MAGRO)", "wilaya": "16 - Alger", "category": "Wholesale Produce Market", "lat": 36.7323, "lon": 3.1678, "maps_link": "https://maps.google.com/?q=36.7323,3.1678"},
    {"name": "CCLS Silo & Grain Point", "wilaya": "19 - Sétif", "category": "OAIC Cereal Silo (CCLS)", "lat": 36.1911, "lon": 5.4137, "maps_link": "https://maps.google.com/?q=36.1911,5.4137"},
    {"name": "Asmidal Fertilizer Depot", "wilaya": "23 - Annaba", "category": "ASMIDAL Fertilizer Depot", "lat": 36.9000, "lon": 7.7667, "maps_link": "https://maps.google.com/?q=36.9000,7.7667"},
    {"name": "Wholesale Market (Attaf)", "wilaya": "44 - Aïn Defla", "category": "Wholesale Produce Market", "lat": 36.2238, "lon": 1.9682, "maps_link": "https://maps.google.com/?q=36.2238,1.9682"},
    {"name": "CCLS Cereal Storage Depot", "wilaya": "14 - Tiaret", "category": "OAIC Cereal Silo (CCLS)", "lat": 35.3710, "lon": 1.3169, "maps_link": "https://maps.google.com/?q=35.3710,1.3169"},
    {"name": "Wholesale Dates Market", "wilaya": "07 - Biskra", "category": "Wholesale Produce Market", "lat": 34.8502, "lon": 5.7281, "maps_link": "https://maps.google.com/?q=34.8502,5.7281"},
    {"name": "CCLS Grain Point El Oued", "wilaya": "39 - El Oued", "category": "OAIC Cereal Silo (CCLS)", "lat": 33.3683, "lon": 6.8674, "maps_link": "https://maps.google.com/?q=33.3683,6.8674"},
    {"name": "Fertilizer & Seed Point (OAIC)", "wilaya": "25 - Constantine", "category": "ASMIDAL Fertilizer Depot", "lat": 36.3650, "lon": 6.6147, "maps_link": "https://maps.google.com/?q=36.3650,6.6147"}
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
    "yellow": {
        "bg_color": "#fff9c4",
        "border_color": "#fbc02d",
        "text_color": "#574200",
        "badge_bg": "#fbc02d",
        "badge_text": "#000000",
        "icon": "⚠️",
        "label": "Yellow / Vigilance (يقظة)"
    },
    "orange": {
        "bg_color": "#ffe0b2",
        "border_color": "#f57c00",
        "text_color": "#4a2400",
        "badge_bg": "#f57c00",
        "badge_text": "#ffffff",
        "icon": "🍊",
        "label": "Orange / High Alert (حذر شديد)"
    },
    "red": {
        "bg_color": "#ffcdd2",
        "border_color": "#d32f2f",
        "text_color": "#490c0c",
        "badge_bg": "#d32f2f",
        "badge_text": "#ffffff",
        "icon": "🚨",
        "label": "Red / Extreme Danger (خطر أقصى)"
    }
}

def get_current_crop_area(crop_name: str) -> float:
    try:
        res = supabase_client.table("declarations").select("area").eq("crop", crop_name).execute()
        if res and res.data:
            return sum(item["area"] for item in res.data if item.get("area") is not None)
    except Exception:
        return 0.0
    return 0.0

# ---------------------------------------------------------
# Session State Initializer
# ---------------------------------------------------------
if 'lang' not in st.session_state: st.session_state.lang = 'AR'
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'farmer_name' not in st.session_state: st.session_state.farmer_name = ""
if 'carte_num' not in st.session_state: st.session_state.carte_num = ""
if 'active_tab' not in st.session_state: st.session_state.active_tab = "home"
if 'selected_service' not in st.session_state: st.session_state.selected_service = None
if 'admin_attempts' not in st.session_state: st.session_state.admin_attempts = 0
if 'admin_authenticated' not in st.session_state: st.session_state.admin_authenticated = False
if 'captcha_num1' not in st.session_state:
    st.session_state.captcha_num1 = random.randint(1, 9)
    st.session_state.captcha_num2 = random.randint(1, 9)

def generate_new_captcha():
    st.session_state.captcha_num1 = random.randint(1, 9)
    st.session_state.captcha_num2 = random.randint(1, 9)

TEXTS = {
    'AR': {
        'title': "بوابة الفلاح - 48 ولاية",
        'banner': "برنامج التخطيط والتنسيق الفلاحي 2026",
        'home': "الرئيسية",
        'card': "بطاقتي",
        'account': "حسابي",
        'weather': "الأحوال الجوية والتنبيهات",
        'crop': "نصائح الزراعة والتصريح (QR)",
        'pay': "تجديد بطاقة الفلاح (CIB/الذهبية)",
        'suppliers': "خريطة أسواق الجملة، نقاط CCLS والأسمدة",
        'support': "طلب دعم الدولة (الدعم الفلاحي)",
        'news': "الأخبار والإعلانات الرسمية",
        'admin': "لوحة تحكم المالِك (Owner Admin)"
    },
    'EN': {
        'title': "Felah Farmer Portal - 48 Wilayas",
        'banner': "Agricultural Planning & Coordination Program 2026",
        'home': "Home",
        'card': "My Card",
        'account': "Account",
        'weather': "Weather & Ag-Alerts",
        'crop': "Cultivation & QR Permit",
        'pay': "Carte Fellah Subscription",
        'suppliers': "Wholesale Markets, CCLS & Fertilizer Map",
        'support': "Government Agricultural Support",
        'news': "News & Official Announcements",
        'admin': "Owner Admin Dashboard"
    }
}

t = TEXTS[st.session_state.lang]

# ---------------------------------------------------------
# SIDEBAR NAVIGATION & LOGIN
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="background-color: #0b8a62; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px;">
            ⚙️ MENU / القائمة
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🌐 Language / اللغة")
    selected_lang = st.radio("Choose Language", ["العربية", "English"], key="sb_lang", label_visibility="collapsed")
    st.session_state.lang = 'AR' if selected_lang == "العربية" else 'EN'
    st.divider()
    
    st.markdown("### 👤 Account / تسجيل الدخول")
    if not st.session_state.logged_in:
        farmer_name_input = st.text_input("Name / الاسم", placeholder="Enter full name", key="sb_name")
        carte_num_input = st.text_input("Carte Fellah N°", placeholder="e.g. DZ-2026-XXXXX", key="sb_card")
        
        correct_answer = st.session_state.captcha_num1 + st.session_state.captcha_num2
        st.write(f"**Security Check:** `{st.session_state.captcha_num1} + {st.session_state.captcha_num2}` = ?")
        captcha_input = st.text_input("Answer", placeholder="Result", key="sb_captcha", label_visibility="collapsed")

        if st.button("🔓 Log In / دخول", use_container_width=True, type="primary"):
            if not farmer_name_input.strip() or not carte_num_input.strip():
                st.error("Please fill in both Name and Card Number.")
            elif str(captcha_input).strip() != str(correct_answer):
                st.error("Incorrect CAPTCHA answer.")
                generate_new_captcha()
            else:
                st.session_state.logged_in = True
                st.session_state.farmer_name = sanitize(farmer_name_input)
                st.session_state.carte_num = sanitize(carte_num_input)
                generate_new_captcha()
                st.rerun()
    else:
        st.success(f"🟢 Connected:\n**{st.session_state.farmer_name}**")
        st.caption(f"Card N°: `{st.session_state.carte_num}`")
        if st.button("🔒 Log Out / خروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.farmer_name = ""
            st.session_state.carte_num = ""
            st.session_state.admin_authenticated = False
            st.rerun()

# ---------------------------------------------------------
# TOP STATUS HEADER
# ---------------------------------------------------------
mobile_status = f"🟢 Connected: {st.session_state.farmer_name}" if st.session_state.logged_in else "🔴 Not Logged In — Click top-left arrow ↗ to Login"
st.markdown(f'<div class="mobile-sidebar-notice">👉 {mobile_status}</div>', unsafe_allow_html=True)
st.markdown(f"<h2 style='text-align: center;'>{t['title']}</h2>", unsafe_allow_html=True)
st.markdown(f"""
    <div class="promo-banner">
        <h4 style="margin:0;">{t['banner']}</h4>
        <small>الجمهورية الجزائرية الديمقراطية الشعبية - وزارة الفلاحة والتنمية الريفية</small>
    </div>
""", unsafe_allow_html=True)

nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    if st.button(f"{t['home']}", use_container_width=True): st.session_state.active_tab = "home"
with nav_col2:
    if st.button(f"{t['card']}", use_container_width=True): st.session_state.active_tab = "card"
with nav_col3:
    if st.button(f"{t['account']}", use_container_width=True): st.session_state.active_tab = "account"

st.divider()

# ---------------------------------------------------------
# VIEW 1: HOME DASHBOARD & SERVICES
# ---------------------------------------------------------
if st.session_state.active_tab == "home":
    st.subheader("الخدمات الإلكترونية / Main Services")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t['crop'], use_container_width=True, type="primary"): st.session_state.selected_service = "crop"
        if st.button(t['support'], use_container_width=True): st.session_state.selected_service = "support"
        if st.button(t['pay'], use_container_width=True): st.session_state.selected_service = "pay"
    
    with col2:
        if st.button(t['news'], use_container_width=True): st.session_state.selected_service = "news"
        if st.button(t['weather'], use_container_width=True): st.session_state.selected_service = "weather"
        if st.button(t['suppliers'], use_container_width=True): st.session_state.selected_service = "suppliers"

    st.divider()

    # --- SERVICE 1: AGRICULTURAL SUPPORT DEMAND ---
    if st.session_state.selected_service == "support":
        st.subheader(t['support'])
        st.write("Submit official requests for Ministry subsidies (Geomembrane basins, well digging, solar, drip irrigation).")
        
        if not st.session_state.logged_in:
            st.warning("⚠️ Please log in from the left menu ↗ to submit a support demand.")
        else:
            selected_w_sup = st.selectbox("Wilaya / الولاية", WILAYAS_48, key="sup_w")
            selected_sector = st.selectbox("Select Subsidized Sector / اختر مجال الدعم", list(SUPPORT_SECTORS.keys()))
            
            st.markdown(f"#### 📄 Required Documents for `{selected_sector}`:")
            req_docs = SUPPORT_SECTORS[selected_sector]
            for doc in req_docs:
                st.write(f"• **{doc}**")
            
            st.divider()
            st.write("### Attach Your Files & Papers (رفع الملفات والوثائق)")
            uploaded_files = {}
            
            for idx, doc in enumerate(req_docs):
                up_file = st.file_uploader(f"Upload: {doc}", type=["pdf", "jpg", "jpeg", "png"], key=f"file_{idx}")
                if up_file:
                    uploaded_files[doc] = up_file
            
            additional_notes = st.text_area("Additional Notes / ملاحظات إضافية", placeholder="Describe your farm capacity or specific project details...")

            if st.button("Submit Support Demand (إرسال طلب الدعم)", type="primary", use_container_width=True):
                if len(uploaded_files) < len(req_docs):
                    st.error(f"Please upload all {len(req_docs)} required documents before submitting.")
                else:
                    uploaded_links = {}
                    try:
                        with st.spinner("Uploading documents securely to Supabase Storage..."):
                            for doc_name, file_obj in uploaded_files.items():
                                clean_filename = f"{st.session_state.carte_num}_{random.randint(1000,9999)}_{file_obj.name}"
                                file_path = f"support_docs/{clean_filename}"
                                file_bytes = file_obj.read()
                                
                                res = supabase_client.storage.from_("agricultural-docs").upload(file_path, file_bytes)
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

                            st.success("🎉 Your Agricultural Support demand has been submitted successfully!")
                    except Exception as e:
                        st.error(f"Error submitting request: {e}")

    # --- SERVICE 2: NEWS & ANNOUNCEMENTS ---
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
                        <h4 style="margin: 8px 0 5px 0; color: #1e5340;">📢 {sanitize(n.get("title",""))}</h4>
                        <p style="margin: 0; color: #333;">{sanitize(n.get("content",""))}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📰 No official news releases published today.")

    # --- SERVICE 3: DECLARATION & QUOTA SYSTEM (WITH CULTIVATION START DATE) ---
    elif st.session_state.selected_service == "crop":
        st.subheader(t['crop'])
        selected_w = st.selectbox("Wilaya / الولاية (48 Wilayas)", WILAYAS_48)
        cat_choice = st.radio("Category / الصنف:", ["Vegetables (خضروات)", "Fruits (فواكه)"])
        area_ha = st.number_input("Your Farming Area (Hectares / هكتار)", min_value=0.1, value=5.0, max_value=10000.0)
        
        # New Field: Date of Starting Cultivation
        start_date = st.date_input("Date of Starting Cultivation / تاريخ بداية الزراعة", value=date.today())
        
        if cat_choice == "Fruits (فواكه)":
            selected_c = st.selectbox("Select Fruit / اختر الفاكهة", FRUIT_LIST)
            st.success("Unlimited Capacity / بدون حد أقصى — Fruit cultivation is open without national hectare restrictions.")
        else:
            selected_c = st.selectbox("Select Vegetable / اختر الخضار", list(VEGETABLE_LIMITS.keys()))
            limit = VEGETABLE_LIMITS[selected_c]
            current_total = get_current_crop_area(selected_c)
            projected_total = current_total + area_ha
            percentage = min((projected_total / limit), 1.0)
            
            st.write(f"**National Area Quota Status ({selected_c}):**")
            st.progress(percentage)
            st.caption(f"Currently Registered: {current_total:.1f} Ha | Your Input: {area_ha:.1f} Ha | Target Limit: {limit:.0f} Ha")

        if st.button("Submit & Generate QR Permit"):
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
                    qr_payload = f"FELAH-PERMIT|{st.session_state.farmer_name}|{st.session_state.carte_num}|{selected_w}|{selected_c}|{area_ha}HA|START:{start_date}"
                    qr = qrcode.make(qr_payload)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    st.image(buf.getvalue(), caption=f"Official QR Permit (Start Date: {start_date})", width=220)
                except Exception as e:
                    st.error(f"Failed to record declaration: {e}")
            else:
                st.warning("Please log in first.")

    # --- SERVICE 4: WEATHER ALERTS ---
    elif st.session_state.selected_service == "weather":
        st.subheader(t['weather'])
        
        try:
            res = supabase_client.table("weather_alerts").select("*").order("id", desc=True).execute()
            alerts = res.data if res.data else []
        except Exception: 
            alerts = []
        
        if alerts:
            for item in alerts:
                title = sanitize(item.get("title", "Weather Notice"))
                region = sanitize(item.get("region", "All Wilayas"))
                message = sanitize(item.get("message", ""))
                
                raw_level = str(item.get("severity", "yellow")).lower().strip()
                style = ALERT_STYLES.get(raw_level, ALERT_STYLES["yellow"])

                st.markdown(f"""
                    <div style="
                        background-color: {style['bg_color']};
                        border-left: 6px solid {style['border_color']};
                        border-radius: 8px;
                        padding: 14px 16px;
                        margin-bottom: 14px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        color: {style['text_color']};
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-weight: bold; font-size: 1.05em;">
                                {style['icon']} {title} — <small style="font-weight: normal;">({region})</small>
                            </span>
                            <span style="
                                background-color: {style['badge_bg']};
                                color: {style['badge_text']};
                                padding: 3px 8px;
                                border-radius: 4px;
                                font-size: 0.75em;
                                font-weight: bold;
                                text-transform: uppercase;
                            ">{style['label']}</span>
                        </div>
                        <p style="margin: 0; font-size: 0.95em; line-height: 1.4;">{message}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("🟢 No severe weather warnings active across the 48 wilayas.")

    # --- SERVICE 5: PAYMENTS ---
    elif st.session_state.selected_service == "pay":
        st.subheader(t['pay'])
        st.write("Annual Subscription Fee: **2,500 DZD**")
        st.radio("Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"])
        st.text_input("Card Number:", placeholder="6037 XXXX XXXX XXXX")
        if st.button("Confirm Payment"): st.success("Carte Fellah renewed for season 2026/2027!")

    # --- SERVICE 6: MAPS DIRECTORY FOR MARKETS, CCLS & FERTILIZER DEPOTS ---
    elif st.session_state.selected_service == "suppliers":
        st.subheader("🗺️ خريطة الموزعين وأسوق الجملة ونقاط CCLS")
        st.caption("Interactive Map — Click any marker on the map to get direct Google Maps navigation.")
        
        try:
            res = supabase_client.table("suppliers_directory").select("*").execute()
            db_locations = res.data if res.data else []
        except Exception:
            db_locations = []
            
        all_locations = DEFAULT_AGRI_LOCATIONS + db_locations

        categories = ["All", "Wholesale Produce Market", "OAIC Cereal Silo (CCLS)", "ASMIDAL Fertilizer Depot"]
        selected_cat = st.selectbox("Filter Points by Type / تصفية حسب النوع:", categories)

        if selected_cat != "All":
            filtered_locs = [loc for loc in all_locations if loc.get("category") == selected_cat]
        else:
            filtered_locs = all_locations

        m = folium.Map(location=[34.5000, 3.2000], zoom_start=6, tiles="OpenStreetMap")

        color_map = {
            "Wholesale Produce Market": "green",
            "OAIC Cereal Silo (CCLS)": "cadetblue",
            "ASMIDAL Fertilizer Depot": "orange"
        }

        for loc in filtered_locs:
            lat = float(loc.get("lat", 36.7323))
            lon = float(loc.get("lon", 3.1678))
            name = loc.get("name", "Agricultural Point")
            wilaya = loc.get("wilaya", "")
            cat = loc.get("category", "")
            maps_url = loc.get("maps_link", f"https://maps.google.com/?q={lat},{lon}")

            popup_html = f"""
            <div style="font-family: Arial; width: 210px;">
                <h4 style="margin:0 0 5px 0; color:#0b8a62;">{name}</h4>
                <p style="margin:0; font-size:12px;"><b>Category:</b> {cat}</p>
                <p style="margin:0 0 8px 0; font-size:12px;"><b>Wilaya:</b> {wilaya}</p>
                <a href="{maps_url}" target="_blank" style="
                    display: inline-block;
                    background-color: #4285F4;
                    color: white;
                    padding: 6px 12px;
                    text-decoration: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                ">🗺️ Open in Google Maps ↗</a>
            </div>
            """
            
            icon_color = color_map.get(cat, "blue")
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{name} ({wilaya})",
                icon=folium.Icon(color=icon_color, icon="info-sign")
            ).add_to(m)

        st_folium(m, width=700, height=480)

        st.divider()
        st.write("### Directory List / القائمة التفصيلية")
        for loc in filtered_locs:
            lat = float(loc.get("lat", 36.7323))
            lon = float(loc.get("lon", 3.1678))
            maps_url = loc.get("maps_link", f"https://maps.google.com/?q={lat},{lon}")
            st.markdown(f"""
                <div class="market-card">
                    <h4 style="margin: 0; color: #0b8a62;">📍 {loc.get('name')}</h4>
                    <p style="margin: 2px 0;"><b>Wilaya:</b> {loc.get('wilaya')} | <b>Category:</b> {loc.get('category')}</p>
                    <a href="{maps_url}" target="_blank" style="color: #1a73e8; font-weight: bold;">🗺️ Open Location in Google Maps ↗</a>
                </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# VIEW 2: CARTE FELLAH
# ---------------------------------------------------------
elif st.session_state.active_tab == "card":
    st.subheader("Digital Carte Fellah - البطاقة الفلاحية الرقمية")
    if st.session_state.logged_in:
        st.markdown(f"""
            <div style="border: 2px solid #0b8a62; border-radius: 15px; padding: 20px; background: white;">
                <h3 style="color: #0b8a62;">الجمهورية الجزائرية الديمقراطية الشعبية</h3>
                <p><b>وزارة الفلاحة والتنمية الريفية</b></p>
                <hr>
                <p><b>Farmer Name:</b> {st.session_state.farmer_name}</p>
                <p><b>Card N°:</b> {st.session_state.carte_num}</p>
                <p><b>Status:</b> <span style="color: green; font-weight: bold;">ACTIVE / 2026 Valid</span></p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Please log in to view your digital card.")

# ---------------------------------------------------------
# VIEW 3: OWNER-ONLY ADMIN DASHBOARD (SLIDE-TAB CONTROL PANEL)
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
    st.subheader("Account Info & Owner Dashboard")
    if st.session_state.logged_in:
        st.write(f"Logged in as: **{st.session_state.farmer_name}** | Card: `{st.session_state.carte_num}`")
    st.divider()
    
    st.subheader(t['admin'])
    if not st.session_state.admin_authenticated:
        admin_pass = st.text_input("Enter Admin Password", type="password")
        if st.button("Authenticate Admin"):
            if hash_password(admin_pass) == hash_password(get_admin_password()):
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect Password.")
    else:
        st.success("Owner Access Granted!")
        if st.button("🔒 Lock Admin Session"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.divider()

        # SLIDE CONTROL PANEL USING TABBED SLIDES
        tab_w, tab_m, tab_n, tab_s, tab_d = st.tabs([
            "🌩️ Weather Alerts", 
            "📍 Map Pins", 
            "📢 News", 
            "📋 Support Demands", 
            "🌱 Declarations"
        ])

        # --- SLIDE 1: WEATHER ALERTS ---
        with tab_w:
            st.write("### 🌩️ Weather Warning Management")
            w_title = st.text_input("Alert Title", placeholder="e.g. Sirocco / Extreme Heat")
            w_region = st.selectbox("Wilaya / Region", WILAYAS_48, key="w_reg_admin")
            w_severity = st.selectbox("Warning Severity Level (Color)", ["yellow", "orange", "red"], format_func=lambda x: f"{x.upper()} Threat Level")
            w_msg = st.text_area("Alert Message details...")

            if st.button("Publish Weather Alert Live", type="primary"):
                if w_title.strip() and w_msg.strip():
                    try:
                        supabase_client.table("weather_alerts").insert({
                            "title": sanitize(w_title),
                            "region": w_region,
                            "severity": w_severity,
                            "message": sanitize(w_msg)
                        }).execute()
                        st.success(f"Weather alert published in {w_severity.upper()} level color!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to publish alert: {e}")

            st.divider()
            st.write("#### 📜 Active Weather Alerts Database")
            try:
                w_res = supabase_client.table("weather_alerts").select("*").order("id", desc=True).execute()
                w_list = w_res.data if w_res.data else []
            except Exception:
                w_list = []

            if w_list:
                df_w = pd.DataFrame(w_list)
                st.dataframe(df_w, use_container_width=True)

                w_del_id = st.number_input("Enter Weather Alert ID to Delete:", min_value=1, step=1, key="del_w_id")
                if st.button("Delete Weather Alert", type="primary", key="btn_del_w"):
                    try:
                        supabase_client.table("weather_alerts").delete().eq("id", w_del_id).execute()
                        st.success(f"Weather alert ID {w_del_id} deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting record: {e}")
            else:
                st.info("No weather alerts recorded in database.")

        # --- SLIDE 2: MAP LOCATIONS ---
        with tab_m:
            st.write("### 📍 Add New Map Location Pin")
            m_name = st.text_input("Location Name")
            m_wil = st.selectbox("Wilaya", WILAYAS_48, key="m_w_admin")
            m_cat = st.selectbox("Type", ["Wholesale Produce Market", "OAIC Cereal Silo (CCLS)", "ASMIDAL Fertilizer Depot"])
            m_lat = st.number_input("Latitude", value=36.7323, format="%.4f")
            m_lon = st.number_input("Longitude", value=3.1678, format="%.4f")
            
            if st.button("Add Pin to Map Live", type="primary"):
                if m_name.strip():
                    try:
                        maps_auto_url = f"https://maps.google.com/?q={m_lat},{m_lon}"
                        supabase_client.table("suppliers_directory").insert({
                            "name": sanitize(m_name),
                            "wilaya": m_wil,
                            "category": m_cat,
                            "lat": m_lat,
                            "lon": m_lon,
                            "maps_link": maps_auto_url
                        }).execute()
                        st.success("Location added live to map!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding location: {e}")

            st.divider()
            st.write("#### 📜 Map Locations Database")
            try:
                m_res = supabase_client.table("suppliers_directory").select("*").order("id", desc=True).execute()
                m_list = m_res.data if m_res.data else []
            except Exception:
                m_list = []

            if m_list:
                df_m = pd.DataFrame(m_list)
                st.dataframe(df_m, use_container_width=True)

                m_del_id = st.number_input("Enter Map Location ID to Delete:", min_value=1, step=1, key="del_m_id")
                if st.button("Delete Location Pin", type="primary", key="btn_del_m"):
                    try:
                        supabase_client.table("suppliers_directory").delete().eq("id", m_del_id).execute()
                        st.success(f"Map Location ID {m_del_id} deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting location: {e}")
            else:
                st.info("No custom map pins recorded in database.")

        # --- SLIDE 3: NEWS & ANNOUNCEMENTS ---
        with tab_n:
            st.write("### 📢 Publish Official News Announcement")
            n_title = st.text_input("News Title")
            n_cat = st.selectbox("Category", ["Official Notice", "Subsidies", "Weather", "Export/Import", "General"])
            n_content = st.text_area("Content Details")

            if st.button("Publish News Release", type="primary"):
                if n_title.strip() and n_content.strip():
                    try:
                        supabase_client.table("portal_news").insert({
                            "title": sanitize(n_title),
                            "category": n_cat,
                            "content": sanitize(n_content)
                        }).execute()
                        st.success("News published live!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to publish news: {e}")

            st.divider()
            st.write("#### 📜 Published News Database")
            try:
                n_res = supabase_client.table("portal_news").select("*").order("id", desc=True).execute()
                n_list = n_res.data if n_res.data else []
            except Exception:
                n_list = []

            if n_list:
                df_n = pd.DataFrame(n_list)
                st.dataframe(df_n, use_container_width=True)

                n_del_id = st.number_input("Enter News ID to Delete:", min_value=1, step=1, key="del_n_id")
                if st.button("Delete News Entry", type="primary", key="btn_del_n"):
                    try:
                        supabase_client.table("portal_news").delete().eq("id", n_del_id).execute()
                        st.success(f"News entry ID {n_del_id} deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting news: {e}")
            else:
                st.info("No news entries found in database.")

        # --- SLIDE 4: SUPPORT DEMANDS ---
        with tab_s:
            st.write("### 📋 Submitted Farmer Support Demands")
            try:
                s_res = supabase_client.table("support_requests").select("*").order("id", desc=True).execute()
                s_list = s_res.data if s_res.data else []
            except Exception:
                s_list = []

            if s_list:
                df_s = pd.DataFrame(s_list)
                st.dataframe(df_s, use_container_width=True)

                s_del_id = st.number_input("Enter Support Demand ID to Delete:", min_value=1, step=1, key="del_s_id")
                if st.button("Delete Support Demand", type="primary", key="btn_del_s"):
                    try:
                        supabase_client.table("support_requests").delete().eq("id", s_del_id).execute()
                        st.success(f"Support Request ID {s_del_id} deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting request: {e}")
            else:
                st.info("No support demands submitted yet.")

        # --- SLIDE 5: DECLARATIONS (INCLUDES CULTIVATION START DATE) ---
        with tab_d:
            st.write("### 🌱 Crop Area Declarations Database")
            try:
                d_res = supabase_client.table("declarations").select("*").order("id", desc=True).execute()
                d_list = d_res.data if d_res.data else []
            except Exception:
                d_list = []

            if d_list:
                df_d = pd.DataFrame(d_list)
                st.dataframe(df_d, use_container_width=True)

                d_del_id = st.number_input("Enter Declaration ID to Delete:", min_value=1, step=1, key="del_d_id")
                if st.button("Delete Declaration", type="primary", key="btn_del_d"):
                    try:
                        supabase_client.table("declarations").delete().eq("id", d_del_id).execute()
                        st.success(f"Declaration ID {d_del_id} deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting declaration: {e}")
            else:
                st.info("No declarations recorded in database.")
