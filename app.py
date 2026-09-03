from datetime import date
from io import BytesIO
import random
import re
import folium
import pandas as pd
import qrcode
import streamlit as st
from streamlit_folium import st_folium
from supabase import create_client, Client

# ---------------------------------------------------------
# STREAMLIT PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="المناصة الرقمية للخدمات الفلاحية - Felah Portal",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling for portal UI and alert elements
st.markdown(
    """
    <style>
    .main { padding: 1rem 2rem; }
    .news-card {
        background-color: #f8f9fa;
        border-left: 5px solid #0b8a62;
        padding: 15px;
        margin-bottom: 12px;
        border-radius: 4px;
    }
    .notif-card {
        background-color: #eef7f4;
        border: 1px solid #c2e5d9;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 8px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION DATA
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

VEGETABLE_LIMITS = {
    "Potatoes (بطاطا)": 150000.0,
    "Tomatoes (طماطم)": 80000.0,
    "Onions (بصل)": 60000.0,
    "Garlic (ثوم)": 20000.0,
    "Carrots (جزر)": 30000.0,
}

FRUIT_LIST = [
    "Dates (تمور)",
    "Olives (زيتون)",
    "Citrus (حمضيات)",
    "Apples (تفاح)",
    "Grapes (عنب)",
]

SUPPORT_SECTORS = {
    "Geomembrane Water Basin (أحواض الجيوممبران)": [
        "Farmer Card (بطاقة الفلاح)",
        "Land Ownership or Lease Contract (عقد الملكية أو الامتياز)",
        "Technical Soil/Topography Report (تقرير تقني)",
    ],
    "Agricultural Well Digging (حفر الأبار الفلاحية)": [
        "Farmer Card (بطاقة الفلاح)",
        "Water Resources Authorization (ترخيص الموارد المائية)",
        "Land Cadastral Plan (مخطط مساحي)",
    ],
    "Solar Pumping Systems (الطاقة الشمسية للمضخات)": [
        "Farmer Card (بطاقة الفلاح)",
        "Proforma Invoice for Equipment (فاتورة شكلية)",
        "Pumping Station Specifications (دفتر الشروط)",
    ],
    "Drip Irrigation Networks (الري بالتقطير)": [
        "Farmer Card (بطاقة الفلاح)",
        "Water Source Proof (إثبات توفر الماء)",
        "Irrigation Network Layout Map (مخطط الشبكة)",
    ],
}

ALERT_STYLES = {
    "yellow": {
        "bg_color": "#fff3cd",
        "border_color": "#ffeba2",
        "text_color": "#856404",
        "badge_bg": "#ffe8a1",
        "badge_text": "#856404",
        "icon": "⚠️",
        "label": "Moderate / معتدل",
    },
    "orange": {
        "bg_color": "#ffe8cc",
        "border_color": "#ffd8a8",
        "text_color": "#d9480f",
        "badge_bg": "#ffd8a8",
        "badge_text": "#d9480f",
        "icon": "🍊",
        "label": "High / مرتفع",
    },
    "red": {
        "bg_color": "#f8d7da",
        "border_color": "#f5c6cb",
        "text_color": "#721c24",
        "badge_bg": "#f5c6cb",
        "badge_text": "#721c24",
        "icon": "🚨",
        "label": "Critical / خطير جداً",
    },
}

DEFAULT_AGRI_LOCATIONS = [
    {
        "name": "EURL Marché Gros Eucalyptus",
        "wilaya": "16 - Alger",
        "category": "Wholesale Produce Market",
        "lat": 36.6580,
        "lon": 3.1420,
        "maps_link": "https://maps.google.com/?q=36.6580,3.1420",
    },
    {
        "name": "OAIC CCLS Depot Biskra",
        "wilaya": "07 - Biskra",
        "category": "OAIC Cereal Silo (CCLS)",
        "lat": 34.8500,
        "lon": 5.7333,
        "maps_link": "https://maps.google.com/?q=34.8500,5.7333",
    },
    {
        "name": "ASMIDAL Fertilizer Distribution Centre",
        "wilaya": "23 - Annaba",
        "category": "ASMIDAL Fertilizer Depot",
        "lat": 36.9000,
        "lon": 7.7667,
        "maps_link": "https://maps.google.com/?q=36.9000,7.7667",
    },
]

TRANSLATIONS = {
    "AR": {
        "title": "المنصة الرقمية للخدمات الفلاحية",
        "nav_col1": "🌾 الخدمات الفلاحية",
        "nav_col2": "🪪 البطاقة الفلاحية",
        "nav_col3": "👤 حسابي واللوحة الإدارية",
        "support": "📝 طلب الدعم والدعم الريفي",
        "crop": "🌱 التصريح بالمزروعات والكتلة الإقليمية",
        "pay": "💳 تجديد الاشتراك والدفع",
        "news": "📰 الأخبار والبلاغات الرسمية",
        "weather": "🌩️ التنبيهات الجوية والأحوال الجوية",
        "suppliers": "🗺️ دليل شبكة الموزعين والأسواق",
        "back_btn": "⬅️ العودة للخدمات الرئيسية",
    },
    "FR": {
        "title": "Portail Numérique des Services Agricoles",
        "nav_col1": "🌾 Services Agricoles",
        "nav_col2": "🪪 Carte Fellah",
        "nav_col3": "👤 Mon Compte & Admin",
        "support": "📝 Demandes Subventions",
        "crop": "🌱 Déclaration de Cultures & Quotas",
        "pay": "💳 Paiement & Renouvellement",
        "news": "📰 Actualités Officielle",
        "weather": "🌩️ Alertes Météo",
        "suppliers": "🗺️ Carte des Distributeurs & CCLS",
        "back_btn": "⬅️ Retour aux Services",
    },
    "EN": {
        "title": "Digital Agricultural Services Portal",
        "nav_col1": "🌾 Agricultural Services",
        "nav_col2": "🪪 Fellah Card",
        "nav_col3": "👤 My Account & Admin",
        "support": "📝 Support & Subsidy Demand",
        "crop": "🌱 Crop Declaration & Quota",
        "pay": "💳 Subscription Payment",
        "news": "📰 Official News Portal",
        "weather": "🌩️ Weather Alerts",
        "suppliers": "🗺️ Directory & Markets Map",
        "back_btn": "⬅️ Back to All Services",
    },
}

# ---------------------------------------------------------
# INITIALIZE SESSION STATE
# ---------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "AR"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "farmer_name" not in st.session_state:
    st.session_state.farmer_name = ""
if "farmer_email" not in st.session_state:
    st.session_state.farmer_email = ""
if "carte_num" not in st.session_state:
    st.session_state.carte_num = ""
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "services"
if "selected_service" not in st.session_state:
    st.session_state.selected_service = None
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# ---------------------------------------------------------
# SUPABASE CONNECTION SETUP
# ---------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)


supabase_client = init_supabase()

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def sanitize(input_str: str) -> str:
    """Basic input sanitizer removing HTML tags to prevent XSS."""
    if not isinstance(input_str, str):
        return str(input_str)
    return re.sub(r"<[^>]*>", "", input_str).strip()


def get_admin_password() -> str:
    """Retrieve secret key for system administration."""
    try:
        return st.secrets["ADMIN_SECRET_PASSWORD"]
    except Exception:
        return "admin1234"


def get_current_crop_area(crop_name: str) -> float:
    """Query total registered hectares for a specific vegetable crop from Supabase."""
    try:
        res = (
            supabase_client.table("declarations")
            .select("area")
            .eq("crop", crop_name)
            .execute()
        )
        if res.data:
            return sum(float(item["area"]) for item in res.data)
    except Exception:
        pass
    return 0.0


t = TRANSLATIONS[st.session_state.lang]

# ---------------------------------------------------------
# SIDEBAR LOGISTICS AND AUTHENTICATION
# ---------------------------------------------------------
with st.sidebar:
    st.title("🇩🇿 Felah Services")

    # Language Switcher
    st.session_state.lang = st.selectbox(
        "🌐 Language / اللغة / Langue", ["AR", "FR", "EN"], index=0
    )
    t = TRANSLATIONS[st.session_state.lang]

    st.divider()

    # User Login / Authentication
    if not st.session_state.logged_in:
        st.subheader("🔑 Farmer Login / تسجيل الدخول")
        login_carte = st.text_input(
            "Carte Fellah N° (رقم البطاقة)", placeholder="e.g. DZ-2026-1234"
        )
        login_email = st.text_input("Email / البريد الإلكتروني")

        if st.button("Log In (دخول)", type="primary", use_container_width=True):
            if login_carte and login_email:
                try:
                    res = (
                        supabase_client.table("farmer_profiles")
                        .select("*")
                        .eq("carte_num", login_carte)
                        .execute()
                    )
                    if res.data:
                        profile = res.data[0]
                        st.session_state.logged_in = True
                        st.session_state.farmer_name = profile.get(
                            "farmer_name", "Farmer User"
                        )
                        st.session_state.farmer_email = login_email
                        st.session_state.carte_num = login_carte
                        st.success(f"Welcome back, {st.session_state.farmer_name}!")
                        st.rerun()
                    else:
                        # Auto-register new farmer entry
                        new_profile = {
                            "farmer_name": f"Farmer ({login_carte})",
                            "carte_num": login_carte,
                            "email": login_email,
                        }
                        supabase_client.table("farmer_profiles").insert(
                            new_profile
                        ).execute()
                        st.session_state.logged_in = True
                        st.session_state.farmer_name = new_profile["farmer_name"]
                        st.session_state.farmer_email = login_email
                        st.session_state.carte_num = login_carte
                        st.success("New profile registered & logged in!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Authentication error: {e}")
            else:
                st.warning("Please fill in both fields.")
    else:
        st.success(f"👤 Connected: **{st.session_state.farmer_name}**")
        st.caption(f"Card: `{st.session_state.carte_num}`")
        if st.button("Logout (خروج)", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.farmer_name = ""
            st.session_state.farmer_email = ""
            st.session_state.carte_num = ""
            st.rerun()

# ---------------------------------------------------------
# MAIN NAVIGATION HEADER
# ---------------------------------------------------------
st.title(t["title"])

nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    if st.button(t["nav_col1"], use_container_width=True):
        st.session_state.active_tab = "services"
        st.rerun()
with nav_col2:
    if st.button(t["nav_col2"], use_container_width=True):
        st.session_state.active_tab = "card"
        st.rerun()
with nav_col3:
    if st.button(t["nav_col3"], use_container_width=True):
        st.session_state.active_tab = "account"
        st.rerun()

st.divider()

# ---------------------------------------------------------
# VIEW 1: AGRICULTURAL SERVICES
# ---------------------------------------------------------
if st.session_state.active_tab == "services":
    if st.session_state.selected_service is None:
        col1, col2 = st.columns(2)

        with col1:
            if st.button(t["support"], use_container_width=True):
                st.session_state.selected_service = "support"
                st.rerun()
            if st.button(t["crop"], use_container_width=True):
                st.session_state.selected_service = "crop"
                # SERVICE 1 CONTINUED / PAYMENTS AND SERVICES BUTTONS
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
        if st.button(t['back_btn'], use_container_width=True):
            st.session_state.selected_service = None
            st.rerun()
        
        st.divider()

        # SERVICE 1: SUPPORT DEMAND
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
                                    
                                    supabase_client.storage.from_("agricultural-docs").upload(file_path, file_bytes)
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
                            <h4 style="margin: 8px 0 5px 0; color: #1e5340;">📢 {sanitize(n.get("title",""))}</h4>
                            <p style="margin: 0; color: #333;">{sanitize(n.get("content",""))}</p>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📰 No official news releases published today.")

        # SERVICE 3: DECLARATION & QUOTA SYSTEM
        elif st.session_state.selected_service == "crop":
            st.subheader(t['crop'])
            selected_w = st.selectbox("Wilaya / الولاية (48 Wilayas)", WILAYAS_48)
            cat_choice = st.radio("Category / الصنف:", ["Vegetables (خضروات)", "Fruits (فواكه)"])
            area_ha = st.number_input("Your Farming Area (Hectares / هكتار)", min_value=0.1, value=5.0, max_value=10000.0)
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
                        qr_payload = f"FELAH-PERMIT|{st.session_state.farmer_name}|{st.session_state.carte_num}|{selected_w}|{selected_c}|{area_ha}HA|START:{start_date}"
                        qr = qrcode.make(qr_payload)
                        buf = BytesIO()
                        qr.save(buf, format="PNG")
                        st.image(buf.getvalue(), caption=f"Official QR Permit (Start Date: {start_date})", width=220)
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
                    title = sanitize(item.get("title", "Weather Notice"))
                    region = sanitize(item.get("region", "All Wilayas"))
                    message = sanitize(item.get("message", ""))
                    raw_level = str(item.get("severity", "yellow")).lower().strip()
                    style = ALERT_STYLES.get(raw_level, ALERT_STYLES["yellow"])

                    st.markdown(f"""
                        <div style="background-color: {style['bg_color']}; border-left: 6px solid {style['border_color']}; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px; color: {style['text_color']};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-weight: bold; font-size: 1.05em;">{style['icon']} {title} — <small style="font-weight: normal;">({region})</small></span>
                                <span style="background-color: {style['badge_bg']}; color: {style['badge_text']}; padding: 3px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold;">{style['label']}</span>
                            </div>
                            <p style="margin: 0; font-size: 0.95em;">{message}</p>
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
            selected_cat = st.selectbox("Filter Points by Type / تصفية حسب النوع:", ["All", "Wholesale Produce Market", "OAIC Cereal Silo (CCLS)", "ASMIDAL Fertilizer Depot"])

            filtered_locs = all_locations if selected_cat == "All" else [loc for loc in all_locations if loc.get("category") == selected_cat]

            m = folium.Map(location=[34.5000, 3.2000], zoom_start=6, tiles="OpenStreetMap")
            color_map = {"Wholesale Produce Market": "green", "OAIC Cereal Silo (CCLS)": "cadetblue", "ASMIDAL Fertilizer Depot": "orange"}

            for loc in filtered_locs:
                lat, lon = float(loc.get("lat", 36.7323)), float(loc.get("lon", 3.1678))
                name, wilaya, cat = loc.get("name", "Agricultural Point"), loc.get("wilaya", ""), loc.get("category", "")
                maps_url = loc.get("maps_link", f"https://maps.google.com/?q={lat},{lon}")

                popup_html = f"""
                <div style="font-family: Arial; width: 200px;">
                    <h4 style="margin:0; color:#0b8a62;">{name}</h4>
                    <p style="margin:0; font-size:12px;"><b>Cat:</b> {cat}</p>
                    <a href="{maps_url}" target="_blank" style="display:inline-block; margin-top:5px; background:#4285F4; color:white; padding:4px 8px; border-radius:4px; font-size:11px; text-decoration:none;">🗺️ Open Google Maps</a>
                </div>
                """
                folium.Marker(location=[lat, lon], popup=folium.Popup(popup_html, max_width=220), tooltip=name, icon=folium.Icon(color=color_map.get(cat, "blue"))).add_to(m)

            st_folium(m, width=700, height=450)

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
                <p><b>Email:</b> {st.session_state.farmer_email}</p>
                <p><b>Card N°:</b> {st.session_state.carte_num}</p>
                <p><b>Status:</b> <span style="color: green; font-weight: bold;">ACTIVE / 2026 Valid</span></p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Please log in to view your digital card.")

# ---------------------------------------------------------
# VIEW 3: PERSONAL ACCOUNT HUB & OWNER ADMIN PANEL
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
    
    # PART 1: FARMER'S PERSONAL HUB
    if st.session_state.logged_in:
        st.subheader(f"👋 Welcome, {st.session_state.farmer_name}")
        st.caption(f"Connected Email: `{st.session_state.farmer_email}` | Card N°: `{st.session_state.carte_num}`")
        
        acc_tab1, acc_tab2, acc_tab3 = st.tabs(["🔔 Notifications", "📜 My Crop Declarations", "📄 My Subsidies Requests"])
        
        with acc_tab1:
            st.subheader("Your Official Notifications")
            try:
                res_notif = supabase_client.table("farmer_notifications").select("*").eq("farmer_email", st.session_state.farmer_email).order("id", desc=True).execute()
                notifs = res_notif.data if res_notif.data else []
                
                if notifs:
                    for n in notifs:
                        st.markdown(f"""
                            <div class="notif-card">
                                <b>📩 {sanitize(n.get('title',''))}</b>
                                <p style="margin:4px 0;">{sanitize(n.get('message',''))}</p>
                                <small style="color:gray;">{n.get('created_at','')[:10]}</small>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    if st.button("Mark All Notifications as Read"):
                        supabase_client.table("farmer_notifications").update({"is_read": True}).eq("farmer_email", st.session_state.farmer_email).execute()
                        st.success("Notifications updated.")
                        st.rerun()
                else:
                    st.info("No personal notifications at this moment.")
            except Exception as e:
                st.error(f"Error reading notifications: {e}")

        with acc_tab2:
            st.subheader("Submitted Crop Declarations")
            try:
                res_dec = supabase_client.table("declarations").select("*").eq("carte_num", st.session_state.carte_num).execute()
                if res_dec.data:
                    df_dec = pd.DataFrame(res_dec.data)
                    st.dataframe(df_dec[["crop", "category", "area", "wilaya", "start_date"]], use_container_width=True)
                else:
                    st.info("No crop declarations on file.")
            except Exception as e:
                st.error(f"Error fetching declarations: {e}")

        with acc_tab3:
            st.subheader("Subsidies & Equipment Applications")
            try:
                res_sup = supabase_client.table("support_requests").select("*").eq("carte_num", st.session_state.carte_num).execute()
                if res_sup.data:
                    df_sup = pd.DataFrame(res_sup.data)
                    st.dataframe(df_sup[["sector", "wilaya", "status", "created_at"]], use_container_width=True)
                else:
                    st.info("No active subsidy applications on file.")
            except Exception as e:
                st.error(f"Error fetching subsidy demands: {e}")
                
        st.divider()

    else:
        st.info("👈 Please log in from the left sidebar menu to see your personal records and notifications.")
        st.divider()

    # PART 2: OWNER ADMIN DASHBOARD MANAGEMENT
    st.subheader("🔐 Owner / Portal Admin Management Console")
    
    if not st.session_state.admin_authenticated:
        admin_input_pass = st.text_input("Enter Admin Security Secret Code", type="password", key="admin_pwd")
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
            "📊 View All Database Records"
        ])

        # ADMIN TAB 1: NEWS AND ALERTS
        with adm_tab1:
            st.markdown("#### Post Weather Alert")
            al_title = st.text_input("Alert Title", placeholder="e.g. Sirocco Heatwave Warning")
            al_region = st.selectbox("Target Wilaya", ["All Wilayas"] + WILAYAS_48)
            al_severity = st.selectbox("Severity Level", ["yellow", "orange", "red"])
            al_msg = st.text_area("Alert Message Body")
            
            if st.button("Broadcast Weather Alert"):
                try:
                    supabase_client.table("weather_alerts").insert({
                        "title": sanitize(al_title),
                        "region": al_region,
                        "severity": al_severity,
                        "message": sanitize(al_msg)
                    }).execute()
                    st.success("Weather Alert Published!")
                except Exception as e:
                    st.error(f"Failed to post alert: {e}")

            st.divider()
            st.markdown("#### Post Portal News Release")
            news_title = st.text_input("Article Title")
            news_cat = st.selectbox("News Category", ["General", "Subsidies", "Weather", "Market Prices"])
            news_body = st.text_area("Article Content Body")
            
            if st.button("Publish News Release"):
                try:
                    supabase_client.table("portal_news").insert({
                        "title": sanitize(news_title),
                        "category": news_cat,
                        "content": sanitize(news_body)
                    }).execute()
                    st.success("Official News Article Published!")
                except Exception as e:
                    st.error(f"Failed to publish news: {e}")

        # ADMIN TAB 2: DIRECT NOTIFICATIONS
        with adm_tab2:
            st.markdown("#### Send Targeted Notification to Farmer")
            target_email = st.text_input("Target Farmer Email", placeholder="farmer@domain.dz")
            notif_title = st.text_input("Notification Subject Title")
            notif_body = st.text_area("Message Body Text")
            
            if st.button("Dispatch Direct Notification"):
                try:
                    supabase_client.table("farmer_notifications").insert({
                        "farmer_email": sanitize(target_email),
                        "title": sanitize(notif_title),
                        "message": sanitize(notif_body),
                        "is_read": False
                    }).execute()
                    st.success(f"Notification dispatched to {target_email}!")
                except Exception as e:
                    st.error(f"Dispatch failed: {e}")

        # ADMIN TAB 3: ADD DIRECTORY LOCATION
        with adm_tab3:
            st.markdown("#### Add Location to Map Directory")
            loc_name = st.text_input("Facility Name")
            loc_wilaya = st.selectbox("Wilaya Location", WILAYAS_48, key="adm_w_dir")
            loc_cat = st.selectbox("Facility Type", ["Wholesale Produce Market", "OAIC Cereal Silo (CCLS)", "ASMIDAL Fertilizer Depot"])
            loc_lat = st.number_input("Latitude coordinate", value=36.7323, format="%.4f")
            loc_lon = st.number_input("Longitude coordinate", value=3.1678, format="%.4f")
            loc_address = st.text_input("Address details")
            loc_maps = st.text_input("Google Maps URL link")

            if st.button("Save New Location"):
                try:
                    supabase_client.table("suppliers_directory").insert({
                        "name": sanitize(loc_name),
                        "wilaya": loc_wilaya,
                        "category": loc_cat,
                        "lat": loc_lat,
                        "lon": loc_lon,
                        "address": sanitize(loc_address),
                        "maps_link": sanitize(loc_maps)
                    }).execute()
                    st.success("Location added to public directory!")
                except Exception as e:
                    st.error(f"Failed to insert map point: {e}")

        # ADMIN TAB 4: DATABASE TABLES INSPECTION
        with adm_tab4:
            st.markdown("#### System Database Inspector")
            table_choice = st.selectbox("Select Database Table to Inspect", [
                "farmer_profiles",
                "declarations",
                "support_requests",
                "farmer_notifications",
                "weather_alerts",
                "portal_news",
                "suppliers_directory"
            ])
            
            try:
                res_all = supabase_client.table(table_choice).select("*").execute()
                if res_all.data:
                    st.dataframe(pd.DataFrame(res_all.data), use_container_width=True)
                else:
                    st.info(f"Table `{table_choice}` is currently empty.")
            except Exception as e:
                st.error(f"Failed to query table: {e}")

        if st.button("🔒 Lock Admin Console"):
            st.session_state.admin_authenticated = False
            st.rerun()
