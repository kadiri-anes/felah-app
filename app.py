import math
import random
import re
from datetime import date
from io import BytesIO

import folium
import pandas as pd
import qrcode
import streamlit as st
import streamlit.components.v1 as components
from st_supabase_connection import SupabaseConnection
from streamlit_folium import st_folium

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="برنامج التخطيط والتنسيق الفلاحي 2026",
    page_icon="🌾",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# CONSTANTS & DATA STRUCTURES
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

# Estimated cultivated areas in Algeria, rounded to the nearest 1,000 ha
# for easier national target/quota management in this prototype.
# The values are stored in hectares for compatibility with the database,
# while the UI displays them in thousands of hectares (kha).
VEGETABLE_TARGETS_KHA = {
    "Potatoes (بطاطا)": 160,
    "Tomatoes (طماطم)": 25,
    "Onions (بصل)": 48,
    "Garlic (ثوم)": 12,
    "Carrots (جزر)": 19,
    "Green Beans (فاصوليا خضراء)": 12,
    "Melons (شمام)": 30,
    "Watermelons (بطيخ)": 28,
    "Artichokes (خرشوف)": 5,
    "Peppers (فلفل)": 20,
    "Zucchini (كوسة)": 12,
    "Cucumbers (خيار)": 8,
    "Lettuce (خس)": 10,
    "Eggplant (باذنجان)": 8,
    "Peas (جلبانة)": 8,
    "Cabbage (ملفوف)": 10,
    "Cauliflower (قرنبيط)": 6,
}

VEGETABLE_LIMITS = {
    crop: float(area_kha * 1000)
    for crop, area_kha in VEGETABLE_TARGETS_KHA.items()
}

# Estimated national cultivated area, rounded to the nearest 1,000 ha.
# Fruit areas are shown as reference figures; the current declaration flow
# does not enforce a national quota for fruit.
FRUIT_TARGETS_KHA = {
    "Olives / زيتون": 440,
    "Dates / تمور": 174,
    "Citrus / الموالح": 80,
    "Grapes / عنب": 75,
    "Figs / تين": 47,
    "Almonds / لوز": 50,
    "Apples / تفاح": 50,
    "Apricots / مشمش": 25,
    "Peaches & Nectarines / خوخ ونكتارين": 20,
    "Plums / برقوق": 15,
    "Pomegranates / رمان": 9,
    "Pears / إجاص": 5,
    "Cherries / كرز": 4,
    "Quinces / سفرجل": 3,
}

FRUIT_LIST = list(FRUIT_TARGETS_KHA.keys())

# Built-in planning yield benchmarks (t/ha). These are fallback values only.
# Where an official Algerian source is available, the app labels that source;
# otherwise the value is clearly labeled as a planning estimate until a MADR/technical
# institute benchmark is entered in Supabase.
BUILTIN_YIELD_BENCHMARKS = {
    # Historical ONS benchmark values (2018-2019 campaign)
    "Potatoes / بطاطا": 31.8,
    "Tomatoes / طماطم": 59.12,
    "Onions / بصل": 32.07,
    # Planning estimates pending crop-specific official benchmark entry
    "Garlic / ثوم": 8.0,
    "Carrots / جزر": 25.0,
    "Green Beans / فاصوليا خضراء": 10.0,
    "Melons / شمام": 25.0,
    "Watermelons / بطيخ": 35.0,
    "Artichokes / خرشوف": 10.0,
    "Peppers / فلفل": 25.0,
    "Zucchini / كوسة": 20.0,
    "Cucumbers / خيار": 30.0,
    "Lettuce / خس": 25.0,
    "Eggplant / باذنجان": 30.0,
    "Peas / جلبانة": 8.0,
    "Cabbage / ملفوف": 30.0,
    "Cauliflower / قرنبيط": 20.0,
    "Olives / زيتون": 1.5,
    "Dates / تمور": 6.0,
    "Citrus / الموالح": 20.0,
    "Grapes / عنب": 8.0,
    "Figs / تين": 3.0,
    "Almonds / لوز": 1.2,
    "Apples / تفاح": 20.0,
    "Apricots / مشمش": 8.0,
    "Peaches & Nectarines / خوخ ونكتارين": 12.0,
    "Plums / برقوق": 10.0,
    "Pomegranates / رمان": 10.0,
    "Pears / إجاص": 15.0,
    "Cherries / كرز": 5.0,
    "Quinces / سفرجل": 12.0,
}

BUILTIN_OFFICIAL_BENCHMARKS = {
    "Potatoes / بطاطا", "Tomatoes / طماطم", "Onions / بصل"
}

# ------------------------------------------------------------------
# Built-in Wilaya fallback benchmarks
# ------------------------------------------------------------------
# These are intentionally estimates, not claimed Ministry benchmarks.
# They guarantee that every crop has a usable fallback for every one of
# the 48 Wilayas until official MADR/technical-institute figures are entered
# in crop_yield_benchmarks. Supabase Wilaya-specific values always override
# these estimates.
#
# The factors represent broad agro-climatic/productivity zones only. They
# are NOT field-level yield predictions.
WILAYA_YIELD_ZONE_FACTORS = {
    # North / coastal / humid zones
    "06 - Béjaïa": 1.02, "09 - Blida": 1.10, "13 - Tlemcen": 1.02,
    "15 - Tizi Ouzou": 0.98, "16 - Alger": 1.02, "18 - Jijel": 1.00,
    "21 - Skikda": 1.03, "23 - Annaba": 1.05, "24 - Guelma": 1.08,
    "25 - Constantine": 0.98, "27 - Mostaganem": 1.05, "29 - Mascara": 1.08,
    "31 - Oran": 1.00, "35 - Boumerdès": 1.08, "36 - El Tarf": 1.08,
    "42 - Tipaza": 1.07, "43 - Mila": 1.03, "46 - Aïn Témouchent": 1.02,
    "48 - Relizane": 1.10,
    # Tell / inland agricultural plains
    "02 - Chlef": 1.10, "10 - Bouira": 1.00, "14 - Tiaret": 0.90,
    "19 - Sétif": 0.88, "20 - Saïda": 0.92, "22 - Sidi Bel Abbès": 1.02,
    "26 - Médéa": 0.95, "28 - M'Sila": 0.82, "32 - El Bayadh": 0.72,
    "34 - Bordj Bou Arréridj": 0.90, "38 - Tissemsilt": 0.92, "40 - Khenchela": 0.86,
    "41 - Souk Ahras": 1.00, "44 - Aïn Defla": 1.08,
    # Eastern / highland interior
    "04 - Oum El Bouaghi": 0.86, "05 - Batna": 0.86, "12 - Tébessa": 0.82,
    "30 - Ouargla": 0.82, "07 - Biskra": 0.92,
    # Steppe / arid transition
    "03 - Laghouat": 0.72, "17 - Djelfa": 0.68, "08 - Béchar": 0.78,
    "45 - Naâma": 0.70,
    # Sahara / irrigated production zones
    "01 - Adrar": 0.82, "11 - Tamanrasset": 0.62, "33 - Illizi": 0.62,
    "37 - Tindouf": 0.60, "39 - El Oued": 0.95, "47 - Ghardaïa": 0.78,
}

CROP_WILAYA_GROUP_FACTORS = {
    # Crops that generally benefit from cooler/humid northern conditions.
    "cool_north": {
        "Potatoes / بطاطا", "Tomatoes / طماطم", "Carrots / جزر",
        "Green Beans / فاصوليا خضراء", "Artichokes / خرشوف", "Peppers / فلفل",
        "Zucchini / كوسة", "Cucumbers / خيار", "Lettuce / خس",
        "Eggplant / باذنجان", "Peas / جلبانة", "Cabbage / ملفوف",
        "Cauliflower / قرنبيط", "Citrus / الموالح", "Apples / تفاح",
        "Pears / إجاص", "Cherries / كرز", "Peaches & Nectarines / خوخ ونكتارين",
        "Plums / برقوق", "Quinces / سفرجل",
    },
    # Crops for which arid/irrigated areas can perform comparatively well.
    "arid_irrigated": {
        "Dates / تمور", "Melons / شمام", "Watermelons / بطيخ",
        "Onions / بصل", "Garlic / ثوم",
    },
    "tree_mediterranean": {
        "Olives / زيتون", "Grapes / عنب", "Figs / تين", "Almonds / لوز",
        "Apricots / مشمش", "Pomegranates / رمان",
    },
}

def get_builtin_wilaya_yield(crop_name, wilaya_name):
    """Return a transparent fallback t/ha estimate for any crop + Wilaya."""
    base = BUILTIN_YIELD_BENCHMARKS.get(crop_name)
    if base is None:
        return None
    factor = WILAYA_YIELD_ZONE_FACTORS.get(str(wilaya_name).strip(), 0.85)

    # Slightly adjust the broad zone factor for crop groups. This remains a
    # planning estimate and is deliberately conservative rather than a claim
    # of measured Wilaya productivity.
    if crop_name in CROP_WILAYA_GROUP_FACTORS["arid_irrigated"] and str(wilaya_name).strip() in {
        "01 - Adrar", "07 - Biskra", "08 - Béchar", "11 - Tamanrasset",
        "30 - Ouargla", "33 - Illizi", "37 - Tindouf", "39 - El Oued", "47 - Ghardaïa"
    }:
        factor *= 1.08
    elif crop_name in CROP_WILAYA_GROUP_FACTORS["cool_north"] and factor < 0.80:
        factor *= 0.92
    elif crop_name in CROP_WILAYA_GROUP_FACTORS["tree_mediterranean"] and factor >= 0.95:
        factor *= 1.03

    return round(float(base) * factor, 2)


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
        "bg_color": "#2c2200",
        "border_color": "#eab308",
        "text_color": "#fef08a",
        "icon": "⚠️",
        "label": "يقظة - الأصفر",
        "badge_bg": "#a16207",
        "badge_text": "#ffffff",
    },
    "orange": {
        "bg_color": "#331600",
        "border_color": "#f97316",
        "text_color": "#ffedd5",
        "icon": "🟠",
        "label": "تحذير - البرتقالي",
        "badge_bg": "#c2410c",
        "badge_text": "#ffffff",
    },
    "red": {
        "bg_color": "#370909",
        "border_color": "#ef4444",
        "text_color": "#fee2e2",
        "icon": "🚨",
        "label": "خطر - الأحمر",
        "badge_bg": "#b91c1c",
        "badge_text": "#ffffff",
    },
}

TEXTS = {
    "AR": {
        "title": "برنامج التخطيط والتنسيق الفلاحي 2026",
        "subtitle": "مشروع طلابي تعليمي وتجريبي — ليس منصة حكومية رسمية",
        "tab_home": "الرئيسية 🏠",
        "tab_card": "بطاقاتي 💳",
        "tab_account": "حسابي وسجلاتي 🔔",
        "main_services": "الخدمات الإلكترونية الرئيسية",
        "crop": "نصائح الزراعة والتصريح (QR)",
        "news": "الأخبار والإعلانات الرسمية",
        "support": "طلب دعم الدولة (الدعم الفلاحي)",
        "weather": "الأحوال الجوية والتنبيهات",
        "pay": "تجديد بطاقة الفلاح (الذهبية/CIB)",
        "suppliers": "خريطة CCLS ونقاط الأسمدة وأسوق الجملة",
        "back_btn": "⬅️ العودة للخدمات الرئيسية",
    },
    "EN": {
        "title": "Agricultural Planning & Coordination Program 2026",
        "subtitle": "Educational Student Project — Not an Official Government Service",
        "tab_home": "Home Services 🏠",
        "tab_card": "Digital Farmer Card 💳",
        "tab_account": "Account & History 🔔",
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
# TERMS OF USE & PRIVACY NOTICE
# ---------------------------------------------------------
TERMS_TEXTS = {
    "AR": {
        "badge": "🌾 مشروع طلابي تعليمي وتجريبي — ليس منصة حكومية رسمية",
        "short": "فلاح منصة تعليمية وتجريبية، وليست خدمة حكومية رسمية. المعلومات والتصريحات والطلبات داخل التطبيق لا تحل محل الإجراءات الرسمية.",
        "continue": "باستمرارك، تقر بأنك قرأت شروط الاستخدام وسياسة الخصوصية وتوافق عليهما.",
        "terms_title": "شروط الاستخدام",
        "privacy_title": "سياسة الخصوصية",
        "agree": "أوافق على شروط الاستخدام وسياسة الخصوصية",
        "terms_sections": [
            ("1. حول منصة فلاح", "فلاح هي منصة فلاحية تعليمية وتجريبية تم تطويرها في إطار مشروع طلابي. تهدف إلى عرض وتجربة أدوات رقمية للتخطيط الفلاحي، التصريحات، طلبات الدعم، المعلومات، التنبيهات والخدمات التجريبية الأخرى.\n\nفلاح ليست منصة حكومية رسمية، ولا يتم تشغيلها من طرف الحكومة الجزائرية أو وزارة الفلاحة أو أي ولاية أو مديرية للمصالح الفلاحية أو أي مؤسسة عمومية أخرى. ولا تُعتبر المعلومات أو التصريحات المقدمة عبرها تصريحاً أو ترخيصاً أو طلباً أو تسجيلاً حكومياً رسمياً إلا إذا أكدت الجهة المختصة ذلك عبر قناة رسمية."),
            ("2. هدف المنصة", "تم تطوير فلاح لأغراض التعليم والتعلم والبحث والتجريب وعرض الخدمات الرقمية الفلاحية واختبار النماذج الرقمية وتقديم معلومات فلاحية عامة. قد يتم تعديل الخدمات أو توقيفها أو حذفها مع تطور المشروع."),
            ("3. حسابات المستخدمين", "قد تتطلب بعض الخدمات إنشاء حساب. يتحمل المستخدم مسؤولية تقديم معلومات صحيحة والمحافظة على سرية بيانات الدخول وعدم السماح لغير المصرح لهم باستعمال حسابه وإبلاغ مسؤول المشروع عند الاشتباه في اختراق الحساب. يُمنع إنشاء حساب بمعلومات كاذبة أو انتحال شخصية الغير."),
            ("4. التصريحات والمعلومات الفلاحية", "قد تسمح المنصة بإدخال معلومات وتصريحات فلاحية لأغراض التخطيط والتجربة. التصريح المقدم عبر فلاح لا يكتسب تلقائياً صفة قانونية أو إدارية رسمية. عند الحاجة إلى إجراء رسمي، يجب إتمامه لدى الهيئة المختصة."),
            ("5. المعلومات والتوصيات الفلاحية", "قد توفر فلاح معلومات أو تقديرات أو توصيات أو تنبيهات أو أدوات للتخطيط. هذه المعلومات عامة وتعليمية. تختلف القرارات الفلاحية حسب التربة والمناخ والمياه والصنف والآفات والممارسات والتنظيمات المحلية. يتحمل المستخدم مسؤولية التحقق والاستعانة بمختص عند الحاجة، ولا تضمن فلاح مردودية أو ربحاً معيناً."),
            ("6. الوثائق والملفات", "قد تسمح بعض الخدمات برفع وثائق أو ملفات. ينبغي رفع الملفات الضرورية فقط. يُمنع رفع محتوى غير قانوني أو ملفات ضارة أو وثائق تخص الغير دون تصريح. وقد يتم تخزين الملفات ومعالجتها بواسطة خدمات تقنية خارجية يعتمد عليها المشروع."),
            ("7. خدمات الدفع", "قد تتضمن المنصة واجهات دفع أو خدمات تجريبية لأغراض العرض. ما لم يُذكر خلاف ذلك، لا يعني وجود واجهة دفع أن فلاح تعالج دفعة حكومية أو إعانة أو ضريبة أو معاملة رسمية. يجب التحقق من المعاملات عبر الخدمة الرسمية المعنية."),
            ("8. الاستخدامات الممنوعة", "يُمنع محاولة الدخول غير المصرح به، تجاوز الحماية، تغيير أو حذف البيانات دون تصريح، رفع ملفات ضارة، انتحال شخصية الغير، تقديم معلومات كاذبة عمداً، إساءة استعمال المنصة، تعطيلها أو القيام بأي نشاط غير قانوني."),
            ("9. توفر المنصة", "فلاح مشروع طلابي وتجريبي، لذلك لا يمكن ضمان توفرها بشكل دائم. قد تتوقف بسبب الصيانة أو المشاكل التقنية أو تحديثات البرامج أو الإجراءات الأمنية أو تطوير المشروع."),
            ("10. الخدمات الخارجية", "قد تعتمد فلاح على خدمات خارجية لقواعد البيانات والمصادقة والتخزين والاستضافة والخرائط والطقس وغيرها. قد تكون بعض هذه الخدمات خارج السيطرة المباشرة لفريق المشروع."),
            ("11. الملكية الفكرية", "قد تكون البرمجيات والواجهة والرسومات والشعارات والمحتويات الأصلية الخاصة بالمشروع محمية بموجب قوانين الملكية الفكرية. لا يجوز نسخ أو تعديل أو إعادة توزيع أو استغلال المكونات المحمية تجارياً دون تصريح مناسب."),
            ("12. حدود المسؤولية", "يتم توفير فلاح «كما هي» و«حسب توفرها» لأغراض تعليمية وتجريبية. لا تضمن المنصة، في حدود ما يسمح به القانون، اكتمال المعلومات أو خلوها من الأخطاء أو استمرار الخدمة أو دقة التقديرات في جميع الظروف أو أن تؤدي التصريحات إلى إجراء رسمي. يتحمل المستخدم مسؤولية القرارات التي يتخذها بناءً على معلومات المنصة."),
            ("13. تعديل الشروط", "قد يتم تحديث شروط الاستخدام مع تطور المشروع، ويمكن عرض النسخة الجديدة داخل المنصة عند إجراء تغييرات مهمة."),
            ("14. الموافقة", "عند إنشاء حساب أو استخدام خدمة تتطلب الموافقة، يقر المستخدم بأنه يعلم أن فلاح مشروع طلابي وتجريبي وليست خدمة حكومية رسمية، وأنه قرأ الشروط وفهمها ويوافق على الاستخدام المسؤول والقانوني."),
        ],
        "privacy_sections": [
            ("1. مقدمة", "تحترم فلاح خصوصية مستخدميها. توضح سياسة الخصوصية نوع المعلومات التي قد يتم جمعها وأسباب استخدامها وكيف يمكن تخزينها والمبادئ العامة لحمايتها. فلاح مشروع طلابي تعليمي وتجريبي وليست منصة حكومية رسمية."),
            ("2. المعلومات التي قد يتم جمعها", "حسب الخدمات المستخدمة، قد يتم جمع: معلومات الحساب مثل الاسم والبريد الإلكتروني ومعلومات المصادقة؛ معلومات فلاحية مثل الولاية والقطاع والمحاصيل والمساحة والتصريحات وطلبات الدعم؛ والملفات التي يرفعها المستخدم اختيارياً. وقد تعالج الخدمات التقنية معلومات لازمة للتشغيل والأمن."),
            ("3. لماذا يتم استخدام المعلومات؟", "يمكن استخدام المعلومات لإدارة الحسابات، توفير الخدمات، معالجة التصريحات وطلبات الدعم، إرسال التنبيهات، تطوير المشروع، حماية المنصة، اكتشاف الاستخدام غير المصرح به، واختبار وتقييم الخدمات الرقمية الفلاحية."),
            ("4. مشاركة المعلومات", "لا تهدف فلاح إلى بيع المعلومات الشخصية للمستخدمين. وقد تتم معالجة بعض المعلومات بواسطة مزودي الخدمات التقنية الضرورية مثل الاستضافة وقواعد البيانات والمصادقة والتخزين والخرائط وغيرها. وقد يتم الكشف عن المعلومات عندما يقتضي القانون ذلك أو لحماية أمن وسلامة المنصة."),
            ("5. حماية البيانات", "يُسعى إلى تطبيق إجراءات تقنية وتنظيمية مناسبة لحماية المعلومات من الوصول أو التعديل أو الكشف أو الإتلاف غير المصرح به. ومع ذلك، لا يمكن ضمان أمن أي نظام متصل بالإنترنت بشكل مطلق، لذلك يُنصح بعدم إدخال معلومات حساسة غير ضرورية."),
            ("6. الاحتفاظ بالبيانات", "قد يتم الاحتفاظ بالمعلومات للمدة اللازمة بشكل معقول لتشغيل المشروع وحمايته وتطويره وتحقيق أهدافه التعليمية، أو وفق الالتزامات القانونية. وقد تختلف مدة الاحتفاظ حسب نوع المعلومات."),
            ("7. حقوق المستخدم", "حسب القانون الجزائري وطبيعة معالجة البيانات، قد يتمتع المستخدم بحقوق تتعلق بمعلوماته الشخصية، بما في ذلك الوصول أو التصحيح وغيرها من الحقوق القانونية. يمكن توجيه الطلبات إلى مسؤول المشروع عبر وسيلة الاتصال المتاحة داخل المنصة."),
            ("8. خصوصية الأطفال", "لم يتم تصميم فلاح خصيصاً للأطفال. ولا ينبغي تقديم معلومات شخصية تخص طفل عبر المنصة دون التصريح المناسب."),
            ("9. البنية التحتية والخدمات الخارجية", "قد تستخدم فلاح خدمات خارجية للمصادقة وقواعد البيانات وتخزين الملفات والاستضافة والخرائط ومعلومات الطقس وغيرها. وقد تعالج هذه الجهات المعلومات وفق شروطها وسياسات الخصوصية الخاصة بها."),
            ("10. الروابط الخارجية", "قد تحتوي فلاح على روابط لمواقع خارجية. عند مغادرة المنصة، تنطبق سياسات الخصوصية الخاصة بالموقع الخارجي، وينبغي مراجعتها قبل تقديم معلومات شخصية إليه."),
            ("11. تعديل سياسة الخصوصية", "قد يتم تحديث سياسة الخصوصية مع تطور المشروع. وتُعرض النسخة الأحدث داخل المنصة، مع مراعاة المتطلبات القانونية المعمول بها."),
            ("12. الاتصال", "للاستفسار حول شروط الاستخدام أو سياسة الخصوصية، يمكن التواصل مع مسؤول المشروع عبر معلومات الاتصال المتوفرة داخل المنصة."),
        ],
    },
    "EN": {
        "badge": "🌾 Educational Student Project — Not an Official Government Service",
        "short": "Felah is an educational and experimental student project, not an official government service. Information, declarations and requests submitted through it do not replace official procedures.",
        "continue": "By continuing, you acknowledge that you have read and agree to the Terms of Use and Privacy Policy.",
        "terms_title": "Terms of Use",
        "privacy_title": "Privacy Policy",
        "agree": "I agree to the Terms of Use and Privacy Policy",
        "terms_sections": [
            ("1. About Felah", "Felah is an educational and experimental agricultural platform developed as a student project. It is intended to demonstrate and test digital tools for agricultural planning, declarations, support requests, information, alerts, directories and other experimental services.\n\nFelah is not an official government platform and is not operated by the Algerian government, Ministry of Agriculture, any Wilaya, Directorate of Agricultural Services, or other public authority. Information or declarations submitted through Felah do not constitute an official administrative declaration, authorization, permit, application or registration unless explicitly confirmed by the competent authority through an official channel."),
            ("2. Purpose of the Platform", "Felah is provided for education, learning, research, experimentation, demonstration of agricultural digital services, testing of digital workflows and general agricultural information. Features may be modified, suspended or removed as the project develops."),
            ("3. User Accounts", "Certain features may require an account. Users are responsible for providing accurate information, keeping credentials confidential, preventing unauthorized use and notifying the project administrator if an account may have been compromised. False information and impersonation are prohibited."),
            ("4. Agricultural Information and Declarations", "The platform may allow agricultural information and declarations to be entered for planning and experimental purposes. A declaration submitted through Felah does not automatically have legal or administrative validity. Official procedures must be completed through the appropriate authority."),
            ("5. Agricultural Information and Recommendations", "Felah may provide information, estimates, recommendations, alerts or planning tools for general educational purposes. Agricultural decisions depend on soil, climate, water, variety, planting material, pests, practices and local regulations. Users remain responsible for verification and professional advice when needed. Felah does not guarantee a specific yield, profit or economic result."),
            ("6. Documents and Files", "Some features may allow users to upload documents or files. Only necessary files should be uploaded. Illegal content, malicious files, or documents belonging to others without authorization must not be uploaded. Files may be stored and processed using third-party technical infrastructure used by the project."),
            ("7. Payments and Demonstration Features", "Some payment interfaces or features may be experimental or demonstrational. Unless explicitly stated otherwise, a payment interface does not mean Felah is processing a real government payment, subsidy, tax or official transaction. Users should verify financial transactions through the relevant official service."),
            ("8. Prohibited Activities", "Users may not attempt unauthorized access, bypass security controls, alter or delete data without authorization, upload malicious files, impersonate others, intentionally submit false information, abuse or disrupt the platform, or conduct unlawful activities."),
            ("9. Availability", "Because Felah is an educational and experimental project, continuous availability is not guaranteed. The platform may be unavailable because of maintenance, technical problems, updates, security measures or project development."),
            ("10. Third-Party Services", "Felah may rely on external services for databases, authentication, storage, hosting, maps, weather information and other functions. Their availability and operation may be outside the direct control of the project team."),
            ("11. Intellectual Property", "The Felah platform, including original software, interface, graphics, logos and project-specific content, may be protected by applicable intellectual-property laws. Protected components may not be copied, modified, redistributed or commercially exploited without appropriate authorization."),
            ("12. Limitation of Responsibility", "Felah is provided on an “as is” and “as available” basis for educational and experimental purposes. To the extent permitted by applicable law, the platform does not guarantee that information is complete or error-free, that the service will always be available, that estimates will always reflect real-world conditions, or that declarations will result in official action. Users are responsible for decisions based on information available through the platform."),
            ("13. Changes to These Terms", "These Terms of Use may be updated as the project develops. Significant changes may be presented to users through the platform."),
            ("14. Acceptance", "By creating an account or using a feature that requires acceptance, you acknowledge that Felah is a student and experimental project, not an official government service, that you have read and understood these Terms, and that you agree to use the platform responsibly and lawfully."),
        ],
        "privacy_sections": [
            ("1. Introduction", "Felah respects user privacy. This Privacy Policy explains what information may be collected, why it may be used, how it may be stored, and the general principles applied to its protection. Felah is an educational and experimental student project and is not an official government platform."),
            ("2. Information We May Collect", "Depending on the features used, the platform may collect account information such as name, email address and authentication-related information; agricultural information such as Wilaya, sector, crops, cultivated area, declarations and support requests; and files voluntarily uploaded by users. Technical services may also process information necessary for operation and security."),
            ("3. Why Information Is Used", "Information may be used to manage accounts, provide platform functionality, process agricultural declarations and support requests, display notifications, improve the educational project, maintain security, detect unauthorized activity, and test and evaluate digital agricultural workflows."),
            ("4. Data Sharing", "Felah does not intend to sell users’ personal information. Information may be processed by technical providers required to operate the platform, such as hosting, database, authentication, storage, mapping and other providers. Information may also be disclosed where required by law or necessary to protect platform security and integrity."),
            ("5. Data Security", "Reasonable technical and organizational measures are intended to protect stored information against unauthorized access, alteration, disclosure or destruction. However, no internet-based system can be guaranteed completely secure. Users should avoid submitting unnecessary sensitive information."),
            ("6. Data Retention", "Information may be retained for as long as reasonably necessary for operation, security, development and educational purposes, or as required by applicable obligations. Retention periods may vary by information type."),
            ("7. Your Rights", "Depending on applicable Algerian law and the circumstances of processing, users may have rights concerning their personal information, including access, correction and other legally applicable protections. Requests may be directed to the project administrator through the available contact method."),
            ("8. Children’s Privacy", "Felah is not specifically designed for children. Users should not provide personal information belonging to a child without appropriate authorization."),
            ("9. Third-Party Infrastructure", "Felah may use third-party services for authentication, databases, file storage, hosting, maps, weather information and other functions. These providers may process information under their own terms and privacy policies."),
            ("10. External Links", "Felah may contain links to external websites. Once you leave Felah, the external website’s privacy practices apply. Users should review its privacy policy before providing personal information."),
            ("11. Changes to This Privacy Policy", "This Privacy Policy may be updated as the project develops. The latest version presented through the platform will apply, subject to applicable legal requirements."),
            ("12. Contact", "For questions concerning these Terms of Use or Privacy Policy, users may contact the project administrator through the contact information provided within the platform."),
        ],
    },
}


# ---------------------------------------------------------
# INITIALIZE SESSION STATE
# ---------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "AR"
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Light"
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
if "show_notif_popup" not in st.session_state:
    st.session_state.show_notif_popup = False
if "show_terms" not in st.session_state:
    st.session_state.show_terms = False

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
def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two coordinates in kilometers."""
    r = 6371.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def min_cost_transfer_plan(surplus_rows, deficit_rows, distance_map, cost_per_t_km, road_factor=1.25):
    """
    Solve the surplus -> deficit transportation problem with a pure-Python
    successive-shortest-path min-cost-flow algorithm.
    Returns transfer rows and total transport cost.
    """
    if not surplus_rows or not deficit_rows:
        return [], 0.0

    # Node layout: source -> surplus -> deficit -> sink.
    source = 0
    surplus_start = 1
    deficit_start = surplus_start + len(surplus_rows)
    sink = deficit_start + len(deficit_rows)
    n = sink + 1
    graph = [[] for _ in range(n)]

    def add_edge(u, v, capacity, cost, meta=None):
        graph[u].append({"to": v, "rev": len(graph[v]), "cap": float(capacity), "cost": float(cost), "meta": meta})
        graph[v].append({"to": u, "rev": len(graph[u]) - 1, "cap": 0.0, "cost": -float(cost), "meta": None})

    for i, row in enumerate(surplus_rows):
        add_edge(source, surplus_start + i, row["amount"], 0.0)

    for j, row in enumerate(deficit_rows):
        add_edge(deficit_start + j, sink, row["amount"], 0.0)

    for i, srow in enumerate(surplus_rows):
        for j, drow in enumerate(deficit_rows):
            key = (srow["wilaya"], drow["wilaya"])
            distance = distance_map.get(key)
            if distance is None or distance <= 0:
                continue
            unit_cost = float(distance) * float(road_factor) * float(cost_per_t_km)
            add_edge(
                surplus_start + i,
                deficit_start + j,
                min(srow["amount"], drow["amount"]),
                unit_cost,
                meta={
                    "from": srow["wilaya"],
                    "to": drow["wilaya"],
                    "distance_km": float(distance),
                    "road_distance_km": float(distance) * float(road_factor),
                },
            )

    transfers = []
    total_cost = 0.0
    eps = 1e-8

    while True:
        # Bellman-Ford on the residual graph. The graph is small (48 Wilayas),
        # and this also handles negative reverse-edge costs safely.
        dist = [float("inf")] * n
        prev = [None] * n
        dist[source] = 0.0
        for _ in range(n - 1):
            changed = False
            for u in range(n):
                if not math.isfinite(dist[u]):
                    continue
                for ei, edge in enumerate(graph[u]):
                    if edge["cap"] <= eps:
                        continue
                    nd = dist[u] + edge["cost"]
                    if nd < dist[edge["to"]] - 1e-10:
                        dist[edge["to"]] = nd
                        prev[edge["to"]] = (u, ei)
                        changed = True
            if not changed:
                break

        if prev[sink] is None:
            break

        path_cap = float("inf")
        node = sink
        while node != source:
            u, ei = prev[node]
            path_cap = min(path_cap, graph[u][ei]["cap"])
            node = u

        if path_cap <= eps:
            break

        node = sink
        path_edges = []
        while node != source:
            u, ei = prev[node]
            edge = graph[u][ei]
            path_edges.append((u, ei, edge))
            node = u
        path_edges.reverse()

        for u, ei, edge in path_edges:
            reverse_index = edge["rev"]
            edge["cap"] -= path_cap
            graph[edge["to"]][reverse_index]["cap"] += path_cap
            if edge.get("meta"):
                meta = edge["meta"]
                transfers.append({
                    "From Wilaya": meta["from"],
                    "To Wilaya": meta["to"],
                    "Transfer (t)": path_cap,
                    "Straight-line Distance (km)": meta["distance_km"],
                    "Estimated Road Distance (km)": meta["road_distance_km"],
                    "Transport Cost (DZD)": path_cap * meta["road_distance_km"] * float(cost_per_t_km),
                })
                total_cost += path_cap * meta["road_distance_km"] * float(cost_per_t_km)

    # Residual-path augmentation can touch the same route more than once.
    if transfers:
        transfer_df = pd.DataFrame(transfers)
        transfer_df = (
            transfer_df.groupby(
                ["From Wilaya", "To Wilaya", "Straight-line Distance (km)", "Estimated Road Distance (km)"],
                as_index=False,
            )[["Transfer (t)", "Transport Cost (DZD)"]]
            .sum()
        )
        transfers = transfer_df.to_dict("records")

    return transfers, total_cost


def sanitize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[<>]", "", str(text)).strip()


def get_admin_password() -> str:
    # Read the admin code from Streamlit Secrets without a hard-coded fallback.
    # If the secret is missing, return an empty value so the app does not crash.
    return str(st.secrets.get("ADMIN_SECRET_KEY", "")).strip()


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


def get_user_notifications():
    if not st.session_state.logged_in or not supabase_client:
        return []
    try:
        res = (
            supabase_client.table("farmer_notifications")
            .select("*")
            .eq("farmer_email", st.session_state.farmer_email)
            .order("id", desc=True)
            .execute()
        )
        return res.data if res.data else []
    except Exception:
        return []


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
# DYNAMIC CSS STYLING WITH BALANCING SIDE SPACERS
# ---------------------------------------------------------
is_dark = st.session_state.theme_mode == "Dark"

if is_dark:
    # Deep charcoal base + restrained red-orange + dark golden-yellow accents
    # Designed to be comfortable for the eyes while keeping text highly visible.
    bg_color = "#101214"
    card_bg = "#191c20"
    sidebar_bg = "#17191d"
    text_color = "#f4f1e8"
    border_color = "#34383d"
    subtext_color = "#b4b0a7"
    accent_color = "#d94a2f"
    accent_hover = "#b93622"
    accent_yellow = "#c89d2a"
    accent_yellow_hover = "#a9811f"

    btn_css = f"""
        background: linear-gradient(135deg, {accent_color} 0%, #bd3824 100%) !important;
        color: #fffaf0 !important;
        border-radius: 10px !important;
        border: 1px solid {accent_hover} !important;
        font-weight: 650 !important;
        padding: 0.6rem 1.2rem !important;
        box-shadow: 0 2px 7px rgba(0,0,0,0.30) !important;
        transition: all 0.2s ease-in-out !important;
    """
    btn_hover_css = f"""
        background: linear-gradient(135deg, {accent_hover} 0%, #9f2d1d 100%) !important;
        border-color: {accent_yellow} !important;
        color: #fffaf0 !important;
    """
    sidebar_css = f"""
        background-color: {sidebar_bg} !important;
        border-right: 1px solid {border_color} !important;
        color: {text_color} !important;
    """
    sidebar_inputs_css = f"""
        div[data-testid="stSidebar"] input {{
            background-color: #202328 !important;
            color: #fffaf0 !important;
            border: 1px solid #4a4d50 !important;
            border-radius: 8px !important;
        }}
        div[data-testid="stSidebar"] input:focus {{
            border-color: {accent_yellow} !important;
            box-shadow: 0 0 0 1px {accent_yellow} !important;
        }}
        div[data-testid="stSidebar"] label,
        div[data-testid="stSidebar"] p,
        div[data-testid="stSidebar"] span,
        div[data-testid="stSidebar"] h1,
        div[data-testid="stSidebar"] h2,
        div[data-testid="stSidebar"] h3 {{
            color: {text_color} !important;
        }}
        div[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
            color: {text_color} !important;
        }}
        div[data-testid="stSidebar"] hr {{
            border-color: #3a3d40 !important;
        }}
    """
    segmented_active_css = f"""
        background: linear-gradient(135deg, {accent_color} 0%, #a83220 100%) !important;
        color: #fff8e7 !important;
        font-weight: 700 !important;
        border: 1px solid {accent_yellow} !important;
        box-shadow: 0 2px 7px rgba(0,0,0,0.38) !important;
    """
else:
    bg_color = "#f8fafc"
    card_bg = "#ffffff"
    sidebar_bg = "#f1f5f9"
    text_color = "#0f172a"
    border_color = "#cbd5e1"
    subtext_color = "#64748b"
    accent_color = "#047857"

    btn_css = """
        background-color: #e2e8f0 !important;
        color: #1e293b !important;
        border-radius: 10px !important;
        border: 1px solid #cbd5e1 !important;
        font-weight: 600 !important;
        padding: 0.65rem 1.25rem !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease-in-out !important;
    """
    btn_hover_css = """
        background-color: #cbd5e1 !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    """
    sidebar_css = f"background-color: {sidebar_bg} !important;"
    sidebar_inputs_css = ""
    segmented_active_css = "background-color: #ffffff !important; color: #047857 !important; font-weight: 700 !important; box-shadow: 0 2px 6px rgba(0,0,0,0.12) !important;"

st.markdown(
    f"""
    <style>
    /* App Container */
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
        font-family: system-ui, -apple-system, sans-serif;
        color-scheme: {"dark" if is_dark else "light"} !important;
    }}

    html, body {{
        color-scheme: {"dark" if is_dark else "light"} !important;
    }}

    .block-container {{
        padding-top: 3rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 800px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        box-sizing: border-box !important;
    }}

    div[data-testid="stSidebar"] {{
        {sidebar_css}
    }}
    {sidebar_inputs_css}

    .terms-shell {{
        max-width: 980px;
        margin: 0 auto 1rem auto;
    }}
    .terms-hero {{
        padding: 1.35rem 1.5rem;
        border-radius: 18px;
        border: 1px solid rgba(80, 170, 105, 0.30);
        background: linear-gradient(135deg, rgba(44, 120, 69, 0.18), rgba(210, 160, 45, 0.10));
        text-align: center;
    }}
    .terms-hero h2 {{ margin: 0.55rem 0 0.4rem 0; }}
    .terms-hero p {{ margin: 0; opacity: 0.86; line-height: 1.65; }}
    .terms-badge {{
        display: inline-block;
        padding: 0.38rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        border: 1px solid rgba(220, 155, 45, 0.38);
    }}

/* Compact creative Language / Theme selectors */
    div[data-testid="stSidebar"] div[data-testid="column"] {{
        min-width: 0 !important;
    }}

    div[data-testid="stSidebar"] div[data-testid="column"] > div {{
        margin-bottom: -4px !important;
    }}

    div[data-testid="stSidebar"] div[data-testid="column"] [data-testid="stSegmentedControl"] {{
        width: 100% !important;
    }}

    div[data-testid="stSidebar"] div[data-testid="column"] [data-testid="stSegmentedControl"] button {{
        min-height: 28px !important;
        height: 28px !important;
        padding: 2px 7px !important;
        font-size: 0.72rem !important;
        line-height: 1 !important;
    }}

    div[data-testid="stSidebar"] div[data-testid="column"] [data-testid="stSegmentedControl"] + div {{
        display: none !important;
    }}

    div[data-testid="stSidebar"] .compact-control-label {{
        font-size: 0.70rem !important;
        font-weight: 700 !important;
        margin-bottom: 2px !important;
        opacity: 0.85;
    }}

    /* Clear, touch-friendly account action selector */
    div[data-testid="stSidebar"] [data-testid="stSelectbox"] > div {{
        min-height: 44px !important;
    }}
    div[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"] {{
        min-height: 42px !important;
        font-weight: 600 !important;
    }}

    /* Dark-mode finishing accents */
    .section-title {{
        text-shadow: 0 1px 2px rgba(0,0,0,0.35);
    }}

    .news-card, .notif-card {{
        box-shadow: 0 3px 10px rgba(0,0,0,0.22);
    }}

    .notif-popover {{
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }}

    /* Green Header Banner Setup */
    .header-banner {{
        background: linear-gradient(135deg, #047857 0%, #065f46 100%);
        color: #ffffff;
        padding: 22px 16px;
        border-radius: 14px;
        text-align: center !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
        width: 100% !important;
        margin: 0 auto 15px auto !important;
        box-sizing: border-box !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    .header-banner h2 {{
        margin: 0 0 6px 0 !important;
        font-weight: 800 !important;
        font-size: 1.45rem !important;
        color: #ffffff !important;
        text-align: center !important;
        padding: 0 !important;
        line-height: 1.3 !important;
    }}
    .header-banner p {{
        margin: 0 !important;
        opacity: 0.95;
        font-size: 0.88rem !important;
        color: #ecfdf5 !important;
        text-align: center !important;
        padding: 0 !important;
    }}

    /* HEADER + BELL: CENTER THE BANNER AND KEEP THE BELL VISIBLE */
    div[data-testid="stHorizontalBlock"]:has(.header-banner) {{
        display: grid !important;
        grid-template-columns: minmax(0, 1fr) minmax(0, 800px) minmax(48px, 1fr) !important;
        align-items: start !important;
        width: 100% !important;
        margin: 0 auto !important;
        column-gap: 6px !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.header-banner) > div:first-child {{
        grid-column: 1 !important;
        width: 100% !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.header-banner) > div:nth-child(2) {{
        grid-column: 2 !important;
        width: 100% !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.header-banner) > div:last-child {{
        grid-column: 3 !important;
        width: 100% !important;
        padding-left: 0 !important;
        padding-top: 4px !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.header-banner) > div:last-child .stButton {{
        width: 100% !important;
        min-width: 44px !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.header-banner) > div:last-child .stButton > button {{
        min-width: 44px !important;
        min-height: 42px !important;
        padding: 4px 6px !important;
        font-size: 0.95rem !important;
    }}

    /* FLEX CENTER CONTAINMENT */
    div[data-testid="stSegmentedControl"] {{
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        margin: 0 auto 20px auto !important;
        background: transparent !important;
    }}

    /* Inner Bar Shell */
    div[data-testid="stSegmentedControl"] > div,
    div[data-testid="stSegmentedControl"] [role="radiogroup"] {{
        display: flex !important;
        flex-direction: row-reverse !important; /* RTL Support */
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        max-width: 600px !important;
        margin: 0 auto !important;
        background-color: transparent !important;
        padding: 4px !important;
        box-sizing: border-box !important;
        flex-wrap: nowrap !important;
        overflow: visible !important;
    }}

    /* LEFT & RIGHT TRANSPARENT BALANCING SPACERS */
    div[data-testid="stSegmentedControl"] > div::before,
    div[data-testid="stSegmentedControl"] > div::after,
    div[data-testid="stSegmentedControl"] [role="radiogroup"]::before,
    div[data-testid="stSegmentedControl"] [role="radiogroup"]::after {{
        content: "" !important;
        flex: 1 1 0% !important; /* Pushes interactive buttons into exact horizontal center */
        min-width: 10px !important;
        height: 1px !important;
        background: transparent !important;
        pointer-events: none !important;
    }}

    /* Individual Option Buttons with Gap Spacing */
    div[data-testid="stSegmentedControl"] button,
    div[data-testid="stSegmentedControl"] [role="option"] {{
        flex: 0 0 auto !important;
        white-space: nowrap !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        padding: 8px 18px !important; /* Comfortable button padding */
        text-align: center !important;
        border-radius: 24px !important;
        border: 1px solid {border_color} !important;
        background-color: {card_bg} !important; /* Standard button color */
        color: {text_color} !important;
        margin: 0 6px !important; /* Controlled gap distance between buttons */
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }}

    /*
       Streamlit's collapsed sidebar control is framework-owned.
       The visible large MENU opener is rendered by render_sidebar_toggle()
       below using a tiny iframe that forwards the click to Streamlit's native
       [data-testid="stSidebarCollapseButton"].
    */
    .st-key-sidebar_toggle_iframe {{
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 220px !important;
        height: 70px !important;
        min-width: 220px !important;
        min-height: 70px !important;
        padding: 0 !important;
        margin: 0 !important;
        z-index: 2147483646 !important;
        pointer-events: none !important;
        overflow: visible !important;
    }}

    .st-key-sidebar_toggle_iframe iframe,
    .st-key-sidebar_toggle_iframe [data-testid="stIFrame"] {{
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 220px !important;
        height: 70px !important;
        min-width: 220px !important;
        min-height: 70px !important;
        border: 0 !important;
        background: transparent !important;
        pointer-events: auto !important;
        z-index: 2147483647 !important;
    }}

    @media (max-width: 640px) {{
        .st-key-sidebar_toggle_iframe,
        .st-key-sidebar_toggle_iframe iframe,
        .st-key-sidebar_toggle_iframe [data-testid="stIFrame"] {{
            width: 190px !important;
            min-width: 190px !important;
        }}
    }}

    [data-testid="stSidebarCollapseButton"] button[data-testid="stBaseButton-headerNoPadding"] {{
        cursor: pointer !important;
    }}

    /* Expanded sidebar close button remains compact and clear. */
    div[data-testid="stSidebar"] button[data-testid="stSidebarCollapseButton"] {{
        min-width: 40px !important;
        width: 40px !important;
        min-height: 40px !important;
        height: 40px !important;
        padding: 6px !important;
        border-radius: 10px !important;
    }}

    /* Account expander: large, obvious header/arrow for touch devices. */
    div[data-testid="stSidebar"] details summary {{
        min-height: 52px !important;
        padding: 10px 12px !important;
        border-radius: 12px !important;
        font-size: 1.02rem !important;
        font-weight: 750 !important;
        cursor: pointer !important;
    }}

    div[data-testid="stSidebar"] details summary svg {{
        width: 1.25rem !important;
        height: 1.25rem !important;
        min-width: 1.25rem !important;
        min-height: 1.25rem !important;
    }}

    div[data-testid="stSidebar"] details summary:hover {{
        background-color: rgba(100, 116, 139, 0.10) !important;
    }}

    /* Main 3-item navigation: keep the original full-width placement and force only the 3 items to stay in one row. */
    section[data-testid="stMain"] div[data-testid="stSegmentedControl"] > div,
    section[data-testid="stMain"] div[data-testid="stSegmentedControl"] [role="radiogroup"] {{
        display: grid !important;
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        width: 100% !important;
        max-width: none !important;
        gap: 4px !important;
        padding: 4px !important;
        box-sizing: border-box !important;
        margin: 0 auto !important;
    }}

    section[data-testid="stMain"] div[data-testid="stSegmentedControl"] > div::before,
    section[data-testid="stMain"] div[data-testid="stSegmentedControl"] > div::after,
    section[data-testid="stMain"] div[data-testid="stSegmentedControl"] [role="radiogroup"]::before,
    section[data-testid="stMain"] div[data-testid="stSegmentedControl"] [role="radiogroup"]::after {{
        display: none !important;
    }}

    section[data-testid="stMain"] div[data-testid="stSegmentedControl"] button,
    section[data-testid="stMain"] div[data-testid="stSegmentedControl"] [role="option"] {{
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        margin: 0 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        box-sizing: border-box !important;
    }}

    /* Active Highlighted Button */
    div[data-testid="stSegmentedControl"] button[data-checked="true"],
    div[data-testid="stSegmentedControl"] [aria-selected="true"] {{
        {segmented_active_css}
        border-color: {accent_color} !important;
    }}

    /* Main navigation marker: keep the navigation bar compact and centered. */
    #main-navigation-marker {{
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    /* Mobile Responsive Scaling (< 640px): KEEP MAIN NAVIGATION IN ONE ROW */
    @media (max-width: 640px) {{
        .block-container {{
            padding-top: 2rem !important;
            padding-left: 0.55rem !important;
            padding-right: 0.55rem !important;
            padding-bottom: 0.7rem !important;
            max-width: 100% !important;
        }}

        /* Compact service Back button on mobile */
        div[data-testid="stHorizontalBlock"] .stButton > button {{
            min-height: 38px !important;
            padding: 5px 9px !important;
            font-size: 0.78rem !important;
        }}

        /* Make the Account expander header easy to see and tap on phones. */
        div[data-testid="stSidebar"] details summary {{
            min-height: 56px !important;
            padding: 11px 12px !important;
            font-size: 0.98rem !important;
        }}

        div[data-testid="stSidebar"] details summary svg {{
            width: 1.35rem !important;
            height: 1.35rem !important;
        }}

        /* Keep the Account action selector easy to see and tap on phones. */
        div[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"] {{
            min-height: 44px !important;
            font-size: 0.86rem !important;
        }}

        /* Keep sidebar language/theme controls compact */
        div[data-testid="stSidebar"] div[data-testid="column"] label {{
            font-size: 0.64rem !important;
            line-height: 1 !important;
        }}

        div[data-testid="stSidebar"] div[data-testid="column"] [role="radiogroup"] {{
            gap: 0 !important;
            margin-top: -4px !important;
        }}

        div[data-testid="stSidebar"] div[data-testid="column"] [role="radiogroup"] label {{
            font-size: 0.58rem !important;
            padding: 0 !important;
            margin: 0 !important;
        }}

        div[data-testid="stSidebar"] div[data-testid="column"] [role="radiogroup"] label div {{
            transform: scale(0.78) !important;
            transform-origin: left center !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.header-banner) {{
            grid-template-columns: minmax(0, 1fr) minmax(0, 11fr) minmax(44px, 1fr) !important;
            gap: 4px !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.header-banner) > div:first-child {{
            grid-column: 1 !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.header-banner) > div:nth-child(2) {{
            grid-column: 2 !important;
        }}

        div[data-testid="stHorizontalBlock"]:has(.header-banner) > div:last-child {{
            grid-column: 3 !important;
            padding-left: 0 !important;
            padding-top: 2px !important;
        }}

        .header-banner {{
            min-height: 84px !important;
            padding: 16px 10px !important;
            margin-bottom: 12px !important;
        }}

        .header-banner h2 {{
            font-size: 1.02rem !important;
            line-height: 1.25 !important;
        }}

        .header-banner p {{
            font-size: 0.70rem !important;
            line-height: 1.25 !important;
        }}

        div[data-testid="stSegmentedControl"] {{
            margin: 0 auto 16px auto !important;
        }}

        /* Force the three main navigation options to remain one horizontal row.
           Equal-width grid cells prevent long English labels from wrapping into
           a second/third row on phones. */
        section[data-testid="stMain"] div[data-testid="stSegmentedControl"] > div,
        section[data-testid="stMain"] div[data-testid="stSegmentedControl"] [role="radiogroup"] {{
            width: 100% !important;
            max-width: 100% !important;
            display: grid !important;
            grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
            gap: 3px !important;
            padding: 2px !important;
            box-sizing: border-box !important;
            flex-wrap: nowrap !important;
        }}

        section[data-testid="stMain"] div[data-testid="stSegmentedControl"] > div::before,
        section[data-testid="stMain"] div[data-testid="stSegmentedControl"] > div::after,
        section[data-testid="stMain"] div[data-testid="stSegmentedControl"] [role="radiogroup"]::before,
        section[data-testid="stMain"] div[data-testid="stSegmentedControl"] [role="radiogroup"]::after {{
            display: none !important;
        }}

        section[data-testid="stMain"] div[data-testid="stSegmentedControl"] button,
        section[data-testid="stMain"] div[data-testid="stSegmentedControl"] [role="option"] {{
            width: 100% !important;
            min-width: 0 !important;
            max-width: 100% !important;
            white-space: nowrap !important;
            font-size: clamp(0.53rem, 2.35vw, 0.72rem) !important;
            line-height: 1.1 !important;
            padding: 7px 2px !important;
            margin: 0 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            box-sizing: border-box !important;
        }}

        /* Sidebar Language/Theme still use their own two-option horizontal layout. */
        div[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] > div,
        div[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radiogroup"] {{
            display: flex !important;
            flex-direction: row !important;
            grid-template-columns: none !important;
            width: 100% !important;
            max-width: 100% !important;
            gap: 0 !important;
            padding: 2px !important;
        }}

        div[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button,
        div[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="option"] {{
            flex: 1 1 0 !important;
            width: auto !important;
            max-width: none !important;
            font-size: 0.62rem !important;
            padding: 5px 3px !important;
        }}
    }}

    .stButton>button {{
        {btn_css}
    }}
    .stButton>button:hover {{
        {btn_hover_css}
    }}

    .section-title {{
        text-align: center;
        color: {text_color};
        margin-top: 4px;
        margin-bottom: 12px;
        font-size: 1.35rem;
        font-weight: 700;
    }}

    /* Service page: compact back button + immediate content */
    .service-content-start {{
        height: 2px !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    div[data-testid="stHorizontalBlock"] .stButton {{
        margin-bottom: 0 !important;
    }}

    /* Compact main-services area: less empty vertical space */
    div[data-testid="stHorizontalBlock"]:has(#main-services-grid) {{
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(#main-services-grid) .stButton > button {{
        min-height: 58px !important;
    }}

    .news-card, .notif-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-left: 5px solid {accent_color};
        padding: 16px;
        border-radius: 10px;
        margin-bottom: 12px;
        color: {text_color};
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }}

    .notif-popover {{
        background-color: {card_bg};
        border: 1px solid {accent_color};
        border-radius: 12px;
        padding: 16px;
        margin-top: 10px;
        margin-bottom: 20px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }}
    </style>
""",
    unsafe_allow_html=True,
)

t = TEXTS[st.session_state.lang]
unread_count = get_unread_notif_count()

# ---------------------------------------------------------
# SIDEBAR CONTROL PANEL
# ---------------------------------------------------------
def render_sidebar_toggle():
    """Render a large custom opener that forwards its click to Streamlit's native sidebar toggle."""
    toggle_html = r"""
    <style>
      html, body {
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: transparent;
      }

      #felah-sidebar-toggle {
        position: fixed;
        top: 8px;
        left: 8px;
        width: 202px;
        height: 50px;
        padding: 0 14px;
        border: 1px solid #9a4d0d;
        border-radius: 13px;
        background: #c96a18;
        color: #ffffff;
        box-shadow: 0 4px 14px rgba(0,0,0,0.22);
        font-family: Arial, sans-serif;
        font-size: 15px;
        font-weight: 800;
        letter-spacing: 0.1px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 9px;
        white-space: nowrap;
        z-index: 2147483647;
        transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
      }

      #felah-sidebar-toggle:hover {
        background: #b85d12;
        box-shadow: 0 5px 16px rgba(0,0,0,0.28);
        transform: translateY(-1px);
      }

      #felah-sidebar-toggle:active {
        transform: translateY(0);
      }

      #felah-sidebar-toggle.hidden {
        display: none;
      }

      #felah-sidebar-toggle .icon {
        font-size: 20px;
        line-height: 1;
      }

      @media (max-width: 640px) {
        #felah-sidebar-toggle {
          top: 7px;
          left: 7px;
          width: 174px;
          height: 46px;
          padding: 0 8px;
          border-radius: 12px;
          font-size: 12.5px;
          gap: 7px;
        }

        #felah-sidebar-toggle .icon {
          font-size: 18px;
        }
      }
    </style>

    <button id="felah-sidebar-toggle" type="button" aria-label="Open menu and account settings">
      <span class="icon">⚙️</span>
      <span>MENU / القائمة</span>
    </button>

    <script>
      (function () {
        const button = document.getElementById("felah-sidebar-toggle");

        function nativeSidebarButton() {
          try {
            return window.parent.document.querySelector(
              '[data-testid="stSidebarCollapseButton"] button[data-testid="stBaseButton-headerNoPadding"]'
            ) || window.parent.document.querySelector(
              '[data-testid="stSidebarCollapseButton"] button'
            );
          } catch (e) {
            return null;
          }
        }

        function syncVisibility() {
          try {
            const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
            const isExpanded = sidebar && sidebar.getAttribute("aria-expanded") === "true";
            button.classList.toggle("hidden", !!isExpanded);
          } catch (e) {
            // Keep the opener visible if the parent DOM cannot be inspected.
            button.classList.remove("hidden");
          }
        }

        button.addEventListener("click", function () {
          const nativeButton = nativeSidebarButton();
          if (nativeButton) {
            nativeButton.click();
            setTimeout(syncVisibility, 80);
            setTimeout(syncVisibility, 350);
          }
        });

        syncVisibility();
        setInterval(syncVisibility, 300);
      })();
    </script>
    """

    # The keyed container lets us position only this iframe, without affecting
    # maps or any other iframe-based widgets used elsewhere in the app.
    with st.container(key="sidebar_toggle_iframe"):
        components.html(toggle_html, height=70, width=220, scrolling=False)


with st.sidebar:
    st.title("⚙️ MENU / القائمة")

    # Compact Language + Theme controls
    lang_col, theme_col = st.columns(2, gap="small")

    with lang_col:
        st.markdown('<div class="compact-control-label">🌐 Language</div>', unsafe_allow_html=True)
        lang_choice = st.segmented_control(
            "Language",
            options=["العربية", "EN"],
            default="العربية" if st.session_state.lang == "AR" else "EN",
            key="lang_segmented_select",
            label_visibility="collapsed",
        )

    with theme_col:
        st.markdown('<div class="compact-control-label">🎨 Theme</div>', unsafe_allow_html=True)
        theme_choice = st.segmented_control(
            "Theme",
            options=["☀️", "🌙"],
            default="☀️" if st.session_state.theme_mode == "Light" else "🌙",
            key="theme_segmented_select",
            label_visibility="collapsed",
        )

    if lang_choice is None:
        lang_choice = "العربية" if st.session_state.lang == "AR" else "EN"
    if theme_choice is None:
        theme_choice = "☀️" if st.session_state.theme_mode == "Light" else "🌙"

    new_lang = "AR" if lang_choice == "العربية" else "EN"
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()

    new_theme = "Dark" if theme_choice == "🌙" else "Light"
    if new_theme != st.session_state.theme_mode:
        st.session_state.theme_mode = new_theme
        st.rerun()

    st.divider()

    if st.button(f"📜 {TERMS_TEXTS[st.session_state.lang]['terms_title']} & {TERMS_TEXTS[st.session_state.lang]['privacy_title']}", use_container_width=True, key="sidebar_terms_btn"):
        st.session_state.show_terms = not st.session_state.show_terms
        st.rerun()

    # Expandable account area with a large, clearly visible arrow.
    # The whole header is tappable, which is easier to use on phones.
    with st.expander("👤 Account / تسجيل الدخول", expanded=not st.session_state.logged_in):
        if not st.session_state.logged_in:
            auth_mode = st.selectbox(
                "Action / الإجراء",
                ["Log In (دخول)", "Register (إنشاء حساب)", "Forgot Password"],
                key="auth_mode_select",
            )

            email_input = st.text_input("Email / البريد الإلكتروني")
            pass_input = st.text_input("Password / كلمة السر", type="password")

            if auth_mode == "Register (إنشاء حساب)":
                name_input = st.text_input("Full Name / الاسم الكامل")
                carte_input = st.text_input(
                    "Carte Fellah N° / رقم بطاقة الفلاح", placeholder="DZ-2026-XXXX"
                )

                captcha_ans = st.number_input(
                    f"Security Check: {st.session_state.captcha_num1} + {st.session_state.captcha_num2} = ?",
                    step=1,
                    value=0,
                )

                terms_agreed = st.checkbox(
                    TERMS_TEXTS[st.session_state.lang]["agree"],
                    key="register_terms_agreed",
                )
                st.caption(TERMS_TEXTS[st.session_state.lang]["short"])

                if st.button("Submit Registration", use_container_width=True):
                    if not terms_agreed:
                        st.error("Please accept the Terms of Use and Privacy Policy before registering.")
                    elif (
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
                # Clear notice immediately above the Login button so every user
                # sees the student-project status before entering the application.
                st.markdown(
                    f"""
                    <div style="
                        border:1.5px solid #f59e0b;
                        border-radius:9px;
                        padding:9px 11px;
                        margin:6px 0 7px 0;
                        background:rgba(245,158,11,0.08);
                    ">
                        <div style="font-weight:800; font-size:0.88rem;">
                            {TERMS_TEXTS[st.session_state.lang]['badge']}
                        </div>
                        <div style="font-size:0.76rem; line-height:1.35; margin-top:3px;">
                            {TERMS_TEXTS[st.session_state.lang]['short']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                login_terms_agreed = st.checkbox(
                    TERMS_TEXTS[st.session_state.lang]["agree"],
                    key="login_terms_agreed",
                )
                st.caption(TERMS_TEXTS[st.session_state.lang]["continue"])
                if st.button("Login", use_container_width=True):
                    if not login_terms_agreed:
                        st.error(
                            "Please accept the Terms of Use and Privacy Policy before logging in."
                        )
                    elif email_input and pass_input and supabase_client:
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
                if st.button("Send Reset Link", use_container_width=True):
                    if email_input and supabase_client:
                        try:
                            supabase_client.auth.reset_password_for_email(
                                email_input
                            )
                            st.info("Password reset link sent to your email.")
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.success(f"Logged in: {st.session_state.farmer_name}")
            st.caption(f"Carte N°: {st.session_state.carte_num}")
            if unread_count > 0:
                st.warning(f"🔔 You have {unread_count} unread notifications!")

            if st.button("Log Out / خروج", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.farmer_email = ""
                st.session_state.admin_authenticated = False
                st.rerun()

# Large custom opener for the collapsed sidebar. It disappears while the sidebar is open.
render_sidebar_toggle()

# ---------------------------------------------------------
# HEADER BANNER & BELL ICON
# ---------------------------------------------------------
banner_spacer_col, banner_col, bell_col = st.columns([1, 11, 1])

with banner_col:
    st.markdown(
        f"""
        <div class="header-banner">
            <h2>{t['title']}</h2>
            <p>{t['subtitle']}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

with bell_col:
    bell_label = f"🔔 {unread_count}" if unread_count > 0 else "🔔"
    if st.button(
        bell_label,
        key="hdr_bell_btn",
        help="View Notifications",
        use_container_width=True,
    ):
        st.session_state.show_notif_popup = not st.session_state.show_notif_popup
        st.rerun()

# Quick Notification Viewer Overlay
if st.session_state.show_notif_popup:
    st.markdown('<div class="notif-popover">', unsafe_allow_html=True)
    st.markdown("#### 🔔 Quick Notifications Inbox")
    if not st.session_state.logged_in:
        st.info("Please log in to view your private notifications.")
    else:
        notifs = get_user_notifications()
        if notifs:
            for n in notifs[:3]:
                st.markdown(
                    f"""
                    <div class="notif-card">
                        <b>📩 {sanitize(n.get('title',''))}</b>
                        <p style="margin:2px 0; font-size:0.9em;">{sanitize(n.get('message',''))}</p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No notifications available.")
    if st.button("Close Notifications", key="close_notif"):
        st.session_state.show_notif_popup = False
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TERMS / PRIVACY PANEL
# ---------------------------------------------------------
if st.session_state.show_terms:
    terms_data = TERMS_TEXTS[st.session_state.lang]
    st.markdown(
        f"""
        <div class="terms-shell">
            <div class="terms-hero">
                <div class="terms-badge">{terms_data['badge']}</div>
                <h2>{terms_data['terms_title']} &amp; {terms_data['privacy_title']}</h2>
                <p>{terms_data['short']}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    terms_tab, privacy_tab = st.tabs([
        f"📄 {terms_data['terms_title']}",
        f"🔒 {terms_data['privacy_title']}",
    ])
    with terms_tab:
        for title, body in terms_data['terms_sections']:
            st.markdown(f"### {title}")
            st.markdown(body)
            st.divider()
    with privacy_tab:
        for title, body in terms_data['privacy_sections']:
            st.markdown(f"### {title}")
            st.markdown(body)
            st.divider()
    st.info(terms_data['continue'])
    if st.button("✕ Close / إغلاق", key="close_terms_panel"):
        st.session_state.show_terms = False
        st.rerun()

# ---------------------------------------------------------
# ALIGNED SLIDING TABS SWITCHER (WITH SIDE SPACERS)
# ---------------------------------------------------------
tab_options_map = {
    f"{t['tab_home']}": "home",
    f"{t['tab_card']}": "card",
    f"{t['tab_account']}": "account",
}

reverse_map = {v: k for k, v in tab_options_map.items()}

st.markdown('<div id="main-navigation-marker"></div>', unsafe_allow_html=True)

selected_segmented_label = st.segmented_control(
    label="Navigation Tabs",
    options=list(tab_options_map.keys()),
    default=reverse_map.get(
        st.session_state.active_tab, list(tab_options_map.keys())[0]
    ),
    label_visibility="collapsed",
    key="sliding_tabs_control",
    width="stretch",
)

if (
    selected_segmented_label
    and tab_options_map[selected_segmented_label] != st.session_state.active_tab
):
    st.session_state.active_tab = tab_options_map[selected_segmented_label]
    st.rerun()

# ---------------------------------------------------------
# FAST SERVICE NAVIGATION
# ---------------------------------------------------------
def open_service(service_name):
    st.session_state.selected_service = service_name


def close_service():
    st.session_state.selected_service = None


# ---------------------------------------------------------
# TAB 1: MAIN SERVICES VIEW
# ---------------------------------------------------------
if st.session_state.active_tab == "home":
    if st.session_state.selected_service is None:
        st.markdown(
            f"<h3 class='section-title'>{t['main_services']}</h3>",
            unsafe_allow_html=True,
        )

        st.markdown("<div id='main-services-grid'></div>", unsafe_allow_html=True)
        srv_col1, srv_col2 = st.columns(2)

        with srv_col1:
            st.button(
                f"🌾 {t['crop']}",
                use_container_width=True,
                key="srv_crop",
                on_click=open_service,
                args=("crop",),
            )
            st.button(
                f"📑 {t['support']}",
                use_container_width=True,
                key="srv_sup",
                on_click=open_service,
                args=("support",),
            )
            st.button(
                f"💳 {t['pay']}",
                use_container_width=True,
                key="srv_pay",
                on_click=open_service,
                args=("pay",),
            )

        with srv_col2:
            st.button(
                f"📢 {t['news']}",
                use_container_width=True,
                key="srv_news",
                on_click=open_service,
                args=("news",),
            )
            st.button(
                f"🌤️ {t['weather']}",
                use_container_width=True,
                key="srv_weather",
                on_click=open_service,
                args=("weather",),
            )
            st.button(
                f"🗺️ {t['suppliers']}",
                use_container_width=True,
                key="srv_map",
                on_click=open_service,
                args=("suppliers",),
            )

    else:
        back_col, back_spacer = st.columns([1.35, 8.65], gap="small")
        with back_col:
            st.button(
                t["back_btn"],
                use_container_width=True,
                key="back_btn",
                on_click=close_service,
            )

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
                            <span style="background: {accent_color}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8em;">{sanitize(n.get("category",""))}</span>
                            <h4 style="margin: 8px 0 5px 0; color: {accent_color};">📢 {sanitize(n.get("title",""))}</h4>
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
                fruit_target_kha = FRUIT_TARGETS_KHA[selected_c]
                st.success(
                    f"Estimated cultivated area in Algeria: ≈ {fruit_target_kha:,}k Ha "
                    f"({fruit_target_kha * 1000:,} Ha) — no national quota is enforced for fruit in this version."
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
                target_kha = VEGETABLE_TARGETS_KHA[selected_c]
                st.caption(
                    f"Currently Registered: {current_total:,.1f} Ha | "
                    f"Your Input: {area_ha:,.1f} Ha | "
                    f"Estimated National Target: ≈ {target_kha:,}k Ha ({limit:,.0f} Ha)"
                )

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
            if st.button("Confirm Payment"):
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
                <div style="font-family: Arial; width: 200px; color: black;">
                    <h4 style="margin:0; color:#047857;">{name}</h4>
                    <p style="margin:0; font-size:12px;"><b>Cat:</b> {cat}</p>
                    <a href="{maps_url}" target="_blank" style="display:inline-block; margin-top:5px; background:#047857; color:white; padding:4px 8px; border-radius:4px; font-size:11px; text-decoration:none;">🗺️ Open Google Maps</a>
                </div>
                """
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=220),
                    tooltip=name,
                    icon=folium.Icon(color=color_map.get(cat, "green")),
                ).add_to(m)

            st_folium(m, width=700, height=450)

# ---------------------------------------------------------
# TAB 2: DIGITAL CARTE FELLAH
# ---------------------------------------------------------
elif st.session_state.active_tab == "card":
    st.subheader("Digital Carte Fellah - البطاقة الفلاحية الرقمية")

    if st.session_state.logged_in:
        st.markdown(
            f"""
            <div style="border: 2px solid {accent_color}; border-radius: 15px; padding: 20px; background: {card_bg}; text-align: center;">
                <h3 style="color: {accent_color}; margin-top:0;">الجمهورية الجزائرية الديمقراطية الشعبية</h3>
                <p><b>وزارة الفلاحة والتنمية الريفية</b></p>
                <hr style="border-color: {border_color};">
                <div style="text-align: right; display: inline-block;">
                    <p><b>Farmer Name / الاسم:</b> {st.session_state.farmer_name}</p>
                    <p><b>Email / البريد:</b> {st.session_state.farmer_email}</p>
                    <p><b>Card N° / رقم البطاقة:</b> {st.session_state.carte_num}</p>
                    <p><b>Status / الحالة:</b> <span style="color: {accent_color}; font-weight: bold;">ACTIVE / 2026 Valid</span></p>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("Please log in to view your digital card.")

# ---------------------------------------------------------
# TAB 3: PERSONAL HUB & OWNER ADMIN CONSOLE
# ---------------------------------------------------------
elif st.session_state.active_tab == "account":
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
            notifs = get_user_notifications()

            if notifs:
                for n in notifs:
                    st.markdown(
                        f"""
                        <div class="notif-card">
                            <b>📩 {sanitize(n.get('title',''))}</b>
                            <p style="margin:4px 0;">{sanitize(n.get('message',''))}</p>
                            <small style="color:{subtext_color};">{n.get('created_at','')[:10]}</small>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

                if st.button("Mark All Notifications as Read"):
                    supabase_client.table("farmer_notifications").update(
                        {"is_read": True}
                    ).eq(
                        "farmer_email", st.session_state.farmer_email
                    ).execute()
                    st.success("Notifications updated.")
                    st.rerun()
            else:
                st.info("No personal notifications at this moment.")

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

    # OWNER ADMIN DASHBOARD MANAGEMENT
    st.subheader(
        "🔐 Owner / Portal Admin Management Console"
    )

    if not st.session_state.admin_authenticated:
        admin_input_pass = st.text_input(
            "Enter Admin Security Secret Code",
            type="password",
            key="admin_pwd",
        )
        if st.button("Unlock Admin Panel"):
            if admin_input_pass == get_admin_password():
                st.session_state.admin_authenticated = True
                st.success("Access Granted to Portal Admin Console.")
                st.rerun()
            else:
                st.error("Invalid Secret Key.")
    else:
        st.success("🔓 Authenticated as System Administrator")

        adm_tab1, adm_tab2, adm_tab3, adm_tab4, adm_tab5 = st.tabs([
            "📰 Post News",
            "🚨 Weather Alerts",
            "📨 Send Farmer Notifications",
            "📍 Add Map Location",
            "🗃️ Manage Database",
        ])

        with adm_tab1:
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

        with adm_tab2:
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

        with adm_tab3:
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

        with adm_tab4:
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

        with adm_tab5:
            st.markdown("#### 📊 Agricultural Intelligence & Database Management")
            st.caption(
                "Live planning dashboard based on farmer crop declarations. "
                "The first version measures declared cultivated area against the national planning targets."
            )

            # -------------------------------------------------
            # LIVE AGRICULTURAL BOARD
            # -------------------------------------------------
            try:
                res_live = (
                    supabase_client.table("declarations")
                    .select("crop, category, area, wilaya, start_date")
                    .execute()
                )
                live_records = res_live.data if res_live.data else []
                df_live = pd.DataFrame(live_records)

                if not df_live.empty:
                    df_live["area"] = pd.to_numeric(
                        df_live["area"], errors="coerce"
                    ).fillna(0.0)
                else:
                    df_live = pd.DataFrame(
                        columns=["crop", "category", "area", "wilaya", "start_date"]
                    )

                # Planning targets used by the declaration system.
                # Fruits are shown as reference planning areas; they are not
                # treated as legal quotas by the declaration form.
                # Normalize all planning targets to real numeric values.
                # Supabase/Streamlit can sometimes return numeric-looking values
                # as strings; never allow those strings into arithmetic below.
                def _safe_number(value, default=0.0):
                    try:
                        if value is None or (isinstance(value, str) and not value.strip()):
                            return float(default)
                        return float(value)
                    except (TypeError, ValueError):
                        return float(default)

                all_crop_targets = {}
                for crop, target_area in VEGETABLE_LIMITS.items():
                    all_crop_targets[str(crop)] = _safe_number(target_area)
                for crop, area_kha in FRUIT_TARGETS_KHA.items():
                    all_crop_targets[str(crop)] = _safe_number(area_kha) * 1000.0

                national_rows = []
                for crop, target_area in all_crop_targets.items():
                    declared_area = (
                        float(df_live.loc[df_live["crop"] == crop, "area"].sum())
                        if not df_live.empty
                        else 0.0
                    )
                    coverage = (declared_area / target_area * 100) if target_area else 0.0
                    if coverage > 110:
                        status = "🔴 Over target"
                    elif coverage >= 90:
                        status = "🟢 Near target"
                    else:
                        status = "🟡 Under target"

                    national_rows.append({
                        "Crop": crop,
                        "Target Area (Ha)": target_area,
                        "Declared Area (Ha)": declared_area,
                        "% of Target": coverage,
                        "Status": status,
                    })

                df_national = pd.DataFrame(national_rows)
                df_national = df_national.sort_values(
                    "% of Target", ascending=False
                ).reset_index(drop=True)

                total_declared = float(df_live["area"].sum()) if not df_live.empty else 0.0
                over_count = int((df_national["% of Target"] > 110).sum())
                near_count = int(
                    ((df_national["% of Target"] >= 90) &
                     (df_national["% of Target"] <= 110)).sum()
                )
                under_count = int((df_national["% of Target"] < 90).sum())

                metric_cols = st.columns(4)
                with metric_cols[0]:
                    st.metric("🌾 Declared Area", f"{total_declared:,.1f} Ha")
                with metric_cols[1]:
                    st.metric("🔴 Over Target", over_count)
                with metric_cols[2]:
                    st.metric("🟢 Near Target", near_count)
                with metric_cols[3]:
                    st.metric("🟡 Under Target", under_count)

                board_tab, wilaya_tab, production_tab, optimization_tab, db_tab = st.tabs([
                    "📡 Live National Board",
                    "🗺️ Wilaya × Crop Analysis",
                    "🌾 Production & Balance",
                    "🔄 Wilaya Optimization",
                    "🗃️ Database Records",
                ])

                with board_tab:
                    st.markdown("##### 🇩🇿 National Crop Balance")
                    st.caption(
                        "Coverage = declared cultivated area ÷ planning target area. "
                        "🔴 >110% = over target, 🟢 90–110% = near target, 🟡 <90% = under target."
                    )

                    display_national = df_national.copy()
                    display_national["Target Area (Ha)"] = display_national["Target Area (Ha)"].map(
                        lambda x: f"{x:,.0f}"
                    )
                    display_national["Declared Area (Ha)"] = display_national["Declared Area (Ha)"].map(
                        lambda x: f"{x:,.1f}"
                    )
                    display_national["% of Target"] = display_national["% of Target"].map(
                        lambda x: f"{x:.1f}%"
                    )
                    st.dataframe(
                        display_national,
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.markdown("##### 📈 Highest Coverage Crops")
                    top_crops = df_national.head(8).copy()
                    top_crops = top_crops.set_index("Crop")[["% of Target"]]
                    st.bar_chart(top_crops, y="% of Target")

                with wilaya_tab:
                    st.markdown("##### 🗺️ Crop Distribution by Wilaya")

                    if df_live.empty:
                        st.info("No farmer declarations are available yet.")
                    else:
                        available_crops = list(all_crop_targets.keys())
                        if not available_crops:
                            st.info("No crop targets are configured yet.")
                        else:
                            selected_analysis_crop = st.selectbox(
                                "Select Crop",
                                available_crops,
                                key="admin_live_analysis_crop",
                            )

                            crop_df = df_live[df_live["crop"] == selected_analysis_crop].copy()
                            crop_wilaya = (
                                crop_df.groupby("wilaya", dropna=False)["area"]
                                .sum()
                                .reset_index()
                                .rename(columns={"area": "Declared Area (Ha)"})
                            )
                            crop_wilaya = pd.DataFrame({"wilaya": WILAYAS_48}).merge(
                                crop_wilaya, on="wilaya", how="left"
                            )
                            crop_wilaya["Declared Area (Ha)"] = crop_wilaya["Declared Area (Ha)"].fillna(0.0)
                            crop_wilaya = crop_wilaya.sort_values("Declared Area (Ha)", ascending=False)

                            national_target = all_crop_targets[selected_analysis_crop]
                            national_declared = float(crop_wilaya["Declared Area (Ha)"].sum())
                            national_coverage = (
                                national_declared / national_target * 100
                                if national_target
                                else 0.0
                            )

                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.metric("National Target", f"{national_target:,.0f} Ha")
                            with c2:
                                st.metric("Declared", f"{national_declared:,.1f} Ha")
                            with c3:
                                st.metric("Target Coverage", f"{national_coverage:.1f}%")

                            crop_wilaya["Share of Declared Crop"] = crop_wilaya["Declared Area (Ha)"].apply(
                                lambda x: (x / national_declared * 100) if national_declared else 0
                            )
                            crop_wilaya["Share of Declared Crop"] = crop_wilaya["Share of Declared Crop"].map(
                                lambda x: f"{x:.1f}%"
                            )
                            crop_wilaya["Declared Area (Ha)"] = crop_wilaya["Declared Area (Ha)"].map(
                                lambda x: f"{x:,.1f}"
                            )

                            st.dataframe(
                                crop_wilaya,
                                use_container_width=True,
                                hide_index=True,
                            )

                            chart_df = (
                                df_live[df_live["crop"] == selected_analysis_crop]
                                .groupby("wilaya")["area"]
                                .sum()
                                .sort_values(ascending=False)
                                .head(15)
                                .to_frame()
                            )
                            st.markdown("##### Top 15 Wilayas by Declared Area")
                            st.bar_chart(chart_df, y="area")

                            st.info(
                                "💡 This analysis now works with all 48 Wilayas. It shows crop concentration, including Wilayas with zero declarations. "
                                "Production and surplus/deficit calculations are available in the Production & Balance and Wilaya Optimization tabs."
                            )

                with production_tab:
                    st.markdown("##### 🌾 Estimated Production & Supply Balance")
                    st.caption(
                        "This phase converts declared area into estimated production using crop yield benchmarks. "
                        "It is an analytical estimate, not measured farm production. Exact Wilaya surplus/deficit requires "
                        "Wilaya-specific targets and yield benchmarks in Supabase."
                    )

                    # Optional Supabase benchmark table. The app continues to work if the table
                    # has not been created yet, and explains exactly what is still needed.
                    benchmark_rows = []
                    benchmark_table_ready = True
                    try:
                        res_yields = (
                            supabase_client.table("crop_yield_benchmarks")
                            .select("crop, wilaya, yield_t_ha")
                            .execute()
                        )
                        benchmark_rows = res_yields.data if res_yields.data else []
                    except Exception:
                        benchmark_table_ready = False

                    # A national benchmark can be supplied with wilaya = "National".
                    # If no national row exists, a crop-level row with a blank/null Wilaya is used.
                    benchmark_map = {}
                    national_benchmarks = {}
                    for row in benchmark_rows:
                        crop_name = str(row.get("crop", "")).strip()
                        wilaya_name = row.get("wilaya")
                        try:
                            yld = float(row.get("yield_t_ha"))
                        except (TypeError, ValueError):
                            continue
                        if not crop_name or yld <= 0:
                            continue
                        if wilaya_name and str(wilaya_name).strip() not in {"National", "National / وطني"}:
                            benchmark_map[(crop_name, str(wilaya_name).strip())] = yld
                        else:
                            national_benchmarks[crop_name] = yld

                    # Built-in fallback benchmarks keep the analyzer usable while official MADR/technical
                    # institute figures are being collected. Supabase values always override these defaults.
                    for crop_name, fallback_yield in BUILTIN_YIELD_BENCHMARKS.items():
                        national_benchmarks.setdefault(crop_name, fallback_yield)
                        # Create a fallback for every crop × Wilaya pair.
                        # Explicit Supabase Wilaya values remain higher priority.
                        for w in WILAYAS_48:
                            benchmark_map.setdefault(
                                (crop_name, w),
                                get_builtin_wilaya_yield(crop_name, w)
                            )

                    if not benchmark_table_ready:
                        st.warning(
                            "⚙️ `crop_yield_benchmarks` is not available yet. The analyzer will use its built-in planning benchmarks for now. "
                            "When you obtain official MADR/technical-institute figures, add them to Supabase and they will override the built-ins."
                        )
                        with st.expander("SQL to add the required Supabase table"):
                            st.code(
                                """create table if not exists public.crop_yield_benchmarks (
  id bigint generated by default as identity primary key,
  crop text not null,
  wilaya text,
  yield_t_ha numeric not null check (yield_t_ha > 0),
  created_at timestamptz default now()
);

create index if not exists idx_crop_yield_benchmarks_crop_wilaya
on public.crop_yield_benchmarks (crop, wilaya);
""",
                                language="sql",
                            )
                    elif not benchmark_rows:
                        st.info(
                            "The benchmark table exists but has no yield data yet. Add one benchmark for each crop "
                            "and, when available, a specific benchmark for each Wilaya."
                        )

                    available_production_crops = list(all_crop_targets.keys()) if not df_live.empty else []

                    if available_production_crops:
                        selected_prod_crop = st.selectbox(
                            "Select Crop / اختر المحصول",
                            available_production_crops,
                            key="admin_production_crop",
                        )

                        crop_declared_df = df_live[df_live["crop"] == selected_prod_crop].copy()
                        wilaya_prod = (
                            crop_declared_df.groupby("wilaya", dropna=False)["area"]
                            .sum()
                            .reset_index()
                            .rename(columns={"area": "Declared Area (Ha)"})
                        )

                        def get_yield_for_wilaya(w):
                            w = "" if pd.isna(w) else str(w).strip()
                            return benchmark_map.get((selected_prod_crop, w), national_benchmarks.get(selected_prod_crop))

                        wilaya_prod["Yield (t/Ha)"] = wilaya_prod["wilaya"].apply(get_yield_for_wilaya)
                        wilaya_prod["Estimated Production (t)"] = (
                            wilaya_prod["Declared Area (Ha)"] * wilaya_prod["Yield (t/Ha)"].fillna(0)
                        )
                        wilaya_prod["Benchmark Source"] = wilaya_prod["wilaya"].apply(
                            lambda w: (
                                "Wilaya benchmark (Supabase)"
                                if (selected_prod_crop, "" if pd.isna(w) else str(w).strip()) in {
                                    (selected_prod_crop, str(r.get("wilaya")).strip())
                                    for r in benchmark_rows
                                    if r.get("wilaya") and str(r.get("wilaya")).strip() not in {"National", "National / وطني"}
                                }
                                else (
                                    "National benchmark (Supabase)"
                                    if selected_prod_crop in national_benchmarks and selected_prod_crop not in BUILTIN_YIELD_BENCHMARKS
                                    else (
                                        "Official historical ONS benchmark (national base)"
                                        if selected_prod_crop in BUILTIN_OFFICIAL_BENCHMARKS
                                        else "Planning estimate (Wilaya fallback)"
                                    )
                                )
                            )
                        )

                        national_yield = national_benchmarks.get(selected_prod_crop)
                        if national_yield:
                            national_declared_prod = float(wilaya_prod["Declared Area (Ha)"].sum()) * national_yield
                            national_target_prod = float(all_crop_targets[selected_prod_crop]) * national_yield
                            production_coverage = (national_declared_prod / national_target_prod * 100) if national_target_prod else 0.0

                            pc1, pc2, pc3, pc4 = st.columns(4)
                            with pc1:
                                st.metric("National Target", f"{national_target_prod:,.0f} t")
                            with pc2:
                                st.metric("Estimated Declared", f"{national_declared_prod:,.0f} t")
                            with pc3:
                                st.metric("Yield Benchmark", f"{national_yield:.2f} t/Ha")
                            with pc4:
                                st.metric("Production Coverage", f"{production_coverage:.1f}%")
                        else:
                            st.info(
                                "No benchmark is available for this crop yet."
                            )

                        # Show every one of the 48 Wilayas, including zero-declaration Wilayas.
                        # This is intentional: a missing Wilaya must appear as zero, not disappear.
                        full_wilaya_prod = pd.DataFrame({"wilaya": WILAYAS_48}).merge(
                            wilaya_prod, on="wilaya", how="left"
                        )
                        full_wilaya_prod["Declared Area (Ha)"] = full_wilaya_prod["Declared Area (Ha)"].fillna(0.0)
                        full_wilaya_prod["Yield (t/Ha)"] = full_wilaya_prod["Yield (t/Ha)"].fillna(
                            national_benchmarks.get(selected_prod_crop, float("nan"))
                        )
                        full_wilaya_prod["Estimated Production (t)"] = full_wilaya_prod["Estimated Production (t)"].fillna(0.0)
                        full_wilaya_prod["Benchmark Source"] = full_wilaya_prod["Benchmark Source"].fillna(
                            "Planning estimate (Wilaya fallback)"
                        )

                        st.markdown("##### All 48 Wilayas — one row per Wilaya")
                        display_prod = full_wilaya_prod.copy()
                        display_prod["Declared Area (Ha)"] = display_prod["Declared Area (Ha)"].map(lambda x: f"{x:,.1f}")
                        display_prod["Yield (t/Ha)"] = display_prod["Yield (t/Ha)"].map(
                            lambda x: "—" if pd.isna(x) else f"{x:.2f}"
                        )
                        display_prod["Estimated Production (t)"] = display_prod["Estimated Production (t)"].map(lambda x: f"{x:,.1f}")
                        st.dataframe(display_prod, use_container_width=True, hide_index=True)

                        # Built-in fallback benchmarks ensure that every Wilaya has a value.
                        # Official/Supabase values override the fallback automatically.

                        st.markdown("##### 🤖 Initial Analytical Signal")
                        if national_yield:
                            if production_coverage > 110:
                                st.error("National signal: estimated declared production is above the planning target.")
                            elif production_coverage < 90:
                                st.warning("National signal: estimated declared production is below the planning target.")
                            else:
                                st.success("National signal: estimated declared production is close to the planning target.")

                        st.info(
                            "ℹ️ Benchmark policy: a Wilaya-specific Supabase value has highest priority. If absent, a national Supabase value is used. "
                            "If neither exists, the app uses its built-in fallback for every crop and every Wilaya. Potato, tomato and onion use historical ONS national yield figures as the base; "
                            "the Wilaya adjustment and all other crop values are planning estimates pending official MADR/technical-institute benchmarks. "
                            "Entering an official value in Supabase automatically overrides the estimate."
                        )
                    else:
                        st.info(
                            "Add crop yield benchmarks in Supabase first. The system already keeps every crop and all 48 Wilayas separate; "
                            "no Wilaya is merged with another."
                        )

                with optimization_tab:
                    st.markdown("##### 🔄 Wilaya Logistics Optimization")
                    st.caption(
                        "This phase adds transport distance and cost to the surplus/deficit model. "
                        "The quantities are still based on estimated production, while the transport plan is solved "
                        "mathematically to minimize estimated transport cost."
                    )

                    target_table_ready = True
                    target_rows = []
                    try:
                        res_targets = (
                            supabase_client.table("wilaya_crop_targets")
                            .select("crop, wilaya, target_area_ha, target_production_t")
                            .execute()
                        )
                        target_rows = res_targets.data if res_targets.data else []
                    except Exception:
                        target_table_ready = False

                    location_table_ready = True
                    location_rows = []
                    try:
                        res_locations = (
                            supabase_client.table("wilaya_locations")
                            .select("wilaya, latitude, longitude")
                            .execute()
                        )
                        location_rows = res_locations.data if res_locations.data else []
                    except Exception:
                        location_table_ready = False

                    logistics_table_ready = True
                    logistics_rows = []
                    try:
                        res_logistics = (
                            supabase_client.table("wilaya_logistics_constraints")
                            .select("wilaya, max_outbound_t, max_inbound_t, storage_capacity_t")
                            .execute()
                        )
                        logistics_rows = res_logistics.data if res_logistics.data else []
                    except Exception:
                        logistics_table_ready = False

                    if not target_table_ready:
                        st.warning(
                            "⚙️ Supabase update required: `wilaya_crop_targets` is needed for Wilaya production targets."
                        )
                        with st.expander("SQL — Wilaya production targets"):
                            st.code(
                                """create table if not exists public.wilaya_crop_targets (
  id bigint generated by default as identity primary key,
  crop text not null,
  wilaya text not null,
  target_area_ha numeric check (target_area_ha is null or target_area_ha >= 0),
  target_production_t numeric check (target_production_t is null or target_production_t >= 0),
  created_at timestamptz default now(),
  unique (crop, wilaya)
);

create index if not exists idx_wilaya_crop_targets_crop_wilaya
on public.wilaya_crop_targets (crop, wilaya);
""",
                                language="sql",
                            )

                    if not location_table_ready:
                        st.warning(
                            "⚙️ Supabase update required for logistics: create `wilaya_locations` and add the coordinates "
                            "of the 48 Wilaya capitals. Coordinates are used only to estimate distance; they are not road distances."
                        )
                        with st.expander("SQL — Wilaya coordinates"):
                            st.code(
                                """create table if not exists public.wilaya_locations (
  id bigint generated by default as identity primary key,
  wilaya text not null unique,
  latitude numeric not null check (latitude between -90 and 90),
  longitude numeric not null check (longitude between -180 and 180),
  created_at timestamptz default now()
);

create index if not exists idx_wilaya_locations_wilaya
on public.wilaya_locations (wilaya);

-- Add one row for every Wilaya using the exact names already used by the app,
-- for example:
-- insert into public.wilaya_locations (wilaya, latitude, longitude)
-- values ('16 - Alger', 36.7538, 3.0588);
""",
                                language="sql",
                            )

                    if not logistics_table_ready:
                        st.warning(
                            "⚙️ Optional Supabase update for the next logistics layer: `wilaya_logistics_constraints` "
                            "stores maximum outbound/inbound quantities and storage capacity for each Wilaya. "
                            "Without it, the optimizer assumes no logistics capacity limit."
                        )
                        with st.expander("SQL — Wilaya logistics constraints"):
                            st.code(
                                """create table if not exists public.wilaya_logistics_constraints (
  id bigint generated by default as identity primary key,
  wilaya text not null unique,
  max_outbound_t numeric check (max_outbound_t is null or max_outbound_t >= 0),
  max_inbound_t numeric check (max_inbound_t is null or max_inbound_t >= 0),
  storage_capacity_t numeric check (storage_capacity_t is null or storage_capacity_t >= 0),
  created_at timestamptz default now()
);

create index if not exists idx_wilaya_logistics_constraints_wilaya
on public.wilaya_logistics_constraints (wilaya);
""",
                                language="sql",
                            )

                    if target_rows and location_rows and not df_live.empty:
                        target_df = pd.DataFrame(target_rows)
                        target_df["target_production_t"] = pd.to_numeric(
                            target_df["target_production_t"], errors="coerce"
                        )
                        target_df = target_df[
                            target_df["crop"].notna() & target_df["wilaya"].notna()
                        ].copy()

                        location_df = pd.DataFrame(location_rows)
                        location_df["latitude"] = pd.to_numeric(location_df["latitude"], errors="coerce")
                        location_df["longitude"] = pd.to_numeric(location_df["longitude"], errors="coerce")
                        location_df = location_df.dropna(subset=["latitude", "longitude"]).copy()
                        location_df["wilaya"] = location_df["wilaya"].astype(str).str.strip()
                        location_df = location_df.drop_duplicates("wilaya", keep="last")
                        coords = location_df.set_index("wilaya")[["latitude", "longitude"]].to_dict("index")

                        missing_coords = [w for w in WILAYAS_48 if w not in coords]
                        if missing_coords:
                            st.warning(
                                f"Coordinates are missing for {len(missing_coords)} Wilaya(s). "
                                "The optimizer will only create routes between Wilayas with known coordinates."
                            )

                        # Optional node-level logistics constraints. A missing value means
                        # no explicit capacity limit for that Wilaya.
                        logistics_map = {}
                        for row in logistics_rows:
                            w = str(row.get("wilaya", "")).strip()
                            if not w:
                                continue
                            parsed = {}
                            for key in ["max_outbound_t", "max_inbound_t", "storage_capacity_t"]:
                                try:
                                    value = row.get(key)
                                    parsed[key] = float(value) if value is not None else None
                                except (TypeError, ValueError):
                                    parsed[key] = None
                            logistics_map[w] = parsed

                        optimization_crops = sorted(set(target_df["crop"]) & set(df_live["crop"].dropna()))

                        if optimization_crops:
                            selected_opt_crop = st.selectbox(
                                "Select Crop / اختر المحصول",
                                optimization_crops,
                                key="admin_optimization_crop",
                            )

                            cost_per_t_km = st.number_input(
                                "Estimated transport cost (DZD / tonne / km)",
                                min_value=0.1,
                                max_value=1000.0,
                                value=8.0,
                                step=0.5,
                                key="admin_transport_cost",
                            )
                            road_factor = st.number_input(
                                "Road-distance factor × straight-line distance",
                                min_value=1.0,
                                max_value=2.0,
                                value=1.25,
                                step=0.05,
                                key="admin_road_factor",
                                help="1.25 means estimated road distance = straight-line distance × 1.25. Replace with real route distances when available.",
                            )
                            truck_capacity_t = st.number_input(
                                "Truck capacity (tonnes)",
                                min_value=1.0,
                                max_value=100.0,
                                value=20.0,
                                step=1.0,
                                key="admin_truck_capacity_t",
                                help="Used to estimate the number of truckloads for the recommended transfers.",
                            )

                            opt_declared = (
                                df_live[df_live["crop"] == selected_opt_crop]
                                .groupby("wilaya")["area"]
                                .sum()
                                .reindex(WILAYAS_48, fill_value=0.0)
                            )

                            opt_benchmark_map = {}
                            opt_national_yield = None
                            for row in benchmark_rows:
                                if str(row.get("crop", "")).strip() != selected_opt_crop:
                                    continue
                                try:
                                    yld = float(row.get("yield_t_ha"))
                                except (TypeError, ValueError):
                                    continue
                                if yld <= 0:
                                    continue
                                w = row.get("wilaya")
                                if w and str(w).strip() not in {"National", "National / وطني"}:
                                    opt_benchmark_map[str(w).strip()] = yld
                                else:
                                    opt_national_yield = yld

                            # Fall back to the same built-in benchmark policy used by Production & Balance.
                            if opt_national_yield is None:
                                opt_national_yield = BUILTIN_YIELD_BENCHMARKS.get(selected_opt_crop)

                            crop_targets = target_df[target_df["crop"] == selected_opt_crop].copy().set_index("wilaya")
                            opt_rows = []
                            for w in WILAYAS_48:
                                target_prod = crop_targets.at[w, "target_production_t"] if w in crop_targets.index else float("nan")
                                yld = opt_benchmark_map.get(w)
                                if yld is None:
                                    yld = get_builtin_wilaya_yield(selected_opt_crop, w) or opt_national_yield
                                area = float(opt_declared.get(w, 0.0))
                                estimated_prod = area * yld if yld and pd.notna(yld) else float("nan")
                                if pd.isna(target_prod) or pd.isna(estimated_prod):
                                    balance = float("nan")
                                    status = "⚪ Missing data"
                                else:
                                    balance = float(estimated_prod) - float(target_prod)
                                    status = "🟢 Surplus" if balance > 0 else ("🔴 Deficit" if balance < 0 else "🟡 Balanced")
                                opt_rows.append({
                                    "Wilaya": w,
                                    "Target Production (t)": target_prod,
                                    "Estimated Production (t)": estimated_prod,
                                    "Balance (t)": balance,
                                    "Status": status,
                                })

                            opt_df = pd.DataFrame(opt_rows)
                            valid_opt = opt_df.dropna(
                                subset=["Target Production (t)", "Estimated Production (t)", "Balance (t)"]
                            ).copy()

                            if valid_opt.empty:
                                st.warning("No complete Wilaya target + production data is available for this crop yet.")
                            else:
                                surplus_df = valid_opt[valid_opt["Balance (t)"] > 0].copy()
                                deficit_df = valid_opt[valid_opt["Balance (t)"] < 0].copy()
                                total_surplus = float(surplus_df["Balance (t)"].sum()) if not surplus_df.empty else 0.0
                                total_deficit = float(-deficit_df["Balance (t)"].sum()) if not deficit_df.empty else 0.0

                                oc1, oc2, oc3 = st.columns(3)
                                with oc1:
                                    st.metric("🟢 Total Surplus", f"{total_surplus:,.1f} t")
                                with oc2:
                                    st.metric("🔴 Total Deficit", f"{total_deficit:,.1f} t")
                                with oc3:
                                    st.metric("⚖️ National Gap", f"{total_surplus - total_deficit:,.1f} t")

                                display_opt = opt_df.copy()
                                for col in ["Target Production (t)", "Estimated Production (t)", "Balance (t)"]:
                                    display_opt[col] = display_opt[col].map(lambda x: "—" if pd.isna(x) else f"{x:,.1f}")
                                st.dataframe(display_opt, use_container_width=True, hide_index=True)

                                if not surplus_df.empty and not deficit_df.empty:
                                    distance_map = {}
                                    for srow in surplus_df.itertuples(index=False):
                                        for drow in deficit_df.itertuples(index=False):
                                            sc = coords.get(srow[0])
                                            dc = coords.get(drow[0])
                                            if sc and dc:
                                                distance_map[(srow[0], drow[0])] = haversine_km(
                                                    sc["latitude"], sc["longitude"],
                                                    dc["latitude"], dc["longitude"],
                                                )

                                    surplus_rows = []
                                    for _, r in surplus_df.iterrows():
                                        w = r["Wilaya"]
                                        amount = float(r["Balance (t)"])
                                        limits = logistics_map.get(w, {})
                                        outbound_cap = limits.get("max_outbound_t")
                                        if outbound_cap is not None:
                                            amount = min(amount, max(0.0, outbound_cap))
                                        if amount > 0:
                                            surplus_rows.append({"wilaya": w, "amount": amount})

                                    deficit_rows = []
                                    for _, r in deficit_df.iterrows():
                                        w = r["Wilaya"]
                                        amount = float(-r["Balance (t)"])
                                        limits = logistics_map.get(w, {})
                                        inbound_cap = limits.get("max_inbound_t")
                                        storage_cap = limits.get("storage_capacity_t")
                                        caps = [x for x in [inbound_cap, storage_cap] if x is not None]
                                        if caps:
                                            amount = min(amount, max(0.0, min(caps)))
                                        if amount > 0:
                                            deficit_rows.append({"wilaya": w, "amount": amount})

                                    constrained_surplus = sum(r["amount"] for r in surplus_rows)
                                    constrained_deficit = sum(r["amount"] for r in deficit_rows)
                                    if logistics_rows:
                                        st.caption(
                                            f"Capacity constraints active: {len(logistics_map)} Wilaya record(s). "
                                            f"Available constrained supply = {constrained_surplus:,.1f} t; "
                                            f"receiving capacity = {constrained_deficit:,.1f} t."
                                        )

                                    transfers, total_transport_cost = min_cost_transfer_plan(
                                        surplus_rows,
                                        deficit_rows,
                                        distance_map,
                                        cost_per_t_km,
                                        road_factor=road_factor,
                                    )

                                    if transfers:
                                        st.markdown("##### 🚚 Minimum-Cost Suggested Transfers")
                                        rec_df = pd.DataFrame(transfers)
                                        for col in [
                                            "Transfer (t)",
                                            "Straight-line Distance (km)",
                                            "Estimated Road Distance (km)",
                                            "Transport Cost (DZD)",
                                        ]:
                                            rec_df[col] = rec_df[col].map(lambda x: f"{x:,.1f}")
                                        rec_df["Estimated Truckloads"] = rec_df["Transfer (t)"].astype(float).apply(
                                            lambda x: math.ceil(x / float(truck_capacity_t))
                                        )
                                        rec_df["Transfer (t)"] = rec_df["Transfer (t)"].map(lambda x: f"{float(x):,.1f}")
                                        st.dataframe(rec_df, use_container_width=True, hide_index=True)
                                        st.metric(
                                            "Estimated Total Transport Cost",
                                            f"{total_transport_cost:,.0f} DZD",
                                        )
                                        st.metric(
                                            "Estimated Truckloads",
                                            f"{int(rec_df['Estimated Truckloads'].sum()):,}",
                                        )
                                        st.success(
                                            "The transfer quantities above minimize the estimated transport cost under the current "
                                            "surplus/deficit, distance and cost assumptions."
                                        )
                                    else:
                                        st.warning(
                                            "No transport plan could be generated. Check that every surplus/deficit Wilaya "
                                            "has coordinates in `wilaya_locations`."
                                        )

                                    st.info(
                                        "⚠️ This is a planning optimizer, not an operational dispatch system. It now supports "
                                        "optional Wilaya outbound/inbound/storage constraints and estimates truckloads. It still does not "
                                        "include road closures, crop-specific perishability windows, harvest dates, contracts, market demand, "
                                        "or live transport prices. Coordinate-based distance is an estimate; real road distances should replace it "
                                        "before operational use."
                                    )
                                elif deficit_df.empty:
                                    st.success("No Wilaya has a production deficit for this crop in the available data.")
                                elif surplus_df.empty:
                                    st.warning("There are deficits, but no surplus Wilaya is available to cover them.")
                        else:
                            st.info("No crop has both declarations and Wilaya production targets yet. Add target rows in Supabase.")
                    elif target_table_ready and location_table_ready and target_rows and location_rows and df_live.empty:
                        st.info("No farmer declarations are available yet, so there is nothing to optimize.")
                    elif target_table_ready and location_table_ready and not target_rows:
                        st.info("Add Wilaya production targets first; the optimizer cannot infer them automatically.")
                    elif target_table_ready and location_table_ready and not location_rows:
                        st.info("Add Wilaya coordinates first; the optimizer needs a location for each participating Wilaya.")

                with db_tab:
                    st.markdown("##### System Database Inspector & Management")
                    st.caption(
                        "View records and manage individual rows by ID. Deletion is permanent. "
                        "For crop declarations you can also set the cultivated area to 0 without deleting the record."
                    )

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
                        key="admin_table_choice",
                    )

                    try:
                        res_all = (
                            supabase_client.table(table_choice)
                            .select("*")
                            .execute()
                        )
                        records = res_all.data if res_all.data else []

                        if records:
                            df_admin = pd.DataFrame(records)
                            st.dataframe(
                                df_admin,
                                use_container_width=True,
                                hide_index=True,
                            )

                            id_values = [
                                r.get("id") for r in records if r.get("id") is not None
                            ]

                            if not id_values:
                                st.warning(
                                    "No `id` column/value was found in this table. "
                                    "Individual management requires a primary key named `id`."
                                )
                            else:
                                st.divider()
                                st.markdown("##### Manage One Record by ID")
                                record_id = st.selectbox(
                                    "Select Record ID",
                                    id_values,
                                    key=f"admin_record_id_{table_choice}",
                                )

                                selected_record = next(
                                    (r for r in records if r.get("id") == record_id),
                                    None,
                                )

                                if selected_record is not None:
                                    preview_cols = [
                                        k for k in [
                                            "id", "title", "crop", "category", "area",
                                            "farmer_email", "carte_num", "wilaya", "status"
                                        ]
                                        if k in selected_record
                                    ]
                                    if preview_cols:
                                        st.json({
                                            k: selected_record.get(k)
                                            for k in preview_cols
                                        })

                                if table_choice == "declarations":
                                    st.markdown("**Crop Declaration Actions**")
                                    col_zero, col_delete = st.columns(2)

                                    with col_zero:
                                        if st.button(
                                            "0️⃣ Set Area to 0",
                                            key=f"zero_declaration_{record_id}",
                                            use_container_width=True,
                                        ):
                                            try:
                                                supabase_client.table("declarations").update(
                                                    {"area": 0}
                                                ).eq("id", record_id).execute()
                                                st.success(
                                                    f"Declaration ID {record_id} area set to 0."
                                                )
                                                st.rerun()
                                            except Exception as e:
                                                st.error(
                                                    f"Failed to set declaration area to 0: {e}"
                                                )

                                    with col_delete:
                                        delete_declaration = st.checkbox(
                                            "Confirm permanent deletion",
                                            key=f"confirm_delete_dec_{record_id}",
                                        )
                                        if st.button(
                                            "🗑️ Delete Declaration",
                                            key=f"delete_declaration_{record_id}",
                                            use_container_width=True,
                                            disabled=not delete_declaration,
                                        ):
                                            try:
                                                supabase_client.table("declarations").delete().eq(
                                                    "id", record_id
                                                ).execute()
                                                st.success(
                                                    f"Declaration ID {record_id} deleted."
                                                )
                                                st.rerun()
                                            except Exception as e:
                                                st.error(
                                                    f"Failed to delete declaration: {e}"
                                                )
                                else:
                                    confirm_delete = st.checkbox(
                                        "Confirm permanent deletion of this record",
                                        key=f"confirm_delete_{table_choice}_{record_id}",
                                    )
                                    if st.button(
                                        f"🗑️ Delete {table_choice} Record",
                                        key=f"delete_record_{table_choice}_{record_id}",
                                        use_container_width=True,
                                        disabled=not confirm_delete,
                                    ):
                                        try:
                                            supabase_client.table(table_choice).delete().eq(
                                                "id", record_id
                                            ).execute()
                                            st.success(
                                                f"Record ID {record_id} deleted from `{table_choice}`."
                                            )
                                            st.rerun()
                                        except Exception as e:
                                            st.error(
                                                f"Failed to delete record from `{table_choice}`: {e}"
                                            )
                        else:
                            st.info(f"Table `{table_choice}` is currently empty.")
                    except Exception as e:
                        st.error(f"Failed to query table: {e}")

            except Exception as e:
                st.error(f"Unable to load the agricultural live board: {e}")

        if st.button("🔒 Lock Admin Console"):
            st.session_state.admin_authenticated = False
            st.rerun()
