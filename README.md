# Yad2 Apartment Search

A full-stack web application that scrapes apartment listings from [Yad2.co.il](https://www.yad2.co.il) (Israel's largest real estate platform), stores them locally, and provides a modern dashboard for filtering and browsing results.

## Features

- **Automated Scraping** — Browser-based scraping with Playwright, including login handling and anti-bot measures
- **Smart Filtering** — Filter by city, rooms, price, size, floor, and amenities (elevator, parking, balcony, A/C, mamad, furnished, pets)
- **Two View Modes** — Grid view (card layout) and list view (table)
- **Sorting** — Sort by date, price, rooms, or size
- **Pagination** — Browse results 50 at a time
- **Persistent Storage** — SQLite database with upsert logic to avoid duplicates
- **RTL Hebrew Support** — Right-to-left layout with Hebrew city autocomplete
- **Rate Limiting** — Random delays between requests to avoid detection

## Architecture

```
yad2-apartment-search/
├── main.py                     # Entry point
├── requirements.txt
├── .env                        # Credentials (not committed)
├── data/
│   ├── cities.json             # City name → Yad2 code mapping
│   └── listings.db             # SQLite database (created at runtime)
├── browser_data/               # Persistent Chromium profile
├── config/
│   ├── settings.py             # Pydantic settings from .env
│   └── constants.py            # URLs, CSS selectors, feature mappings
├── models/
│   ├── listing.py              # ApartmentListing model
│   └── search_params.py        # SearchFilters model
├── database/
│   ├── db.py                   # Database class + schema
│   └── queries.py              # Dynamic SQL filter builder
├── scraper/
│   ├── browser.py              # Playwright browser manager
│   ├── auth.py                 # Yad2 login handler
│   ├── search.py               # Search execution + pagination
│   ├── extractor.py            # HTML parsing + data extraction
│   └── rate_limiter.py         # Anti-bot delay logic
└── web/
    ├── app.py                  # Flask app factory
    ├── routes.py               # API endpoints
    ├── templates/
    │   └── dashboard.html      # Main UI
    └── static/
        ├── css/style.css       # Soft Bento design system
        └── js/app.js           # Client-side logic
```

## How It Works

### Scraping Flow

1. User submits search filters via the web UI
2. Backend spawns an async thread with a threading lock (one scrape at a time)
3. Playwright launches a Chromium browser with a persistent context
4. Authenticates with Yad2 if needed (email/password login)
5. Navigates to the search URL built from filters
6. For each page (up to `MAX_PAGES_PER_SEARCH`):
   - Waits a random 2–5 second delay
   - Extracts all listing cards from the page HTML
   - Parses price, rooms, floor, size, address, features, and images
   - Clicks through to the next page
7. Deduplicates by `listing_id` and upserts into SQLite
8. Reports progress back to the UI via polling

### Query Flow

1. User applies filters on the dashboard (city name, rooms, price, etc.)
2. Frontend calls `GET /api/results` with filter parameters
3. Backend dynamically builds a SQL `WHERE` clause
4. Returns paginated results as JSON
5. Frontend renders the grid or list view

## API Endpoints

| Endpoint             | Method | Description                          |
|----------------------|--------|--------------------------------------|
| `/`                  | GET    | Serve the dashboard                  |
| `/api/search`        | POST   | Start a scraping job (async)         |
| `/api/status`        | GET    | Poll scraping progress               |
| `/api/results`       | GET    | Query stored listings with filters   |
| `/api/filters/cities`| GET    | Get city name → code mapping         |

### `POST /api/search`

Accepts JSON body with optional filters:

```json
{
  "city": "5000",
  "rooms_min": 2,
  "rooms_max": 4,
  "price_min": 3000,
  "price_max": 8000
}
```

Returns `409` if a scrape is already running.

### `GET /api/results`

Query parameters:

| Param       | Type    | Description                     |
|-------------|---------|---------------------------------|
| `city`      | string  | City name (partial match)       |
| `rooms_min` | float   | Minimum rooms                   |
| `rooms_max` | float   | Maximum rooms                   |
| `price_min` | int     | Minimum price (ILS)             |
| `price_max` | int     | Maximum price (ILS)             |
| `size_min`  | int     | Minimum size (sqm)              |
| `size_max`  | int     | Maximum size (sqm)              |
| `floor_min` | int     | Minimum floor                   |
| `floor_max` | int     | Maximum floor                   |
| `has_elevator`, `has_parking`, `has_balcony`, `has_ac`, `is_furnished`, `pets_allowed`, `has_mamad` | bool | Amenity filters |
| `sort_by`   | string  | `date_scraped`, `price`, `rooms`, `size_sqm` |
| `sort_order` | string | `ASC` or `DESC`                 |
| `page`      | int     | Page number (default 1)         |
| `per_page`  | int     | Results per page (default 50)   |

## Database Schema

SQLite table `listings`:

| Column          | Type    | Description                        |
|-----------------|---------|------------------------------------|
| `listing_id`    | TEXT PK | Yad2 listing ID                    |
| `url`           | TEXT    | Direct link to listing             |
| `price`         | INTEGER | Monthly rent in ILS                |
| `rooms`         | REAL    | Number of rooms (e.g. 3.5)         |
| `size_sqm`      | INTEGER | Apartment size in square meters    |
| `floor`         | INTEGER | Floor number                       |
| `total_floors`  | INTEGER | Total floors in building           |
| `city`          | TEXT    | City name                          |
| `neighborhood`  | TEXT    | Neighborhood                       |
| `street`        | TEXT    | Street name                        |
| `address_full`  | TEXT    | Full address string                |
| `has_elevator`  | BOOLEAN | Elevator available                 |
| `has_parking`   | BOOLEAN | Parking available                  |
| `has_balcony`   | BOOLEAN | Has balcony                        |
| `has_ac`        | BOOLEAN | Air conditioning                   |
| `is_furnished`  | BOOLEAN | Furnished apartment                |
| `pets_allowed`  | BOOLEAN | Pets allowed                       |
| `has_mamad`     | BOOLEAN | Has safe room (mamad)              |
| `has_bars`      | BOOLEAN | Has window bars                    |
| `thumbnail_url` | TEXT    | Listing thumbnail image            |
| `image_urls`    | TEXT    | JSON array of image URLs           |
| `description`   | TEXT    | Listing description                |
| `contact_name`  | TEXT    | Contact person                     |
| `date_published`| TEXT    | Original publish date              |
| `date_updated`  | TEXT    | Last update date                   |
| `date_scraped`  | TEXT    | When we scraped it                 |
| `raw_text`      | TEXT    | Raw listing text                   |

Indexed columns: `price`, `rooms`, `city`, `date_scraped`

## Setup

### Prerequisites

- Python 3.10+
- A Yad2 account (email/password)

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd yad2-apartment-search

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```env
YAD2_EMAIL=your-email@example.com
YAD2_PASSWORD=your-password

# Optional overrides
HEADLESS=true
SLOW_MO=100
MIN_DELAY_SECONDS=2.0
MAX_DELAY_SECONDS=5.0
MAX_PAGES_PER_SEARCH=10
DB_PATH=./data/listings.db
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```

### Running

```bash
python main.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Design System

The UI uses a **Soft Bento** design language:

| Token            | Value       | Usage                    |
|------------------|-------------|--------------------------|
| Accent           | `#FACC15`   | Buttons, active states   |
| Background       | `#F9F9F9`   | Page background          |
| Surface          | `#FFFFFF`   | Cards, panels            |
| Text Primary     | `#111827`   | Headings, prices         |
| Text Secondary   | `#4B5563`   | Body text, labels        |
| Text Muted       | `#9CA3AF`   | Placeholders, hints      |
| Border           | `#E5E7EB`   | Input borders, dividers  |
| Border Radius    | `16px`      | Cards                    |
| Border Radius SM | `12px`      | Buttons, inputs          |
| Font             | Inter       | All text                 |

### Property Badges

- **Apartment** — Yellow (`#FEF3C7`)
- **Penthouse** — Blue (`#DBEAFE`)
- **Sublet** — Indigo (`#E0E7FF`)

### Feature Tags

Green pill badges (`#ECFDF5` background, `#065F46` text) for amenities like Elevator, Parking, Balcony, A/C, Furnished, Pets, Mamad.

## Anti-Detection Measures

- Persistent browser context (preserves cookies/session)
- Random delays between page loads (configurable)
- Hebrew locale and Israel timezone
- Disabled automation detection flags
- Real Chrome user agent
- Configurable `SLOW_MO` for human-like interaction speed

## Tech Stack

| Layer     | Technology                  |
|-----------|-----------------------------|
| Scraping  | Playwright (Chromium)       |
| Backend   | Flask                       |
| Database  | SQLite                      |
| Models    | Pydantic                    |
| Frontend  | Vanilla JS, CSS (no framework) |
| Config    | pydantic-settings, python-dotenv |

## License

This project is for personal/educational use. Scraping Yad2 may be subject to their terms of service.
