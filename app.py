import math
import random
import re
from datetime import date, timedelta
from io import BytesIO

import folium
import pandas as pd
import requests
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

def get_builtin_base_yield(crop_name):
    """Return a built-in yield while accepting the app's two crop-name formats.

    The declaration lists historically used both ``Crop (Arabic)`` and
    ``Crop / Arabic``. Benchmark lookup must treat them as the same crop so
    the analytical board never loses a yield just because of punctuation.
    """
    name = str(crop_name or "").strip()
    base = BUILTIN_YIELD_BENCHMARKS.get(name)
    if base is not None:
        return float(base)

    # Convert: Potatoes (بطاطا) <-> Potatoes / بطاطا
    if "(" in name and name.endswith(")"):
        left, arabic = name.rsplit("(", 1)
        alias = f"{left.strip()} / {arabic[:-1].strip()}"
        base = BUILTIN_YIELD_BENCHMARKS.get(alias)
    elif " / " in name:
        left, arabic = name.split(" / ", 1)
        alias = f"{left.strip()} ({arabic.strip()})"
        base = BUILTIN_YIELD_BENCHMARKS.get(alias)

    return float(base) if base is not None else None


def is_builtin_official_crop(crop_name):
    """True when the crop corresponds to one of the historical ONS base benchmarks."""
    name = str(crop_name or "").strip()
    if name in BUILTIN_OFFICIAL_BENCHMARKS:
        return True
    if "(" in name and name.endswith(")"):
        left, arabic = name.rsplit("(", 1)
        alias = f"{left.strip()} / {arabic[:-1].strip()}"
        return alias in BUILTIN_OFFICIAL_BENCHMARKS
    if " / " in name:
        left, arabic = name.split(" / ", 1)
        alias = f"{left.strip()} ({arabic.strip()})"
        return alias in BUILTIN_OFFICIAL_BENCHMARKS
    return False


def get_builtin_wilaya_yield(crop_name, wilaya_name):
    """Return a transparent fallback t/ha estimate for any crop + Wilaya."""
    base = get_builtin_base_yield(crop_name)
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


def _ai_percent(value, decimals=1):
    try:
        return f"{float(value):,.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def _ai_float(value, default=0.0):
    try:
        if value is None or (isinstance(value, str) and not value.strip()):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)



# ------------------------------------------------------------------
# AI AGRICULTURAL INVESTIGATION ENGINE v2
# ------------------------------------------------------------------
# The investigation layer is deliberately deterministic. It collects the
# strongest evidence available, scores competing causes, estimates impact,
# and only then lets the language/agent layer explain the finding.
# Missing external datasets are never silently treated as observed facts.

AI_CROP_RISK_PROFILES = {
    "Almonds / لوز": {
        "aliases": {"Almonds (لوز)", "Almonds / لوز"},
        "phenology": "flowering commonly late-winter/early-spring; timing varies by variety and site",
        "frost_sensitive_months": {1, 2, 3},
        "frost_threshold_c": -1.0,
        "severe_frost_threshold_c": -3.0,
        "group": "tree_mediterranean",
    },
    "Apricots / مشمش": {
        "aliases": {"Apricots (مشمش)", "Apricots / مشمش"},
        "phenology": "early flowering; highly exposed to late-frost risk",
        "frost_sensitive_months": {1, 2, 3},
        "frost_threshold_c": -1.0,
        "severe_frost_threshold_c": -3.0,
        "group": "tree_mediterranean",
    },
    "Peaches & Nectarines / خوخ ونكتارين": {
        "aliases": {"Peaches & Nectarines (خوخ ونكتارين)", "Peaches & Nectarines / خوخ ونكتارين"},
        "phenology": "early spring flowering; late-frost sensitive",
        "frost_sensitive_months": {2, 3},
        "frost_threshold_c": -1.5,
        "severe_frost_threshold_c": -3.5,
        "group": "tree_mediterranean",
    },
    "Cherries / كرز": {
        "aliases": {"Cherries (كرز)", "Cherries / كرز"},
        "phenology": "spring flowering; frost sensitivity depends strongly on stage",
        "frost_sensitive_months": {2, 3, 4},
        "frost_threshold_c": -1.0,
        "severe_frost_threshold_c": -3.0,
        "group": "tree_mediterranean",
    },
    "Apples / تفاح": {
        "aliases": {"Apples (تفاح)", "Apples / تفاح"},
        "phenology": "spring flowering; frost sensitivity depends on cultivar/stage",
        "frost_sensitive_months": {2, 3, 4},
        "frost_threshold_c": -1.5,
        "severe_frost_threshold_c": -3.5,
        "group": "cool_north",
    },
}

AI_RISK_CAUSE_LABELS = {
    "frost": "Late frost / الصقيع المتأخر",
    "drought": "Water stress / الجفاف والإجهاد المائي",
    "disease": "Disease / المرض",
    "irrigation": "Irrigation limitation / نقص الري",
    "soil": "Soil limitation / مشكلة التربة",
    "area": "Area / declaration effect",
    "heat": "Heat stress / الإجهاد الحراري",
    "insufficient_evidence": "Insufficient evidence / بيانات غير كافية",
}


def ai_crop_key(crop_name):
    name = str(crop_name or "").strip()
    for canonical, profile in AI_CROP_RISK_PROFILES.items():
        if name in profile.get("aliases", set()) or name == canonical:
            return canonical
    return name


def ai_crop_profile(crop_name):
    canonical = ai_crop_key(crop_name)
    if canonical in AI_CROP_RISK_PROFILES:
        return AI_CROP_RISK_PROFILES[canonical]
    # Generic fallback: tree crops get a conservative frost window; annual
    # crops remain neutral until crop-stage/weather data are available.
    if any(x in str(crop_name).lower() for x in ["almond", "apricot", "peach", "cherry", "apple", "plum", "pear"]):
        return {
            "phenology": "tree crop; stage-specific risk requires phenology data",
            "frost_sensitive_months": {2, 3},
            "frost_threshold_c": -1.0,
            "severe_frost_threshold_c": -3.0,
            "group": "tree_mediterranean",
        }
    return {
        "phenology": "crop stage not yet available",
        "frost_sensitive_months": set(),
        "frost_threshold_c": -1.0,
        "severe_frost_threshold_c": -3.0,
        "group": "",
    }


def ai_safe_num(value):
    try:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None



@st.cache_data(ttl=1800, show_spinner=False)
def ai_fetch_external_weather(wilaya, latitude, longitude, days_back=365):
    """Fetch historical daily weather as an external planning source.

    This uses Open-Meteo's public archive endpoint as a fallback data source.
    It is not an Algerian official observation network; source provenance is
    shown explicitly so ONM/MADR data can replace it later.
    """
    try:
        end_day = date.today()
        start_day = end_day - timedelta(days=int(days_back))
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
            "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum",
            "timezone": "auto",
        }
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        mins = daily.get("temperature_2m_min", [])
        maxs = daily.get("temperature_2m_max", [])
        rains = daily.get("precipitation_sum", [])
        rows = []
        for dt, tmin, tmax, rain in zip(dates, mins, maxs, rains):
            rows.append({
                "observed_at": dt,
                "wilaya": wilaya,
                "tmin_c": tmin,
                "tmax_c": tmax,
                "rainfall_mm": rain,
                "source": "Open-Meteo archive (external planning source)",
            })
        return rows
    except Exception:
        return []



@st.cache_data(ttl=21600, show_spinner=False)
def ai_fetch_copernicus_satellite(wilaya, latitude, longitude, days_back=90):
    """Fetch automatic Sentinel-2/Sentinel-1 statistics when CDSE credentials exist.

    Satellite observations are never typed manually. Credentials are a one-time
    deployment setting in Streamlit Secrets. If absent, return an explicit
    unavailable state rather than inventing observations.
    """
    try:
        cdse = st.secrets.get("copernicus", {})
        client_id = str(cdse.get("CLIENT_ID", "")).strip()
        client_secret = str(cdse.get("CLIENT_SECRET", "")).strip()
        if not client_id or not client_secret:
            return [], "Copernicus credentials not configured"
        token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        token_resp = requests.post(token_url, data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }, timeout=15)
        token_resp.raise_for_status()
        token = token_resp.json().get("access_token")
        if not token:
            return [], "Copernicus token unavailable"
        end_day = date.today()
        start_day = end_day - timedelta(days=int(days_back))
        lat, lon = float(latitude), float(longitude)
        delta = 0.05
        bbox = [lon - delta, lat - delta, lon + delta, lat + delta]
        headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {token}"}
        stats_url = "https://sh.dataspace.copernicus.eu/statistics/v1"
        s2_evalscript = """
//VERSION=3
function setup() {
  return { input: [{ bands: ["B03", "B04", "B08", "SCL", "dataMask"] }], output: [{ id: "indices", bands: 2, sampleType: "FLOAT32" }, { id: "dataMask", bands: 1 }] };
}
function evaluatePixel(samples) {
  var valid = samples.dataMask;
  var cloud = (samples.SCL == 3 || samples.SCL == 8 || samples.SCL == 9 || samples.SCL == 10 || samples.SCL == 11);
  if (cloud) valid = 0;
  var ndvi = (samples.B08 + samples.B04 == 0) ? 0 : (samples.B08 - samples.B04) / (samples.B08 + samples.B04);
  var ndwi = (samples.B03 + samples.B08 == 0) ? 0 : (samples.B03 - samples.B08) / (samples.B03 + samples.B08);
  return { indices: [ndvi, ndwi], dataMask: [valid] };
}
"""
        s2_payload = {
            "input": {"bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}}, "data": [{"type": "sentinel-2-l2a", "dataFilter": {"maxCloudCoverage": 30, "mosaickingOrder": "leastCC"}}]},
            "aggregation": {"timeRange": {"from": f"{start_day.isoformat()}T00:00:00Z", "to": f"{end_day.isoformat()}T23:59:59Z"}, "aggregationInterval": {"of": "P10D"}, "evalscript": s2_evalscript, "resx": 20, "resy": 20},
        }
        s2_resp = requests.post(stats_url, headers=headers, json=s2_payload, timeout=40)
        s2_resp.raise_for_status()
        rows = []
        for item in s2_resp.json().get("data", []):
            interval = item.get("interval", {})
            bands = item.get("outputs", {}).get("indices", {}).get("bands", {})
            ndvi = ai_safe_num(bands.get("B0", {}).get("stats", {}).get("mean"))
            ndwi = ai_safe_num(bands.get("B1", {}).get("stats", {}).get("mean"))
            if ndvi is None and ndwi is None:
                continue
            rows.append({
                "observed_at": interval.get("from", "")[:10], "wilaya": wilaya, "crop": None,
                "ndvi": ndvi, "ndwi": ndwi, "evi": None, "fapar": None, "anomaly_percent": None,
                "source": "Copernicus Sentinel-2 L2A statistical API",
            })
        # Sentinel-1 radar adds a cloud-independent surface/moisture signal.
        s1_evalscript = """
//VERSION=3
function setup() {
  return { input: [{ bands: ["VV", "VH", "dataMask"] }], output: [{ id: "radar", bands: 2, sampleType: "FLOAT32" }, { id: "dataMask", bands: 1 }] };
}
function evaluatePixel(samples) {
  return { radar: [samples.VV, samples.VH], dataMask: [samples.dataMask] };
}
"""
        s1_payload = {
            "input": {
                "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}},
                "data": [{"type": "sentinel-1-grd", "dataFilter": {"polarization": "DV", "acquisitionMode": "IW"}}],
            },
            "aggregation": {
                "timeRange": {"from": f"{start_day.isoformat()}T00:00:00Z", "to": f"{end_day.isoformat()}T23:59:59Z"},
                "aggregationInterval": {"of": "P10D"},
                "evalscript": s1_evalscript,
                "resx": 20,
                "resy": 20,
            },
        }
        try:
            s1_resp = requests.post(stats_url, headers=headers, json=s1_payload, timeout=40)
            s1_resp.raise_for_status()
            for item in s1_resp.json().get("data", []):
                interval = item.get("interval", {})
                bands = item.get("outputs", {}).get("radar", {}).get("bands", {})
                vv = ai_safe_num(bands.get("B0", {}).get("stats", {}).get("mean"))
                vh = ai_safe_num(bands.get("B1", {}).get("stats", {}).get("mean"))
                if vv is None and vh is None:
                    continue
                rows.append({
                    "observed_at": interval.get("from", "")[:10], "wilaya": wilaya, "crop": None,
                    "ndvi": None, "ndwi": None, "evi": None, "fapar": None, "anomaly_percent": None,
                    "sentinel1_vv": vv, "sentinel1_vh": vh,
                    "source": "Copernicus Sentinel-1 GRD statistical API",
                })
        except Exception:
            pass

        return rows, "Copernicus Sentinel-1 + Sentinel-2 automatic remote sensing"
    except Exception as exc:
        return [], f"Copernicus unavailable: {exc}"

def ai_load_optional_table(table_name, columns):
    """Load an optional Supabase table without breaking the app if absent."""
    if not supabase_client:
        return [], False, "Supabase connection unavailable"
    try:
        res = supabase_client.table(table_name).select(columns).execute()
        return (res.data if res.data else []), True, ""
    except Exception as exc:
        return [], False, str(exc)


def ai_declaration_area(df_live, crop, wilaya):
    if df_live is None or df_live.empty:
        return 0.0
    work = df_live.copy()
    if "crop" not in work or "wilaya" not in work or "area" not in work:
        return 0.0
    work["area"] = pd.to_numeric(work["area"], errors="coerce").fillna(0.0)
    crop_aliases = set(AI_CROP_RISK_PROFILES.get(ai_crop_key(crop), {}).get("aliases", set()))
    crop_aliases.add(str(crop).strip())
    mask = work["crop"].astype(str).str.strip().isin(crop_aliases)
    mask &= work["wilaya"].astype(str).str.strip().eq(str(wilaya).strip())
    return float(work.loc[mask, "area"].sum())


def ai_historical_production_signal(rows, crop, wilaya):
    """Return historical baseline and trend if the optional history table exists."""
    if not rows:
        return {"available": False, "baseline_t": None, "trend_percent": None, "years": 0}
    aliases = set(AI_CROP_RISK_PROFILES.get(ai_crop_key(crop), {}).get("aliases", set()))
    aliases.add(str(crop).strip())
    vals = []
    for r in rows:
        rc = str(r.get("crop", "")).strip()
        rw = str(r.get("wilaya", "")).strip()
        prod = ai_safe_num(r.get("production_t"))
        if rc in aliases and rw == str(wilaya).strip() and prod is not None:
            vals.append((str(r.get("year", "")), prod))
    if not vals:
        return {"available": False, "baseline_t": None, "trend_percent": None, "years": 0}
    vals.sort(key=lambda x: x[0])
    recent = vals[-5:]
    baseline = sum(v for _, v in recent) / len(recent)
    trend = None
    if len(vals) >= 2 and vals[0][1] > 0:
        trend = (vals[-1][1] - vals[0][1]) / vals[0][1] * 100
    return {"available": True, "baseline_t": baseline, "trend_percent": trend, "years": len(vals)}



@st.cache_data(ttl=86400, show_spinner=False)
def ai_geocode_wilaya(wilaya):
    """Find approximate Wilaya coordinates when the optional table is empty."""
    try:
        name = re.sub(r"^\d+\s*-\s*", "", str(wilaya).strip())
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": f"{name}, Algeria", "count": 1, "language": "en", "format": "json"}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            return float(results[0]["latitude"]), float(results[0]["longitude"]), "Open-Meteo geocoding estimate"
    except Exception:
        pass
    return None, None, None


def ai_resolve_wilaya_coordinates(wilaya, location_rows):
    for row in location_rows or []:
        if str(row.get("wilaya", "")).strip() == str(wilaya).strip():
            lat = ai_safe_num(row.get("latitude")); lon = ai_safe_num(row.get("longitude"))
            if lat is not None and lon is not None:
                return lat, lon, "Supabase wilaya_locations"
    for loc in DEFAULT_AGRI_LOCATIONS:
        if str(loc.get("wilaya", "")).strip() == str(wilaya).strip():
            lat = ai_safe_num(loc.get("lat")); lon = ai_safe_num(loc.get("lon"))
            if lat is not None and lon is not None:
                return lat, lon, "Built-in map coordinate"
    return ai_geocode_wilaya(wilaya)

def ai_parse_weather_evidence(weather_rows, crop, wilaya):
    """Extract observed weather/frost evidence from a normalized optional table."""
    profile = ai_crop_profile(crop)
    mins = []
    rainfall = []
    heat_days = []
    relevant = []
    for r in weather_rows or []:
        rw = str(r.get("wilaya", "")).strip()
        if rw not in {str(wilaya).strip(), "All Wilayas", "ALL", ""}:
            continue
        tmin = ai_safe_num(r.get("tmin_c"))
        rain = ai_safe_num(r.get("rainfall_mm"))
        tmax = ai_safe_num(r.get("tmax_c"))
        dt = pd.to_datetime(r.get("observed_at"), errors="coerce")
        month = int(dt.month) if not pd.isna(dt) else None
        if tmin is not None:
            mins.append(tmin)
        if rain is not None:
            rainfall.append(rain)
        if tmax is not None and tmax >= 38:
            heat_days.append(tmax)
        if tmin is not None and month in profile.get("frost_sensitive_months", set()) and tmin <= profile.get("frost_threshold_c", -1):
            relevant.append({"date": str(r.get("observed_at", "")), "tmin_c": tmin, "type": "frost"})
    frost_event = min(mins) if mins else None
    return {
        "available": bool(weather_rows),
        "frost_min_c": frost_event,
        "frost_events": relevant,
        "rainfall_total_mm": sum(rainfall) if rainfall else None,
        "heat_days": len(heat_days),
    }


def ai_parse_weather_alerts(alert_rows, crop, wilaya):
    """Use existing admin weather alerts as secondary evidence, not as measured weather."""
    matches = []
    keywords = {
        "frost": ["frost", "freeze", "cold", "الصقيع", "برد"],
        "rain": ["rain", "rainfall", "مطر", "أمطار"],
        "heat": ["heat", "heatwave", "sirocco", "حرارة", "موجة حر", "شهيلي"],
        "drought": ["drought", "جفاف", "water stress", "نقص المياه"],
    }
    for r in alert_rows or []:
        region = str(r.get("region", "")).strip()
        if region not in {str(wilaya).strip(), "All Wilayas", "ALL", ""}:
            continue
        text = " ".join(str(r.get(k, "")) for k in ["title", "message"]).lower()
        found = [kind for kind, words in keywords.items() if any(w.lower() in text for w in words)]
        if found:
            matches.append({"kind": found[0], "title": str(r.get("title", "")), "date": str(r.get("created_at", ""))})
    return matches




# ---------------------------------------------------------
# AUTOMATIC AGRICULTURAL EVIDENCE HELPERS
# ---------------------------------------------------------
COMMON_DISEASES_BY_GROUP = {
    "tree": [
        "Brown rot / Monilinia",
        "Shot hole / Coryneum",
        "Leaf curl / Taphrina",
        "Powdery mildew",
        "Rust",
        "Bacterial canker",
        "Root/crown rot",
        "Verticillium wilt",
        "Other / Unknown disease",
    ],
    "vegetable": [
        "Late blight / Phytophthora",
        "Early blight / Alternaria",
        "Powdery mildew",
        "Downy mildew",
        "Fusarium wilt",
        "Verticillium wilt",
        "Bacterial wilt/spot",
        "Root/collar rot",
        "Other / Unknown disease",
    ],
    "general": [
        "Powdery mildew",
        "Downy mildew",
        "Fusarium wilt",
        "Verticillium wilt",
        "Alternaria leaf spot",
        "Bacterial disease",
        "Root/crown rot",
        "Virus-like symptoms",
        "Other / Unknown disease",
    ],
}

def ai_crop_is_tree(crop):
    text = str(crop or "").lower()
    tree_words = ["almond", "apple", "apricot", "peach", "nectarine", "cherry", "plum", "pear", "olive", "date", "citrus", "fig", "pomegranate", "quince", "grape"]
    return any(w in text for w in tree_words)

def ai_common_diseases(crop):
    return COMMON_DISEASES_BY_GROUP["tree" if ai_crop_is_tree(crop) else "general"]

def ai_regional_soil_estimate(wilaya, crop=None):
    """Regional planning estimate only; never presented as a measured soil test."""
    w = str(wilaya or "").strip()
    factor = WILAYA_YIELD_ZONE_FACTORS.get(w, 0.85)
    if factor >= 0.95:
        zone = "higher-productivity northern/highland zone"
        ph_range = "7.2–8.0"
        ec_risk = "low to moderate"
        lime = "low to moderate, locally calcareous"
        texture = "variable loam to clay-loam"
    elif factor >= 0.80:
        zone = "intermediate/highland-transition zone"
        ph_range = "7.5–8.3"
        ec_risk = "moderate"
        lime = "moderate to high, locally calcareous"
        texture = "variable loam to sandy-loam/clay-loam"
    else:
        zone = "arid/semi-arid or lower-productivity zone"
        ph_range = "7.8–8.6"
        ec_risk = "moderate to high"
        lime = "moderate to high calcareous tendency"
        texture = "variable sandy-loam to loam"
    return {
        "source": "regional planning estimate (Wilaya/zone; not a laboratory measurement)",
        "zone": zone,
        "ph_range": ph_range,
        "ec_risk": ec_risk,
        "lime": lime,
        "texture": texture,
        "confidence": 0.45,
    }

def ai_satellite_irrigation_proxy(rows, crop, wilaya):
    """Infer irrigation likelihood only from satellite indicators already available.

    This is a proxy, not proof of irrigation. Stronger evidence requires a time series
    (NDWI/vegetation anomaly plus ET/soil-moisture information) and ideally field data.
    """
    if not rows:
        return {"available": False, "label": "No satellite irrigation evidence", "score": 0.0, "evidence": []}
    ndwi_vals = []
    ndvi_vals = []
    anomaly_vals = []
    radar_vals = []
    for r in rows:
        rv = ai_safe_num(r.get("sentinel1_vv"))
        if rv is not None:
            radar_vals.append(rv)
        for key, arr in [("ndwi", ndwi_vals), ("ndvi", ndvi_vals), ("anomaly_percent", anomaly_vals)]:
            v = ai_safe_num(r.get(key))
            if v is not None:
                arr.append(v)
    evidence = []
    score = 0.0
    if len(ndwi_vals) >= 2 and sum(ndwi_vals[-3:]) / min(3, len(ndwi_vals)) > 0.15:
        score += 0.25
        evidence.append("Satellite NDWI remains relatively elevated across recent observations")
    if len(ndvi_vals) >= 2 and sum(ndvi_vals[-3:]) / min(3, len(ndvi_vals)) > 0.35:
        score += 0.15
        evidence.append("Vegetation activity remains sustained in recent satellite observations")
    if anomaly_vals and sum(anomaly_vals[-3:]) / min(3, len(anomaly_vals)) > 5:
        score += 0.10
        evidence.append("Positive vegetation anomaly supports continued water availability, but does not prove irrigation")
    if len(radar_vals) >= 2 and abs(radar_vals[-1] - radar_vals[-2]) > 0.03:
        score += 0.05
        evidence.append("Sentinel-1 radar variation provides an additional surface-moisture/structure signal")
    score = min(score, 0.45)
    if score >= 0.30:
        label = "Likely irrigated / satellite proxy"
    elif score > 0:
        label = "Possible irrigation signal / satellite proxy"
    else:
        label = "No strong irrigation signal"
    return {"available": True, "label": label, "score": score, "evidence": evidence, "source_quality": "satellite proxy"}

def ai_rank_causes(crop, wilaya, weather_signal, historical_signal, declared_area, benchmark_yield,
                   neighboring_signal=None, soil_rows=None, irrigation_rows=None,
                   satellite_rows=None, disease_rows=None, soil_estimate=None, irrigation_proxy=None):
    """Rank competing explanations using transparent evidence weights.

    This is an expert-rule baseline, not an ML model. Each score is clipped to
    0..1 and accompanied by evidence text so the admin can audit why it fired.
    """
    causes = {k: {"score": 0.0, "evidence": [], "source_quality": "none"} for k in AI_RISK_CAUSE_LABELS}

    # Area/production baseline: always available if declarations and a yield benchmark exist.
    if declared_area > 0 and benchmark_yield and benchmark_yield > 0:
        causes["area"]["evidence"].append(f"Declared area available: {declared_area:,.1f} ha")
        causes["area"]["score"] += 0.10
        causes["area"]["source_quality"] = "estimated"

    # Observed frost: strongest single rule when timing overlaps crop sensitivity.
    if weather_signal.get("frost_events"):
        min_t = weather_signal.get("frost_min_c")
        causes["frost"]["score"] += 0.55
        causes["frost"]["evidence"].append(f"Observed minimum temperature reached {min_t:.1f}°C during a crop-sensitive period")
        if min_t is not None and min_t <= ai_crop_profile(crop).get("severe_frost_threshold_c", -3.0):
            causes["frost"]["score"] += 0.20
            causes["frost"]["evidence"].append("Temperature crossed the severe-frost planning threshold")
        causes["frost"]["source_quality"] = "observed"

    # Weather alerts are weaker than measurements.
    alert_matches = weather_signal.get("alert_matches", [])
    for a in alert_matches:
        if a["kind"] == "frost":
            causes["frost"]["score"] += 0.15
            causes["frost"]["evidence"].append(f"Admin weather alert mentions frost: {a['title']}")
            causes["frost"]["source_quality"] = "alert"
        elif a["kind"] == "drought":
            causes["drought"]["score"] += 0.20
            causes["drought"]["evidence"].append(f"Admin weather alert mentions drought: {a['title']}")
            causes["drought"]["source_quality"] = "alert"
        elif a["kind"] == "heat":
            causes["heat"]["score"] += 0.20
            causes["heat"]["evidence"].append(f"Admin weather alert mentions heat: {a['title']}")
            causes["heat"]["source_quality"] = "alert"

    # Rainfall / irrigation / soil / satellite / disease optional evidence.
    if irrigation_rows:
        causes["irrigation"]["score"] += 0.20
        causes["irrigation"]["evidence"].append("Irrigation observations are available for this investigation")
        causes["irrigation"]["source_quality"] = "observed"
    elif irrigation_proxy and irrigation_proxy.get("score", 0) > 0:
        causes["irrigation"]["score"] += float(irrigation_proxy.get("score", 0))
        causes["irrigation"]["evidence"].extend(irrigation_proxy.get("evidence", []))
        causes["irrigation"]["source_quality"] = "satellite proxy"
    if soil_rows:
        causes["soil"]["score"] += 0.15
        causes["soil"]["evidence"].append("Soil observations are available for this investigation")
        causes["soil"]["source_quality"] = "observed"
    elif soil_estimate:
        causes["soil"]["score"] += 0.05
        causes["soil"]["evidence"].append(
            f"Regional soil estimate: pH {soil_estimate.get('ph_range')}, {soil_estimate.get('lime')}, {soil_estimate.get('ec_risk')} salinity risk"
        )
        causes["soil"]["source_quality"] = "regional estimate"
    disease_positive_rows = [
        r for r in (disease_rows or [])
        if str(r.get("status", "")).strip().lower() not in {
            "checked — no disease / تمت المعاينة دون مرض",
            "checked - no disease",
            "no disease",
        }
    ]
    if disease_positive_rows:
        causes["disease"]["score"] += 0.25
        causes["disease"]["evidence"].append("Disease reports exist for this crop/Wilaya")
        confirmed = any("confirmed" in str(r.get("status", "")).lower() or "مؤكد" in str(r.get("status", "")) for r in disease_positive_rows)
        causes["disease"]["score"] += 0.15 if confirmed else 0.0
        causes["disease"]["evidence"].append("At least one report is marked confirmed" if confirmed else "Disease evidence is reported/suspected, not necessarily confirmed")
        causes["disease"]["source_quality"] = "confirmed report" if confirmed else "reported"
    if satellite_rows:
        causes["disease"]["score"] += 0.05
        causes["disease"]["evidence"].append("Satellite indicators are available as an independent vegetation check")
        causes["disease"]["source_quality"] = "satellite+reported" if disease_rows else "satellite"

    # Neighbor comparison increases confidence when neighboring Wilayas behave differently.
    if neighboring_signal and neighboring_signal.get("available"):
        gap = neighboring_signal.get("target_gap_percent")
        if gap is not None and abs(gap) >= 10:
            causes["frost"]["score"] += 0.10 if causes["frost"]["score"] else 0.0
            causes["drought"]["score"] += 0.03 if causes["drought"]["score"] else 0.0
            for key in ["frost", "drought", "disease", "irrigation", "soil"]:
                if causes[key]["score"] > 0:
                    causes[key]["evidence"].append(
                        f"Neighbor comparison shows a {abs(gap):.1f}% local-vs-neighbor production/coverage difference"
                    )

    # Historical decline is supporting evidence, not a cause by itself.
    if historical_signal.get("available") and historical_signal.get("trend_percent") is not None:
        tr = historical_signal["trend_percent"]
        if tr < -10:
            causes["area"]["score"] += 0.05
            causes["area"]["evidence"].append(f"Historical production trend is {tr:+.1f}%")

    for data in causes.values():
        data["score"] = min(max(float(data["score"]), 0.0), 0.99)
    ranked = sorted(causes.items(), key=lambda x: x[1]["score"], reverse=True)
    # If there is no real causal evidence, explicitly return an evidence-gap
    # result instead of pretending that declared area is a diagnosis.
    if not ranked or ranked[0][1]["score"] < 0.20:
        return [(
            "insufficient_evidence",
            {
                "score": 0.10,
                "evidence": [
                    "No external causal observation crossed the minimum evidence threshold."
                ],
                "source_quality": "missing data",
            },
        )] + ranked
    return ranked


def ai_estimate_investigation_impact(crop, wilaya, declared_area, benchmark_yield, historical_signal, cause_score):
    """Estimate production and potential loss using transparent planning rules."""
    baseline = None
    if historical_signal.get("available") and historical_signal.get("baseline_t"):
        baseline = float(historical_signal["baseline_t"])
    elif declared_area > 0 and benchmark_yield:
        baseline = float(declared_area) * float(benchmark_yield)

    if baseline is None or baseline <= 0:
        return {"baseline_t": None, "expected_t": None, "loss_t": None, "loss_percent": None, "method": "insufficient data"}

    # Conservative cause-impact priors. They are planning estimates until a
    # trained Algerian impact model is available. The score scales the prior.
    cause_name, cause_data = cause_score
    priors = {
        "frost": 0.25,
        "drought": 0.20,
        "disease": 0.18,
        "irrigation": 0.15,
        "soil": 0.12,
        "heat": 0.15,
        "area": 0.05,
    }
    if cause_name == "insufficient_evidence":
        return {"baseline_t": baseline, "expected_t": None, "loss_t": None, "loss_percent": None, "method": "insufficient causal evidence"}

    prior = priors.get(cause_name, 0.05)
    loss_pct = min(0.45, max(0.0, prior * max(0.35, float(cause_data.get("score", 0.0)))))
    expected = baseline * (1.0 - loss_pct)
    return {
        "baseline_t": baseline,
        "expected_t": expected,
        "loss_t": baseline - expected,
        "loss_percent": loss_pct * 100,
        "method": "historical baseline" if historical_signal.get("available") else "declared area × planning yield",
    }


def ai_investigate_crop_wilaya(crop, wilaya, df_live, benchmark_map, national_benchmarks,
                               weather_rows=None, weather_alert_rows=None,
                               historical_rows=None, soil_rows=None, irrigation_rows=None,
                               satellite_rows=None, disease_rows=None, location_rows=None):
    """Run the complete 12-step investigation for one crop/Wilaya."""
    crop = str(crop).strip()
    wilaya = str(wilaya).strip()
    declared_area = ai_declaration_area(df_live, crop, wilaya)
    yield_benchmark = benchmark_map.get((crop, wilaya))
    if yield_benchmark is None:
        yield_benchmark = national_benchmarks.get(crop)
    if yield_benchmark is None:
        yield_benchmark = get_builtin_wilaya_yield(crop, wilaya)

    weather_signal = ai_parse_weather_evidence(weather_rows or [], crop, wilaya)
    weather_signal["alert_matches"] = ai_parse_weather_alerts(weather_alert_rows or [], crop, wilaya)
    historical_signal = ai_historical_production_signal(historical_rows or [], crop, wilaya)

    # Restrict crop-specific evidence to the selected crop/Wilaya. This is
    # critical: a disease in another crop must never become evidence for this
    # investigation.
    crop_aliases = set(AI_CROP_RISK_PROFILES.get(ai_crop_key(crop), {}).get("aliases", set()))
    crop_aliases.add(str(crop).strip())

    def _filter_crop_wilaya(rows, crop_field="crop", wilaya_field="wilaya"):
        out = []
        for row in rows or []:
            rw = str(row.get(wilaya_field, "")).strip()
            rc = str(row.get(crop_field, "")).strip()
            if rw not in {wilaya, "All Wilayas", "ALL", ""}:
                continue
            if crop_field and rc and rc not in crop_aliases:
                continue
            out.append(row)
        return out

    selected_soil_rows = _filter_crop_wilaya(soil_rows)
    selected_irrigation_rows = _filter_crop_wilaya(irrigation_rows)
    selected_satellite_rows = _filter_crop_wilaya(satellite_rows)
    selected_disease_rows = _filter_crop_wilaya(disease_rows, crop_field="crop", wilaya_field="wilaya")
    soil_estimate = ai_regional_soil_estimate(wilaya, crop) if not selected_soil_rows else None
    irrigation_proxy = ai_satellite_irrigation_proxy(selected_satellite_rows, crop, wilaya)

    # Add basic neighbor comparison when Wilaya coordinates are available.
    neighboring_signal = {"available": False}
    if location_rows:
        locs = {}
        for r in location_rows:
            lat = ai_safe_num(r.get("latitude")); lon = ai_safe_num(r.get("longitude"))
            if lat is not None and lon is not None:
                locs[str(r.get("wilaya", "")).strip()] = (lat, lon)
        if wilaya in locs:
            distances = []
            lat1, lon1 = locs[wilaya]
            for other, (lat2, lon2) in locs.items():
                if other == wilaya:
                    continue
                distances.append((haversine_km(lat1, lon1, lat2, lon2), other))
            distances.sort()
            nearest = [w for _, w in distances[:5]]
            # Compare declared-area coverage of nearest Wilayas.
            neighbor_values = []
            for nw in nearest:
                a = ai_declaration_area(df_live, crop, nw)
                if a > 0:
                    y = benchmark_map.get((crop, nw), national_benchmarks.get(crop))
                    y = y if y is not None else get_builtin_wilaya_yield(crop, nw)
                    neighbor_values.append(a * _ai_float(y))
            current_est = declared_area * _ai_float(yield_benchmark)
            if neighbor_values:
                avg_n = sum(neighbor_values) / len(neighbor_values)
                gap = ((current_est - avg_n) / avg_n * 100) if avg_n else None
                neighboring_signal = {"available": True, "nearest": nearest, "target_gap_percent": gap, "neighbor_average_t": avg_n}

    ranked = ai_rank_causes(
        crop, wilaya, weather_signal, historical_signal, declared_area,
        _ai_float(yield_benchmark), neighboring_signal, selected_soil_rows, selected_irrigation_rows,
        selected_satellite_rows, selected_disease_rows, soil_estimate, irrigation_proxy,
    )
    primary = ranked[0]
    impact = ai_estimate_investigation_impact(crop, wilaya, declared_area, _ai_float(yield_benchmark), historical_signal, primary)

    confidence = min(0.95, max(0.20, primary[1]["score"] + (0.15 if historical_signal.get("available") else 0.0) + (0.10 if weather_signal.get("available") else 0.0)))
    evidence_count = sum(len(x[1]["evidence"]) for x in ranked if x[1]["score"] > 0)

    recommendations = []
    if primary[0] == "frost":
        recommendations = [
            "Inspect orchards in the affected flowering/fruit-set window.",
            "Estimate the actually damaged flowering area before revising the production forecast.",
            "Re-run the forecast after the next satellite/field observation.",
        ]
    elif primary[0] in {"drought", "irrigation"}:
        recommendations = [
            "Check irrigation records and water availability by farm/Wilaya.",
            "Prioritize field moisture assessment in the most exposed zones.",
            "Update the production forecast after verified irrigation and rainfall data arrive.",
        ]
    elif primary[0] == "disease":
        recommendations = [
            "Prioritize field scouting in affected areas.",
            "Cross-check disease reports with weather and satellite anomalies.",
            "Recalculate expected impact after confirmed diagnosis.",
        ]
    elif primary[0] == "soil":
        recommendations = [
            "Collect/verify soil analyses for the affected crop areas.",
            "Compare pH, salinity, active lime and nutrient status with crop requirements.",
        ]
    else:
        recommendations = [
            "Collect the missing weather, production and field observations before taking operational action.",
            "Keep the current result as a planning signal rather than a confirmed diagnosis.",
        ]

    # A useful notification should fire only when evidence is meaningful.
    notify = bool(
        primary[1]["score"] >= 0.55
        and impact.get("loss_percent") is not None
        and impact.get("loss_percent", 0) >= 10
    )

    return {
        "crop": crop,
        "wilaya": wilaya,
        "declared_area_ha": declared_area,
        "yield_benchmark_t_ha": _ai_float(yield_benchmark),
        "historical": historical_signal,
        "weather": weather_signal,
        "soil_estimate": soil_estimate,
        "irrigation_proxy": irrigation_proxy,
        "neighbors": neighboring_signal,
        "causes": ranked,
        "primary_cause": primary[0],
        "primary_label": AI_RISK_CAUSE_LABELS.get(primary[0], primary[0]),
        "confidence": confidence,
        "evidence_count": evidence_count,
        "impact": impact,
        "recommendations": recommendations,
        "notify_admin": notify,
        "data_status": {
            "historical_production": bool(historical_rows),
            "declared_area": declared_area > 0,
            "weather": bool(weather_signal.get("available")),
            "rainfall": bool(weather_signal.get("rainfall_total_mm") is not None),
            "soil": bool(selected_soil_rows) or bool(soil_estimate),
            "soil_measured": bool(selected_soil_rows),
            "irrigation": bool(selected_irrigation_rows) or bool(irrigation_proxy.get("available")),
            "irrigation_measured": bool(selected_irrigation_rows),
            "irrigation_satellite_proxy": bool(irrigation_proxy.get("available")),
            "satellite": bool(selected_satellite_rows),
            "disease": bool(selected_disease_rows),
            "neighbors": bool(neighboring_signal.get("available")),
        },
    }


def ai_investigation_text(result):
    """Human-readable evidence-backed explanation for the admin UI."""
    impact = result.get("impact", {})
    if impact.get("loss_percent") is None:
        finding_text = (
            f"**Finding:** {result['crop']} in {result['wilaya']} cannot yet be assigned a reliable production-loss percentage "
            "because causal evidence is insufficient."
        )
    else:
        finding_text = (
            f"**Finding:** {result['crop']} in {result['wilaya']} has an estimated production outlook of "
            f"{impact.get('loss_percent', 0):.1f}% below its current baseline, if the leading risk signal is real."
        )
    lines = [
        finding_text,
        f"**Most likely cause:** {result['primary_label']} — confidence {result['confidence']*100:.0f}%.",
    ]
    baseline_t = impact.get("baseline_t")
    expected_t = impact.get("expected_t")
    loss_t = impact.get("loss_t")
    if baseline_t is not None:
        if expected_t is not None and loss_t is not None:
            lines.append(
                f"**Baseline:** {baseline_t:,.0f} t → **expected:** {expected_t:,.0f} t → **potential impact:** {loss_t:,.0f} t."
            )
        else:
            lines.append(
                f"**Baseline:** {baseline_t:,.0f} t. Expected production impact is not estimated because causal evidence is insufficient."
            )
    lines.append(f"**Evidence items used:** {result.get('evidence_count', 0)}. The result is an analytical signal, not a confirmed diagnosis.")
    return "\n\n".join(lines)


def ai_alert_payload(result):
    impact = result.get("impact", {})
    return {
        "alert_type": "production_risk",
        "severity": "red" if result.get("confidence", 0) >= 0.80 else "orange",
        "crop": result.get("crop"),
        "wilaya": result.get("wilaya"),
        "title": f"AI production risk: {result.get('crop')} — {result.get('wilaya')}",
        "summary": ai_investigation_text(result),
        "expected_impact_t": impact.get("loss_t"),
        "confidence": result.get("confidence"),
        "primary_cause": result.get("primary_cause"),
        "evidence": [
            {"cause": k, "score": round(v.get("score", 0), 3), "evidence": v.get("evidence", [])}
            for k, v in result.get("causes", []) if v.get("score", 0) > 0
        ],
        "recommendations": result.get("recommendations", []),
        "status": "new",
    }

def ai_build_crop_summary(df_live, all_crop_targets, benchmark_map, national_benchmarks):
    """Deterministic agricultural facts used by the local AI agent."""
    rows = []
    if df_live is None or df_live.empty:
        return pd.DataFrame(columns=[
            "Crop", "Declared Area (Ha)", "Target Area (Ha)", "Coverage (%)",
            "Estimated Production (t)", "Wilayas Active", "Top Wilaya", "Top Wilaya Share (%)"
        ])

    work = df_live.copy()
    work["area"] = pd.to_numeric(work.get("area"), errors="coerce").fillna(0.0)
    work["crop"] = work.get("crop", pd.Series(dtype=str)).astype(str).str.strip()
    work["wilaya"] = work.get("wilaya", pd.Series(dtype=str)).astype(str).str.strip()

    for crop, target in all_crop_targets.items():
        crop_df = work[work["crop"] == crop]
        area = float(crop_df["area"].sum()) if not crop_df.empty else 0.0
        target = _ai_float(target)
        coverage = area / target * 100 if target > 0 else 0.0
        est_prod = 0.0
        for wilaya, area_w in crop_df.groupby("wilaya")["area"].sum().items():
            yld = benchmark_map.get((crop, wilaya), national_benchmarks.get(crop))
            if yld is None:
                yld = get_builtin_wilaya_yield(crop, wilaya)
            est_prod += float(area_w) * _ai_float(yld)
        active = int(crop_df["wilaya"].nunique()) if not crop_df.empty else 0
        top_w = "—"
        top_share = 0.0
        if not crop_df.empty and area > 0:
            by_w = crop_df.groupby("wilaya")["area"].sum().sort_values(ascending=False)
            if len(by_w):
                top_w = str(by_w.index[0])
                top_share = float(by_w.iloc[0]) / area * 100
        rows.append({
            "Crop": crop,
            "Declared Area (Ha)": area,
            "Target Area (Ha)": target,
            "Coverage (%)": coverage,
            "Estimated Production (t)": est_prod,
            "Wilayas Active": active,
            "Top Wilaya": top_w,
            "Top Wilaya Share (%)": top_share,
        })
    return pd.DataFrame(rows)


def ai_detect_declaration_anomalies(df_live):
    """Flag unusually large individual declarations using a robust IQR rule."""
    if df_live is None or df_live.empty:
        return pd.DataFrame()
    work = df_live.copy()
    work["area"] = pd.to_numeric(work.get("area"), errors="coerce")
    work = work.dropna(subset=["area"]).copy()
    if work.empty:
        return pd.DataFrame()
    q1 = float(work["area"].quantile(0.25))
    q3 = float(work["area"].quantile(0.75))
    iqr = q3 - q1
    if iqr <= 0:
        threshold = max(q3 * 3, 1.0)
    else:
        threshold = q3 + 1.5 * iqr
    out = work[work["area"] > threshold].copy()
    out["Anomaly Threshold (Ha)"] = threshold
    out = out.sort_values("area", ascending=False)
    return out


def ai_trend_analysis(df_live):
    """Analyze declaration-area trends by crop when usable dates exist."""
    if df_live is None or df_live.empty or "start_date" not in df_live.columns:
        return pd.DataFrame()
    work = df_live.copy()
    work["area"] = pd.to_numeric(work.get("area"), errors="coerce").fillna(0.0)
    work["start_date"] = pd.to_datetime(work["start_date"], errors="coerce")
    work = work.dropna(subset=["start_date"]).copy()
    if work.empty:
        return pd.DataFrame()
    work["Year"] = work["start_date"].dt.year.astype(int)
    annual = work.groupby(["Year", "crop"], dropna=False)["area"].sum().reset_index()
    results = []
    for crop, g in annual.groupby("crop"):
        g = g.sort_values("Year")
        if len(g) < 2:
            continue
        first = float(g.iloc[0]["area"])
        last = float(g.iloc[-1]["area"])
        change = ((last - first) / first * 100) if first > 0 else None
        results.append({
            "Crop": str(crop),
            "First Year": int(g.iloc[0]["Year"]),
            "Last Year": int(g.iloc[-1]["Year"]),
            "First Area (Ha)": first,
            "Last Area (Ha)": last,
            "Change (%)": change,
        })
    return pd.DataFrame(results)


def ai_concentration_analysis(df_live):
    if df_live is None or df_live.empty:
        return pd.DataFrame()
    work = df_live.copy()
    work["area"] = pd.to_numeric(work.get("area"), errors="coerce").fillna(0.0)
    work["crop"] = work.get("crop", pd.Series(dtype=str)).astype(str).str.strip()
    work["wilaya"] = work.get("wilaya", pd.Series(dtype=str)).astype(str).str.strip()
    rows = []
    for crop, g in work.groupby("crop"):
        total = float(g["area"].sum())
        if total <= 0:
            continue
        by_w = g.groupby("wilaya")["area"].sum().sort_values(ascending=False)
        top_share = float(by_w.iloc[0]) / total * 100 if len(by_w) else 0.0
        rows.append({"Crop": crop, "Top Wilaya": str(by_w.index[0]) if len(by_w) else "—", "Top Wilaya Share (%)": top_share, "Active Wilayas": int(len(by_w))})
    return pd.DataFrame(rows).sort_values("Top Wilaya Share (%)", ascending=False) if rows else pd.DataFrame()


def ai_agent_answer(question, df_live, crop_summary, trend_df, concentration_df, anomaly_df):
    """Small tool-using local agent: routes the question to deterministic analytics."""
    q = (question or "").strip().lower()
    if not q:
        return "Ask me about crops, Wilayas, trends, concentration, anomalies, coverage, production estimates, or missing data."

    if any(k in q for k in ["missing", "data quality", "بيانات ناق", "البيانات", "نقص"]):
        n_records = 0 if df_live is None else len(df_live)
        missing_area = int(pd.to_numeric(df_live["area"], errors="coerce").isna().sum()) if df_live is not None and not df_live.empty and "area" in df_live else 0
        missing_w = int(df_live["wilaya"].isna().sum()) if df_live is not None and not df_live.empty and "wilaya" in df_live else 0
        missing_crop = int(df_live["crop"].isna().sum()) if df_live is not None and not df_live.empty and "crop" in df_live else 0
        return (f"📋 Data quality: {n_records:,} declaration records. Missing/invalid area: {missing_area:,}; "
                f"missing Wilaya: {missing_w:,}; missing crop: {missing_crop:,}. "
                "For real ML learning, historical production/yield and market-demand records are still the most important missing datasets.")

    if any(k in q for k in ["concentr", "one wilaya", "most concentrated", "تركز", "متركز"]):
        if concentration_df is None or concentration_df.empty:
            return "I cannot measure crop concentration yet because there are no usable declaration records."
        r = concentration_df.iloc[0]
        return (f"🎯 Most concentrated crop: {r['Crop']}. Its largest declared Wilaya is {r['Top Wilaya']}, "
                f"representing about {float(r['Top Wilaya Share (%)']):,.1f}% of declared area across {int(r['Active Wilayas'])} active Wilayas.")

    if any(k in q for k in ["trend", "fastest", "grown", "growth", "تطور", "نمو", "أسرع"]):
        if trend_df is None or trend_df.empty:
            return "📈 I need declarations from at least two different years for a reliable growth/trend comparison."
        valid = trend_df.dropna(subset=["Change (%)"]).sort_values("Change (%)", ascending=False)
        if valid.empty:
            return "No usable multi-year crop trend is available yet."
        up = valid.iloc[0]
        down = valid.iloc[-1]
        return (f"📈 Fastest increase in the available history: {up['Crop']} ({float(up['Change (%)']):+,.1f}%). "
                f"Largest decrease: {down['Crop']} ({float(down['Change (%)']):+,.1f}%). "
                "This is a declaration-area trend, not a production trend.")

    if any(k in q for k in ["anomal", "outlier", "unusual", "غير عادي", "شاذ"]):
        if anomaly_df is None or anomaly_df.empty:
            return "🔎 No unusually large declaration was detected by the current IQR rule."
        r = anomaly_df.iloc[0]
        return (f"🔎 Largest flagged declaration: {r.get('crop', 'Unknown')} in {r.get('wilaya', 'Unknown')}, "
                f"{float(r['area']):,.1f} ha. The IQR-based threshold is about {float(r['Anomaly Threshold (Ha)']):,.1f} ha. "
                "This is a review flag, not proof of an error or fraud.")

    # Crop-specific question: search exact crop label first.
    if crop_summary is not None and not crop_summary.empty:
        for crop in crop_summary["Crop"].astype(str):
            if crop.lower() in q:
                r = crop_summary[crop_summary["Crop"] == crop].iloc[0]
                return (f"🌱 {crop}: {float(r['Declared Area (Ha)']):,.1f} ha declared vs "
                        f"{float(r['Target Area (Ha)']):,.1f} ha planning target ({float(r['Coverage (%)']):,.1f}% coverage). "
                        f"Estimated production: {float(r['Estimated Production (t)']):,.1f} t. "
                        f"Active Wilayas: {int(r['Wilayas Active'])}; most represented: {r['Top Wilaya']} ({float(r['Top Wilaya Share (%)']):,.1f}%).")

    if any(k in q for k in ["under", "over", "target", "coverage", "نقص", "فائض", "هدف"]):
        if crop_summary is None or crop_summary.empty:
            return "No crop declarations are available for coverage analysis."
        low = crop_summary.sort_values("Coverage (%)").iloc[0]
        high = crop_summary.sort_values("Coverage (%)", ascending=False).iloc[0]
        return (f"🧭 Lowest coverage: {low['Crop']} at {float(low['Coverage (%)']):,.1f}% of its planning area target. "
                f"Highest coverage: {high['Crop']} at {float(high['Coverage (%)']):,.1f}%. "
                "Coverage is based on declared area, not confirmed harvest production.")

    return ("🤖 I can currently analyze: (1) crop coverage, (2) Wilaya concentration, (3) multi-year declaration trends, "
            "(4) unusual declarations, and (5) data quality. Ask a direct question such as 'Which crop is most concentrated?' "
            "or 'What data is missing for real AI forecasting?'")


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

        adm_tab1, adm_tab2, adm_tab3, adm_tab4, adm_tab5, adm_tab6, adm_tab7 = st.tabs([
            "📰 Post News",
            "🚨 Weather Alerts",
            "📨 Send Farmer Notifications",
            "📍 Add Map Location",
            "🦠 Disease Reports",
            "🤖 AI Agricultural Analyst",
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
            st.markdown("#### 🦠 Disease Reports / تقارير الأمراض")
            st.caption(
                "This is the main manual evidence input. The system does not require you to manually enter weather, soil, irrigation or satellite data. "
                "Report only what is observed in the field; the AI keeps suspected and confirmed disease separate."
            )

            disease_crop_options = list(VEGETABLE_LIMITS.keys()) + list(FRUIT_TARGETS_KHA.keys())
            dc1, dc2 = st.columns(2)
            with dc1:
                disease_crop = st.selectbox(
                    "Crop / المحصول",
                    disease_crop_options,
                    key="admin_disease_crop",
                )
            with dc2:
                disease_status = st.selectbox(
                    "Observation status / حالة الملاحظة",
                    ["Suspected / مشتبه", "Confirmed / مؤكد", "Checked — no disease / تمت المعاينة دون مرض"],
                    key="admin_disease_status",
                )

            disease_wilayas = st.multiselect(
                "Affected Wilayas / الولايات المتأثرة",
                WILAYAS_48,
                key="admin_disease_wilayas",
            )
            disease_options = ai_common_diseases(disease_crop)
            disease_name_choice = st.selectbox(
                "Disease / المرض",
                disease_options,
                key="admin_disease_name",
            )
            disease_custom_name = ""
            if disease_name_choice == "Other / Unknown disease":
                disease_custom_name = st.text_input(
                    "Observed/unknown disease name",
                    placeholder="e.g. Unknown leaf spotting — suspected fungal disease",
                    key="admin_disease_custom_name",
                )

            dd1, dd2, dd3 = st.columns(3)
            with dd1:
                disease_severity = st.selectbox(
                    "Severity / الشدة",
                    ["Low / خفيفة", "Moderate / متوسطة", "High / شديدة", "Critical / حرجة"],
                    key="admin_disease_severity",
                )
            with dd2:
                disease_area = st.number_input(
                    "Affected area (ha) / المساحة المتأثرة",
                    min_value=0.0, value=0.0, step=1.0,
                    key="admin_disease_area",
                )
            with dd3:
                disease_date = st.date_input(
                    "Observation date / تاريخ الملاحظة",
                    value=date.today(),
                    key="admin_disease_date",
                )

            ds1, ds2 = st.columns(2)
            with ds1:
                disease_source = st.selectbox(
                    "Source / المصدر",
                    [
                        "Field officer / مفتش ميداني",
                        "Farmer report / بلاغ فلاح",
                        "Laboratory / مخبر",
                        "Agricultural extension / إرشاد فلاحي",
                        "Other / مصدر آخر",
                    ],
                    key="admin_disease_source",
                )
            with ds2:
                disease_confidence = st.slider(
                    "Confidence / الثقة", 0.0, 1.0, 0.70, 0.05,
                    key="admin_disease_confidence",
                )

            disease_notes = st.text_area(
                "Notes / ملاحظات",
                placeholder="Symptoms, affected varieties, field observations, laboratory information...",
                key="admin_disease_notes",
            )

            if st.button("🦠 Save Disease Report", key="admin_save_disease_report", type="primary"):
                if not disease_wilayas:
                    st.error("Select at least one affected Wilaya.")
                elif disease_name_choice == "Other / Unknown disease" and not disease_custom_name.strip():
                    st.error("Enter the observed/unknown disease name.")
                else:
                    final_disease_name = disease_custom_name.strip() if disease_name_choice == "Other / Unknown disease" else disease_name_choice
                    inserted = 0
                    for target_wilaya in disease_wilayas:
                        payload = {
                            "reported_at": disease_date.isoformat(),
                            "wilaya": target_wilaya,
                            "crop": disease_crop,
                            "disease": sanitize(final_disease_name),
                            "severity": disease_severity,
                            "affected_area_ha": disease_area if disease_area > 0 else None,
                            "source": disease_source,
                            "status": disease_status,
                            "confidence": float(disease_confidence),
                            "notes": sanitize(disease_notes),
                        }
                        try:
                            supabase_client.table("disease_reports").insert(payload).execute()
                            inserted += 1
                        except Exception:
                            # Backward compatibility with the original 8-column table.
                            legacy_payload = {k: payload[k] for k in [
                                "reported_at", "wilaya", "crop", "disease", "severity",
                                "affected_area_ha", "source"
                            ]}
                            try:
                                supabase_client.table("disease_reports").insert(legacy_payload).execute()
                                inserted += 1
                            except Exception as exc:
                                st.error(f"Could not save report for {target_wilaya}: {exc}")
                    if inserted:
                        st.success(f"Saved {inserted} disease report(s).")
                        st.rerun()

            st.divider()
            st.markdown("##### 📋 Recent disease reports")
            recent_disease_rows, recent_disease_ready, _ = ai_load_optional_table(
                "disease_reports",
                "reported_at, wilaya, crop, disease, severity, affected_area_ha, source, status, confidence, notes"
            )
            if not recent_disease_ready:
                recent_disease_rows, recent_disease_ready, _ = ai_load_optional_table(
                    "disease_reports",
                    "reported_at, wilaya, crop, disease, severity, affected_area_ha, source"
                )
            if recent_disease_rows:
                rdf = pd.DataFrame(recent_disease_rows).sort_values("reported_at", ascending=False)
                st.dataframe(rdf.head(100), use_container_width=True, hide_index=True)
            else:
                st.info("No disease reports have been recorded yet.")

            st.markdown("##### 🧠 Important evidence rule")
            st.info(
                "A disease report is evidence of an observation, not automatically a confirmed diagnosis. "
                "The AI will combine it with crop stage, weather and satellite anomalies. Unknown diseases remain unknown until a qualified diagnosis confirms them."
            )

        with adm_tab6:
            st.markdown("#### 🤖 AI Agricultural Analyst v2 — Investigation Engine")
            st.caption(
                "The agent now investigates a crop × Wilaya instead of only answering statistics. "
                "It checks available evidence, ranks competing causes, estimates impact, and can create an admin-only alert. "
                "Missing external observations are explicitly marked as missing; built-in yield/phenology values are labeled as planning estimates."
            )

            try:
                # -------------------------------------------------
                # LIVE DECLARATION DATA
                # -------------------------------------------------
                ai_res = (
                    supabase_client.table("declarations")
                    .select("crop, category, area, wilaya, start_date")
                    .execute()
                )
                ai_records = ai_res.data if ai_res.data else []
                ai_df = pd.DataFrame(ai_records)
                if ai_df.empty:
                    ai_df = pd.DataFrame(columns=["crop", "category", "area", "wilaya", "start_date"])
                else:
                    ai_df["area"] = pd.to_numeric(ai_df["area"], errors="coerce")
                    ai_df["crop"] = ai_df["crop"].astype(str).str.strip()
                    ai_df["wilaya"] = ai_df["wilaya"].astype(str).str.strip()

                ai_targets = {str(k): _ai_float(v) for k, v in VEGETABLE_LIMITS.items()}
                ai_targets.update({str(k): _ai_float(v) * 1000.0 for k, v in FRUIT_TARGETS_KHA.items()})

                # -------------------------------------------------
                # BENCHMARKS — Supabase overrides built-in values
                # -------------------------------------------------
                ai_benchmark_rows, ai_benchmark_ready, _ = ai_load_optional_table(
                    "crop_yield_benchmarks", "crop, wilaya, yield_t_ha"
                )
                ai_benchmark_map = {}
                ai_national = {}
                for row in ai_benchmark_rows:
                    crop_name = str(row.get("crop", "")).strip()
                    w = row.get("wilaya")
                    y = _ai_float(row.get("yield_t_ha"), 0)
                    if not crop_name or y <= 0:
                        continue
                    if w and str(w).strip() not in {"National", "National / وطني"}:
                        ai_benchmark_map[(crop_name, str(w).strip())] = y
                    else:
                        ai_national[crop_name] = y
                for crop_name, base_yield in BUILTIN_YIELD_BENCHMARKS.items():
                    aliases = {crop_name}
                    if " / " in crop_name:
                        left, arabic = crop_name.split(" / ", 1)
                        aliases.add(f"{left.strip()} ({arabic.strip()})")
                    for alias in aliases:
                        ai_national.setdefault(alias, base_yield)
                        for w in WILAYAS_48:
                            ai_benchmark_map.setdefault((alias, w), get_builtin_wilaya_yield(alias, w))

                # -------------------------------------------------
                # OPTIONAL INVESTIGATION DATA SOURCES
                # -------------------------------------------------
                history_rows, history_ready, _ = ai_load_optional_table(
                    "historical_production", "year, crop, wilaya, area_ha, production_t, yield_t_ha, source"
                )
                weather_rows, weather_ready, _ = ai_load_optional_table(
                    "weather_observations", "observed_at, wilaya, tmin_c, tmax_c, rainfall_mm, source"
                )
                soil_rows, soil_ready, _ = ai_load_optional_table(
                    "soil_observations", "observed_at, wilaya, crop, ph, ec_ds_m, caco3_percent, organic_matter_percent, soil_moisture_percent, source"
                )
                irrigation_rows, irrigation_ready, _ = ai_load_optional_table(
                    "irrigation_observations", "observed_at, wilaya, crop, water_mm, irrigation_hours, source"
                )
                satellite_rows, satellite_ready, _ = ai_load_optional_table(
                    "satellite_indicators", "observed_at, wilaya, crop, ndvi, ndwi, evi, fapar, anomaly_percent, source"
                )
                disease_rows, disease_ready, _ = ai_load_optional_table(
                    "disease_reports", "reported_at, wilaya, crop, disease, severity, affected_area_ha, source, status, confidence, notes"
                )
                if not disease_ready:
                    disease_rows, disease_ready, _ = ai_load_optional_table(
                        "disease_reports", "reported_at, wilaya, crop, disease, severity, affected_area_ha, source"
                    )
                location_rows, location_ready, _ = ai_load_optional_table(
                    "wilaya_locations", "wilaya, latitude, longitude"
                )
                weather_alert_rows, _, _ = ai_load_optional_table(
                    "weather_alerts", "id, title, region, severity, message, created_at"
                )
                ai_alert_rows, ai_alert_table_ready, _ = ai_load_optional_table(
                    "admin_ai_alerts", "id, created_at, alert_type, severity, crop, wilaya, title, summary, expected_impact_t, confidence, primary_cause, status, reviewed_at"
                )

                ai_crop_summary = ai_build_crop_summary(ai_df, ai_targets, ai_benchmark_map, ai_national)
                ai_trends = ai_trend_analysis(ai_df)
                ai_concentration = ai_concentration_analysis(ai_df)
                ai_anomalies = ai_detect_declaration_anomalies(ai_df)

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("📋 Declarations", f"{len(ai_df):,}")
                with m2:
                    st.metric("🌱 Active Crops", f"{int((ai_crop_summary['Declared Area (Ha)'] > 0).sum()) if not ai_crop_summary.empty else 0}")
                with m3:
                    st.metric("🗺️ Active Wilayas", f"{ai_df['wilaya'].nunique() if not ai_df.empty else 0}")
                with m4:
                    st.metric("🚨 AI Alerts", f"{len(ai_alert_rows):,}")

                ai_tab1, ai_tab2, ai_tab3, ai_tab4, ai_tab5 = st.tabs([
                    "🔎 Investigation",
                    "🚨 AI Alerts",
                    "📈 Automatic Analysis",
                    "🧠 Ask the Agent",
                    "🧪 Data & Learning",
                ])

                # -------------------------------------------------
                # TAB 1 — INVESTIGATION
                # -------------------------------------------------
                with ai_tab1:
                    st.markdown("##### 🔎 12-step agricultural investigation")
                    st.write(
                        "Select a crop and Wilaya. The engine will inspect historical production, declared area, "
                        "weather, rainfall, soil, irrigation, satellite indicators, disease reports and nearby Wilayas, "
                        "then rank causes, estimate impact and recommend interventions."
                    )

                    investigation_crops = list(ai_targets.keys())
                    default_crop = "Almonds (لوز)" if "Almonds (لوز)" in investigation_crops else (investigation_crops[0] if investigation_crops else "")
                    ic1, ic2 = st.columns(2)
                    with ic1:
                        selected_investigation_crop = st.selectbox(
                            "Crop / المحصول",
                            investigation_crops,
                            index=investigation_crops.index(default_crop) if default_crop in investigation_crops else 0,
                            key="ai_investigation_crop",
                        )
                    with ic2:
                        selected_investigation_wilaya = st.selectbox(
                            "Wilaya / الولاية",
                            WILAYAS_48,
                            index=WILAYAS_48.index("17 - Djelfa") if "17 - Djelfa" in WILAYAS_48 else 0,
                            key="ai_investigation_wilaya",
                        )

                    run_investigation = st.button("🔍 Run Full Investigation", key="ai_run_investigation", type="primary")
                    if run_investigation:
                        # Weather is the first external sensor we can safely add
                        # without a secret key. Prefer stored observations; if none
                        # exist, fetch an explicitly-labelled external planning series.
                        investigation_weather_rows = list(weather_rows or [])
                        weather_source_label = "Supabase observations" if investigation_weather_rows else "Not available"
                        if not investigation_weather_rows:
                            wlat, wlon, coord_source = ai_resolve_wilaya_coordinates(
                                selected_investigation_wilaya, location_rows
                            )
                            if wlat is not None and wlon is not None:
                                external_rows = ai_fetch_external_weather(
                                    selected_investigation_wilaya, wlat, wlon, days_back=365
                                )
                                if external_rows:
                                    investigation_weather_rows.extend(external_rows)
                                    weather_source_label = "Open-Meteo historical weather (external planning source)"
                        investigation_satellite_rows = list(satellite_rows or [])
                        satellite_source_label = "Supabase satellite indicators" if investigation_satellite_rows else "Not available"
                        if not investigation_satellite_rows:
                            slat, slon, _sat_coord_source = ai_resolve_wilaya_coordinates(selected_investigation_wilaya, location_rows)
                            if slat is not None and slon is not None:
                                live_sat_rows, live_sat_source = ai_fetch_copernicus_satellite(selected_investigation_wilaya, slat, slon, days_back=90)
                                if live_sat_rows:
                                    investigation_satellite_rows.extend(live_sat_rows)
                                satellite_source_label = live_sat_source

                        result = ai_investigate_crop_wilaya(
                            selected_investigation_crop,
                            selected_investigation_wilaya,
                            ai_df,
                            ai_benchmark_map,
                            ai_national,
                            weather_rows=investigation_weather_rows,
                            weather_alert_rows=weather_alert_rows,
                            historical_rows=history_rows,
                            soil_rows=soil_rows,
                            irrigation_rows=irrigation_rows,
                            satellite_rows=investigation_satellite_rows,
                            disease_rows=disease_rows,
                            location_rows=location_rows,
                        )
                        result["satellite_source_label"] = satellite_source_label
                        result["weather_source_label"] = weather_source_label
                        st.session_state["last_ai_investigation"] = result

                    result = st.session_state.get("last_ai_investigation")
                    if result:
                        st.divider()
                        impact = result.get("impact", {})
                        confidence = result.get("confidence", 0.0) * 100
                        primary = result.get("primary_label", "Unknown")

                        if result.get("notify_admin"):
                            st.error(
                                f"🚨 HIGH PRIORITY SIGNAL — {result['crop']} / {result['wilaya']} — "
                                f"{primary} — confidence {confidence:.0f}%"
                            )
                        else:
                            st.info(
                                f"🧠 Current finding — {result['crop']} / {result['wilaya']} — "
                                f"{primary} — confidence {confidence:.0f}%"
                            )

                        r1, r2, r3, r4 = st.columns(4)
                        with r1:
                            st.metric("Declared Area", f"{result['declared_area_ha']:,.1f} ha")
                        with r2:
                            st.metric("Baseline", "—" if impact.get("baseline_t") is None else f"{impact['baseline_t']:,.0f} t")
                        with r3:
                            st.metric("Expected", "—" if impact.get("expected_t") is None else f"{impact['expected_t']:,.0f} t")
                        with r4:
                            st.metric("Potential Impact", "—" if impact.get("loss_t") is None else f"-{impact['loss_t']:,.0f} t")

                        st.markdown("##### 🧠 Agent conclusion")
                        st.markdown(ai_investigation_text(result))
                        if result.get("weather_source_label"):
                            st.caption(f"Weather source used: {result['weather_source_label']}. External weather is a planning source until ONM/official observations are connected.")
                        if result.get("satellite_source_label"):
                            st.caption(f"Satellite source used: {result['satellite_source_label']}. Satellite-derived irrigation is a proxy, not proof of a specific irrigation system.")

                        st.markdown("##### 🔬 Evidence chain")
                        status_rows = [
                            ("1. Historical production", result["data_status"]["historical_production"], "Historical production/yield baseline"),
                            ("2. Declared area", result["data_status"]["declared_area"], f"{result['declared_area_ha']:,.1f} ha declared"),
                            ("3. Weather", result["data_status"]["weather"], "Observed weather table"),
                            ("4. Rainfall", result["data_status"]["rainfall"], "Rainfall observations"),
                            ("5. Soil", result["data_status"]["soil"], "Measured soil observations" if result["data_status"].get("soil_measured") else "Regional soil estimate (not laboratory measured)"),
                            ("6. Irrigation", result["data_status"]["irrigation"], "Measured irrigation observations" if result["data_status"].get("irrigation_measured") else ("Satellite irrigation proxy" if result["data_status"].get("irrigation_satellite_proxy") else "No irrigation observation")),
                            ("7. Satellite indicators", result["data_status"]["satellite"], "NDVI/NDWI/EVI/FAPAR indicators"),
                            ("8. Disease reports", result["data_status"]["disease"], "Disease reports"),
                            ("9. Neighboring Wilayas", result["data_status"]["neighbors"], "Nearest-Wilaya comparison"),
                        ]
                        evidence_display = pd.DataFrame([
                            {"Check": name, "Status": "✅ Available" if available else "🟡 Missing", "What it contributes": contribution}
                            for name, available, contribution in status_rows
                        ])
                        st.dataframe(evidence_display, use_container_width=True, hide_index=True)

                        st.markdown("##### ⚖️ Competing causes")
                        cause_rows = []
                        for cause, data in result.get("causes", []):
                            cause_rows.append({
                                "Cause": AI_RISK_CAUSE_LABELS.get(cause, cause),
                                "Score": f"{data['score']*100:.0f}%",
                                "Evidence": "; ".join(data.get("evidence", [])) if data.get("evidence") else "No supporting evidence",
                                "Source quality": data.get("source_quality", "none"),
                            })
                        st.dataframe(pd.DataFrame(cause_rows), use_container_width=True, hide_index=True)

                        st.markdown("##### 🌍 Neighbor comparison")
                        if result.get("neighbors", {}).get("available"):
                            ns = result["neighbors"]
                            st.write(
                                f"Nearest Wilayas: {', '.join(ns.get('nearest', []))}. "
                                f"Current estimated production differs from their average by "
                                f"{ns.get('target_gap_percent', 0):+.1f}%."
                            )
                        else:
                            st.info("Neighbor comparison requires `wilaya_locations` coordinates and at least one neighboring declaration.")

                        st.markdown("##### 🛠️ Recommended interventions")
                        for recommendation in result.get("recommendations", []):
                            st.write(f"• {recommendation}")

                        if result.get("notify_admin"):
                            if ai_alert_table_ready:
                                if st.button("🚨 Create Admin AI Alert", key="ai_create_alert"):
                                    try:
                                        supabase_client.table("admin_ai_alerts").insert(ai_alert_payload(result)).execute()
                                        st.success("AI alert saved for the administrator.")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Could not save the AI alert: {exc}")
                            else:
                                st.warning("The investigation reached the alert threshold, but `admin_ai_alerts` does not exist yet. Create the SQL shown in the Data & Learning tab.")

                # -------------------------------------------------
                # TAB 2 — ADMIN AI ALERTS
                # -------------------------------------------------
                with ai_tab2:
                    st.markdown("##### 🚨 Admin-only AI production alerts")
                    st.caption("These alerts are intentionally separate from farmer notifications. They require administrator review before any farmer-facing action.")
                    if ai_alert_table_ready:
                        st.markdown("###### 🔄 National risk scan")
                        st.write(
                            "The scan checks every crop × active Wilaya combination with the same evidence engine. "
                            "It only creates alerts when the cause score and estimated impact cross the configured threshold."
                        )
                        if st.button("🔍 Run National AI Risk Scan", key="ai_national_risk_scan"):
                            active_pairs = []
                            if not ai_df.empty:
                                for (crop_name, wilaya_name), _group in ai_df.groupby(["crop", "wilaya"]):
                                    if str(crop_name).strip() and str(wilaya_name).strip():
                                        active_pairs.append((str(crop_name).strip(), str(wilaya_name).strip()))
                            generated = []
                            weather_cache = {}
                            satellite_cache = {}
                            for _crop_name, wilaya_name in active_pairs:
                                if wilaya_name not in weather_cache:
                                    if weather_rows:
                                        weather_cache[wilaya_name] = weather_rows
                                    else:
                                        wlat, wlon, _coord_source = ai_resolve_wilaya_coordinates(wilaya_name, location_rows)
                                        weather_cache[wilaya_name] = (
                                            ai_fetch_external_weather(wilaya_name, wlat, wlon, days_back=365)
                                            if wlat is not None and wlon is not None else []
                                        )
                                if wilaya_name not in satellite_cache:
                                    if satellite_rows:
                                        satellite_cache[wilaya_name] = satellite_rows
                                    else:
                                        slat, slon, _ = ai_resolve_wilaya_coordinates(wilaya_name, location_rows)
                                        satellite_cache[wilaya_name] = []
                                        if slat is not None and slon is not None:
                                            live_sat_rows, _ = ai_fetch_copernicus_satellite(wilaya_name, slat, slon, days_back=90)
                                            satellite_cache[wilaya_name] = live_sat_rows
                                scan_result = ai_investigate_crop_wilaya(
                                    crop_name, wilaya_name, ai_df, ai_benchmark_map, ai_national,
                                    weather_rows=weather_cache.get(wilaya_name, []), weather_alert_rows=weather_alert_rows,
                                    historical_rows=history_rows, soil_rows=soil_rows,
                                    irrigation_rows=irrigation_rows, satellite_rows=satellite_cache.get(wilaya_name, []),
                                    disease_rows=disease_rows, location_rows=location_rows,
                                )
                                if scan_result.get("notify_admin"):
                                    generated.append(scan_result)
                            inserted = 0
                            existing_alert_keys = {
                                (str(r.get("crop", "")).strip(), str(r.get("wilaya", "")).strip(), str(r.get("primary_cause", "")).strip())
                                for r in ai_alert_rows
                            }
                            for scan_result in generated:
                                alert_key = (
                                    str(scan_result.get("crop", "")).strip(),
                                    str(scan_result.get("wilaya", "")).strip(),
                                    str(scan_result.get("primary_cause", "")).strip(),
                                )
                                if alert_key in existing_alert_keys:
                                    continue
                                try:
                                    supabase_client.table("admin_ai_alerts").insert(ai_alert_payload(scan_result)).execute()
                                    existing_alert_keys.add(alert_key)
                                    inserted += 1
                                except Exception:
                                    pass
                            if inserted:
                                st.success(f"National scan complete: {inserted} admin AI alert(s) created.")
                            else:
                                st.info("National scan complete: no investigation crossed the alert threshold.")
                            st.rerun()

                    if not ai_alert_table_ready:
                        st.warning("`admin_ai_alerts` is not available yet. Create the table from the SQL in the Data & Learning tab.")
                    elif not ai_alert_rows:
                        st.success("🟢 No stored AI production alerts yet.")
                    else:
                        alerts_df = pd.DataFrame(ai_alert_rows)
                        if "confidence" in alerts_df:
                            alerts_df["confidence"] = pd.to_numeric(alerts_df["confidence"], errors="coerce").map(lambda x: "—" if pd.isna(x) else f"{x*100:.0f}%")
                        if "expected_impact_t" in alerts_df:
                            alerts_df["expected_impact_t"] = pd.to_numeric(alerts_df["expected_impact_t"], errors="coerce").map(lambda x: "—" if pd.isna(x) else f"{x:,.0f} t")
                        cols = [c for c in ["created_at", "severity", "crop", "wilaya", "title", "expected_impact_t", "confidence", "primary_cause", "status"] if c in alerts_df.columns]
                        st.dataframe(alerts_df[cols], use_container_width=True, hide_index=True)
                        st.info("Review the full investigation before publishing any recommendation to farmers.")

                # -------------------------------------------------
                # TAB 3 — AUTOMATIC ANALYSIS
                # -------------------------------------------------
                with ai_tab3:
                    st.markdown("##### 📈 Automatic national analysis")
                    if ai_crop_summary.empty:
                        st.info("No declarations are available yet. The agent will start analyzing as farmer data arrives.")
                    else:
                        low = ai_crop_summary.sort_values("Coverage (%)").iloc[0]
                        high = ai_crop_summary.sort_values("Coverage (%)", ascending=False).iloc[0]
                        conc = ai_concentration.iloc[0] if not ai_concentration.empty else None
                        st.write(f"🟡 **Lowest declared-area coverage:** {low['Crop']} — {float(low['Coverage (%)']):,.1f}% of target.")
                        st.write(f"🔵 **Highest declared-area coverage:** {high['Crop']} — {float(high['Coverage (%)']):,.1f}% of target.")
                        if conc is not None:
                            st.write(f"🎯 **Highest geographic concentration:** {conc['Crop']} — {conc['Top Wilaya']} holds about {float(conc['Top Wilaya Share (%)']):,.1f}% of declared area.")
                        if not ai_anomalies.empty:
                            r = ai_anomalies.iloc[0]
                            st.write(f"🔎 **Largest review flag:** {r.get('crop', 'Unknown')} / {r.get('wilaya', 'Unknown')} — {float(r['area']):,.1f} ha.")
                        else:
                            st.write("🔎 **Anomaly scan:** no unusually large declaration was flagged by the current IQR rule.")

                        display_ai = ai_crop_summary.copy()
                        for c in ["Declared Area (Ha)", "Target Area (Ha)", "Estimated Production (t)"]:
                            display_ai[c] = display_ai[c].map(lambda x: f"{float(x):,.1f}")
                        display_ai["Coverage (%)"] = display_ai["Coverage (%)"].map(lambda x: f"{float(x):,.1f}%")
                        display_ai["Top Wilaya Share (%)"] = display_ai["Top Wilaya Share (%)"].map(lambda x: f"{float(x):,.1f}%")
                        st.dataframe(display_ai, use_container_width=True, hide_index=True)

                        if not ai_trends.empty:
                            st.markdown("##### Historical declaration trends")
                            trend_display = ai_trends.copy()
                            trend_display["Change (%)"] = trend_display["Change (%)"].map(lambda x: "—" if pd.isna(x) else f"{float(x):+,.1f}%")
                            st.dataframe(trend_display, use_container_width=True, hide_index=True)

                # -------------------------------------------------
                # TAB 4 — ASK AGENT
                # -------------------------------------------------
                with ai_tab4:
                    st.markdown("##### 🧠 Ask the agricultural agent")
                    st.write(
                        "Examples: *Which crop is most concentrated?* · *What crop has the lowest coverage?* · "
                        "*What data is missing for real forecasting?* · *What causes should I investigate for almonds?*"
                    )
                    ai_question = st.text_input(
                        "Question / السؤال",
                        placeholder="What data is missing for a reliable almond production forecast?",
                        key="ai_agri_question_v2",
                    )
                    if st.button("🤖 Analyze", key="ai_agri_analyze_v2"):
                        answer = ai_agent_answer(
                            ai_question, ai_df, ai_crop_summary, ai_trends, ai_concentration, ai_anomalies
                        )
                        st.markdown("##### Agent finding")
                        st.info(answer)

                # -------------------------------------------------
                # TAB 5 — DATA, SQL & LEARNING READINESS
                # -------------------------------------------------
                with ai_tab5:
                    st.markdown("##### 🧪 Investigation data readiness")
                    readiness = pd.DataFrame([
                        {"Data stream": "Farmer declarations", "Status": "✅ Live", "Agent use": "Area, crop, Wilaya, current planning baseline"},
                        {"Data stream": "Historical production", "Status": "🟡 Optional table", "Agent use": "True production baseline and trend"},
                        {"Data stream": "Weather + rainfall", "Status": "🟡 Optional table", "Agent use": "Frost, heat, rainfall anomalies"},
                        {"Data stream": "Soil", "Status": "🟢 Automatic regional estimate + optional measured data", "Agent use": "pH range, salinity/lime risk and soil limitations; measured lab data override estimates"},
                        {"Data stream": "Irrigation", "Status": "🟢 Satellite proxy + optional measured data", "Agent use": "Sentinel-1/Sentinel-2 water/vegetation signals; measured irrigation data override the satellite proxy"},
                        {"Data stream": "Satellite", "Status": "🟢 Automatic when Copernicus credentials are configured", "Agent use": "Sentinel-2 NDVI/NDWI indicators"},
                        {"Data stream": "Disease reports", "Status": "🟡 Optional table", "Agent use": "Disease evidence and impact"},
                        {"Data stream": "Wilaya coordinates", "Status": "🟡 Existing optional table", "Agent use": "Nearest-Wilaya comparison"},
                        {"Data stream": "Admin AI alerts", "Status": "🟡 Optional table", "Agent use": "Store and review high-priority investigations"},
                    ])
                    st.dataframe(readiness, use_container_width=True, hide_index=True)

                    st.markdown("##### 🧮 Fallback policy")
                    st.info(
                        "The agent uses Supabase observations first. If a yield benchmark is missing, it uses the built-in planning benchmark; "
                        "Potato, tomato and onion use historical ONS national yield bases already documented in this app, while the remaining crop/Wilaya yields are planning estimates. "
                        "Phenology/frost windows are planning rules. Soil may use a regional estimate until measured soil data exist; satellite is fetched automatically when connected. The agent never invents measured observations."
                    )

                    st.markdown("##### 🛰️ Automatic satellite connection")
                    st.info(
                        "No satellite observations need to be typed manually. The app can request Sentinel-2 statistics automatically for the selected Wilaya when a Copernicus Data Space OAuth client is configured in Streamlit Secrets. Without credentials, the app keeps satellite evidence as missing instead of inventing it."
                    )
                    st.code('''[copernicus]
CLIENT_ID = "your_copernicus_client_id"
CLIENT_SECRET = "your_copernicus_client_secret"''', language="toml")

                    st.markdown("##### 🗄️ SQL — create the investigation data tables")
                    st.code(r'''-- 1) Historical production / yield
create table if not exists public.historical_production (
  id bigint generated by default as identity primary key,
  year integer not null,
  crop text not null,
  wilaya text not null,
  area_ha numeric check (area_ha is null or area_ha >= 0),
  production_t numeric check (production_t is null or production_t >= 0),
  yield_t_ha numeric check (yield_t_ha is null or yield_t_ha >= 0),
  source text,
  created_at timestamptz default now()
);

-- 2) Weather + rainfall observations
create table if not exists public.weather_observations (
  id bigint generated by default as identity primary key,
  observed_at timestamptz not null,
  wilaya text,
  tmin_c numeric,
  tmax_c numeric,
  rainfall_mm numeric check (rainfall_mm is null or rainfall_mm >= 0),
  source text,
  created_at timestamptz default now()
);

-- 3) Soil observations
create table if not exists public.soil_observations (
  id bigint generated by default as identity primary key,
  observed_at timestamptz default now(),
  wilaya text,
  crop text,
  ph numeric,
  ec_ds_m numeric,
  caco3_percent numeric,
  organic_matter_percent numeric,
  soil_moisture_percent numeric,
  source text,
  created_at timestamptz default now()
);

-- 4) Irrigation observations
create table if not exists public.irrigation_observations (
  id bigint generated by default as identity primary key,
  observed_at timestamptz default now(),
  wilaya text,
  crop text,
  water_mm numeric check (water_mm is null or water_mm >= 0),
  irrigation_hours numeric check (irrigation_hours is null or irrigation_hours >= 0),
  source text,
  created_at timestamptz default now()
);

-- 5) Satellite indicators
create table if not exists public.satellite_indicators (
  id bigint generated by default as identity primary key,
  observed_at timestamptz not null,
  wilaya text,
  crop text,
  ndvi numeric,
  ndwi numeric,
  evi numeric,
  fapar numeric,
  anomaly_percent numeric,
  source text,
  created_at timestamptz default now()
);

-- 6) Disease reports
create table if not exists public.disease_reports (
  id bigint generated by default as identity primary key,
  reported_at timestamptz default now(),
  wilaya text,
  crop text,
  disease text,
  severity text,
  affected_area_ha numeric check (affected_area_ha is null or affected_area_ha >= 0),
  source text,
  status text default 'Suspected / مشتبه',
  confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 1)),
  notes text,
  created_at timestamptz default now()
);

-- If the table already existed from an earlier app version, run these once:
alter table public.disease_reports add column if not exists status text default 'Suspected / مشتبه';
alter table public.disease_reports add column if not exists confidence numeric;
alter table public.disease_reports add column if not exists notes text;

-- 7) Admin-only AI alerts
create table if not exists public.admin_ai_alerts (
  id bigint generated by default as identity primary key,
  created_at timestamptz default now(),
  alert_type text,
  severity text,
  crop text,
  wilaya text,
  title text,
  summary text,
  expected_impact_t numeric,
  confidence numeric,
  primary_cause text,
  evidence jsonb,
  recommendations jsonb,
  status text default 'new',
  reviewed_at timestamptz
);

create index if not exists idx_admin_ai_alerts_status
on public.admin_ai_alerts(status, created_at desc);
''', language="sql")

                    st.markdown("##### 🌐 External data roadmap")
                    st.write(
                        "Next connectors should populate these tables automatically. For satellite monitoring, Copernicus Sentinel-2 provides "
                        "free multispectral data suitable for vegetation, soil and water monitoring; the agent can later calculate NDVI/EVI/NDWI "
                        "and compare current values with historical baselines."
                    )
                    st.markdown("Sources to connect next: **MADR/ONS → weather → Copernicus Sentinel → soil → disease → market data.**")

            except Exception as e:
                st.error(f"Unable to run the agricultural AI analyst: {e}")

        with adm_tab7:
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
                        # Store both historical naming styles so declarations such as
                        # ``Potatoes (بطاطا)`` still resolve the benchmark stored as
                        # ``Potatoes / بطاطا`` (and vice versa).
                        crop_aliases = {crop_name}
                        if " / " in crop_name:
                            left, arabic = crop_name.split(" / ", 1)
                            crop_aliases.add(f"{left.strip()} ({arabic.strip()})")
                        for crop_alias in crop_aliases:
                            national_benchmarks.setdefault(crop_alias, fallback_yield)
                            # Create a fallback for every crop × Wilaya pair.
                            # Explicit Supabase Wilaya values remain higher priority.
                            for w in WILAYAS_48:
                                benchmark_map.setdefault(
                                    (crop_alias, w),
                                    get_builtin_wilaya_yield(crop_alias, w)
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
                            "No Supabase benchmark rows yet. Built-in planning benchmarks are active for all crops and all 48 Wilayas; "
                            "you can later add official values in Supabase and they will override these estimates."
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
                                        if is_builtin_official_crop(selected_prod_crop)
                                        else "Planning estimate (Wilaya fallback)"
                                    )
                                )
                            )
                        )

                        national_yield = national_benchmarks.get(selected_prod_crop)
                        if national_yield is None:
                            national_yield = get_builtin_base_yield(selected_prod_crop)
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
                        full_wilaya_prod["Yield (t/Ha)"] = full_wilaya_prod.apply(
                            lambda row: (
                                row["Yield (t/Ha)"]
                                if pd.notna(row["Yield (t/Ha)"])
                                else benchmark_map.get(
                                    (selected_prod_crop, str(row["wilaya"]).strip()),
                                    national_benchmarks.get(
                                        selected_prod_crop,
                                        get_builtin_base_yield(selected_prod_crop)
                                    )
                                )
                            ),
                            axis=1,
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
                                opt_national_yield = get_builtin_base_yield(selected_opt_crop)

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
