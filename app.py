import streamlit as st
import sqlite3
import pandas as pd
import qrcode
import random
import html
import hashlib
from io import BytesIO

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
    .promo-banner {
        background: linear-gradient(135deg, #0b8a62 0%, #1e5340 100%);
        color: white;
        border-radius: 15px;
        padding: 18px;
        text-align: center;
        margin-bottom: 15px;
        border: 2px solid #d4af37;
    }
    .alert-red {
        background-color: #ffe6e6;
        border-left: 6px solid #d9534f;
        padding: 15px;
        border-radius: 8px;
        color: #a94442;
        margin-bottom: 15px;
    }
    .alert-yellow {
        background-color: #fffde6;
        border-left: 6px solid #f0ad4e;
        padding: 15px;
        border-radius: 8px;
        color: #8a6d3b;
        margin-bottom: 15px;
    }
    .alert-green {
        background-color: #e6fffa;
        border-left: 6px solid #5cb85c;
        padding: 15px;
        border-radius: 8px;
        color: #3c763d;
        margin-bottom: 15px;
    }
    .market-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Database Setup (SQLite - Parameterized Schema & Queries)
# ---------------------------------------------------------
conn = sqlite3.connect('felah_database.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS declarations 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              farmer_name TEXT, 
              carte_num TEXT, 
              wilaya TEXT, 
              category TEXT, 
              crop TEXT, 
              area REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS weather_alerts 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              title TEXT, 
              region TEXT, 
              severity TEXT, 
              message TEXT, 
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

c.execute('''CREATE TABLE IF NOT EXISTS suppliers_directory 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              name TEXT, 
              wilaya TEXT, 
              category TEXT, 
              address TEXT, 
              maps_link TEXT)''')
conn.commit()

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
    c.execute("SELECT SUM(area) FROM declarations WHERE crop = ?", (crop_name,))
    res = c.fetchone()[0]
    return res if res else 0.0

# ---------------------------------------------------------
# Session State & Security Controls
# ---------------------------------------------------------
if 'lang' not in st.session_state:
    st.session_state.lang = 'AR'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "home"
if 'selected_service' not in st.session_state:
    st.session_state.selected_service = None

# Brute-force rate limiting state
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
        'suppliers': "أسواق الجملة ونقاط الأسمدة (48 ولاية)",
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
# Sidebar - Authentication & Anti-Bot CAPTCHA
# ---------------------------------------------------------
st.sidebar.title("Language / اللغة")
lang_choice = st.sidebar.radio("Select Language", ["العربية", "English"])
st.session_state.lang = 'AR' if lang_choice == "العربية" else 'EN'

st.sidebar.divider()
st.sidebar.title("Account Authentication")

if not st.session_state.logged_in:
    farmer_name_input = st.sidebar.text_input("Name / الاسم", placeholder="Enter your full name")
    carte_num_input = st.sidebar.text_input("Carte Fellah N°", placeholder="e.g. DZ-2026-XXXXX")
    
    correct_answer = st.session_state.captcha_num1 + st.session_state.captcha_num2
    st.sidebar.write(f"**Security Check (CAPTCHA):**")
    st.sidebar.caption(f"Solve: {st.session_state.captcha_num1} + {st.session_state.captcha_num2} = ?")
    captcha_input = st.sidebar.text_input("Security Answer / إجابة التحقق", placeholder="Result")

    if st.sidebar.button("Log In / دخول"):
        if not farmer_name_input.strip() or not carte_num_input.strip():
            st.sidebar.error("Please fill in both Name and Card Number.")
        elif str(captcha_input).strip() != str(correct_answer):
            st.sidebar.error("Incorrect CAPTCHA answer. Try again.")
            generate_new_captcha()
        else:
            st.session_state.logged_in = True
            st.session_state.farmer_name = sanitize(farmer_name_input)
            st.session_state.carte_num = sanitize(carte_num_input)
            generate_new_captcha()
            st.rerun()
else:
    st.sidebar.success(f"Connected: {st.session_state.farmer_name}")
    if st.sidebar.button("Log Out / خروج"):
        st.session_state.logged_in = False
        st.session_state.farmer_name = ""
        st.session_state.carte_num = ""
        st.session_state.admin_authenticated = False
        st.rerun()

# ---------------------------------------------------------
# Main UI Header
# ---------------------------------------------------------
st.markdown(f"<h2 style='text-align: center;'>{t['title']}</h2>", unsafe_allow_html=True)

st.markdown(f"""
    <div class="promo-banner">
        <h3>{t['banner']}</h3>
        <p>الجمهورية الجزائرية الديمقراطية الشعبية - وزارة الفلاحة والتنمية الريفية</p>
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
                # Parameterized INSERT prevents SQL Injection
                c.execute("INSERT INTO declarations (farmer_name, carte_num, wilaya, category, crop, area) VALUES (?, ?, ?, ?, ?, ?)",
                          (st.session_state.farmer_name, st.session_state.carte_num, selected_w, cat_choice, selected_c, area_ha))
                conn.commit()
                st.success("Declaration registered successfully in the National Database!")
                
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
            else:
                st.warning("Please log in from the sidebar first to submit.")

    # --- SERVICE 2: WEATHER & AG-ALERTS ---
    elif st.session_state.selected_service == "weather":
        st.subheader(t['weather'])
        
        c.execute("SELECT title, region, severity, message, created_at FROM weather_alerts ORDER BY id DESC")
        alerts = c.fetchall()
        
        if alerts:
            for title, region, severity, msg, created in alerts:
                title_clean = sanitize(title)
                region_clean = sanitize(region)
                severity_clean = sanitize(severity)
                msg_clean = sanitize(msg)
                
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
        c.execute("SELECT name, wilaya, category, address, maps_link FROM suppliers_directory ORDER BY id DESC")
        directory = c.fetchall()
        
        if directory:
            for name, wilaya, category, address, link in directory:
                name_clean = sanitize(name)
                wilaya_clean = sanitize(wilaya)
                category_clean = sanitize(category)
                address_clean = sanitize(address)
                link_clean = sanitize(link)
                
                # Sanitize URL protocol
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

        st.write("---")
        st.write("**Default Regional Hubs:**")
        st.write("- **Wholesale Markets:** Boufarik (Blida), Attatba (Tipaza), Chelghoum Laid (Mila), Setif, Biskra, Oran.")
        st.write("- **Fertilizer & Input Hubs:** ASMIDAL Outlets (El Oued, Adrar, Annaba).")
        st.write("- **CCLS Silos:** OAIC Grain Storage points in Tiaret, Setif, Batna, Constantine, and Chlef.")

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
        st.warning("Please log in from the sidebar to view your digital card.")

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
    
    # Check Rate Limit Status (Max 5 Failed Attempts)
    if st.session_state.admin_attempts >= 5:
        st.error("🔒 Admin access locked due to 5 consecutive failed attempts. Please restart session.")
    else:
        if not st.session_state.admin_authenticated:
            admin_pass = st.text_input("Enter Admin Password / كلمة السر للوحة التحكم", type="password")
            
            if st.button("Authenticate Admin"):
                # Compare SHA-256 Hashes
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
        
        # Display Dashboard only if securely authenticated
        if st.session_state.admin_authenticated:
            st.success("Owner Access Granted!")
            
            if st.button("🔒 Lock Admin Session"):
                st.session_state.admin_authenticated = False
                st.rerun()
                
            admin_tab1, admin_tab2, admin_tab3 = st.tabs(["🌾 Quota & Declarations", "🚨 Weather Alerts Manager", "📍 Markets & Locations Manager"])
            
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
                        # Parameterized DELETE
                        c.execute("DELETE FROM declarations WHERE crop = ?", (reset_crop_target,))
                        conn.commit()
                        st.success(f"Successfully reset {reset_crop_target} area back to 0 Ha!")
                        st.rerun()

                with col_reset2:
                    st.write("**Delete Specific Entry by ID:**")
                    entry_id_to_delete = st.number_input("Enter Entry ID", min_value=1, step=1)
                    if st.button("Delete Entry"):
                        # Parameterized DELETE
                        c.execute("DELETE FROM declarations WHERE id = ?", (entry_id_to_delete,))
                        conn.commit()
                        st.success(f"Entry ID #{entry_id_to_delete} deleted!")
                        st.rerun()
                
                st.write("---")
                if st.button("⚠️ Clear Entire Declarations Database (Reset All to Zero)"):
                    c.execute("DELETE FROM declarations")
                    conn.commit()
                    st.success("Entire database wiped out! All crop totals are 0 Ha.")
                    st.rerun()

                st.write("---")
                st.write("### Live Database Declarations")
                df = pd.read_sql_query("SELECT * FROM declarations", conn)
                st.dataframe(df, use_container_width=True)

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
                        # Parameterized INSERT with Sanitized Content
                        c.execute("INSERT INTO weather_alerts (title, region, severity, message) VALUES (?, ?, ?, ?)",
                                  (sanitize(alert_title), alert_region, alert_severity, sanitize(alert_msg)))
                        conn.commit()
                        st.success("Weather Alert successfully published and visible on user portal!")
                        st.rerun()
                    else:
                        st.error("Please provide both Alert Title and Instructions.")
                        
                st.write("---")
                st.write("### Active Published Alerts")
                df_alerts = pd.read_sql_query("SELECT * FROM weather_alerts ORDER BY id DESC", conn)
                st.dataframe(df_alerts, use_container_width=True)
                
                delete_alert_id = st.number_input("Enter Alert ID to Delete", min_value=1, step=1, key="del_alert")
                if st.button("Delete Weather Alert"):
                    c.execute("DELETE FROM weather_alerts WHERE id = ?", (delete_alert_id,))
                    conn.commit()
                    st.success(f"Alert ID #{delete_alert_id} deleted!")
                    st.rerun()

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
                        # Parameterized INSERT with Sanitized Inputs
                        c.execute("INSERT INTO suppliers_directory (name, wilaya, category, address, maps_link) VALUES (?, ?, ?, ?, ?)",
                                  (sanitize(loc_name), loc_wilaya, loc_category, sanitize(loc_address), sanitize(loc_maps_link)))
                        conn.commit()
                        st.success("Location added to public directory successfully!")
                        st.rerun()
                    else:
                        st.error("Please fill in Location Name and Google Maps URL.")
                        
                st.write("---")
                st.write("### Managed Directory Locations")
                df_suppliers = pd.read_sql_query("SELECT * FROM suppliers_directory ORDER BY id DESC", conn)
                st.dataframe(df_suppliers, use_container_width=True)
                
                delete_loc_id = st.number_input("Enter Location ID to Delete", min_value=1, step=1, key="del_loc")
                if st.button("Delete Location"):
                    c.execute("DELETE FROM suppliers_directory WHERE id = ?", (delete_loc_id,))
                    conn.commit()
                    st.success(f"Location ID #{delete_loc_id} deleted!")
                    st.rerun()
