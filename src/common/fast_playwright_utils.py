"""
Fast Playwright utilities for high-performance web scraping.

This module provides optimized Playwright configurations with aggressive
performance settings to minimize scraping time while maintaining reliability.
"""
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Playwright
from typing import Optional, List, Dict, Any, Union
import logging
import time

logger = logging.getLogger(__name__)


class FastPlaywrightManager:
    """
    High-performance Playwright manager with aggressive optimizations.
    
    Configured for maximum speed with disabled images, CSS, fonts,
    and reduced timeouts for fast scraping operations.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 10000, 
                 disable_images: bool = True, disable_css: bool = True):
        """
        Initialize fast Playwright manager.
        
        Args:
            headless: Run browser in headless mode
            timeout: Page timeout in milliseconds (reduced from 30s to 10s)
            disable_images: Disable image loading for faster performance
            disable_css: Disable CSS loading for faster performance
        """
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.headless = headless
        self.timeout = timeout
        self.disable_images = disable_images
        self.disable_css = disable_css
        self.contexts: List[BrowserContext] = []
        
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def start(self):
        """Start Playwright with performance optimizations"""
        if not self.playwright:
            logger.info("Starting fast Playwright with performance optimizations")
            self.playwright = sync_playwright().start()
            
    def create_fast_driver(self, **kwargs) -> Page:
        """
        Create a fast-optimized page for high-performance scraping.
        
        Returns:
            Playwright Page instance with aggressive optimizations
        """
        self.start()
        
        if not self.browser:
            # Launch browser with aggressive performance flags
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-sync',
                '--disable-plugins',
                '--disable-extensions',
                '--disable-default-apps',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-component-extensions-with-background-pages',
                '--no-first-run',
                '--no-default-browser-check',
                '--aggressive-cache-discard',
                '--memory-pressure-off'
            ]
            
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=launch_args
            )
            
        # Create context with performance optimizations
        context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        # Add resource blocking for images and CSS if enabled
        if self.disable_images or self.disable_css:
            def handle_route(route, request):
                if self.disable_images and request.resource_type in ['image', 'imageset']:
                    route.abort()
                elif self.disable_css and request.resource_type == 'stylesheet':
                    route.abort()
                else:
                    route.continue_()
            
            context.route("**/*", handle_route)
            
        self.contexts.append(context)
        
        # Create page with fast settings
        page = context.new_page()
        
        # Set aggressive timeouts for fast operation
        page.set_default_timeout(self.timeout)  # 10s instead of 30s
        page.set_default_navigation_timeout(self.timeout)  # 10s instead of 30s
        
        logger.info(f"Fast Playwright driver created with {self.timeout}ms timeout")
        return page
        
    def close(self):
        """Close all contexts and browser"""
        try:
            for context in self.contexts:
                try:
                    context.close()
                except Exception as e:
                    logger.warning(f"Error closing context: {e}")
                    
            if self.browser:
                self.browser.close()
                self.browser = None
                
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
                
            self.contexts.clear()
            logger.info("Fast Playwright manager closed successfully")
            
        except Exception as e:
            logger.warning(f"Error during fast Playwright cleanup: {e}")


def create_fast_driver(headless: bool = True, timeout: int = 10000, 
                      disable_images: bool = True, disable_css: bool = True) -> Page:
    """
    Create a fast-optimized Playwright page.
    
    Args:
        headless: Run browser in headless mode
        timeout: Page timeout in milliseconds
        disable_images: Disable image loading
        disable_css: Disable CSS loading
        
    Returns:
        Optimized Playwright Page instance
    """
    manager = FastPlaywrightManager(headless, timeout, disable_images, disable_css)
    return manager.create_fast_driver()


def fast_page_fetch(page: Page, url: str, wait_time: int = 2) -> str:
    """
    Fast page fetch with minimal wait time.
    
    Args:
        page: Playwright Page instance
        url: URL to fetch
        wait_time: Wait time after page load (reduced from 5s to 2s)
        
    Returns:
        Page HTML content
    """
    start_time = time.time()
    logger.info(f"Starting fast page fetch: {url}")
    
    try:
        # Navigate with fast timeout
        page.goto(url, wait_until='domcontentloaded')  # Don't wait for all resources
        
        # Minimal wait for dynamic content
        page.wait_for_timeout(wait_time * 1000)
        
        content = page.content()
        fetch_time = time.time() - start_time
        
        logger.info(f"Fast page fetch completed in {fetch_time:.2f}s")
        return content
        
    except Exception as e:
        logger.error(f"Fast page fetch failed: {e}")
        raise


def fast_wait_for_element(page: Page, selector: str, timeout: int = 5000) -> Optional[Any]:
    """
    Fast element wait with reduced timeout.
    
    Args:
        page: Playwright Page instance
        selector: CSS selector
        timeout: Wait timeout in milliseconds (reduced from 10s to 5s)
        
    Returns:
        Element handle or None
    """
    try:
        return page.wait_for_selector(selector, timeout=timeout)
    except Exception:
        return None


def fast_find_elements(page: Page, selector: str) -> List[Any]:
    """
    Fast element finding with immediate return.
    
    Args:
        page: Playwright Page instance
        selector: CSS selector
        
    Returns:
        List of element handles
    """
    try:
        return page.query_selector_all(selector)
    except Exception:
        return []


def fast_get_text_content(element) -> str:
    """
    Fast text content extraction.
    
    Args:
        element: Playwright element handle
        
    Returns:
        Text content or empty string
    """
    try:
        return element.text_content() or ""
    except Exception:
        return ""


def fast_scroll_to_bottom(page: Page, scroll_pause: float = 0.5) -> None:
    """
    Fast scroll to bottom with minimal pause time.
    
    Args:
        page: Playwright Page instance
        scroll_pause: Pause between scrolls (reduced from 1s to 0.5s)
    """
    try:
        last_height = page.evaluate("document.body.scrollHeight")
        
        while True:
            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content
            page.wait_for_timeout(int(scroll_pause * 1000))
            
            # Check if we've reached the bottom
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
    except Exception as e:
        logger.warning(f"Fast scroll failed: {e}")
