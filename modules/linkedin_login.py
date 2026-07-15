"""
modules/linkedin_login.py
Handles automated LinkedIn login using Playwright.
Uses a persistent browser context to save login sessions.
"""

import time
import os
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, Page
from utils.logger import setup_logger
from config.settings import (
    LINKEDIN_EMAIL, LINKEDIN_PASSWORD,
    LINKEDIN_LOGIN_URL, PAGE_LOAD_DELAY, ACTION_DELAY,
    USER_DATA_DIR
)

logger = setup_logger()

class LinkedInLogin:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright = None
        self._browser_context = None
        self._page: Page | None = None

    def login(self) -> Page | None:
        """
        Launch browser with persistent context. 
        If a session exists, it will skip login.
        """
        try:
            if not os.path.exists(USER_DATA_DIR):
                os.makedirs(USER_DATA_DIR)

            self._playwright = sync_playwright().start()
            
            # Using launch_persistent_context to save cookies/session
            self._browser_context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                channel="chrome",  # Attempts to use actual Google Chrome
                headless=self.headless,
                slow_mo=50,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )

            self._page = self._browser_context.pages[0]
            
            # 1. Try to go to feed directly to see if we are already logged in
            logger.info("Checking for existing LinkedIn session...")
            self._page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            time.sleep(PAGE_LOAD_DELAY)

            parsed = urlparse(self._page.url)
            if parsed.path.startswith("/feed") or parsed.path.startswith("/mynetwork"):
                logger.info("Existing session found! Skipping login.")
                return self._page

            # 2. If not logged in, go to login page
            logger.info("No active session. Navigating to login page...")
            self._page.goto(LINKEDIN_LOGIN_URL, wait_until="domcontentloaded")
            time.sleep(PAGE_LOAD_DELAY)

            # Check if login form is actually there (sometimes it redirects)
            if self._page.locator('input[name="session_key"], input#username').count() > 0:
                logger.info("Filling login credentials...")
                
                # Fill email
                email_locator = self._page.locator('input[name="session_key"], input#username, input[autocomplete="username"]').first
                email_locator.fill(LINKEDIN_EMAIL)
                time.sleep(ACTION_DELAY)

                # Fill password
                password_locator = self._page.locator('input[name="session_password"], input#password, input[autocomplete="current-password"]').first
                password_locator.fill(LINKEDIN_PASSWORD)
                time.sleep(ACTION_DELAY)

                # Click Sign In
                time.sleep(1)
                try:
                    submit_locator = self._page.get_by_role("button", name="Sign in", exact=True)
                    submit_locator.click()
                except:
                    fallback_locator = self._page.locator('button.btn__primary--large, button[data-litms-control-urn="login-submit"], form.login__form > button').first
                    fallback_locator.click()
                
                time.sleep(PAGE_LOAD_DELAY)

            # 3. Check for 2FA
            if "checkpoint" in self._page.url or "challenge" in self._page.url:
                logger.warning("2FA/Verification required. Please complete it in the browser window...")
                time.sleep(60) 

            # 4. Final verification
            parsed_final = urlparse(self._page.url)
            success_paths = ["/feed", "/mynetwork", "/jobs", "/dashboard", "/home", "/messaging"]
            if any(parsed_final.path.startswith(x) for x in success_paths):
                logger.info("LinkedIn login successful and session saved.")
                return self._page
            else:
                logger.error(f"Login failed. Current URL: {self._page.url}")
                return None

        except Exception as e:
            logger.error(f"Exception during LinkedIn login: {e}")
            return None

    def close(self):
        try:
            if self._browser_context:
                self._browser_context.close()
            if self._playwright:
                self._playwright.stop()
            logger.info("Browser session closed.")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
