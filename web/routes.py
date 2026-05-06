import logging
import threading
from flask import Blueprint, render_template, request, jsonify, current_app
from config import constants
from models.search_params import SearchFilters
from database.db import Database
from scraper.browser import BrowserManager
from scraper.auth import Yad2Auth
from scraper.search import Yad2Search
from scraper.rate_limiter import RateLimiter
from scraper.detail import fetch_listing_details

logger = logging.getLogger(__name__)
bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    return render_template("dashboard.html", cities=constants.CITY_CODES)


@bp.route("/api/search", methods=["POST"])
def start_search():
    settings = current_app.config["SETTINGS"]
    status = current_app.config["SCRAPE_STATUS"]
    lock = current_app.config["SCRAPE_LOCK"]

    if not lock.acquire(blocking=False):
        return jsonify({"error": "Search already in progress"}), 409

    data = request.get_json() or {}
    filters = SearchFilters(**data)
    status.update(
        {
            "running": True,
            "progress": "Starting...",
            "error": None,
            "count": 0,
        }
    )

    def run_scrape():
        browser = None
        db = None
        try:
            status["progress"] = "Launching browser..."
            browser = BrowserManager(settings)
            browser.launch()
            page = browser.new_page()

            status["progress"] = "Checking login status..."
            auth = Yad2Auth(page, settings)
            if not auth.is_logged_in():
                status["progress"] = "Logging in..."
                auth.login()

            rate_limiter = RateLimiter(
                settings.min_delay_seconds, settings.max_delay_seconds
            )
            searcher = Yad2Search(page, rate_limiter, settings.max_pages_per_search)
            db = Database(settings.db_path)

            def on_progress(msg):
                status["progress"] = msg

            def on_batch(new_listings, page_num, total_found):
                db.upsert_many(new_listings)
                status["count"] = total_found
                status["progress"] = (
                    f"Scraping page {page_num}... Found {total_found} listings so far."
                )

            listings = searcher.search(
                filters,
                on_progress=on_progress,
                on_batch=on_batch,
            )

            status["count"] = len(listings)
            status["progress"] = f"Done! Found {len(listings)} listings."
        except Exception as e:
            logger.exception("Scrape failed")
            status["error"] = str(e)
            status["progress"] = f"Error: {e}"
        finally:
            if db:
                db.close()
            if browser:
                browser.close()
            status["running"] = False
            lock.release()

    thread = threading.Thread(target=run_scrape, daemon=True)
    thread.start()

    return jsonify({"status": "started"})


@bp.route("/api/status")
def scrape_status():
    return jsonify(current_app.config["SCRAPE_STATUS"])


@bp.route("/api/results")
def get_results():
    settings = current_app.config["SETTINGS"]
    args = request.args.to_dict()

    sort_by = args.pop("sort_by", "date_scraped")
    sort_order = args.pop("sort_order", "DESC")
    page = int(args.pop("page", 1))
    per_page = int(args.pop("per_page", 50))

    db = Database(settings.db_path)
    results = db.query_listings(
        filters=args,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=per_page,
        offset=(page - 1) * per_page,
    )
    total = db.count_listings(args)
    db.close()

    return jsonify({"results": results, "total": total, "page": page, "per_page": per_page})


@bp.route("/api/listing/<listing_id>/details")
def get_listing_details(listing_id):
    settings = current_app.config["SETTINGS"]
    listing_url = request.args.get("url", "").strip()

    db = Database(settings.db_path)
    listing = None
    for row in db.conn.execute("SELECT * FROM listings WHERE listing_id = ?", [listing_id]).fetchall():
        listing = dict(row)

    if not listing and listing_url:
        row = db.conn.execute("SELECT * FROM listings WHERE url = ?", [listing_url]).fetchone()
        if row:
            listing = dict(row)

    if not listing and listing_url:
        listing = {"listing_id": listing_id, "url": listing_url}

    if not listing or not listing.get("url"):
        db.close()
        return jsonify({"error": "Listing not found"}), 404

    try:
        details = fetch_listing_details(listing["url"], settings=settings)
    except Exception:
        logger.exception("Failed to fetch listing details for %s", listing_id)
        details = {
            "description": None,
            "has_elevator": False,
            "has_parking": False,
            "has_balcony": False,
            "has_ac": False,
            "is_furnished": False,
            "pets_allowed": False,
            "has_mamad": False,
            "has_bars": False,
        }

    updates = []
    params = []
    for field in ["has_elevator", "has_parking", "has_balcony", "has_ac",
                   "is_furnished", "pets_allowed", "has_mamad", "has_bars"]:
        if details.get(field):
            updates.append(f"{field} = ?")
            params.append(True)
    if details.get("description") and not listing.get("description"):
        updates.append("description = ?")
        params.append(details["description"])
    if updates:
        params.append(listing_id)
        db.conn.execute(
            f"UPDATE listings SET {', '.join(updates)} WHERE listing_id = ?",
            params,
        )
        db.conn.commit()
    db.close()

    return jsonify(details)


@bp.route("/api/filters/cities")
def get_cities():
    return jsonify(constants.CITY_CODES)
