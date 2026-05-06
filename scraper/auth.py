import time
import logging
from playwright.sync_api import Page
from config import constants

logger = logging.getLogger(__name__)


class Yad2Auth:
    def __init__(self, page: Page, settings):
        self.page = page
        self.settings = settings

    def is_logged_in(self) -> bool:
        try:
            self.page.goto(
                constants.BASE_URL, wait_until="domcontentloaded", timeout=30000
            )
            time.sleep(3)
            return (
                self.page.locator(constants.SELECTORS["logged_in_indicator"]).count() > 0
            )
        except Exception as e:
            logger.warning(f"Login check failed: {e}")
            return False

    def login(self):
        logger.info("Starting login flow")
        self.page.goto(
            constants.LOGIN_URL, wait_until="domcontentloaded", timeout=30000
        )
        time.sleep(5)

        self._dismiss_cookie_popup()

        email_input = self.page.locator(constants.SELECTORS["login_email"]).first
        email_input.wait_for(state="visible", timeout=15000)
        email_input.fill(self.settings.yad2_email)

        password_input = self.page.locator(constants.SELECTORS["login_password"]).first
        password_input.wait_for(state="visible", timeout=15000)
        password_input.fill(self.settings.yad2_password)

        self.page.locator(constants.SELECTORS["login_submit"]).first.click()
        self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        time.sleep(3)

        logger.info("Login flow completed")

    def _dismiss_cookie_popup(self):
        try:
            cookie_btn = self.page.locator(constants.SELECTORS["cookie_accept"]).first
            if cookie_btn.is_visible(timeout=3000):
                cookie_btn.click()
                time.sleep(1)
        except Exception:
            pass
