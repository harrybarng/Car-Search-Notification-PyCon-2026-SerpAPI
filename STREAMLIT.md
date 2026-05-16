# STREAMLIT.md — Car Price Comparison & Alert App

---

## Changelog

All requirement additions and changes are recorded here. Newest entries at the top.

| Date | Version | Change Summary |
|---|---|---|
| 2026-05-14 | 1.5.0 | Added distance search and pagination. Criterion now has `zip_code` (optional 5-digit) and `radius_miles` (default 50, range 10–500). When a zip code is set, "near {zip}" is appended to the Google query and `location={zip_code}` is passed to SerpAPI to bias results geographically. Settings now has `pages_per_search` (default 1, range 1–5): each page fetches 10 results (1 SerpAPI call); pages are paginated via SerpAPI's `start` param and deduplicated by URL. Pages per search control added to Settings UI with auto-save. storage.py defaults updated to include `pages_per_search: 1`. |
| 2026-05-15 | 1.8.0 | Search optimization and call estimate. `run_search` now groups criteria by (zip, make, model) — criteria sharing the same make/model pair use one set of dealer searches and share the result set, then each criterion's filters (trim/price/year/mileage) are applied independently. Home page shows a compact call estimate below the Run Search button: live calls, cached dealer searches, and a per-group breakdown (e.g. "3 live calls + 2 cached · Audi A4 × 3 dealers, Audi Q5 × 2 dealers"). Warnings surface criteria with no zip or no discovered dealers without needing to run a search. `is_cache_fresh(key, ttl_hours)` added to cache.py for lightweight cache status checks without loading result data. |
| 2026-05-15 | 1.7.0 | Replaced two-phase organic+dealer search with a pure dealer-based search. Added 🏪 Dealers sidebar page: shows all (zip, make) pairs from saved criteria, with a "Discover Dealers" button per pair that calls SerpAPI google_maps engine and permanently stores results in `data/dealers.json` (keyed by `{zip}_{make}`, no TTL — refreshed only on explicit re-discovery, costs 1 API call). Search now skips Phase 1 organic search entirely; `run_search` loads stored dealers for each criterion's (zip_code, make), runs one `site:{domain}` search per dealer (with TTL-cached results), and filters all results against the criterion. `Dealer` model added to `models.py`. `services/dealers.py` created. `data/dealers.json` added to `ensure_data_files`. Debug file updated to dealer-mode format. Criteria without a zip code or without discovered dealers produce a warning instead of silently failing. |
| 2026-05-15 | 1.6.0 | Two-phase local dealer search. Phase 1 broad organic search extracts local dealer domains from `local_results["places"]` (Google Maps pack). Phase 2 issues up to 3 `site:{dealer_domain} "{make} {model}" used` searches, one per dealer, to surface individual inventory pages from local dealers. Dealer domains are passed to `filter_results_for_criterion` as `extra_domains` and added to the URL allowlist alongside the known national platforms. Debug file now includes `dealer_domains_found`. `_fetch_for_criterion` return signature changed to `(results, dealer_domains, error)`. |
| 2026-05-15 | 1.5.1 | Switched URL filter from path-pattern matching (`/inventory/`, `/listing/`) to domain allowlisting (`_CAR_PLATFORMS`). Removed HEAD-request liveness check (`_is_listing_live`) — dealer sites redirect harmlessly, causing all results to be rejected. Kept snippet-based sold detection (`_SOLD_RE`). Reverted SerpAPI engine back to `google` with simple query `used {make} {model} {trim} for sale` + `location={zip_code}` for geographic bias. |
| 2026-05-15 | 1.4.0 | Added mock mode (zero API calls, realistic fake listings) and result cache with configurable TTL. Search priority: mock → cache hit → live API. Added ⚙️ Settings sidebar page exposing: mock mode toggle, cache TTL input, cache status + clear button, Pushover credentials. Home page shows an inline info banner when mock mode is active. Cache files stored in data/cache/ (gitignored). Settings model updated with mock_mode (default: true) and cache_ttl_hours (default: 1). |
| 2026-05-15 | 1.3.0 | Switched SerpAPI engine from `google` (organic results) to `google_shopping` (car marketplace listings). Fixed result key from `organic_results` to `shopping_results`. Updated filter engine to use `extracted_price` (pre-parsed float) instead of regex price parsing. Added smart API-level price pre-filtering: computes widest price range across all criteria for a make/model pair and passes `min_price`/`max_price` to the API, with local filter narrowing per criterion. Added `ensure_data_files()` in storage.py — runs at every startup and creates missing data directory and JSON files with safe defaults, so new users cloning the repo never need to manually create data files. Added `data/criteria.json`, `data/matches.json`, `data/schedule.json` to `.gitignore` — all four data files are now excluded from git and auto-created on first run. |
| 2026-05-14 | 1.2.0 | Renamed `pages/` to `views/` to prevent Streamlit from auto-generating its own sidebar navigation from the folder, which was showing duplicate/wrong nav items ("app", "home", "criteria"). Custom sidebar nav in `app.py` is the sole navigation control. |
| 2026-05-14 | 1.1.0 | Search button and schedule widget are now fully disabled (not just guarded in code) when no criteria are saved. Three enforcement layers: UI button disabled, schedule widget fields/toggle/save disabled, background scheduler job exits early before any API call. |
| 2026-05-14 | 1.0.0 | Initial spec created from interview. Covers purpose, pages (Home + Search Criteria), JSON storage schemas, SerpAPI batching strategy, local filter engine, Pushover + in-app badge notifications, APScheduler daily scheduling with configurable buffer window, teal/gray color system, atomic design component inventory, project structure, Python/security best practices, and v1 out-of-scope items. |

### How to Use This Changelog

Whenever a requirement is added, removed, or changed during development, a new row is prepended to the table above and the relevant section(s) below are updated in place. Each entry records the date, a bumped version number, and a plain-English summary of exactly what changed and why — so the file always reflects the current intended behavior with full traceability.

---

## 1. Purpose & User

A personal-use Streamlit app that monitors car listings across the web, compares them against saved search criteria, and alerts the owner when a matching deal appears. Designed for a single user — no authentication or multi-user support.

---

## 2. Pages & Navigation

Sidebar navigation with two pages:

| Sidebar Label | Route Key | Description |
|---|---|---|
| 🏠 Home | `home` | Recent matches + manual search trigger + schedule config |
| 🔍 Search Criteria | `criteria` | CRUD interface for saved search criteria |

### 2.1 Home Page

- **Recent Matches panel** — displays cached results sorted by timestamp (newest first). Each match card shows: make/model/trim, price, year, mileage, match timestamp, and a direct link to the listing.
- **Search Controls row** (below the header, above results):
  - `[Run Search Now]` — teal CTA button; triggers a batch search across all saved criteria.
  - `[Schedule]` — inline schedule config (see §6).
- **Empty state** — if no matches yet, show a neutral gray placeholder with a prompt to add criteria or run a search.

### 2.2 Search Criteria Page

- List of all saved criteria as cards.
- `[+ Add Criteria]` — teal CTA button opens a form (drawer or modal).
- Each card has `[Edit]` and `[Delete]` actions.
- **Criteria form fields:**

| Field | Type | Notes |
|---|---|---|
| Make | Text input | e.g. "Audi" |
| Model | Text input | e.g. "A4" |
| Trim Level | Text input | Optional; e.g. "Premium Plus" |
| Min Price | Number input | USD |
| Max Price | Number input | USD |
| Min Year | Number input | 4-digit year |
| Max Year | Number input | 4-digit year |
| Min Mileage | Number input | Miles |
| Max Mileage | Number input | Miles |

---

## 3. Data Layer

### 3.1 Storage Format

All persistence is via JSON files on local disk. No database.

```
data/
  criteria.json       # list of search criteria objects
  matches.json        # list of cached match results
  schedule.json       # single schedule config object
  settings.json       # app settings (buffer window, Pushover keys, etc.)
```

### 3.2 Schemas

**Criterion object** (`criteria.json` is a list of these):
```json
{
  "id": "uuid4-string",
  "make": "Audi",
  "model": "A4",
  "trim": "Premium Plus",
  "price_min": 20000,
  "price_max": 35000,
  "year_min": 2019,
  "year_max": 2022,
  "mileage_min": 0,
  "mileage_max": 60000,
  "created_at": "2026-01-01T10:00:00Z",
  "updated_at": "2026-01-01T10:00:00Z"
}
```

**Match object** (`matches.json` is a list of these):
```json
{
  "id": "uuid4-string",
  "criterion_id": "uuid4-string",
  "make": "Audi",
  "model": "A4",
  "trim": "Premium Plus",
  "price": 28500,
  "year": 2021,
  "mileage": 34000,
  "listing_url": "https://...",
  "source": "craigslist",
  "found_at": "2026-01-01T08:05:00Z",
  "notified": true
}
```

**Schedule object** (`schedule.json`):
```json
{
  "enabled": true,
  "run_at": "08:00",
  "buffer_hours": 1,
  "last_run_at": "2026-01-01T08:00:00Z"
}
```

**Settings object** (`settings.json`):
```json
{
  "pushover_user_key": "",
  "pushover_api_token": "",
  "notifications_enabled": false
}
```

> **Security note:** `settings.json` holds API keys and must never be committed to version control. Add it to `.gitignore`. At startup, validate file permissions (readable only by owner). Consider using `python-dotenv` or OS keychain via `keyring` as a more secure alternative for storing secrets.

---

## 4. Search & Filtering Strategy

### 4.1 API Calls Budget

SerpAPI limit: **250 calls/month**. The app must be conservative.

### 4.2 Batching Logic

Search is grouped by **Make + Model only** — not by trim, year, price, or mileage. This means one SerpAPI call per unique Make+Model pair across all saved criteria, regardless of how many criteria share that pair.

**Example:** If the user has three criteria all for "Audi A4" (different trims/years), only **one** SerpAPI call is made for "Audi A4 for sale". Local filtering then applies all three criteria to the returned results.

**De-duplication algorithm before calling API:**
1. Load all criteria.
2. Extract unique `(make, model)` tuples.
3. For each unique tuple, build one query string and make one API call.
4. Pass the full result set to the local filter engine.

### 4.3 Local Filter Engine

After fetching raw listings for a `(make, model)` pair, apply each matching criterion:

1. **Trim match** — if criterion has a trim, check if the listing title/description contains the trim string (case-insensitive, partial match allowed).
2. **Year** — parse year from listing; check `year_min <= year <= year_max`.
3. **Price** — parse price; check `price_min <= price <= price_max`.
4. **Mileage** — parse mileage; check `mileage_min <= mileage <= mileage_max`.

A listing must pass **all** populated filters to be counted as a match.

### 4.4 Deduplication of Results

Before saving a match, check if a listing URL already exists in `matches.json`. If yes, skip — do not store duplicates or re-notify.

### 4.5 SerpAPI Query Construction

Query format:
```
"{make} {model} for sale near me"
```
Use SerpAPI's Google Shopping or Google Search engine. Parse structured fields (price, year, mileage) from result snippets using regex patterns with fallback heuristics. Log unparseable fields rather than silently dropping listings.

---

## 5. Notifications

### 5.1 Pushover (Primary)

When new matches are found after a search run:
1. Check `settings.json` for `pushover_user_key` and `pushover_api_token`.
2. If both are present and `notifications_enabled` is true, send one Pushover notification per new match batch (not one per listing — group them to avoid spamming).
3. Message format: `"3 new matches found: Audi A4, BMW 3 Series. Tap to open app."`

Pushover API call must be made over HTTPS only. Never log API keys.

### 5.2 In-App Badge (Fallback / Always Shown)

- A teal badge in the sidebar next to "🏠 Home" showing the count of new (unread) matches.
- Matches are marked as "read" when the user views the Home page.
- If Pushover is not configured, show a persistent info banner on Home guiding the user to set it up in Settings.

### 5.3 Settings Page (Lightweight)

Add a third sidebar item **⚙️ Settings** (lower priority, can be added in v2) for entering Pushover credentials and toggling notifications. For v1, credentials can be set via `settings.json` directly.

---

## 6. Scheduling

### 6.1 Configuration

Displayed inline on the Home page next to the Search button. Fields:
- **Run at** — time picker (HH:MM, 24h).
- **Buffer window** — number input (hours, default 1). Label: "Skip scheduled run if manually searched within X hours."
- `[Save Schedule]` button — teal.
- Toggle: `[Enable / Disable]` schedule.

### 6.2 Skip Logic

Before the scheduled run executes:
1. Read `schedule.last_run_at`.
2. If `now - last_run_at < buffer_hours`, skip the scheduled run and log the skip reason.
3. If a manual search is run, always update `last_run_at` to `now`.

### 6.3 Scheduler Implementation

Use `APScheduler` (BackgroundScheduler) started at app boot inside `streamlit`'s session state guard:

```python
if "scheduler_started" not in st.session_state:
    start_scheduler()
    st.session_state["scheduler_started"] = True
```

The scheduler fires the same search function used by the manual button. No separate cron job or OS-level task needed.

---

## 7. Styling & Theme

### 7.1 Color Palette

| Role | Color | Hex |
|---|---|---|
| Accent / CTA | Teal | `#009688` |
| Accent hover | Dark Teal | `#00796B` |
| Background | White | `#FFFFFF` |
| Surface / Card | Light Gray | `#F5F5F5` |
| Border | Medium Gray | `#E0E0E0` |
| Body text | Dark Gray | `#212121` |
| Secondary text | Medium Gray | `#757575` |
| Success indicator | Green | `#4CAF50` |
| Warning indicator | Amber | `#FFC107` |
| Error indicator | Red | `#F44336` |

> Red, amber, and green are **reserved exclusively** for success/warning/error states. They must not appear anywhere else in the UI (buttons, backgrounds, accents, charts).

### 7.2 Theme Config

`/.streamlit/config.toml`:
```toml
[theme]
base = "light"
primaryColor = "#009688"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F5F5"
textColor = "#212121"
font = "sans serif"
```

### 7.3 Atomic Design & Reusable Widgets

The app follows **Atomic Design** principles. All UI components live in `components/`. Before building any new UI element:

1. **Scan `components/` first** — check if a valid component already exists.
2. **Ask before creating** — if a new reusable widget is needed, confirm before writing it.
3. **Never duplicate** — if a component exists, use it. Do not inline equivalent markup elsewhere.

Planned atoms and molecules:

| Component | File | Description |
|---|---|---|
| `Badge` | `components/badge.py` | Teal count badge for sidebar |
| `CTAButton` | `components/cta_button.py` | Teal primary action button |
| `StatusIndicator` | `components/status_indicator.py` | Red/yellow/green dot + label |
| `MatchCard` | `components/match_card.py` | Single result card with link |
| `CriteriaCard` | `components/criteria_card.py` | Saved criteria display card |
| `CriteriaForm` | `components/criteria_form.py` | Add/edit form for one criterion |
| `ScheduleWidget` | `components/schedule_widget.py` | Inline schedule config row |
| `EmptyState` | `components/empty_state.py` | Neutral placeholder for empty lists |
| `SectionHeader` | `components/section_header.py` | Consistent page/section title |

---

## 8. Project Structure

```
car-search-notification/
├── .streamlit/
│   └── config.toml
├── components/           # Atomic reusable widgets
│   ├── badge.py
│   ├── cta_button.py
│   ├── status_indicator.py
│   ├── match_card.py
│   ├── criteria_card.py
│   ├── criteria_form.py
│   ├── schedule_widget.py
│   ├── empty_state.py
│   └── section_header.py
├── data/                 # JSON persistence (gitignored except schema examples)
│   ├── criteria.json
│   ├── matches.json
│   ├── schedule.json
│   └── settings.json
├── views/
│   ├── home.py
│   └── criteria.py
├── services/
│   ├── search.py         # SerpAPI integration & batching logic
│   ├── filter.py         # Local filter engine
│   ├── notify.py         # Pushover + in-app badge
│   ├── scheduler.py      # APScheduler setup
│   └── storage.py        # JSON read/write helpers
├── app.py                # Entry point, sidebar nav, scheduler boot
├── requirements.txt
├── .gitignore            # Must include data/settings.json
└── STREAMLIT.md          # This file
```

---

## 9. Python Best Practices & Security

- **Python 3.11+**. Use `pyproject.toml` or `requirements.txt` with pinned versions.
- **Type hints** on all function signatures. Use `pydantic` v2 models for all JSON schema objects (Criterion, Match, Schedule, Settings) — validates data on load and prevents silent corruption.
- **Secrets never in code or committed files.** `settings.json` is gitignored. Provide `settings.example.json` with empty strings as a template.
- **File I/O safety.** Use `filelock` for all JSON reads/writes to prevent race conditions between the scheduler and the UI thread.
- **HTTPS only.** All outbound requests (SerpAPI, Pushover) use HTTPS. Validate SSL certificates (default in `requests` / `httpx`).
- **No `eval` or dynamic code execution** anywhere in the codebase.
- **Input sanitization.** Strip and validate all user inputs before writing to JSON or building query strings.
- **Error boundaries.** Network calls (SerpAPI, Pushover) are wrapped in try/except with user-visible error messages via `StatusIndicator` (red). Never crash the UI on API failure.
- **Logging.** Use Python's `logging` module (not `print`). Log to a rotating file (`logs/app.log`). Never log API keys or user data.
- **Dependency audit.** Run `pip-audit` before shipping to check for known vulnerabilities in dependencies.

---

## 10. Key Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | UI framework |
| `google-search-results` | SerpAPI Python client |
| `apscheduler` | Background scheduler |
| `pydantic` | Data validation & JSON schema |
| `requests` or `httpx` | HTTP client for Pushover |
| `filelock` | Safe concurrent file access |
| `python-dateutil` | Date/time parsing |
| `pip-audit` | Dependency vulnerability scanning |

---

## 11. Out of Scope (v1)

- Multi-user support or authentication
- Cloud database
- Email notifications
- Per-criteria scheduling
- Mobile-responsive layout customization
- Historical price trend charts
