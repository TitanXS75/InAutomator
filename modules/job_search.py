"""
modules/job_search.py

PROFESSIONAL STRATEGY:
  Instead of fighting LinkedIn's complex nested DOM with fragile CSS selectors,
  we use the simplest, most reliable approach:

  1. Navigate to LinkedIn search (posts, last 24h)
  2. Click EVERY 'see more' / 'more' button using real Playwright clicks
  3. Wait for DOM to settle
  4. Grab document.body.innerText  — the ENTIRE visible text of the page
  5. Run comprehensive email regex on that raw text
  6. For each post author, also deep-scan their profile page + recent activity

  Email regex handles ALL real-world formats:
    standard:    hr@company.com
    with subdomain: jobs.india@company.co.in
    spaced:      hr @ company . com
    obfuscated:  hr at company dot com
    bracketed:   hr[at]company[dot]com
"""

import re
import time
from urllib.parse import quote
from playwright.sync_api import Page
from utils.logger import setup_logger
from utils.csv_handler import save_recruiters
from config.settings import (
    LINKEDIN_SEARCH_URL, PAGE_LOAD_DELAY,
    SCROLL_DELAY, MAX_SCROLL_COUNT
)

logger = setup_logger()


# ── Email Patterns ─────────────────────────────────────────────────────────────

# The definitive email regex — handles all real TLDs up to 10 chars (.com, .in, .co.in, etc.)
_EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9][a-zA-Z0-9._%+\-]{0,63}"   # local part
    r"@"
    r"[a-zA-Z0-9.\-]+"                          # domain
    r"\.[a-zA-Z]{2,10}\b",                      # TLD
    re.IGNORECASE
)

# Obfuscated patterns — "hr at company dot com", "hr[at]company[dot]com"
_OBFUSC_RE = re.compile(
    r"\b([a-zA-Z0-9][a-zA-Z0-9._%+\-]{0,63})"             # local
    r"\s*(?:@|\[at\]|\(at\)|(?<!\w)at(?!\w))\s*"           # @ or "at"
    r"([a-zA-Z0-9.\-]+)"                                   # domain
    r"\s*(?:\.|\[dot\]|\(dot\)|(?<!\w)dot(?!\w))\s*"       # . or "dot"
    r"([a-zA-Z]{2,10})\b",                                 # TLD
    re.IGNORECASE
)

# Domains to ignore (LinkedIn's own tracking, image CDN, etc.)
_JUNK_DOMAINS = {
    "linkedin.com", "licdn.com", "sentry.io", "example.com",
    "test.com", "domain.com", "company.com", "email.com",
    "yourdomain.com", "yourcompany.com", "placeholder.com",
    "w3.org", "schema.org", "google.com", "apple.com",
}

# Author link selectors (best → fallback)
_AUTHOR_LINK_SELECTORS = [
    "a.app-aware-link[href*='/in/']",
    "a[data-field='actor']",
    "a.feed-shared-actor__container-link",
    "a.update-components-actor__container-link",
]

# Post container selectors
_POST_SELECTORS = [
    "div.feed-shared-update-v2",
    "div.occludable-update",
    "li.artdeco-list__item",
    "div[data-urn]",
]

# Author name selectors
_AUTHOR_NAME_SELECTORS = [
    "span.feed-shared-actor__name",
    "span.update-components-actor__name",
    "a.app-aware-link span[aria-hidden='true']",
]

# Company selectors
_COMPANY_SELECTORS = [
    "span.feed-shared-actor__description",
    "span.update-components-actor__description",
]


def _extract_emails(raw_text: str) -> list[str]:
    """
    Extract every unique, valid email from a block of raw text.
    Handles standard, spaced, and obfuscated formats.
    Filters out known junk/LinkedIn tracking domains.
    """
    found: set[str] = set()

    # 1. Standard emails
    for m in _EMAIL_RE.findall(raw_text):
        found.add(m.strip().lower())

    # 2. Obfuscated / "at" / "dot" formats
    for m in _OBFUSC_RE.finditer(raw_text):
        local, domain, tld = m.group(1), m.group(2), m.group(3)
        # Strip residual spaces from spaced variants
        domain = domain.strip()
        email = f"{local}@{domain}.{tld}".lower().replace(" ", "")
        if _EMAIL_RE.fullmatch(email):
            found.add(email)

    # 3. Validate and filter
    valid: list[str] = []
    for e in sorted(found):
        if _is_valid(e):
            valid.append(e)

    return valid


def _is_valid(email: str) -> bool:
    """Basic sanity checks on an extracted email address."""
    if len(email) < 6 or "@" not in email:
        return False
    local, _, domain = email.partition("@")
    if len(local) < 2 or len(domain) < 4:
        return False
    # No double dots, no starting/ending dots in local
    if ".." in email or local.startswith(".") or local.endswith("."):
        return False
    # Reject junk domains
    tld_parts = domain.split(".")
    base_domain = ".".join(tld_parts[-2:]) if len(tld_parts) >= 2 else domain
    if base_domain in _JUNK_DOMAINS or domain in _JUNK_DOMAINS:
        return False
    return True


def _click_all_see_more(page: Page, label: str = "page") -> None:
    """
    Click every 'see more' / 'more' expand button on the page using
    real Playwright clicks so React event handlers fire properly.
    Falls back to JS click for any remaining ones.
    """
    # Strategy 1: LinkedIn's specific class for the inline show-more toggle
    specific_selectors = [
        "button.feed-shared-inline-show-more-text__see-more-less-toggle",
        "button[aria-label*='see more']",
        "button[aria-label*='See more']",
        "span.feed-shared-inline-show-more-text__see-more-less-toggle",
    ]
    clicked = 0
    for sel in specific_selectors:
        try:
            buttons = page.locator(sel).all()
            for btn in buttons:
                try:
                    if btn.is_visible():
                        btn.click(timeout=1200)
                        clicked += 1
                        time.sleep(0.2)
                except Exception:
                    pass
        except Exception:
            pass

    # Strategy 2: JS click on any short "more" text element (catches everything else)
    try:
        page.evaluate("""() => {
            const els = Array.from(
                document.querySelectorAll('button, span[role="button"], a[role="button"]')
            );
            els.forEach(el => {
                const txt = (el.innerText || el.textContent || '').trim();
                const lower = txt.toLowerCase();
                // Match only short expand labels, nothing else
                if (
                    lower === 'see more'     || lower === '…see more'   ||
                    lower === '...see more'  || lower === 'show more'    ||
                    lower === 'more'         || lower === '…more'        ||
                    lower === '...more'      || lower === 'read more'
                ) {
                    try { el.click(); } catch(e) {}
                }
            });
        }""")
    except Exception:
        pass

    if clicked > 0:
        logger.debug(f"    [{label}] Clicked {clicked} Playwright see-more button(s)")


def _get_full_page_text(page: Page) -> str:
    """
    Return the complete visible text of the page.
    This is the nuclear option — guaranteed to capture everything including
    text revealed after 'see more' expansion.
    """
    try:
        return page.evaluate("() => document.body.innerText") or ""
    except Exception:
        try:
            return page.locator("body").inner_text()
        except Exception:
            return ""


class JobSearch:
    """
    Searches LinkedIn for job-related posts and extracts recruiter emails.
    """

    def __init__(self, page: Page):
        self.page = page
        self._seen_emails: set[str] = set()

    def search_and_extract(self, keyword: str) -> list[dict]:
        """
        Full pipeline for one keyword:
        1. Navigate to LinkedIn search (posts, last 24h)
        2. For each scroll: expand all content, grab full page text, extract emails
        3. Deep-scan profiles of first 3 authors found
        Returns a list of recruiter dicts.
        """
        url = LINKEDIN_SEARCH_URL.format(keyword=quote(keyword))
        logger.info(f"🔍 Searching LinkedIn for: '{keyword}'")
        
        # Robust navigation with retries
        if not self._safe_goto(self.page, url, timeout=30000):
            logger.error(f"Failed to navigate to search results for '{keyword}'. Skipping.")
            return []
            
        time.sleep(PAGE_LOAD_DELAY + 1)

        # Wait for posts to appear
        for sel in _POST_SELECTORS:
            try:
                self.page.wait_for_selector(sel, timeout=8000, state="attached")
                logger.debug(f"    Posts detected via selector: {sel}")
                break
            except Exception:
                continue

        recruiters: list[dict] = []
        prev_height = 0
        profiles_deep_scanned: set[str] = set()
        post_authors_seen: list[dict] = []   # track authors for profile deep-scans

        for scroll_num in range(MAX_SCROLL_COUNT):
            logger.info(f"  [Scroll {scroll_num + 1}/{MAX_SCROLL_COUNT}]")

            # ── STEP A: Expand all collapsed content ───────────────────────────
            _click_all_see_more(self.page, label=f"scroll-{scroll_num+1}")
            time.sleep(1.5)  # Let React re-render the expanded text

            # ── STEP B: Grab ENTIRE page text ─────────────────────────────────
            page_text = _get_full_page_text(self.page)
            logger.debug(f"    Page text length: {len(page_text)} chars")

            # ── STEP C: Extract emails from full page text ─────────────────────
            emails_on_page = _extract_emails(page_text)
            logger.info(f"    Emails found on page: {emails_on_page if emails_on_page else 'none'}")

            # ── STEP D: Map emails to post authors ────────────────────────────
            # Collect current post containers to map author → email
            post_elements = self._get_post_elements()
            for el in post_elements:
                author, company, profile_url = self._parse_post_meta(el)
                post_text = ""
                try:
                    post_text = el.inner_text().strip()
                except Exception:
                    pass

                # Emails found directly in this post's text
                post_emails = _extract_emails(post_text)

                # Track for deep scanning
                if profile_url and profile_url not in profiles_deep_scanned:
                    post_authors_seen.append({
                        "author": author,
                        "company": company,
                        "profile_url": profile_url,
                        "post_text": post_text,
                    })

                for email in post_emails:
                    self._add_recruiter(recruiters, email, author, company, keyword, post_text)

            # Page-level emails not yet captured (no specific post mapping)
            for email in emails_on_page:
                if email not in self._seen_emails:
                    self._add_recruiter(recruiters, email, "Unknown", "", keyword, "")

            # ── STEP E: Deep-scan first 3 unique profiles ──────────────────────
            for author_info in post_authors_seen[:]:
                if len(profiles_deep_scanned) >= 3:
                    break
                purl = author_info["profile_url"]
                if purl and purl not in profiles_deep_scanned:
                    profiles_deep_scanned.add(purl)
                    post_authors_seen.remove(author_info)
                    emails = self._deep_scan_profile(
                        purl,
                        author_info["author"],
                        author_info["company"],
                        keyword,
                        author_info["post_text"]
                    )
                    recruiters.extend(emails)

            # ── STEP F: Scroll down ────────────────────────────────────────────
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(SCROLL_DELAY)
            new_height = self.page.evaluate("document.body.scrollHeight")

            if scroll_num > 1 and new_height == prev_height:
                logger.info("    No new content loaded — stopping scroll.")
                break
            prev_height = new_height

        if recruiters:
            save_recruiters(recruiters)
            logger.info(f"✅ Saved {len(recruiters)} recruiter(s) for '{keyword}'")
        else:
            logger.warning(f"⚠  No recruiter emails found for '{keyword}'")

        return recruiters

    def _add_recruiter(
        self,
        recruiters: list[dict],
        email: str,
        author: str,
        company: str,
        keyword: str,
        post_text: str
    ) -> None:
        """Add an email to the recruiters list if not already seen."""
        if email in self._seen_emails:
            return
        self._seen_emails.add(email)
        recruiters.append({
            "name":         author,
            "email":        email,
            "company":      company,
            "keyword":      keyword,
            "post_snippet": post_text[:300].replace("\n", " ").strip(),
        })
        logger.info(f"    ✅ Captured: {email}  (author: {author})")

    def _deep_scan_profile(
        self,
        profile_url: str,
        author: str,
        company: str,
        keyword: str,
        original_post_text: str
    ) -> list[dict]:
        """
        Open recruiter's LinkedIn profile in a new tab.
        Scans:
          1. Main profile page (About, headline, bio)
          2. Contact Info modal
          3. Recent Activity / Posts page (with expanded text)
        Returns list of new recruiter dicts.
        """
        found_recruiters: list[dict] = []
        profile_page = None

        try:
            logger.info(f"    🔎 Deep scanning profile: {profile_url}")
            profile_page = self.page.context.new_page()
            
            # ── 1. Main profile page ───────────────────────────────────────────
            if not self._safe_goto(profile_page, profile_url, timeout=20000):
                return []
                
            time.sleep(PAGE_LOAD_DELAY)
            _click_all_see_more(profile_page, "profile-main")
            time.sleep(1)
            full_text += _get_full_page_text(profile_page) + "\n"

            # ── 2. Contact Info modal ──────────────────────────────────────────
            try:
                contact_sel = 'a:has-text("Contact info"), a[href*="overlay/contact-info"]'
                contact = profile_page.locator(contact_sel).first
                if contact.count() > 0 and contact.is_visible(timeout=2000):
                    contact.click(timeout=3000)
                    time.sleep(1.5)
                    modal = profile_page.locator('div[role="dialog"]').first
                    if modal.is_visible(timeout=2000):
                        full_text += modal.inner_text() + "\n"
                    profile_page.keyboard.press("Escape")
                    time.sleep(0.5)
            except Exception:
                pass

            # ── 3. Recent Activity (posts) page ───────────────────────────────
            try:
                activity_url = profile_url.rstrip("/") + "/recent-activity/all/"
                if self._safe_goto(profile_page, activity_url, timeout=20000):
                    time.sleep(PAGE_LOAD_DELAY)

                    # Expand all posts in the activity feed
                    _click_all_see_more(profile_page, "profile-activity")
                    time.sleep(1.5)

                    full_text += _get_full_page_text(profile_page) + "\n"
            except Exception as e:
                logger.debug(f"    Activity page error: {e}")

            # ── Extract emails from all collected text ─────────────────────────
            emails = _extract_emails(full_text)
            logger.info(f"    Profile scan complete: {emails if emails else 'no emails found'}")

            for email in emails:
                snippet = original_post_text[:300].replace("\n", " ").strip()
                found_recruiters.append({
                    "name":         author,
                    "email":        email,
                    "company":      company,
                    "keyword":      keyword,
                    "post_snippet": snippet,
                })
                self._seen_emails.add(email)
                logger.info(f"    ✅ Profile email: {email}")

        except Exception as e:
            logger.debug(f"    Deep scan exception for {profile_url}: {e}")
        finally:
            if profile_page:
                try:
                    profile_page.close()
                except Exception:
                    pass

        return found_recruiters

    def _safe_goto(self, page: Page, url: str, timeout: int = 30000, retries: int = 3) -> bool:
        """Navigate to a URL with built-in retry logic for connection errors."""
        for attempt in range(1, retries + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                return True
            except Exception as e:
                err_msg = str(e)
                logger.debug(f"    Navigation attempt {attempt} failed for {url[:50]}...: {err_msg}")
                if attempt < retries:
                    time.sleep(2)  # Wait before retrying
                else:
                    logger.warning(f"    Navigation failed after {retries} attempts.")
                    return False
        return False

    def _get_post_elements(self) -> list:
        """Return all currently visible post elements from the page."""
        for sel in _POST_SELECTORS:
            try:
                els = self.page.query_selector_all(sel)
                if els:
                    return els
            except Exception:
                continue
        return []

    def _parse_post_meta(self, el) -> tuple[str, str, str]:
        """Extract (author_name, company, profile_url) from a post element."""
        author = "Unknown"
        company = ""
        profile_url = ""

        for sel in _AUTHOR_NAME_SELECTORS:
            try:
                node = el.query_selector(sel)
                if node:
                    name = node.inner_text().strip()
                    if name and len(name) > 1:
                        author = name
                        break
            except Exception:
                continue

        for sel in _COMPANY_SELECTORS:
            try:
                node = el.query_selector(sel)
                if node:
                    company = node.inner_text().strip()
                    if company:
                        break
            except Exception:
                continue

        for sel in _AUTHOR_LINK_SELECTORS:
            try:
                node = el.query_selector(sel)
                if node:
                    href = node.get_attribute("href") or ""
                    if "/in/" in href:
                        profile_url = href.split("?")[0]
                        break
            except Exception:
                continue

        return author, company, profile_url
