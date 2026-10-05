from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import swisseph as swe

st.set_page_config(page_title="AstroVani Career Kundali", page_icon="🔮", layout="centered")

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

DASHA_SEQUENCE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
NAK_LORDS = [DASHA_SEQUENCE[i % 9] for i in range(27)]
PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
}
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"
}

@dataclass
class GeoResult:
    latitude: float
    longitude: float
    timezone: str
    display_name: str

def deg_norm(x: float) -> float:
    return x % 360.0

def sign_of(longitude: float) -> tuple[str, float, int]:
    lon = deg_norm(longitude)
    idx = int(lon // 30)
    return SIGNS[idx], lon % 30, idx

def nakshatra_of(longitude: float) -> tuple[str, int, str, float]:
    segment = 360 / 27
    pada_segment = segment / 4
    lon = deg_norm(longitude)
    idx = int(lon // segment)
    rem = lon - idx * segment
    pada = min(4, int(rem // pada_segment) + 1)
    return NAKSHATRAS[idx], pada, NAK_LORDS[idx], rem / segment

@st.cache_data(show_spinner=False, ttl=86400)
def geocode_place(place: str) -> GeoResult:
    geolocator = Nominatim(user_agent="astrovani-career-kundali")
    loc = geolocator.geocode(place, exactly_one=True, timeout=10)
    if not loc:
        raise ValueError("Place not found. Try a more specific city/state/country.")
    tz = TimezoneFinder().timezone_at(lat=loc.latitude, lng=loc.longitude)
    if not tz:
        raise ValueError("Could not determine the timezone for this place.")
    return GeoResult(loc.latitude, loc.longitude, tz, loc.address)

def local_to_utc(birth_date: date, birth_time, timezone_name: str) -> datetime:
    local_dt = datetime.combine(birth_date, birth_time).replace(tzinfo=ZoneInfo(timezone_name))
    return local_dt.astimezone(ZoneInfo("UTC"))

def julian_day(utc_dt: datetime) -> float:
    hour = utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour, swe.GREG_CAL)

def calculate_chart(utc_dt: datetime, lat: float, lon: float) -> dict:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = julian_day(utc_dt)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    planets = {}
    for name, pcode in PLANETS.items():
        pos = swe.calc_ut(jd, pcode, flags)[0][0]
        planets[name] = deg_norm(pos)
    planets["Ketu"] = deg_norm(planets["Rahu"] + 180)
    _, ascmc = swe.houses_ex(jd, lat, lon, b"P", swe.FLG_SIDEREAL)
    asc = deg_norm(ascmc[0])
    asc_sign, asc_deg, asc_idx = sign_of(asc)
    pdata = {}
    for name, plon in planets.items():
        sign, degree, sidx = sign_of(plon)
        house = ((sidx - asc_idx) % 12) + 1
        pdata[name] = {
            "longitude": round(plon, 4),
            "sign": sign,
            "degree": round(degree, 2),
            "house": house,
        }
    moon_nak, moon_pada, nak_lord, nak_fraction = nakshatra_of(planets["Moon"])
    return {
        "julian_day": jd,
        "ascendant": {"longitude": round(asc, 4), "sign": asc_sign, "degree": round(asc_deg, 2)},
        "planets": pdata,
        "moon_nakshatra": {"name": moon_nak, "pada": moon_pada, "lord": nak_lord, "fraction_elapsed": nak_fraction},
    }

def add_years_fraction(dt: datetime, years: float) -> datetime:
    return dt + timedelta(days=years * 365.2425)

def dasha_timeline(birth_utc: datetime, moon_longitude: float, years_ahead: float = 120) -> list[dict]:
    _, _, lord, frac_elapsed = nakshatra_of(moon_longitude)
    start_idx = DASHA_SEQUENCE.index(lord)
    lord_years = DASHA_YEARS[lord]
    md_start = add_years_fraction(birth_utc, -(frac_elapsed * lord_years))
    timeline = []
    cur = md_start
    total = 0.0
    i = 0
    while total < years_ahead + 30:
        d_lord = DASHA_SEQUENCE[(start_idx + i) % 9]
        yrs = DASHA_YEARS[d_lord]
        end = add_years_fraction(cur, yrs)
        timeline.append({"lord": d_lord, "start": cur, "end": end, "years": yrs})
        cur = end
        total += yrs
        i += 1
    return timeline

def current_dasha(chart: dict, birth_utc: datetime, at: datetime | None = None) -> dict:
    at = at or datetime.now(tz=ZoneInfo("UTC"))
    moon_long = chart["planets"]["Moon"]["longitude"]
    timeline = dasha_timeline(birth_utc, moon_long)
    md = next((x for x in timeline if x["start"] <= at < x["end"]), timeline[-1])
    seq_start = DASHA_SEQUENCE.index(md["lord"])
    cur = md["start"]
    antars = []
    for i in range(9):
        ad_lord = DASHA_SEQUENCE[(seq_start + i) % 9]
        years = md["years"] * DASHA_YEARS[ad_lord] / 120.0
        end = add_years_fraction(cur, years)
        antars.append({"lord": ad_lord, "start": cur, "end": end})
        cur = end
    ad = next((x for x in antars if x["start"] <= at < x["end"]), antars[-1])
    return {"mahadasha": md, "antardasha": ad}

def career_report(chart: dict, dasha: dict) -> dict:
    asc_sign = chart["ascendant"]["sign"]
    tenth_sign = SIGNS[(SIGNS.index(asc_sign) + 9) % 12]
    tenth_lord = SIGN_LORD[tenth_sign]
    tenth_lord_house = chart["planets"][tenth_lord]["house"]
    archetypes = {
        "Aries": "initiative, competition, action, entrepreneurship and roles that reward decisiveness",
        "Taurus": "stability, finance, design, resources, quality and patient value creation",
        "Gemini": "communication, analysis, technology, sales, writing and multi-disciplinary work",
        "Cancer": "care, public-facing responsibility, hospitality, people support and community-oriented work",
        "Leo": "leadership, visibility, ownership, management, creativity and positions of responsibility",
        "Virgo": "analysis, systems, health, operations, quality control and detail-oriented problem solving",
        "Libra": "partnerships, negotiation, consulting, design, law, client management and diplomacy",
        "Scorpio": "research, investigation, transformation, risk, security, medicine and deep technical work",
        "Sagittarius": "teaching, advisory work, law, travel, strategy, publishing and knowledge-led careers",
        "Capricorn": "structured organizations, management, engineering, administration and long-term execution",
        "Aquarius": "technology, networks, innovation, large systems, social impact and unconventional paths",
        "Pisces": "creative, advisory, healing, research, spiritual or imaginative work requiring intuition",
    }
    house_meaning = {
        1: "Career tends to become closely tied to your personal identity, independence and self-direction.",
        2: "Career growth is often linked with income, speech, family assets, finance or building tangible value.",
        3: "Self-effort, communication, technology, media, sales or entrepreneurial initiative can become important.",
        4: "Work may connect strongly with education, property, public service, home-based work or creating stability.",
        5: "Creativity, intelligence, teaching, leadership, product thinking or speculative ideas may feature strongly.",
        6: "Service, competition, operations, problem-solving and overcoming difficult situations can shape your career.",
        7: "Clients, partnerships, consulting, business and public-facing work can become central to professional growth.",
        8: "Research, transformation, risk, finance, security, investigation or complex hidden systems may attract you.",
        9: "Higher learning, mentoring, travel, global work, advisory roles or values-driven work can support growth.",
        10: "This is a strong career-centered placement: responsibility, visibility and professional achievement may dominate life priorities.",
        11: "Networks, large organizations, technology, communities and long-term gains may be important career channels.",
        12: "Foreign links, remote work, research, institutions or behind-the-scenes roles may be significant.",
    }
    md = dasha["mahadasha"]["lord"]
    ad = dasha["antardasha"]["lord"]
    period_tones = {
        "Sun": "visibility, authority, confidence and responsibility",
        "Moon": "adaptability, people matters, emotional priorities and changing circumstances",
        "Mars": "action, competition, courage, technical execution and impatience if poorly channelled",
        "Mercury": "learning, communication, analytics, business and networking",
        "Jupiter": "expansion, mentors, knowledge, judgment and long-term growth",
        "Venus": "relationships, creativity, comfort, diplomacy and commercial value",
        "Saturn": "discipline, responsibility, delay followed by durable progress and mature decision-making",
        "Rahu": "ambition, unconventional opportunities, foreign/technology themes and sudden changes",
        "Ketu": "specialization, detachment, internal reassessment and non-linear shifts",
    }
    saturn = chart["planets"]["Saturn"]
    mercury = chart["planets"]["Mercury"]
    jupiter = chart["planets"]["Jupiter"]
    sun = chart["planets"]["Sun"]
    strengths = []
    if mercury["house"] in {1, 2, 3, 5, 6, 10, 11}:
        strengths.append("communication, analytics and structured problem solving")
    if saturn["house"] in {3, 6, 10, 11}:
        strengths.append("persistence, process discipline and long-horizon execution")
    if jupiter["house"] in {1, 2, 5, 9, 10, 11}:
        strengths.append("learning, mentoring, judgment and strategic thinking")
    if sun["house"] in {1, 5, 9, 10, 11}:
        strengths.append("ownership, visibility and leadership")
    if not strengths:
        strengths.append("adaptability and the ability to build expertise through experience")
    return {
        "career_axis": f"Your 10th house is {tenth_sign}, traditionally associated with {archetypes[tenth_sign]}.",
        "tenth_lord": f"The 10th lord is {tenth_lord}, placed in house {tenth_lord_house}. {house_meaning[tenth_lord_house]}",
        "strengths": strengths,
        "current_period": f"You are currently in {md} Mahadasha and {ad} Antardasha. Traditionally this emphasizes {period_tones[md]}, with a secondary influence of {period_tones[ad]}.",
        "guidance": "Use the chart as a reflection tool: compare these themes with your actual skills, experience and opportunities before making career decisions.",
    }

def fmt_dt(dt: datetime) -> str:
    return dt.astimezone(ZoneInfo("UTC")).strftime("%d %b %Y")

st.title("🔮 AstroVani Career Kundali")
st.caption("A Vedic astrology career-reflection tool using sidereal calculations (Lahiri ayanamsa).")

with st.form("birth_form"):
    name = st.text_input("Name", placeholder="Your name")
    birth_date = st.date_input("Date of birth", min_value=date(1900, 1, 1), max_value=date.today())
    birth_time = st.time_input("Exact birth time")
    birth_place = st.text_input("Birth place", placeholder="e.g. Chennai, Tamil Nadu, India")
    submitted = st.form_submit_button("Generate Career Kundali", use_container_width=True)

if submitted:
    if not birth_place.strip():
        st.error("Please enter the birth place.")
        st.stop()
    try:
        with st.spinner("Calculating your chart..."):
            geo = geocode_place(birth_place.strip())
            birth_utc = local_to_utc(birth_date, birth_time, geo.timezone)
            chart = calculate_chart(birth_utc, geo.latitude, geo.longitude)
            dasha = current_dasha(chart, birth_utc)
            report = career_report(chart, dasha)
    except Exception as e:
        st.error(f"Could not generate the report: {e}")
        st.stop()
    st.success(f"Career Kundali generated{f' for {name}' if name else ''}.")
    st.caption(f"Resolved place: {geo.display_name} • Timezone: {geo.timezone}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ascendant", chart["ascendant"]["sign"])
    c2.metric("Moon sign", chart["planets"]["Moon"]["sign"])
    c3.metric("Nakshatra", f"{chart['moon_nakshatra']['name']} P{chart['moon_nakshatra']['pada']}")
    st.subheader("Career interpretation")
    st.write(report["career_axis"])
    st.write(report["tenth_lord"])
    st.markdown("**Likely strengths**")
    for x in report["strengths"]:
        st.write(f"• {x.capitalize()}")
    st.write(report["current_period"])
    st.info(report["guidance"])
    st.subheader("Current Dasha")
    md = dasha["mahadasha"]
    ad = dasha["antardasha"]
    st.write(f"**Mahadasha:** {md['lord']} ({fmt_dt(md['start'])} – {fmt_dt(md['end'])})")
    st.write(f"**Antardasha:** {ad['lord']} ({fmt_dt(ad['start'])} – {fmt_dt(ad['end'])})")
    st.subheader("Planetary placements")
    rows = []
    for p, info in chart["planets"].items():
        rows.append({"Planet": p, "Sign": info["sign"], "Degree": info["degree"], "House": info["house"]})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.divider()
    st.caption("For reflection and entertainment only. Astrology is not scientifically established and this tool should not replace professional career, financial, medical or legal advice.")
