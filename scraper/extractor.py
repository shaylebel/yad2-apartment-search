import logging
import re
from typing import Optional

from playwright.sync_api import Locator, Page

from config import constants
from models.listing import ApartmentListing

logger = logging.getLogger(__name__)


class ListingExtractor:
    def extract_listings(self, page: Page) -> list[ApartmentListing]:
        listings = []

        try:
            page.wait_for_selector(constants.SELECTORS["feed_list"], timeout=15000)
        except Exception:
            logger.warning("Feed list not found on page")
            return listings

        cards = page.locator(constants.SELECTORS["listing_card"]).all()
        logger.info("Found %s listing cards", len(cards))

        for card in cards:
            try:
                listing = self._extract_single(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning("Failed to extract listing: %s", e)

        return listings

    def _extract_single(self, card: Locator) -> Optional[ApartmentListing]:
        link_el = card.locator(constants.SELECTORS["listing_link"]).first
        url = ""
        listing_id = ""

        if link_el.count() > 0:
            href = link_el.get_attribute("href") or ""
            if href:
                url = href if href.startswith("http") else constants.BASE_URL + href
                listing_id = self._extract_id_from_url(url) or ""

        if not listing_id:
            return None

        price = self._parse_price(self._safe_text(card, constants.SELECTORS["price"]))
        street = self._safe_text(card, constants.SELECTORS["street_name"])
        info_1 = self._safe_text(card, constants.SELECTORS["info_line_1"])
        info_2 = self._safe_text(card, constants.SELECTORS["info_line_2"])

        rooms, floor, total_floors, size = self._parse_info_line_2(info_2)
        city, neighborhood = self._parse_info_line_1(info_1)

        img_el = card.locator(constants.SELECTORS["image"]).first
        thumbnail = img_el.get_attribute("src") if img_el.count() > 0 else None

        full_text = card.inner_text()
        features = self._parse_features(full_text)

        address_full = ", ".join(filter(None, [street, neighborhood, city]))

        return ApartmentListing(
            listing_id=listing_id,
            url=url,
            price=price,
            rooms=rooms,
            size_sqm=size,
            floor=floor,
            total_floors=total_floors,
            city=city,
            neighborhood=neighborhood,
            street=street,
            address_full=address_full,
            thumbnail_url=thumbnail,
            raw_text=full_text[:500],
            **features,
        )

    def _safe_text(self, parent: Locator, selector: str) -> str:
        try:
            el = parent.locator(selector).first
            if el.count() > 0:
                return el.inner_text().strip()
        except Exception:
            pass
        return ""

    def _parse_price(self, text: str) -> Optional[int]:
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else None

    def _parse_info_line_2(self, text: str) -> tuple:
        rooms = None
        floor = None
        total_floors = None
        size = None

        rooms_match = re.search(r"([\d.]+)\s*חדר", text)
        if rooms_match:
            rooms = float(rooms_match.group(1))

        floor_match = re.search(r"קומה\s+(\d+)", text)
        if floor_match:
            floor = int(floor_match.group(1))

        total_floors_match = re.search(r"מתוך\s+(\d+)", text)
        if total_floors_match:
            total_floors = int(total_floors_match.group(1))

        size_match = re.search(r"(\d+)\s*(?:מ\"ר|מ״ר)", text)
        if size_match:
            size = int(size_match.group(1))

        return rooms, floor, total_floors, size

    def _parse_info_line_1(self, text: str) -> tuple:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if not parts:
            return None, None

        property_kinds = {
            "דירה",
            "פנטהאוז",
            "דופלקס",
            "קוטג",
            "קוטג׳",
            "גג/פנטהאוז",
            "יחידת דיור",
            "סטודיו",
        }
        if len(parts) >= 3 and parts[0] in property_kinds:
            city = parts[-1]
            neighborhood = ", ".join(parts[1:-1]) or None
            return city, neighborhood

        city = parts[-1] if len(parts) > 1 else parts[0]
        neighborhood = ", ".join(parts[:-1]) if len(parts) > 1 else None
        return city, neighborhood

    def _parse_features(self, text: str) -> dict:
        normalized = text.replace("חנייה", "חניה")
        features = {}
        for hebrew, field in constants.HEBREW_FEATURES.items():
            features[field] = hebrew in normalized
        return features

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        match = re.search(r"/item/[^/]+/([^?]+)", url)
        return match.group(1) if match else None
