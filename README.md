# 🚗 Car Search Alerts

A personal Streamlit app that monitors **used car listings at local dealerships** and notifies you when a match appears — built with the [SerpApi Python SDK](https://serpapi.com/integrations/python).

**[▶ Live Demo](https://car-search-notification-pycon-2026-serpapi-vg8fskug2fxgzmqfhku.streamlit.app/)**

---

## What It Does

Most car-search tools only check national platforms like AutoTrader or CarGurus. This app goes a step further:

1. **Discovers local dealers** — uses SerpApi's Google Maps engine to find all dealerships of a given make near your zip code.
2. **Searches dealer inventory** — runs two searches per dealer:
   - `site:{dealer-domain}` — finds vehicle pages Google has indexed on the dealer's own site
   - `"{Dealer Name}" {Make} {Model} used for sale` — finds that dealer's listings on AutoTrader, CarGurus, etc.
3. **Filters intelligently** — blocks parts/service pages, new-car listings, browse pages, and wrong-model results. Fetches each candidate URL to confirm the vehicle is still available.
4. **Notifies you** — new matches appear in the app, and optionally sends a push notification to your phone via Pushover.

---

## SerpApi Usage

This app uses two SerpApi engines via the official Python SDK (`pip install serpapi`):

| Engine | Purpose | When |
|---|---|---|
| `google_maps` | Find all dealerships of a make near a zip code | 🏪 Dealers → "Discover" — 1 call, stored permanently |
| `google` | Search each dealer's inventory (site: + platform name) | Run Search — 2 calls per dealer, cached with TTL |

---

## Screenshots

### 🏠 Home — Recent Matches
Matches sorted newest-first with year, mileage, source, and a direct link to the listing.

![Recent Matches](docs/screenshot-home.png)

---

## How to Use

**Step 1 — Add a search criterion**
Go to 🔍 **Search Criteria** → **+ Add Criteria**. Set make, model, and zip code. Price, year, and mileage ranges are optional.

**Step 2 — Discover local dealers**
Go to 🏪 **Dealers** → click **Discover [Make] Dealers**. Finds all dealerships near your zip using Google Maps. Only needs to be done once.

**Step 3 — Run a search**
Go to 🏠 **Home** → click **Run Search Now**. Results appear as cards with a direct link to each listing.

**Step 4 — Schedule it** *(optional)*
Open the ⏰ Schedule panel on the Home page to run searches automatically at a set daily time.

---

## Streamlit Cloud Deployment

1. Fork this repo and go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your repo, set main file to `app.py`
3. Under **Advanced settings → Secrets**, add:
   ```toml
   SERPAPI_KEY = "your_key_here"
   ```
4. Deploy, then follow the **How to Use** steps above

---

## Local Setup

```bash
git clone https://github.com/harrybarng/Car-Search-Notification-PyCon-2026-SerpAPI.git
cd Car-Search-Notification-PyCon-2026-SerpAPI
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your SERPAPI_KEY to .env
streamlit run app.py
```

Get your free SerpApi key at [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key) (250 searches/month free).

---

## Project Structure

```
├── app.py                    # Entry point
├── components/               # Reusable UI widgets
├── views/                    # Page views (home, criteria, dealers, settings)
├── services/
│   ├── dealers.py            # Google Maps dealer discovery
│   ├── search.py             # SerpApi search + caching
│   ├── filter.py             # Result filtering + availability check
│   ├── models.py             # Pydantic models
│   └── storage.py            # JSON persistence
└── data/                     # Auto-created on first run (gitignored)
```

---

## Prerequisites

- Python 3.11+
- [SerpApi account](https://serpapi.com/users/sign_up) — free tier includes 250 searches/month
- [Pushover](https://pushover.net/) *(optional)* — for phone notifications
