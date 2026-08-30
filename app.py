import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from io import BytesIO

# ---------------------------------------------------------
# Page Configuration & Mobile CSS
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
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #a5d6a7;
        font-weight: bold;
    }
    .status-badge-warn {
        background-color: #fff3e0;
        color: #e65100;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #ffe0b2;
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
             (id INTEGER PRIMARY KEY AUTOINCREMENT, farmer_name TEXT, carte_num TEXT, wilaya TEXT, category TEXT, crop TEXT, area REAL)''')
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

def get_current_crop_area(crop_name):
    c.execute("SELECT SUM(area) FROM declarations WHERE crop = ?", (crop_name,))
    res = c.fetchone()[0]
    return res if res else 0.0

# ---------------------------------------------------------
# Session State & Translations
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
        'title': "بوابة الفلاح - 48 ولاية",
        'banner': "📢 برنامج التخطيط والتنسيق الفلاحي 2026",
        'home': "الرئيسية",
        'card': "بطاقتي",
        'account': "حسابي",
        'weather': "🌤️ الأحوال الجوية والتنبيهات",
        'crop': "🌾 نصائح الزراعة والتصريح (QR)",
        'pay': "💳 تجديد بطاقة الفلاح (CIB/الذهبية)",
        'suppliers': "📍 أسواق الجملة ونقاط الأسمدة (48 ولاية)",
        'admin': "👑 لوحة تحكم المالِك (Owner Admin)"
    },
    'EN': {
        'title': "Felah Farmer Portal - 48 Wilayas",
        'banner': "📢 Agricultural Planning & Coordination Program 2026",
        'home': "Home",
        'card': "My Card",
        'account': "Account",
        'weather': "🌤️ Weather & Ag-Alerts",
        'crop': "🌾 Cultivation & QR Permit",
        'pay': "💳 Carte Fellah Subscription",
        'suppliers': "📍 Wholesale Markets & Fertilizer Depots",
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
# Main UI
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

    # --- SERVICE 1: DECLARATION & QUOTA SYSTEM ---
    if st.session_state.selected_service == "crop":
        st.subheader(t['crop'])
        
        selected_w = st.selectbox("Wilaya / الولاية (48 Wilayas)", WILAYAS_48)
        
        cat_choice = st.radio("Category / الصنف:", ["Vegetables (خضروات)", "Fruits (فواكه)"])
        
        if cat_choice == "Fruits (فواكه)":
            selected_c = st.selectbox("Select Fruit / اختر الفاكهة", FRUIT_LIST)
            st.markdown("""
                <div class="status-badge-ok">
                    ✅ <b>Unlimited Capacity / بدون حد أقصى</b><br>
                    Fruit cultivation is open without national hectare restrictions.
                </div>
            """, unsafe_allow_html=True)
        else:
            selected_c = st.selectbox("Select Vegetable / اختر الخضار", list(VEGETABLE_LIMITS.keys()))
            limit = VEGETABLE_LIMITS[selected_c]
            current_total = get_current_crop_area(selected_c)
            percentage = min((current_total / limit), 1.0)
            
            st.write(f"📊 **National Area Quota Status ({selected_c}):**")
            st.progress(percentage)
            st.caption(f"Registered: **{current_total:.1f} Ha** / Target Limit: **{limit:.0f} Ha** ({percentage*100:.1f}% Full)")
            
            if current_total >= limit:
                # Find alternative under-cultivated crops
                under_crops = [c_n for c_n, l_v in VEGETABLE_LIMITS.items() if get_current_crop_area(c_n) < l_v]
                st.markdown(f"""
                    <div class="status-badge-warn">
                        ⚠️ <b>Quota Target Exceeded / تم تجاوز الحد المستهدف!</b><br>
                        You can still register this crop, but we strongly recommend switching to under-cultivated crops:
                        <br>👉 <b>{', '.join(under_crops[:3])}</b>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div class="status-badge-ok">
                        ✅ <b>Quota Available / المساحة متاحة</b><br>
                        This crop is within national production targets.
                    </div>
                """, unsafe_allow_html=True)

        st.write("---")
        area_ha = st.number_input("Your Farming Area (Hectares / هكتار)", min_value=0.5, max_value=500.0, value=5.0)
        
        if st.button("Submit & Generate QR Permit (تصريح وإنشاء الرمز)"):
            if st.session_state.logged_in:
                c.execute("INSERT INTO declarations (farmer_name, carte_num, wilaya, category, crop, area) VALUES (?, ?, ?, ?, ?, ?)",
                          (st.session_state.farmer_name, st.session_state.carte_num, selected_w, cat_choice, selected_c, area_ha))
                conn.commit()
                st.success("✅ Declaration registered successfully in the National Database!")
                
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
        st.info("☀️ **Sirocco Heatwave Alert**: High temperatures forecasted for Southern & High-Plateau Wilayas. Adjust drip irrigation to night shifts.")

    # --- SERVICE 3: PAYMENTS ---
    elif st.session_state.selected_service == "pay":
        st.subheader(t['pay'])
        st.write("Annual Subscription Fee: **2,500 DZD**")
        card_type = st.radio("Payment Gateway:", ["EDAHABIA (الذهبية)", "CIB Card"])
        st.text_input("Card Number:", "6037 8888 1234 5678")
        if st.button("Confirm Payment (إتمام الدفع)"):
            st.success("🎉 Carte Fellah successfully renewed for season 2026/2027!")

    # --- SERVICE 4: MAPS & SUPPLIERS ---
    elif st.session_state.selected_service == "suppliers":
        st.subheader(t['suppliers'])
        st.write("📍 **Wholesale Produce Markets, OAIC Silos & Fertilizer Suppliers**")
        
        suppliers_df = pd.DataFrame({
            'lat': [36.7538, 36.4722, 36.1911, 35.3708, 34.8516, 33.3683, 36.2642, 36.3650, 35.6969, 36.1528],
            'lon': [3.0588, 2.8333, 5.4092, 1.3225, 5.7280, 6.8674, 2.7539, 6.6147, -0.6331, 6.1667],
            'name': [
                'OAIC Central Depot - Alger', 
                'Wholesale Market - Boufarik (Blida)', 
                'Regional Market - Sétif', 
                'CCLS Cereal Depot - Tiaret', 
                'Dates Wholesale Market - Biskra', 
                'ASMIDAL Fertilizer Hub - El Oued', 
                'Attatba Market - Tipaza', 
                'Chelghoum Laïd Market - Mila', 
                'Oran Wholesale Market', 
                'CCLS Granary - Batna'
            ]
        })
        st.map(suppliers_df, zoom=5)
        
        st.markdown("""
        **Main National Agricultural Hubs:**
        - 🏬 **Wholesale Markets:** Boufarik (Blida), Attatba (Tipaza), Chelghoum Laïd (Mila), Sétif, Biskra, Oran.
        - 🏭 **Fertilizer & Input Hubs:** ASMIDAL Outlets (El Oued, Adrar, Annaba).
        - 🌾 **CCLS Silos:** OAIC Grain Storage points in Tiaret, Sétif, Batna, Constantine, and Chlef.
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
# VIEW 3: OWNER-ONLY ADMIN (Password: greatdz)
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
    st.subheader("👤 Account Info & Owner Dashboard")
    
    if st.session_state.logged_in:
        st.write(f"Logged in as: **{st.session_state.farmer_name}**")
        st.write(f"Carte Fellah: `{st.session_state.carte_num}`")
    
    st.divider()
    
    st.subheader(t['admin'])
    st.caption("🔒 Restricted Access: Only accessible by platform administrator.")
    
    admin_pass = st.text_input("Enter Admin Password / كلمة السر للوحة التحكم", type="password")
    
    if admin_pass == "greatdz":
        st.success("🔓 Owner Access Granted!")
        
        st.write("### 📈 Live Vegetable Capacity Status")
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
        
        st.write("### 🗃️ Live Database Declarations")
        df = pd.read_sql_query("SELECT * FROM declarations", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No declarations registered in the database yet.")
    elif admin_pass != "":
        st.error("Incorrect Password.")
