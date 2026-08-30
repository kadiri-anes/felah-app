import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from io import BytesIO

# ---------------------------------------------------------
# Page Configuration & Mobile CSS Layout
# ---------------------------------------------------------
st.set_page_config(page_title="Felah Mobile Portal - فلاح", page_icon="🌾", layout="centered")

# CSS to replicate WebEtu Green Card UI & Mobile Navigation
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #f4f7f6; }
    
    /* Green Dashboard Buttons Styling */
    .dashboard-card {
        background-color: #0b8a62;
        color: white;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        font-weight: bold;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 12px;
        cursor: pointer;
        transition: transform 0.2s;
    }
    .dashboard-card:hover { transform: scale(1.02); }
    
    /* Banner Styling */
    .promo-banner {
        background: linear-gradient(135deg, #0b8a62 0%, #1e5340 100%);
        color: white;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
        border: 2px solid #d4af37;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Database Setup (SQLite for Live Admin Monitoring)
# ---------------------------------------------------------
conn = sqlite3.connect('felah_database.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS declarations 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, farmer_name TEXT, carte_num TEXT, wilaya TEXT, crop TEXT, area REAL)''')
conn.commit()

# ---------------------------------------------------------
# Session State & Language Dictionary
# ---------------------------------------------------------
if 'lang' not in st.session_state:
    st.session_state.lang = 'AR'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "home"
if 'selected_service' not in st.session_state:
    st.session_state.selected_service = None

# Translations
TEXTS = {
    'AR': {
        'title': "بوابة الفلاح - 48 ولاية",
        'banner': "📢 برنامج الدعم الفلاحي 2026 - اكتشف التسهيلات الجديدة",
        'home': "الرئيسية",
        'card': "بطاقتي",
        'account': "حسابي",
        'weather': "🌤️ الأحوال الجوية والتنبيهات",
        'crop': "🌾 نصائح الزراعة والتصريح (QR)",
        'pay': "💳 تجديد بطاقة الفلاح (CIB/الذهبية)",
        'suppliers': "📍 الموردين والأسواق والخرائط",
        'admin': "👑 لوحة تحكم الإدارة (Admin Database)"
    },
    'EN': {
        'title': "Felah Farmer Portal - 48 Wilayas",
        'banner': "📢 Agricultural Support Program 2026 - Discover New Grants",
        'home': "Home",
        'card': "My Card",
        'account': "Account",
        'weather': "🌤️ Weather & Ag-Alerts",
        'crop': "🌾 Cultivation & QR Aid Permit",
        'pay': "💳 Carte Fellah Subscription",
        'suppliers': "📍 Suppliers, Markets & Maps",
        'admin': "👑 Admin Database Control"
    }
}

t = TEXTS[st.session_state.lang]

# ---------------------------------------------------------
# Sidebar - Language & Auth Controls
# ---------------------------------------------------------
st.sidebar.title("🌐 Language / اللغة")
lang_choice = st.sidebar.radio("Select Language", ["العربية", "English"])
st.session_state.lang = 'AR' if lang_choice == "العربية" else 'EN'

st.sidebar.divider()
st.sidebar.title("🔐 Account Authentication")
if not st.session_state.logged_in:
    farmer_name = st.sidebar.text_input("Name / الاسم", "Abdelkader Benali")
    carte_num = st.sidebar.text_input("Carte Fellah N°", "DZ-2026-88491")
    if st.sidebar.button("Log In / دخول"):
        st.session_state.logged_in = True
        st.session_state.farmer_name = farmer_name
        st.session_state.carte_num = carte_num
        st.rerun()
else:
    st.sidebar.success(f"Connected: {st.session_state.farmer_name}")
    if st.sidebar.button("Log Out / خروج"):
        st.session_state.logged_in = False
        st.rerun()

# ---------------------------------------------------------
# Main App Header & Banner
# ---------------------------------------------------------
st.markdown(f"<h2 style='text-align: center;'>{t['title']}</h2>", unsafe_allow_html=True)

# Top Banner
st.markdown(f"""
    <div class="promo-banner">
        <h3>{t['banner']}</h3>
        <p>وزارة الفلاحة والتنمية الريفية - 2026</p>
    </div>
""", unsafe_allow_html=True)

# Bottom Navigation Bar (Matching Screenshot UI)
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    if st.button(f"🏠 {t['home']}", use_container_width=True):
        st.session_state.active_tab = "home"
with nav_col2:
    if st.button(f"💳 {t['card']}", use_container_width=True):
        st.session_state.active_tab = "card"
with nav_col3:
    if st.button(f"👤 {t['account']}", use_container_width=True):
        st.session_state.active_tab = "account"

st.divider()

# ---------------------------------------------------------
# VIEW 1: HOME DASHBOARD (Green Button Grid)
# ---------------------------------------------------------
if st.session_state.active_tab == "home":
    
    st.subheader("الخدمات الإلكترونية / Main Services")
    
    # 2x2 Grid Layout like WebEtu
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

    # --- SERVICE DETAILS DISPLAY ---
    if st.session_state.selected_service == "crop":
        st.subheader(t['crop'])
        
        wilayas = ["01 - Adrar", "07 - Biskra", "14 - Tiaret", "16 - Alger", "19 - Sétif", "39 - El Oued", "48 - Relizane"]
        selected_w = st.selectbox("Wilaya / الولاية", wilayas)
        
        crop_list = ["Durum Wheat (قمح صلب)", "Potatoes (بطاطس)", "Dates Deglet Nour (تمور)", "Citrus (حمضيات)", "Tomatoes (طماطم)"]
        selected_c = st.selectbox("Crop Type / المحصول", crop_list)
        area_ha = st.number_input("Land Area (Hectares / هكتار)", min_value=1.0, value=12.0)
        
        if st.button("Submit & Save Declaration (حفظ والتصريح)"):
            if st.session_state.logged_in:
                c.execute("INSERT INTO declarations (farmer_name, carte_num, wilaya, crop, area) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.farmer_name, st.session_state.carte_num, selected_w, selected_c, area_ha))
                conn.commit()
                st.success("✅ Declaration registered permanently in Database!")
                
                # QR Code Aid Generation
                qr_payload = f"FELAH-SUBSIDY|{st.session_state.farmer_name}|{selected_w}|{selected_c}|{area_ha}HA"
                qr = qrcode.make(qr_payload)
                buf = BytesIO()
                qr.save(buf)
                st.image(buf.getvalue(), caption="Official CCLS Aid QR Authorization Code", width=200)
            else:
                st.warning("⚠️ Please log in from the sidebar first to submit.")

    elif st.session_state.selected_service == "weather":
        st.subheader(t['weather'])
        st.info("☀️ **Sirocco Heatwave Alert**: High temperatures forecasted for Southern & High-Plateau Wilayas. Adjust drip irrigation to night shifts.")

    elif st.session_state.selected_service == "pay":
        st.subheader(t['pay'])
        st.write("Annual Fee: **2,500 DZD**")
        card_type = st.radio("Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"])
        st.text_input("Card Number (رقم البطاقة):", "6037 8888 1234 5678")
        if st.button("Process Payment (إتمام الدفع)"):
            st.success("🎉 Payment Confirmed! Subscription renewed for 2026/2027.")

    elif st.session_state.selected_service == "suppliers":
        st.subheader(t['suppliers'])
        st.write("📍 **Map & Distribution Centers across Algerian Wilayas**")
        
        # Interactive Map Data
        map_data = pd.DataFrame({
            'lat': [36.19, 35.37, 34.85, 36.75],
            'lon': [5.41, 1.32, 5.73, 3.05],
            'name': ['CCLS Sétif', 'CCLS Tiaret', 'CCLS Biskra', 'CCLS Alger Main']
        })
        st.map(map_data, zoom=5)

# ---------------------------------------------------------
# VIEW 2: CARTE FELLAH PRESENTATION (بطاقتي)
# ---------------------------------------------------------
elif st.session_state.active_tab == "card":
    st.subheader("💳 Digital Carte Fellah - البطاقة الفلاحية الرقمية")
    
    if st.session_state.logged_in:
        st.markdown(f"""
            <div style="border: 2px solid #0b8a62; border-radius: 15px; padding: 20px; background: white;">
                <h3 style="color: #0b8a62;">جمهورية الجزائرية الديمقراطية الشعبية</h3>
                <p><b>وزارة الفلاحة والتنمية الريفية</b></p>
                <hr>
                <p><b>Farmer Name / الاسم:</b> {st.session_state.farmer_name}</p>
                <p><b>Card N° / رقم البطاقة:</b> {st.session_state.carte_num}</p>
                <p><b>Status:</b> <span style="color: green; font-weight: bold;">ACTIVE / 2026 Valid</span></p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Please log in to view your digital card.")

# ---------------------------------------------------------
# VIEW 3: ACCOUNT & ADMIN COMMAND CENTER (حسابي)
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
    st.subheader("👤 User Profile & Settings")
    
    if st.session_state.logged_in:
        st.write(f"Logged in as: **{st.session_state.farmer_name}**")
        st.write(f"Carte Fellah: `{st.session_state.carte_num}`")
    else:
        st.write("Status: Guest Mode")

    st.divider()
    
    # --- ADMIN DATABASE SECTION FOR YOUR PRESENTATION ---
    st.subheader(t['admin'])
    st.write("📊 *Live database view showing connected user declarations:*")
    
    df = pd.read_sql_query("SELECT * FROM declarations", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records submitted in database yet. Try making a crop declaration on the Home page!")