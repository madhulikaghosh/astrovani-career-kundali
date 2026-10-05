# AstroVani Career Kundali

A small Streamlit MVP that accepts birth date, exact birth time, and birth place, then calculates a sidereal Vedic chart (Lahiri ayanamsa) and generates a deterministic career-focused interpretation.

## Features

- Birth-place geocoding
- Time-zone resolution using geographic coordinates
- Sidereal planetary positions via Swiss Ephemeris
- Lahiri ayanamsa
- Ascendant
- Whole-sign houses
- Moon sign, nakshatra and pada
- Vimshottari Mahadasha + Antardasha
- Career-focused interpretation based on the 10th house/lord and major career indicators
- No AI API key required

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Railway

Start command:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

## Important notes

- This MVP uses OpenStreetMap/Nominatim for place geocoding; production use should use a provider whose usage policy fits your traffic.
- `pyswisseph` / Swiss Ephemeris has licensing terms that should be reviewed before commercial deployment.
- Whole-sign houses are used for the career interpretation.
- Validate outputs against trusted astrology software before selling reports.
- Astrology is not scientifically established; keep user-facing claims framed as reflection rather than guaranteed prediction.
