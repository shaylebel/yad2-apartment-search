import json
from pathlib import Path

BASE_URL = "https://www.yad2.co.il"
RENT_URL = f"{BASE_URL}/realestate/rent"
LOGIN_URL = f"{BASE_URL}/login"

SELECTORS = {
    "feed_list": "[data-testid='feed-list']",
    "listing_card": "[data-testid='item-basic'], [data-testid='platinum-item'], [data-testid='agency-item'], [data-testid='booster-item']",
    "price": "[data-testid='price']",
    "street_name": "[data-testid='street-name']",
    "info_line_1": "[data-testid='item-info-line-1st']",
    "info_line_2": "[data-testid='item-info-line-2nd']",
    "image": "[data-testid='image']",
    "listing_link": "a[href*='/item/']",
    "tags_box": "[data-testid='item-tags-box']",
    "pagination_links": "[data-testid='pagination-item-link']",
    "login_email": "input[type='email'], input[name='email'], #email",
    "login_password": "input[type='password'], input[name='password'], #password",
    "login_submit": "button[type='submit']",
    "cookie_accept": "[data-testid='cookie-implementation-disclaimer-submit-button']",
    "logged_in_indicator": "[data-testid='favorites-option'], [data-testid='customerServicePortal-option']",
}

HEBREW_FEATURES = {
    "מעלית": "has_elevator",
    "חניה": "has_parking",
    "מרפסת": "has_balcony",
    "מיזוג": "has_ac",
    "מרוהטת": "is_furnished",
    "חיות": "pets_allowed",
    'ממ"ד': "has_mamad",
    "סורגים": "has_bars",
}

FEATURE_PATTERNS = {
    "has_elevator": ["מעלית"],
    "has_parking": ["חניה", "חנייה"],
    "has_balcony": ["מרפסת", "מרפסות"],
    "has_ac": ["מיזוג", "מזגן", "מזגנים"],
    "is_furnished": ["מרוהטת", "מרוהט", "ריהוט"],
    "pets_allowed": ["חיות", "בעלי חיים", 'בע"ח'],
    "has_mamad": ['ממ"ד', "ממד"],
    "has_bars": ["סורגים"],
}

DETAIL_SELECTORS = {
    "features_section": "[class*='amenities'], [class*='features'], [data-testid='features']",
    "feature_item": "[class*='amenity'], [class*='feature-item']",
    "feature_active": "[class*='active'], [class*='available'], :not([class*='disabled']):not([class*='inactive']):not([class*='not-available'])",
    "description": "[data-testid='description'], [class*='description'] p, [class*='description-text']",
    "total_floors": "[data-testid='total-floors']",
}

_cities_path = Path(__file__).parent.parent / "data" / "cities.json"
if _cities_path.exists():
    with open(_cities_path, "r", encoding="utf-8") as _f:
        CITY_CODES = json.load(_f)
else:
    CITY_CODES = {}
