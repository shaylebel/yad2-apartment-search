import logging
from playwright.sync_api import Page
from config import constants
from models.search_params import SearchFilters
from models.listing import ApartmentListing
from scraper.extractor import ListingExtractor
from scraper.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class Yad2Search:
    def __init__(self, page: Page, rate_limiter: RateLimiter, max_pages: int = 10):
        self.page = page
        self.rate_limiter = rate_limiter
        self.max_pages = max_pages
        self.extractor = ListingExtractor()

    def search(
        self,
        filters: SearchFilters,
        on_progress=None,
        on_batch=None,
    ) -> list[ApartmentListing]:
        all_listings = []
        seen_ids = set()

        url = self._build_search_url(filters)
        logger.info(f"Navigating to: {url}")

        if on_progress:
            on_progress("Loading search page...")

        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_selector(
            constants.SELECTORS["feed_list"], timeout=30000
        )

        for page_num in range(1, self.max_pages + 1):
            if on_progress:
                on_progress(f"Scraping page {page_num}...")

            self.rate_limiter.wait()

            listings = self.extractor.extract_listings(self.page)
            new_listings = []
            new_count = 0
            for listing in listings:
                if listing.listing_id not in seen_ids:
                    seen_ids.add(listing.listing_id)
                    all_listings.append(listing)
                    new_listings.append(listing)
                    new_count += 1

            logger.info(
                f"Page {page_num}: extracted {len(listings)} cards, "
                f"{new_count} new listings"
            )

            if on_batch and new_listings:
                on_batch(new_listings, page_num, len(all_listings))

            if not self._go_to_next_page(page_num):
                break

        logger.info(f"Total unique listings extracted: {len(all_listings)}")
        return all_listings

    def _build_search_url(self, filters: SearchFilters) -> str:
        params = filters.to_url_params()
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            return f"{constants.RENT_URL}?{query_string}"
        return constants.RENT_URL

    def _go_to_next_page(self, current_page: int) -> bool:
        try:
            next_page = current_page + 1
            pagination_links = self.page.locator(
                constants.SELECTORS["pagination_links"]
            ).all()

            for link in pagination_links:
                text = link.inner_text().strip()
                if text == str(next_page):
                    link.click()
                    self.page.wait_for_load_state("networkidle", timeout=30000)
                    return True

            return False
        except Exception as e:
            logger.warning(f"Pagination failed: {e}")
            return False
