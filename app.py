import streamlit as st
import pandas as pd
import qrcode
import random
import html
import hashlib
from io import BytesIO
from st_supabase_connection import SupabaseConnection

# ---------------------------------------------------------
# Security Helpers
# ---------------------------------------------------------
def sanitize(text: str) -> str:
    """Sanitize user input to prevent HTML/Script Injection (XSS)."""
    if not isinstance(text, str):
        return str(text)
    return html.escape(text.strip())

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with a salt."""
    salt = "FelahPortalAlgeria2026SecureSalt"
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def get_admin_password() -> str:
    """Retrieve admin password securely from secrets or fallback."""
    return st.secrets.get("ADMIN_PASSWORD", "greatdz")

# ---------------------------------------------------------
# Page Configuration & Mobile CSS Layout
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
    .sidebar-card {
        background-color: #ffffff;
        border: 2px solid #0b8a62;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .alert-red {
        background-color: #ffe6e6;
        border-left: 6px solid #d9534f;
        padding: 12px;
        border-radius: 8px;
        color: #a94442;
        margin-bottom: 12px;
    }
    .alert-yellow {
        background-color: #fffde6;
        border-left: 6px solid #f0ad4e;
        padding: 12px;
        border-radius: 8px;
        color: #8a6d3b;
        margin-bottom: 12px;
    }
    .alert-green {
        background-color: #e6fffa;
        border-left: 6px solid #5cb85c;
        padding: 12px;
        border-radius: 8px;
        color: #3c763d;
        margin-bottom: 12px;
    }
    .market-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Supabase Cloud Database Connection
# ---------------------------------------------------------
supabase = st.connection("supabase", type=SupabaseConnection)

# ---------------------------------------------------------
# 48 WILAYAS LIST
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

# ---------------------------------------------------------
# CROP CATEGORIES & QUOTAS
# ---------------------------------------------------------
VEGETABLE_LIMITS = {
    "Potato (بطاطس)": 1700.0,
    "Tomato (طماطم)": 1000.0,
    "Pepper (فلفل)": 800.0,
    "Carrot (جزر)": 700.0,
    "Onion (بصل)": 650.0,
    "Garlic (ثوم)": 600.0,
    "Wheat / Cereal (قمح)": 400.0,
    "Beans (فاصولياء)": 400.0,
    "Lettuce (خس)": 300.0,
    "Cucumber (خيار)": 200.0
}

FRUIT_LIST = [
    "Dates Deglet Nour (تمور دقلة نور)",
    "Citrus / Oranges (حمضيات / برتقال)",
    "Apples (تفاح)",
    "Grapes (عنب)",
    "Olives (زيتون)",
    "Figs (تين)",
    "Watermelon / Melon (بطيخ)"
]

def get_current_crop_area(crop_name: str) -> float:
    try:
        res = supabase.table("declarations").select("area").eq("crop", crop_name).execute()
        if res and res.data:
            return sum(item["area"] for item in res.data if item.get("area") is not None)
    except Exception as e:
        # Prevents app crash if table is missing or DB connection hiccups
        return 0.0
    return 0.0

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if 'lang' not in st.session_state:
    st.session_state.lang = 'AR'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'farmer_name' not in st.session_state:
    st.session_state.farmer_name = ""
if 'carte_num' not in st.session_state:
    st.session_state.carte_num = ""
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "home"
if 'selected_service' not in st.session_state:
    st.session_state.selected_service = None

if 'admin_attempts' not in st.session_state:
    st.session_state.admin_attempts = 0
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

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
        'suppliers': "Wholesale Markets & Fertilizer Depots",
        'admin': "Owner Admin Dashboard"
    }
}

t = TEXTS[st.session_state.lang]

# ---------------------------------------------------------
# HIGH-VISIBILITY SIDEBAR (Language & Login Slide)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="background-color: #0b8a62; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px;">
            ⚙️ MENU / القائمة
        </div>
    """, unsafe_allow_html=True)
    
    # 1. LANGUAGE BOX
    st.markdown("### 🌐 Language / اللغة")
    selected_lang = st.radio("Choose Language", ["العربية", "English"], key="sb_lang", label_visibility="collapsed")
    st.session_state.lang = 'AR' if selected_lang == "العربية" else 'EN'
    
    st.divider()
    
    # 2. LOGIN / ACCOUNT CARD
    st.markdown("### 👤 Account / تسجيل الدخول")
    
    if not st.session_state.logged_in:
        farmer_name_input = st.text_input("Name / الاسم", placeholder="Enter full name", key="sb_name")
        carte_num_input = st.text_input("Carte Fellah N°", placeholder="e.g. DZ-2026-XXXXX", key="sb_card")
        
        correct_answer = st.session_state.captcha_num1 + st.session_state.captcha_num2
        st.write(f"**Security Check:** Solve `{st.session_state.captcha_num1} + {st.session_state.captcha_num2}` = ?")
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
# Main Mobile Top Notice Banner
# ---------------------------------------------------------
mobile_status = f"🟢 Connected: {st.session_state.farmer_name}" if st.session_state.logged_in else "🔴 Not Logged In — Click top-left arrow ↗ to Login"
st.markdown(f"""
    <div class="mobile-sidebar-notice">
        👉 {mobile_status}
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Main UI Header
# ---------------------------------------------------------
st.markdown(f"<h2 style='text-align: center;'>{t['title']}</h2>", unsafe_allow_html=True)

st.markdown(f"""
    <div class="promo-banner">
        <h4 style="margin:0;">{t['banner']}</h4>
        <small>الجمهورية الجزائرية الديمقراطية الشعبية - وزارة الفلاحة والتنمية الريفية</small>
    </div>
""", unsafe_allow_html=True)

nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    if st.button(f"{t['home']}", use_container_width=True):
        st.session_state.active_tab = "home"
with nav_col2:
    if st.button(f"{t['card']}", use_container_width=True):
        st.session_state.active_tab = "card"
with nav_col3:
    if st.button(f"{t['account']}", use_container_width=True):
        st.session_state.active_tab = "account"

st.divider()

# ---------------------------------------------------------
# VIEW 1: HOME DASHBOARD
# ---------------------------------------------------------
if st.session_state.active_tab == "home":
    st.subheader("الخدمات الإلكترونية / Main Services")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t['crop'], use_container_width=True, type="primary"):
            st.session_state.selected_service = "crop"
        if st.button(t['pay'], use_container_width=True):
            st.session_state.selected_service = "pay"
    
    with col2:
        if st.button(t['weather'], use_container_width=True):
            st.session_state.selected_service = "weather"
        if st.button(t['suppliers'], use_container_width=True):
            st.session_state.selected_service = "suppliers"

    st.divider()

    # --- SERVICE 1: DECLARATION & QUOTA SYSTEM ---
    if st.session_state.selected_service == "crop":
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
                st.warning(f"⚠️ **Quota Target Exceeded / تم تجاوز الحد المستهدف!**\n\nThe requested area ({area_ha:.1f} Ha) exceeds the national target for **{selected_c}**. You can still proceed with your declaration, but we strongly recommend switching to under-cultivated crops such as: **{recommend_str}**.")
            else:
                st.success("✅ **Quota Available / المساحة متاحة** — This crop is within national production targets.")

        st.write("---")
        
        if st.button("Submit & Generate QR Permit (تصريح وإنشاء الرمز)"):
            if st.session_state.logged_in:
                try:
                    supabase.table("declarations").insert({
                        "farmer_name": st.session_state.farmer_name,
                        "carte_num": st.session_state.carte_num,
                        "wilaya": selected_w,
                        "category": cat_choice,
                        "crop": selected_c,
                        "area": area_ha
                    }).execute()
                    
                    st.success("Declaration registered successfully in Supabase Cloud Database!")
                    
                    qr_payload = f"FELAH-PERMIT|{st.session_state.farmer_name}|{st.session_state.carte_num}|{selected_w}|{selected_c}|{area_ha}HA"
                    qr = qrcode.make(qr_payload)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    qr_bytes = buf.getvalue()
                    
                    st.image(qr_bytes, caption="Official CCLS Aid QR Authorization Code", width=220)
                    
                    st.download_button(
                        label="Download QR Permit (تحميل الرمز)",
                        data=qr_bytes,
                        file_name=f"Permit_{st.session_state.farmer_name}.png",
                        mime="image/png"
                    )
                except Exception as e:
                    st.error(f"Failed to record declaration in database. Please verify table permissions or run SQL setup. Error: {e}")
            else:
                st.warning("Please open the side menu (top-left arrow ↗) and log in first.")

    # --- SERVICE 2: WEATHER & AG-ALERTS ---
    elif st.session_state.selected_service == "weather":
        st.subheader(t['weather'])
        
        try:
            res = supabase.table("weather_alerts").select("*").order("id", desc=True).execute()
            alerts = res.data
        except Exception:
            alerts = []
        
        if alerts:
            for item in alerts:
                title_clean = sanitize(item.get("title", ""))
                region_clean = sanitize(item.get("region", ""))
                severity_clean = sanitize(item.get("severity", ""))
                msg_clean = sanitize(item.get("message", ""))
                created = item.get("created_at", "")
                
                if "Red" in severity_clean:
                    css_class = "alert-red"
                    icon = "🔴"
                elif "Yellow" in severity_clean:
                    css_class = "alert-yellow"
                    icon = "🟡"
                else:
                    css_class = "alert-green"
                    icon = "🟢"
                    
                st.markdown(f"""
                    <div class="{css_class}">
                        <h4>{icon} {title_clean}</h4>
                        <p><b>Target Wilaya / Region:</b> {region_clean} | <b>Severity Level:</b> {severity_clean}</p>
                        <p>{msg_clean}</p>
                        <small style="color: #666;">Issued: {sanitize(str(created))}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("🟢 No severe weather warnings active. All agricultural regions report normal seasonal conditions.")

    # --- SERVICE 3: PAYMENTS ---
    elif st.session_state.selected_service == "pay":
        st.subheader(t['pay'])
        st.write("Annual Subscription Fee: **2,500 DZD**")
        card_type = st.radio("Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"])
        st.text_input("Card Number:", placeholder="6037 XXXX XXXX XXXX")
        if st.button("Confirm Payment (إتمام الدفع)"):
            st.success("Carte Fellah successfully renewed for season 2026/2027!")

    # --- SERVICE 4: MAPS & MARKETS DIRECTORY ---
    elif st.session_state.selected_service == "suppliers":
        st.subheader(t['suppliers'])
        st.write("Wholesale Produce Markets, OAIC Silos & Fertilizer Suppliers")
        
        suppliers_df = pd.DataFrame({
            'lat': [36.7538, 36.4722, 36.1911, 35.3708, 34.8516, 33.3683, 36.2642, 36.3650, 35.6969, 36.1528],
            'lon': [3.0588, 2.8333, 5.4092, 1.3225, 5.7280, 6.8674, 2.7539, 6.6147, -0.6331, 6.1667]
        })
        st.map(suppliers_df, zoom=5)
        
        st.write("### Verified Locations & Directory")
        try:
            res = supabase.table("suppliers_directory").select("*").order("id", desc=True).execute()
            directory = res.data
        except Exception:
            directory = []
        
        if directory:
            for item in directory:
                name_clean = sanitize(item.get("name", ""))
                wilaya_clean = sanitize(item.get("wilaya", ""))
                category_clean = sanitize(item.get("category", ""))
                address_clean = sanitize(item.get("address", ""))
                link_clean = sanitize(item.get("maps_link", ""))
                
                if not (link_clean.startswith("http://") or link_clean.startswith("https://")):
                    link_clean = f"https://{link_clean}"
                
                st.markdown(f"""
                    <div class="market-card">
                        <h4 style="margin: 0; color: #0b8a62;">📍 {name_clean}</h4>
                        <p style="margin: 5px 0;"><b>Wilaya:</b> {wilaya_clean} | <b>Category:</b> {category_clean}</p>
                        <p style="margin: 5px 0; color: #555;">{address_clean}</p>
                        <a href="{link_clean}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; font-weight: bold; color: #1e5340;">🗺️ Open in Google Maps ↗</a>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No custom market addresses added yet by administrator.")

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
                <p><b>Farmer Name / الاسم:</b> {st.session_state.farmer_name}</p>
                <p><b>Card N° / رقم البطاقة:</b> {st.session_state.carte_num}</p>
                <p><b>Status:</b> <span style="color: green; font-weight: bold;">ACTIVE / 2026 Valid</span></p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Please open the side menu (top-left arrow ↗) to log in and view your digital card.")

# ---------------------------------------------------------
# VIEW 3: OWNER-ONLY ADMIN DASHBOARD (SECURED)
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
    st.subheader("Account Info & Owner Dashboard")
    
    if st.session_state.logged_in:
        st.write(f"Logged in as: **{st.session_state.farmer_name}**")
        st.write(f"Carte Fellah: `{st.session_state.carte_num}`")
    
    st.divider()
    
    st.subheader(t['admin'])
    st.caption("Restricted Access: Only accessible by platform administrator.")
    
    if st.session_state.admin_attempts >= 5:
        st.error("🔒 Admin access locked due to 5 consecutive failed attempts. Please restart session.")
    else:
        if not st.session_state.admin_authenticated:
            admin_pass = st.text_input("Enter Admin Password / كلمة السر للوحة التحكم", type="password")
            
            if st.button("Authenticate Admin"):
                target_hash = hash_password(get_admin_password())
                input_hash = hash_password(admin_pass)
                
                if input_hash == target_hash:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_attempts = 0
                    st.rerun()
                else:
                    st.session_state.admin_attempts += 1
                    remaining = 5 - st.session_state.admin_attempts
                    st.error(f"Incorrect Password. Attempts remaining: {remaining}")
        
        if st.session_state.admin_authenticated:
            st.success("Owner Access Granted!")
            
            if st.button("🔒 Lock Admin Session"):
                st.session_state.admin_authenticated = False
                st.rerun()
                
            admin_tab1, admin_tab2, admin_tab3 = st.tabs(["🌾 Quotas", "🚨 Weather", "📍 Markets"])
            
            # --- ADMIN TAB 1: DECLARATION & QUOTA CONTROL ---
            with admin_tab1:
                st.write("### Live Vegetable Capacity Status")
                summary_data = []
                for c_name, limit_val in VEGETABLE_LIMITS.items():
                    curr = get_current_crop_area(c_name)
                    summary_data.append({
                        "Vegetable Crop": c_name,
                        "Declared Area (Ha)": curr,
                        "Target Limit (Ha)": limit_val,
                        "Capacity Used (%)": f"{(curr/limit_val)*100:.1f}%"
                    })
                st.table(pd.DataFrame(summary_data))
                
                st.write("---")
                st.write("### Database Management & Reset Controls")
                
                col_reset1, col_reset2 = st.columns(2)
                with col_reset1:
                    st.write("**Reset Specific Crop to 0 Ha:**")
                    reset_crop_target = st.selectbox("Select Crop to Reset", list(VEGETABLE_LIMITS.keys()) + FRUIT_LIST)
                    if st.button(f"Reset '{reset_crop_target}' to 0 Ha"):
                        try:
                            supabase.table("declarations").delete().eq("crop", reset_crop_target).execute()
                            st.success(f"Successfully reset {reset_crop_target} area back to 0 Ha!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error resetting crop: {e}")

                with col_reset2:
                    st.write("**Delete Specific Entry by ID:**")
                    entry_id_to_delete = st.number_input("Enter Entry ID", min_value=1, step=1)
                    if st.button("Delete Entry"):
                        try:
                            supabase.table("declarations").delete().eq("id", entry_id_to_delete).execute()
                            st.success(f"Entry ID #{entry_id_to_delete} deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting entry: {e}")
                
                st.write("---")
                st.write("### Live Database Declarations")
                try:
                    res = supabase.table("declarations").select("*").execute()
                    st.dataframe(pd.DataFrame(res.data), use_container_width=True)
                except Exception:
                    st.info("No declarations available or table missing.")

            # --- ADMIN TAB 2: WEATHER ALERT MANAGER ---
            with admin_tab2:
                st.write("### 🚨 Publish Weather Warning / Alert")
                
                alert_title = st.text_input("Alert Title / عنوان التنبيه", placeholder="e.g. Sirocco Heatwave / Frost Alert")
                alert_region = st.selectbox("Target Wilaya / Region", ["All Wilayas (كل الولايات)"] + WILAYAS_48)
                alert_severity = st.selectbox("Warning Severity Level / درجة الخطورة", [
                    "🔴 Red Alert (Severe Danger / خطورة عالية)",
                    "🟡 Yellow Alert (Moderate Warning / تحذير متوسط)",
                    "🟢 Green Alert (Normal Advisory / تنبيه عادي)"
                ])
                alert_msg = st.text_area("Detailed Instructions for Farmers", placeholder="e.g. Shift drip irrigation to night shifts to protect crops.")
                
                if st.button("Publish Weather Alert"):
                    if alert_title.strip() and alert_msg.strip():
                        try:
                            supabase.table("weather_alerts").insert({
                                "title": sanitize(alert_title),
                                "region": alert_region,
                                "severity": alert_severity,
                                "message": sanitize(alert_msg)
                            }).execute()
                            st.success("Weather Alert successfully published!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error publishing alert: {e}")
                    else:
                        st.error("Please provide both Alert Title and Instructions.")
                        
                st.write("---")
                st.write("### Active Published Alerts")
                try:
                    res_alerts = supabase.table("weather_alerts").select("*").order("id", desc=True).execute()
                    st.dataframe(pd.DataFrame(res_alerts.data), use_container_width=True)
                except Exception:
                    st.info("No alerts found.")
                
                delete_alert_id = st.number_input("Enter Alert ID to Delete", min_value=1, step=1, key="del_alert")
                if st.button("Delete Weather Alert"):
                    try:
                        supabase.table("weather_alerts").delete().eq("id", delete_alert_id).execute()
                        st.success(f"Alert ID #{delete_alert_id} deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting alert: {e}")

            # --- ADMIN TAB 3: MARKETS & LOCATIONS MANAGER ---
            with admin_tab3:
                st.write("### 📍 Add Market, Silo, or Fertilizer Depot")
                
                loc_name = st.text_input("Location Name / اسم الموقع", placeholder="e.g. Boufarik Wholesale Market")
                loc_wilaya = st.selectbox("Wilaya Location", WILAYAS_48, key="loc_w")
                loc_category = st.selectbox("Category / النوع", ["Wholesale Produce Market", "OAIC Cereal Silo", "ASMIDAL Fertilizer Depot", "Agri-Equipment Supplier"])
                loc_address = st.text_input("Address / Details", placeholder="e.g. RN 42, Boufarik, Blida")
                loc_maps_link = st.text_input("Google Maps URL Link", placeholder="https://maps.google.com/?q=...")
                
                if st.button("Add Location to Public Directory"):
                    if loc_name.strip() and loc_maps_link.strip():
                        try:
                            supabase.table("suppliers_directory").insert({
                                "name": sanitize(loc_name),
                                "wilaya": loc_wilaya,
                                "category": loc_category,
                                "address": sanitize(loc_address),
                                "maps_link": sanitize(loc_maps_link)
                            }).execute()
                            st.success("Location added to public directory successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding location: {e}")
                    else:
                        st.error("Please fill in Location Name and Google Maps URL.")
                        
                st.write("---")
                st.write("### Managed Directory Locations")
                try:
                    res_suppliers = supabase.table("suppliers_directory").select("*").order("id", desc=True).execute()
                    st.dataframe(pd.DataFrame(res_suppliers.data), use_container_width=True)
                except Exception:
                    st.info("No supplier locations found.")
                
                delete_loc_id = st.number_input("Enter Location ID to Delete", min_value=1, step=1, key="del_loc")
                if st.button("Delete Location"):
                    try:
                        supabase.table("suppliers_directory").delete().eq("id", delete_loc_id).execute()
                        st.success(f"Location ID #{delete_loc_id} deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting location: {e}")
