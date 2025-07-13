"""Playwright utilities for web scraping - replaces selenium_utils.py"""
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, ElementHandle, Playwright
from typing import Optional, List, Dict, Any, Union
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class PlaywrightManager:
    """Manages Playwright browser instances - drop-in replacement for SeleniumManager"""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.headless = headless
        self.timeout = timeout
        self.contexts: List[BrowserContext] = []
        
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def start(self):
        """Start Playwright"""
        if not self.playwright:
            self.playwright = sync_playwright().start()
            
    def create_driver(self, browser_type: str = "chromium", **kwargs) -> Page:
        """Creates a new page (equivalent to Selenium's driver)"""
        self.start()
        
        if not self.browser:
            if browser_type == "chromium":
                self.browser = self.playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox'
                    ]
                )
            elif browser_type == "firefox":
                self.browser = self.playwright.firefox.launch(headless=self.headless)
            else:
                self.browser = self.playwright.webkit.launch(headless=self.headless)
        
        # Create context with default options
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'ignore_https_errors': True,
            'extra_http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
        }
        
        # Update with any provided kwargs
        context_options.update(kwargs)
        
        context = self.browser.new_context(**context_options)
        self.contexts.append(context)
        
        page = context.new_page()
        page.set_default_timeout(self.timeout)
        
        # Add stealth scripts
        page.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome object
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        return page
    
    def quit_driver(self, page: Page):
        """Close page and context"""
        if page and not page.is_closed():
            context = page.context
            page.close()
            if context in self.contexts:
                context.close()
                self.contexts.remove(context)
            
    def close(self):
        """Close browser and playwright"""
        for context in self.contexts:
            if context:
                context.close()
        self.contexts.clear()
        
        if self.browser:
            self.browser.close()
            self.browser = None
            
        if self.playwright:
            self.playwright.stop()
            self.playwright = None


# Utility functions that match selenium_utils.py interface
def wait_for_element(page: Page, selector: str, timeout: int = 10000, state: str = "visible") -> ElementHandle:
    """Wait for element - Playwright auto-waits but this gives us explicit control"""
    try:
        element = page.wait_for_selector(selector, timeout=timeout, state=state)
        return element
    except Exception as e:
        logger.error(f"Failed to find element {selector}: {e}")
        raise


def safe_find_element(page: Page, selector: str) -> Optional[ElementHandle]:
    """Find element without throwing exception"""
    try:
        return page.query_selector(selector)
    except Exception:
        return None


def safe_find_elements(page: Page, selector: str) -> List[ElementHandle]:
    """Find multiple elements without throwing exception"""
    try:
        return page.query_selector_all(selector)
    except Exception:
        return []


def scroll_to_element(page: Page, element: Union[ElementHandle, str]):
    """Scroll element into view"""
    if isinstance(element, str):
        page.evaluate(f"document.querySelector('{element}')?.scrollIntoView({{behavior: 'smooth', block: 'center'}})")
    else:
        element.scroll_into_view_if_needed()


def scroll_page(page: Page, direction: str = "down", amount: int = 500):
    """Scroll page by amount"""
    if direction == "down":
        page.evaluate(f"window.scrollBy(0, {amount})")
    else:
        page.evaluate(f"window.scrollBy(0, -{amount})")


def scroll_to_bottom(page: Page):
    """Scroll to bottom of page"""
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")


def get_text_content(element: Optional[ElementHandle], default: str = "") -> str:
    """Safely get text content from element"""
    if element:
        try:
            text = element.text_content()
            return text.strip() if text else default
        except:
            return default
    return default


def get_attribute(element: Optional[ElementHandle], attribute: str, default: str = "") -> str:
    """Safely get attribute from element"""
    if element:
        try:
            value = element.get_attribute(attribute)
            return value if value else default
        except:
            return default
    return default


def wait_for_page_load(page: Page, timeout: int = 30000):
    """Wait for page to load completely"""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except:
        # If networkidle times out, at least wait for domcontentloaded
        page.wait_for_load_state("domcontentloaded", timeout=timeout)


def click_element_with_retry(page: Page, selector: str, max_retries: int = 3, delay: float = 1.0):
    """Click element with retry logic"""
    for attempt in range(max_retries):
        try:
            element = wait_for_element(page, selector, timeout=5000)
            element.click()
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Click attempt {attempt + 1} failed: {e}")
                time.sleep(delay)
            else:
                raise


def take_screenshot(page: Page, path: str):
    """Take screenshot of current page"""
    page.screenshot(path=path, full_page=True)


def get_page_content(page: Page) -> str:
    """Get full page HTML content"""
    return page.content()


def execute_script(page: Page, script: str, *args) -> Any:
    """Execute JavaScript in page context"""
    return page.evaluate(script, *args)


def handle_dialog(page: Page, accept: bool = True, prompt_text: str = ""):
    """Handle JavaScript dialogs"""
    def dialog_handler(dialog):
        if prompt_text and dialog.type == "prompt":
            dialog.accept(prompt_text)
        elif accept:
            dialog.accept()
        else:
            dialog.dismiss()
    
    page.on("dialog", dialog_handler)


def wait_for_navigation(page: Page, timeout: int = 30000):
    """Wait for navigation to complete"""
    page.wait_for_load_state("load", timeout=timeout)


def get_cookies(page: Page) -> List[Dict[str, Any]]:
    """Get all cookies from current context"""
    return page.context.cookies()


def set_cookies(page: Page, cookies: List[Dict[str, Any]]):
    """Set cookies in current context"""
    page.context.add_cookies(cookies)


def clear_cookies(page: Page):
    """Clear all cookies from current context"""
    page.context.clear_cookies()


def set_local_storage(page: Page, key: str, value: str):
    """Set local storage item"""
    page.evaluate(f"localStorage.setItem('{key}', '{value}')")


def get_local_storage(page: Page, key: str) -> Optional[str]:
    """Get local storage item"""
    return page.evaluate(f"localStorage.getItem('{key}')")


def handle_new_page(context: BrowserContext, handler):
    """Handle new pages/tabs opened in context"""
    context.on("page", handler)