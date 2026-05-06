import logging
from playwright.sync_api import sync_playwright, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserManager:
    def __init__(self, settings):
        self.settings = settings
        self.playwright = None
        self.context = None

    def launch(self) -> BrowserContext:
        self.playwright = sync_playwright().start()

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.settings.browser_data_dir,
            headless=self.settings.headless,
            slow_mo=self.settings.slow_mo,
            locale="he-IL",
            timezone_id="Asia/Jerusalem",
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
        )

        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['he-IL', 'he', 'en-US', 'en']
            });
        """)

        logger.info("Browser launched with persistent context")
        return self.context

    def new_page(self) -> Page:
        if not self.context:
            self.launch()
        return self.context.new_page()

    def close(self):
        if self.context:
            self.context.close()
            self.context = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        logger.info("Browser closed")
