import streamlit as st
import pandas as pd
import qrcode
import random
import html
import hashlib
from io import BytesIO
from st_supabase_connection import SupabaseConnection

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
    .support-card {
        background-color: #f9fbf9;
        border: 1px solid #d0e7da;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .alert-red { background-color: #ffe6e6; border-left: 6px solid #d9534f; padding: 12px; border-radius: 8px; color: #a94442; margin-bottom: 12px; }
    .alert-yellow { background-color: #fffde6; border-left: 6px solid #f0ad4e; padding: 12px; border-radius: 8px; color: #8a6d3b; margin-bottom: 12px; }
    .alert-green { background-color: #e6fffa; border-left: 6px solid #5cb85c; padding: 12px; border-radius: 8px; color: #3c763d; margin-bottom: 12px; }
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

# Native Supabase Python client instance:
supabase_client = conn.client

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATIONS
# ---------------------------------------------------------
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
    "Geomembrane Water Basin (حوض الجيو-ممبران)": [
        "Fellah Card (بطاقة الفلاح)",
        "Land Ownership or Lease Contract (عقد الملكية أو الامتياز)",
        "Technical Study / Supplier Proforma Invoice (دراسة تقنية / فاتورة شكلية)"
    ],
    "Well & Water Drilling (حفر الآبار الفلاحية)": [
        "Fellah Card (بطاقة الفلاح)",
        "Water Drilling Authorization Permit (رخصة حفر البئر من الموارد المائية)",
        "Land Title / Lease Agreement (عقد الملكية أو الامتياز)"
    ],
    "Modern Drip/Sprinkler Irrigation (أنظمة الري الحديثة)": [
        "Fellah Card (بطاقة الفلاح)",
        "Proforma Invoice for Equipment (فاتورة شكلية للعتاد)",
        "Land Topography Plan (مخطط طبوغرافي للأرض)"
    ],
    "Solar Energy for Agricultural Pumps (الطاقة الشمسية للمزارع)": [
        "Fellah Card (بطاقة الفلاح)",
        "Solar Installation Technical Quote (عرض سعر للنظام الشمسي)",
        "Well Authorization / Water Source Proof (اثبات وجود مورد مائي)"
    ],
    "Tractors & Farm Machinery (الجرارات والعتاد الفلاحي)": [
        "Fellah Card (بطاقة الفلاح)",
        "Proforma Invoice from Certified Dealer (فاتورة شكلية من موزر معتمد)",
        "Exploitation Certificate (شهادة استغلال فلاحي)"
    ]
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
# Session State Init
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
        'suppliers': "أسوق الجملة ونقاط الأسمدة (48 ولاية)",
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
        'suppliers': "Wholesale Markets & Depots",
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
                                
                                # Access storage through the underlying native client
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

                            st.success("🎉 Your Agricultural Support demand has been submitted successfully to Ministry Administrators!")
                    except Exception as e:
                        st.error(f"Error submitting request: {e}")

    # --- SERVICE 2: NEWS & ANNOUNCEMENTS ---
    elif st.session_state.selected_service == "news":
        st.subheader(t['news'])
        st.caption("Official press releases, ministerial updates, and sector announcements.")
        
        try:
            res_news = supabase_client.table("portal_news").select("*").order("id", desc=True).execute()
            news_items = res_news.data
        except Exception:
            news_items = []

        if news_items:
            for n in news_items:
                title_c = sanitize(n.get("title", ""))
                cat_c = sanitize(n.get("category", "General"))
                content_c = sanitize(n.get("content", ""))
                date_c = sanitize(str(n.get("created_at", "")))
                
                st.markdown(f"""
                    <div class="news-card">
                        <span style="background: #0b8a62; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8em;">{cat_c}</span>
                        <small style="color: #666; float: right;">{date_c[:10]}</small>
                        <h4 style="margin: 8px 0 5px 0; color: #1e5340;">📢 {title_c}</h4>
                        <p style="margin: 0; color: #333; line-height: 1.5;">{content_c}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📰 No official news releases published today.")

    # --- SERVICE 3: DECLARATION & QUOTA SYSTEM ---
    elif st.session_state.selected_service == "crop":
        st.subheader(t['crop'])
        selected_w = st.selectbox("Wilaya / الولاية (48 Wilayas)", WILAYAS_48)
        cat_choice = st.radio("Category / الصنف:", ["Vegetables (خضروات)", "Fruits (فواكه)"])
        area_ha = st.number_input("Your Farming Area (Hectares / هكتار)", min_value=0.1, value=5.0, max_value=10000.0)
        
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
            
            if projected_total > limit:
                under_crops = [c_n for c_n, l_v in VEGETABLE_LIMITS.items() if get_current_crop_area(c_n) < l_v]
                recommend_str = ", ".join(under_crops[:3])
                st.warning(f"⚠️ Quota Target Exceeded! We recommend: **{recommend_str}**.")
            else:
                st.success("✅ Quota Available — Within national targets.")

        if st.button("Submit & Generate QR Permit"):
            if st.session_state.logged_in:
                try:
                    supabase_client.table("declarations").insert({
                        "farmer_name": st.session_state.farmer_name,
                        "carte_num": st.session_state.carte_num,
                        "wilaya": selected_w,
                        "category": cat_choice,
                        "crop": selected_c,
                        "area": area_ha
                    }).execute()
                    
                    st.success("Declaration registered successfully!")
                    qr_payload = f"FELAH-PERMIT|{st.session_state.farmer_name}|{st.session_state.carte_num}|{selected_w}|{selected_c}|{area_ha}HA"
                    qr = qrcode.make(qr_payload)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    qr_bytes = buf.getvalue()
                    
                    st.image(qr_bytes, caption="Official QR Permit", width=220)
                    st.download_button("Download QR Permit", data=qr_bytes, file_name=f"Permit_{st.session_state.farmer_name}.png", mime="image/png")
                except Exception as e:
                    st.error(f"Failed to record declaration: {e}")
            else:
                st.warning("Please log in first.")

    # --- SERVICE 4: WEATHER ALERTS ---
    elif st.session_state.selected_service == "weather":
        st.subheader(t['weather'])
        try:
            res = supabase_client.table("weather_alerts").select("*").order("id", desc=True).execute()
            alerts = res.data
        except Exception: 
            alerts = []
        
        if alerts:
            for item in alerts:
                css_class = "alert-red" if "Red" in item.get("severity","") else ("alert-yellow" if "Yellow" in item.get("severity","") else "alert-green")
                st.markdown(f"""
                    <div class="{css_class}">
                        <h4>{item.get('title')}</h4>
                        <p><b>Wilaya:</b> {item.get('region')} | <b>Severity:</b> {item.get('severity')}</p>
                        <p>{item.get('message')}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("🟢 No severe weather warnings active.")

    # --- SERVICE 5: PAYMENTS ---
    elif st.session_state.selected_service == "pay":
        st.subheader(t['pay'])
        st.write("Annual Subscription Fee: **2,500 DZD**")
        st.radio("Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"])
        st.text_input("Card Number:", placeholder="6037 XXXX XXXX XXXX")
        if st.button("Confirm Payment"): st.success("Carte Fellah renewed for season 2026/2027!")

    # --- SERVICE 6: MARKETS DIRECTORY ---
    elif st.session_state.selected_service == "suppliers":
        st.subheader(t['suppliers'])
        try:
            res = supabase_client.table("suppliers_directory").select("*").order("id", desc=True).execute()
            directory = res.data
        except Exception: 
            directory = []
        
        if directory:
            for item in directory:
                link = item.get("maps_link", "")
                if not (link.startswith("http://") or link.startswith("https://")): link = f"https://{link}"
                st.markdown(f"""
                    <div class="market-card">
                        <h4 style="margin: 0; color: #0b8a62;">📍 {item.get('name')}</h4>
                        <p><b>Wilaya:</b> {item.get('wilaya')} | <b>Type:</b> {item.get('category')}</p>
                        <a href="{link}" target="_blank">🗺️ Open in Google Maps ↗</a>
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
# VIEW 3: OWNER-ONLY ADMIN DASHBOARD
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
    st.subheader("Account Info & Owner Dashboard")
    if st.session_state.logged_in:
        st.write(f"Logged in as: **{st.session_state.farmer_name}** | Card: `{st.session_state.carte_num}`")
    st.divider()
    
    st.subheader(t['admin'])
    if st.session_state.admin_attempts >= 5:
        st.error("🔒 Admin access locked due to failed attempts.")
    else:
        if not st.session_state.admin_authenticated:
            admin_pass = st.text_input("Enter Admin Password", type="password")
            if st.button("Authenticate Admin"):
                if hash_password(admin_pass) == hash_password(get_admin_password()):
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_attempts = 0
                    st.rerun()
                else:
                    st.session_state.admin_attempts += 1
                    st.error("Incorrect Password.")
        
        if st.session_state.admin_authenticated:
            st.success("Owner Access Granted!")
            if st.button("🔒 Lock Admin Session"):
                st.session_state.admin_authenticated = False
                st.rerun()
                
            admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5 = st.tabs([
                "🌾 Quotas", "📂 Support Requests", "📢 Post News", "🚨 Weather", "📍 Markets"
            ])
            
            # --- ADMIN TAB 1: CROP QUOTAS ---
            with admin_tab1:
                st.write("### Live Vegetable Capacity Status")
                summary_data = []
                for c_name, limit_val in VEGETABLE_LIMITS.items():
                    curr = get_current_crop_area(c_name)
                    summary_data.append({"Vegetable": c_name, "Declared (Ha)": curr, "Target Limit": limit_val, "Used": f"{(curr/limit_val)*100:.1f}%"})
                st.table(pd.DataFrame(summary_data))
                try:
                    res_dec = supabase_client.table("declarations").select("*").execute()
                    st.dataframe(pd.DataFrame(res_dec.data), use_container_width=True)
                except Exception: st.info("No declarations available.")

            # --- ADMIN TAB 2: REVIEW AGRICULTURAL SUPPORT REQUESTS ---
            with admin_tab2:
                st.write("### 📂 Review Submitted Support Demands & Attached Documents")
                try:
                    res_sup = supabase_client.table("support_requests").select("*").order("id", desc=True).execute()
                    reqs = res_sup.data
                except Exception: reqs = []

                if reqs:
                    for req in reqs:
                        with st.expander(f"Demand #{req['id']} - {req['farmer_name']} ({req['sector']}) - {req['wilaya']}"):
                            st.write(f"**Farmer Name:** {req['farmer_name']}")
                            st.write(f"**Carte Fellah N°:** {req['carte_num']}")
                            st.write(f"**Wilaya:** {req['wilaya']}")
                            st.write(f"**Subsidized Sector:** {req['sector']}")
                            st.write(f"**Notes:** {req.get('description', 'N/A')}")
                            st.write(f"**Submitted Date:** {req.get('created_at')}")
                            
                            st.write("#### 📎 Inserted Documents & Papers:")
                            files_map = req.get("files_json", {})
                            if isinstance(files_map, dict):
                                for doc_title, file_url in files_map.items():
                                    st.markdown(f"👉 **{doc_title}:** [Download/View File ↗]({file_url})")
                            else:
                                st.caption("No file links formatted.")
                else:
                    st.info("No agricultural support demands received yet.")

            # --- ADMIN TAB 3: PUBLISH NEWS & ANNOUNCEMENTS ---
            with admin_tab3:
                st.write("### 📢 Publish Official News & Press Release")
                news_title = st.text_input("News Title / عنوان الخبر")
                news_cat = st.selectbox("Category", ["Official Subsidy Announcement", "Ministerial Decree", "Seed & Fertilizer Release", "General News"])
                news_content = st.text_area("News Details & Announcement Body")
                
                if st.button("Publish News Release", type="primary"):
                    if news_title.strip() and news_content.strip():
                        try:
                            supabase_client.table("portal_news").insert({
                                "title": sanitize(news_title),
                                "category": news_cat,
                                "content": sanitize(news_content)
                            }).execute()
                            st.success("News release published live!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error publishing news: {e}")

                st.divider()
                st.write("### Managed News Items")
                try:
                    res_all_news = supabase_client.table("portal_news").select("*").order("id", desc=True).execute()
                    st.dataframe(pd.DataFrame(res_all_news.data), use_container_width=True)
                except Exception: st.info("No news found.")
                
                del_news_id = st.number_input("Enter News ID to Delete", min_value=1, step=1, key="del_news_n")
                if st.button("Delete News Entry"):
                    try:
                        supabase_client.table("portal_news").delete().eq("id", del_news_id).execute()
                        st.success(f"News ID #{del_news_id} deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting news: {e}")

            # --- ADMIN TAB 4: WEATHER ---
            with admin_tab4:
                st.write("### Publish Weather Warning")
                w_title = st.text_input("Alert Title")
                w_reg = st.selectbox("Target Wilaya", ["All Wilayas"] + WILAYAS_48)
                w_sev = st.selectbox("Severity", ["🔴 Red Alert", "🟡 Yellow Alert", "🟢 Green Alert"])
                w_msg = st.text_area("Instructions")
                if st.button("Publish Alert"):
                    try:
                        supabase_client.table("weather_alerts").insert({
                            "title": sanitize(w_title),
                            "region": w_reg,
                            "severity": w_sev,
                            "message": sanitize(w_msg)
                        }).execute()
                        st.success("Alert published!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            # --- ADMIN TAB 5: MARKETS ---
            with admin_tab5:
                st.write("### Add Market or Depot")
                m_name = st.text_input("Location Name")
                m_wil = st.selectbox("Wilaya", WILAYAS_48, key="m_w")
                m_cat = st.selectbox("Type", ["Wholesale Produce Market", "OAIC Cereal Silo", "ASMIDAL Fertilizer Depot", "Agri-Equipment Supplier"])
                m_addr = st.text_input("Address")
                m_link = st.text_input("Google Maps URL")
                if st.button("Add Location"):
                    if m_name.strip():
                        try:
                            supabase_client.table("suppliers_directory").insert({
                                "name": sanitize(m_name),
                                "wilaya": m_wil,
                                "category": m_cat,
                                "address": sanitize(m_addr),
                                "maps_link": sanitize(m_link)
                            }).execute()
                            st.success("Market location added!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding market location: {e}")
                    else:
                        st.error("Location Name cannot be empty.")
