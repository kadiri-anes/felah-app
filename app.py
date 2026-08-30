import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from io import BytesIO

# ---------------------------------------------------------
# Page Configuration & Mobile CSS Layout
# ---------------------------------------------------------
st.set_page_config(page_title="Felah Mobile Portal - فلاح", page_icon="🌾", layout="centered")

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
    .status-badge-ok {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 8px;
        border-radius: 8px;
        border: 1px solid #a5d6a7;
        font-weight: bold;
    }
    .status-badge-warn {
        background-color: #ffebee;
        color: #c62828;
        padding: 8px;
        border-radius: 8px;
        border: 1px solid #ef9a9a;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Database Setup (SQLite)
# ---------------------------------------------------------
conn = sqlite3.connect('felah_database.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS declarations 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, farmer_name TEXT, carte_num TEXT, wilaya TEXT, crop TEXT, area REAL)''')
conn.commit()

# ---------------------------------------------------------
# Crop Hectare Limits Dictionary
# ---------------------------------------------------------
CROP_LIMITS = {
    "Potato (بطاطس)": 1700.0,
    "Tomato (طماطم)": 1000.0,
    "Pepper (فلفل)": 800.0,
    "Carrot (جزر)": 700.0,
    "Onion (بصل)": 650.0,
    "Garlic (ثوم)": 600.0,
    "Wheat (قمح)": 400.0,
    "Beans (فاصولياء)": 400.0,
    "Lettuce (خس)": 300.0,
    "Cucumber (خيار)": 200.0
}

# Helper: Get current total declared hectares for a crop
def get_current_crop_area(crop_name):
    c.execute("SELECT SUM(area) FROM declarations WHERE crop = ?", (crop_name,))
    res = c.fetchone()[0]
    return res if res else 0.0

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

TEXTS = {
    'AR': {
        'title': "بوابة الفلاح - الجزائر (48 ولاية)",
        'banner': "📢 التخطيط الذكي للمحاصيل 2026 - تنظيم الإنتاج والتسويق",
        'home': "الرئيسية",
        'card': "بطاقتي",
        'account': "حسابي",
        'weather': "🌤️ الأحوال الجوية والتنبيهات",
        'crop': "🌾 نصائح الزراعة والتصريح (QR)",
        'pay': "💳 تجديد بطاقة الفلاح (CIB/الذهبية)",
        'suppliers': "📍 الموردين والأسواق المعتمدة",
        'admin': "👑 لوحة تحكم المالِك (Owner Admin)"
    },
    'EN': {
        'title': "Felah Farmer Portal - Algeria",
        'banner': "📢 Smart Crop Planning 2026 - Production Capacity Control",
        'home': "Home",
        'card': "My Card",
        'account': "Account",
        'weather': "🌤️ Weather & Ag-Alerts",
        'crop': "🌾 Cultivation & QR Aid Permit",
        'pay': "💳 Carte Fellah Renewal",
        'suppliers': "📍 Fertilizer Suppliers & Markets",
        'admin': "👑 Owner Admin Dashboard"
    }
}

t = TEXTS[st.session_state.lang]

# ---------------------------------------------------------
# Sidebar
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
# Header & Navigation
# ---------------------------------------------------------
st.markdown(f"<h2 style='text-align: center;'>{t['title']}</h2>", unsafe_allow_html=True)

st.markdown(f"""
    <div class="promo-banner">
        <h3>{t['banner']}</h3>
        <p>الجمهورية الجزائرية الديمقراطية الشعبية - وزارة الفلاحة</p>
    </div>
""", unsafe_allow_html=True)

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

    # --- SERVICE 1: CROP DECLARATION & QUOTA SYSTEM ---
    if st.session_state.selected_service == "crop":
        st.subheader(t['crop'])
        
        wilayas = ["01 - Adrar", "07 - Biskra", "14 - Tiaret", "16 - Alger", "19 - Sétif", "25 - Constantine", "39 - El Oued", "48 - Relizane"]
        selected_w = st.selectbox("Wilaya / الولاية", wilayas)
        
        crop_names = list(CROP_LIMITS.keys())
        selected_c = st.selectbox("Select Crop / اختر المحصول", crop_names)
        
        # Calculate & display quota capacity bar
        limit = CROP_LIMITS[selected_c]
        current_total = get_current_crop_area(selected_c)
        percentage = min((current_total / limit), 1.0)
        
        st.write(f"📊 **National Area Quota Status ({selected_c}):**")
        st.progress(percentage)
        st.caption(f"Registered: **{current_total:.1f} Ha** / Max Target: **{limit:.0f} Ha** ({percentage*100:.1f}% Full)")
        
        # Smart Alert & Recommendations
        if current_total >= limit:
            st.markdown(f"""
                <div class="status-badge-warn">
                    ⚠️ <b>Quota Reached / التخصيص مكتمل!</b><br>
                    This crop has reached its maximum planned limit across Algeria. 
                    <b>We strongly recommend switching to under-cultivated crops below:</b>
                </div>
            """, unsafe_allow_html=True)
            
            # Find crops that haven't reached quota
            under_crops = [c_name for c_name, l_val in CROP_LIMITS.items() if get_current_crop_area(c_name) < l_val]
            st.info(f"💡 Recommended alternative crops with available grant quotas: **{', '.join(under_crops[:3])}**")
        else:
            st.markdown(f"""
                <div class="status-badge-ok">
                    ✅ <b>Quota Available / المساحة متاحة</b><br>
                    You can declare your farm area for this crop and receive government support permits.
                </div>
            """, unsafe_allow_html=True)

        st.write("---")
        area_ha = st.number_input("Your Farming Area (Hectares / هكتار)", min_value=0.5, max_value=500.0, value=5.0)
        
        if st.button("Submit & Generate QR Permit (تصريح وإنشاء الرمز)"):
            if st.session_state.logged_in:
                c.execute("INSERT INTO declarations (farmer_name, carte_num, wilaya, crop, area) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.farmer_name, st.session_state.carte_num, selected_w, selected_c, area_ha))
                conn.commit()
                st.success("✅ Declaration registered successfully in the National Database!")
                
                # Generate QR Code
                qr_payload = f"FELAH-PERMIT|{st.session_state.farmer_name}|{selected_w}|{selected_c}|{area_ha}HA"
                qr = qrcode.make(qr_payload)
                buf = BytesIO()
                qr.save(buf)
                st.image(buf.getvalue(), caption="Official CCLS Aid QR Authorization Code", width=200)
                st.rerun()
            else:
                st.warning("⚠️ Please log in from the sidebar first to submit.")

    # --- SERVICE 2: WEATHER ---
    elif st.session_state.selected_service == "weather":
        st.subheader(t['weather'])
        st.info("☀️ **Sirocco Alert**: High temperatures forecasted for Southern Wilayas (Biskra, El Oued, Adrar). Recommended to irrigate during night hours.")

    # --- SERVICE 3: PAYMENTS ---
    elif st.session_state.selected_service == "pay":
        st.subheader(t['pay'])
        st.write("Annual Subscription Fee: **2,500 DZD**")
        card_type = st.radio("Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"])
        st.text_input("Card Number:", "6037 8888 1234 5678")
        if st.button("Confirm Payment (إتمام الدفع)"):
            st.success("🎉 Carte Fellah successfully renewed for season 2026/2027!")

    # --- SERVICE 4: SUPPLIERS & MARKETS MAP ---
    elif st.session_state.selected_service == "suppliers":
        st.subheader(t['suppliers'])
        st.write("📍 **Official OAIC/CCLS Fertilizer Points & Wholesale Produce Markets**")
        
        suppliers_df = pd.DataFrame({
            'lat': [36.7538, 36.1911, 35.3708, 34.8516, 33.3683, 36.2642],
            'lon': [3.0588, 5.4092, 1.3225, 5.7280, 6.8674, 2.7539],
            'name': ['OAIC Central Depot - Alger', 'CCLS Granary - Sétif', 'CCLS Cereal Hub - Tiaret', 'Wholesale Market - Biskra', 'Fertilizer Supply Hub - El Oued', 'Boufarik Produce Market - Blida']
        })
        st.map(suppliers_df, zoom=5)
        
        st.markdown("""
        **Key Distribution Hubs:**
        - 🏭 **Alger / Blida:** Central Inputs Depot & Boufarik Wholesale Market
        - 🌾 **Sétif / Tiaret:** CCLS Cereal Seeds & Fertilizer Distribution
        - 🌴 **Biskra / El Oued:** Regional Vegetable & Date Markets
        """)

# ---------------------------------------------------------
# VIEW 2: CARTE FELLAH
# ---------------------------------------------------------
elif st.session_state.active_tab == "card":
    st.subheader("💳 Digital Carte Fellah - البطاقة الفلاحية الرقمية")
    
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
# VIEW 3: OWNER-ONLY ADMIN & DATABASE CONTROL
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
    st.subheader("👤 Account Info & Owner Dashboard")
    
    if st.session_state.logged_in:
        st.write(f"Logged in as: **{st.session_state.farmer_name}**")
        st.write(f"Carte Fellah: `{st.session_state.carte_num}`")
    
    st.divider()
    
    # OWNER ADMIN LOCK
    st.subheader(t['admin'])
    st.caption("🔒 Restricted Access: Only accessible by platform administrator.")
    
    admin_pass = st.text_input("Enter Admin Password / كلمة السر للوحة التحكم", type="password")
    
    if admin_pass == "admin123":
        st.success("🔓 Owner Access Granted!")
        
        # Summary Statistics
        st.write("### 📈 Live Crop Hectare Totals")
        summary_data = []
        for c_name, limit_val in CROP_LIMITS.items():
            curr = get_current_crop_area(c_name)
            summary_data.append({
                "Crop": c_name,
                "Declared Area (Ha)": curr,
                "Target Limit (Ha)": limit_val,
                "Capacity Used (%)": f"{(curr/limit_val)*100:.1f}%"
            })
        st.table(pd.DataFrame(summary_data))
        
        st.write("### 🗃️ Complete Declarations Database")
        df = pd.read_sql_query("SELECT * FROM declarations", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No declarations in database yet.")
    elif admin_pass != "":
        st.error("Incorrect Password.")
