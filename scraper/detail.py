import logging
import re
import urllib.request
from typing import Optional

from config import constants
from scraper.browser import BrowserManager

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.yad2.co.il/",
}

_SECURITY_PAGE_TEXT = "\u05d0\u05d1\u05d8\u05d7\u05ea \u05d0\u05ea\u05e8"
_FEATURE_SECTION_TITLE = "\u05de\u05d4 \u05d9\u05e9 \u05d1\u05e0\u05db\u05e1"
_DESC_PATTERN = (
    r"(\u05ea\u05d9\u05d0\u05d5\u05e8 \u05d4\u05e0\u05db\u05e1|"
    r"\u05e4\u05e8\u05d8\u05d9\u05dd \u05e0\u05d5\u05e1\u05e4\u05d9\u05dd)"
    r"\s*[:\-]?\s*(.+?)(?:"
    r"\u05d9\u05e6\u05d9\u05e8\u05ea \u05e7\u05e9\u05e8|"
    r"\u05de\u05d0\u05e4\u05d9\u05d9\u05e0\u05d9 \u05d4\u05e0\u05db\u05e1|"
    r"\u05d4\u05e6\u05d2 \u05de\u05e1\u05e4\u05e8|$)"
)


def fetch_listing_details(url: str, settings=None) -> dict:
    details = _empty_details()

    if settings is not None:
        try:
            _fetch_with_browser(url, details, settings)
        except Exception:
            logger.exception("Browser detail fetch failed for %s", url)

        if _has_detail_content(details):
            return details

    try:
        _try_html_fallback(url, details)
    except Exception:
        logger.exception("HTML detail fallback failed for %s", url)

    return details


def _empty_details() -> dict:
    return {
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


def _has_detail_content(details: dict) -> bool:
    return bool(
        details.get("description")
        or any(
            details.get(field)
            for field in (
                "has_elevator",
                "has_parking",
                "has_balcony",
                "has_ac",
                "is_furnished",
                "pets_allowed",
                "has_mamad",
                "has_bars",
            )
        )
    )


def _fetch_with_browser(url: str, details: dict, settings) -> None:
    browser = BrowserManager(settings)
    page = None

    try:
        browser.launch()
        page = browser.new_page()
        response_bodies = []

        def handle_response(response):
            try:
                request = response.request
                resource_type = request.resource_type
                content_type = response.headers.get("content-type", "")
                if resource_type not in ("xhr", "fetch", "document"):
                    return
                if not any(kind in content_type for kind in ("json", "text", "html")):
                    return

                body = response.text()
                if body:
                    response_bodies.append(body)
            except Exception:
                logger.debug("Could not read response body for %s", response.url, exc_info=True)

        page.on("response", handle_response)
        page.goto(url, wait_until="domcontentloaded", timeout=45000)

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            logger.debug("networkidle wait timed out for %s", url)

        page.wait_for_timeout(4000)

        title = page.title() or ""
        body_text = page.locator("body").inner_text(timeout=5000).strip()
        html = page.content()

        if "captcha" in title.lower() or "ShieldSquare Captcha" in html or _SECURITY_PAGE_TEXT in body_text:
            logger.warning("Detail page hit captcha for %s", url)
            return

        found_feature_section = _parse_feature_section(page, details)

        meta_desc = page.locator("meta[name='description']").first.get_attribute("content")
        if meta_desc:
            details["description"] = _clean_text(meta_desc)

        _parse_description_blob("\n".join([body_text, html]), details)
        for body in response_bodies:
            _parse_description_blob(body, details)

        if not found_feature_section:
            _parse_feature_text_blob("\n".join([body_text, html]), details)
    finally:
        if page:
            page.close()
        browser.close()


def _parse_feature_section(page, details: dict) -> None:
    try:
        heading = page.get_by_text(_FEATURE_SECTION_TITLE, exact=False).first
        if heading.count() == 0:
            return False

        container = heading.locator("xpath=ancestor::*[self::section or self::div][1]")
        parsed = container.evaluate(
            """(root) => {
                const termsByField = {
                    has_elevator: ['מעלית'],
                    has_parking: ['חניה', 'חנייה'],
                    has_balcony: ['מרפסת', 'מרפסות'],
                    has_ac: ['מיזוג', 'מזגן', 'מזגנים'],
                    is_furnished: ['מרוהטת', 'מרוהט', 'ריהוט'],
                    pets_allowed: ['חיות', 'בעלי חיים', 'בע"ח'],
                    has_mamad: ['ממ"ד', 'ממד'],
                    has_bars: ['סורגים']
                };

                const result = {
                    has_elevator: false,
                    has_parking: false,
                    has_balcony: false,
                    has_ac: false,
                    is_furnished: false,
                    pets_allowed: false,
                    has_mamad: false,
                    has_bars: false
                };

                const parseColor = (value) => {
                    const match = value && value.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/i);
                    if (!match) return null;
                    return {
                        r: Number(match[1]),
                        g: Number(match[2]),
                        b: Number(match[3]),
                        a: match[4] === undefined ? 1 : Number(match[4])
                    };
                };

                const getLuminance = (color) => {
                    if (!color) return null;
                    return (0.2126 * color.r) + (0.7152 * color.g) + (0.0722 * color.b);
                };

                const scoreElementState = (el) => {
                    let disabledSignals = 0;
                    let activeSignals = 0;
                    const style = getComputedStyle(el);
                    const color = parseColor(style.color);
                    const fill = parseColor(style.fill);
                    const opacity = Number(style.opacity || '1');
                    const fontWeight = Number(style.fontWeight || '400');
                    const colorLuminance = getLuminance(color);
                    const fillLuminance = getLuminance(fill);

                    if (opacity < 0.65) disabledSignals += 3;
                    else if (opacity >= 0.9) activeSignals += 1;

                    if (color && color.a < 0.8) disabledSignals += 2;
                    if (colorLuminance !== null) {
                        if (colorLuminance > 175) disabledSignals += 4;
                        else if (colorLuminance < 145) activeSignals += 3;
                    }

                    if (fill && fill.a < 0.8) disabledSignals += 1;
                    if (fillLuminance !== null) {
                        if (fillLuminance > 180) disabledSignals += 2;
                        else if (fillLuminance < 145) activeSignals += 1;
                    }

                    if (fontWeight >= 500) activeSignals += 1;

                    let node = el;
                    for (let depth = 0; depth < 2 && node && node !== root.parentElement && node !== document.body; depth++) {
                        const cls = String(node.className || '').toLowerCase();
                        if (/(disabled|inactive|unavailable|not-available|muted|off|empty)/.test(cls)) {
                            disabledSignals += 3;
                        }
                        if (/(active|available|selected|enabled)/.test(cls)) {
                            activeSignals += 2;
                        }

                        const ariaDisabled = node.getAttribute && node.getAttribute('aria-disabled');
                        if (ariaDisabled === 'true') disabledSignals += 3;
                        if (ariaDisabled === 'false') activeSignals += 1;

                        node = node.parentElement;
                    }

                    return { disabledSignals, activeSignals };
                };

                const seen = new Set();
                const elements = root.querySelectorAll('span, p, div');

                for (const el of elements) {
                    const text = (el.innerText || '').trim().replace(/\\s+/g, ' ');
                    if (!text || text.length > 20 || text.includes('\\n') || text === 'מה יש בנכס') {
                        continue;
                    }
                    if (el.children.length > 0 && Array.from(el.children).some(child => (child.innerText || '').trim() === text)) {
                        continue;
                    }

                    for (const [field, terms] of Object.entries(termsByField)) {
                        if (!terms.some(term => text === term)) continue;

                        const key = field + '::' + text;
                        if (seen.has(key)) continue;
                        seen.add(key);

                        const { disabledSignals, activeSignals } = scoreElementState(el);
                        if (activeSignals >= disabledSignals + 2) {
                            result[field] = true;
                        }
                    }
                }

                return result;
            }"""
        )
        for field, value in parsed.items():
            if value:
                details[field] = True
        return True
    except Exception:
        logger.debug("Feature section lookup failed", exc_info=True)
        return False


def _try_html_fallback(url: str, details: dict) -> None:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    if "ShieldSquare Captcha" in html or _SECURITY_PAGE_TEXT in html:
        logger.warning("HTML fallback hit captcha for %s", url)
        return

    desc_match = re.search(
        r'<meta\s+name="description"\s+content="([^"]+)"',
        html,
        flags=re.IGNORECASE,
    )
    if desc_match:
        details["description"] = _clean_text(desc_match.group(1))

    _parse_description_blob(html, details)


def _parse_feature_text_blob(blob: str, details: dict) -> None:
    normalized = _normalize_text(blob)
    for field, terms in constants.FEATURE_PATTERNS.items():
        if any(term in normalized for term in terms):
            details[field] = True


def _parse_description_blob(blob: str, details: dict) -> None:
    normalized = _normalize_text(blob)
    if not details.get("description"):
        desc_match = re.search(_DESC_PATTERN, normalized, flags=re.DOTALL)
        if desc_match:
            details["description"] = _clean_text(desc_match.group(2))


def _normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = text.replace("&quot;", '"').replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_text(text: Optional[str]) -> Optional[str]:
    cleaned = _normalize_text(text)
    return cleaned or None
