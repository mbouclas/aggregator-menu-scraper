"""
Fast Selenium utilities optimized for performance.

This module provides high-performance Selenium functionality with
aggressive optimizations for speed while maintaining data quality.
"""
import os
import time
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import logging

# Try to import webdriver-manager for automatic driver management
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class FastSeleniumDriver:
    """
    High-performance Selenium WebDriver optimized for speed.
    
    Provides aggressive optimizations including:
    - Disabled images, CSS, and non-essential resources
    - Faster page load strategies
    - Reduced wait times
    - Minimal DOM processing
    """
    
    def __init__(self, headless: bool = True, fast_mode: bool = True, 
                 implicit_wait: int = 3, page_load_timeout: int = 15):
        """
        Initialize the fast Selenium driver.
        
        Args:
            headless: Run browser in headless mode
            fast_mode: Enable aggressive performance optimizations
            implicit_wait: Implicit wait timeout in seconds (reduced from 10)
            page_load_timeout: Page load timeout in seconds (reduced from 30)
        """
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless
        self.fast_mode = fast_mode
        self.implicit_wait = implicit_wait
        self.page_load_timeout = page_load_timeout
        self.logger = logging.getLogger(__name__)
        
    def __enter__(self):
        """Context manager entry."""
        self.start_driver()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.quit()
        
    def start_driver(self) -> webdriver.Chrome:
        """
        Start Chrome WebDriver with aggressive performance optimizations.
        
        Returns:
            Configured Chrome WebDriver instance optimized for speed
            
        Raises:
            WebDriverException: If driver cannot be started
        """
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless=new')  # Use new headless mode
            
            # Essential anti-detection options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            if self.fast_mode:
                # Aggressive performance optimizations
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-features=VizDisplayCompositor')
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-plugins')
                chrome_options.add_argument('--disable-images')
                chrome_options.add_argument('--disable-javascript-harmony')
                chrome_options.add_argument('--disable-background-networking')
                chrome_options.add_argument('--disable-background-timer-throttling')
                chrome_options.add_argument('--disable-renderer-backgrounding')
                chrome_options.add_argument('--disable-features=TranslateUI')
                chrome_options.add_argument('--disable-ipc-flooding-protection')
                chrome_options.add_argument('--disable-client-side-phishing-detection')
                chrome_options.add_argument('--disable-sync')
                chrome_options.add_argument('--disable-default-apps')
                chrome_options.add_argument('--disable-web-security')
                chrome_options.add_argument('--disable-features=VizDisplayCompositor')
                
                # Memory and CPU optimizations
                chrome_options.add_argument('--memory-pressure-off')
                chrome_options.add_argument('--max_old_space_size=4096')
                chrome_options.add_argument('--aggressive-cache-discard')
                
                # Network optimizations
                chrome_options.add_argument('--disable-background-networking')
                chrome_options.add_argument('--disable-domain-reliability')
                
                # Disable unnecessary features for food delivery sites
                chrome_prefs = {
                    "profile.default_content_setting_values": {
                        "images": 2,                    # Block images
                        "plugins": 2,                   # Block plugins  
                        "popups": 2,                    # Block popups
                        "geolocation": 2,               # Block location
                        "notifications": 2,             # Block notifications
                        "media_stream": 2,              # Block media
                        "automatic_downloads": 2,       # Block downloads
                    },
                    "profile.managed_default_content_settings": {
                        "images": 2,
                        "stylesheets": 2,               # Block CSS (risky but faster)
                    },
                    "webkit.webprefs.loads_images_automatically": False,
                    "profile.default_content_settings.popups": 0,
                }
                chrome_options.add_experimental_option("prefs", chrome_prefs)
                
                # Use eager page load strategy - don't wait for all resources
                chrome_options.add_argument('--page-load-strategy=eager')
            
            # Optimized user agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Smaller window for less rendering overhead
            chrome_options.add_argument('--window-size=1366,768')
            
            # Driver setup with performance monitoring
            start_time = time.time()
            
            try:
                if WEBDRIVER_MANAGER_AVAILABLE:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    self.driver = webdriver.Chrome(options=chrome_options)
            except WebDriverException:
                self.logger.info("Auto driver management failed, trying basic service...")
                service = Service()
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configure aggressive timeouts for speed
            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            
            # Additional performance tweaks
            if self.fast_mode:
                # Set script timeout lower
                self.driver.set_script_timeout(10)
                
                # Disable automation detection
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Clear cache and optimize memory
                self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
                self.driver.execute_cdp_cmd('Runtime.runIfWaitingForDebugger', {})
            
            startup_time = time.time() - start_time
            self.logger.info(f"Fast Chrome WebDriver started in {startup_time:.2f}s")
            return self.driver
            
        except Exception as e:
            self.logger.error(f"Failed to start fast Chrome driver: {e}")
            raise WebDriverException(f"Could not start fast Chrome driver: {e}")
    
    def fast_get_page(self, url: str, wait_for_selector: str = None, max_wait: int = 10) -> bool:
        """
        Load page with minimal waiting optimized for speed.
        
        Args:
            url: URL to load
            wait_for_selector: CSS selector to wait for (optional)
            max_wait: Maximum time to wait for selector
            
        Returns:
            True if page loaded successfully, False otherwise
        """
        if not self.driver:
            raise RuntimeError("Driver not started. Call start_driver() first.")
        
        try:
            start_time = time.time()
            self.driver.get(url)
            
            if wait_for_selector:
                try:
                    # Wait only for essential content
                    WebDriverWait(self.driver, max_wait).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                except TimeoutException:
                    self.logger.warning(f"Timeout waiting for selector '{wait_for_selector}' on {url}")
                    # Continue anyway - might still have content
            
            load_time = time.time() - start_time
            self.logger.info(f"Page loaded in {load_time:.2f}s: {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load page {url}: {e}")
            return False
    
    def fast_scroll_and_wait(self, scroll_pause: float = 0.5, max_scrolls: int = 3) -> None:
        """
        Fast scrolling to trigger lazy loading with minimal waits.
        
        Args:
            scroll_pause: Time to pause between scrolls (reduced)
            max_scrolls: Maximum number of scroll attempts
        """
        if not self.driver:
            return
        
        try:
            for i in range(max_scrolls):
                # Scroll down faster
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(scroll_pause)
                
                # Quick scroll to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause)
                
                # Back to top for consistency
                if i == max_scrolls - 1:
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(scroll_pause)
                    
        except Exception as e:
            self.logger.warning(f"Error during fast scrolling: {e}")
    
    def get_fast_soup(self) -> BeautifulSoup:
        """
        Get BeautifulSoup object with minimal processing.
        
        Returns:
            BeautifulSoup object for fast parsing
        """
        if not self.driver:
            raise RuntimeError("Driver not started")
        
        try:
            # Get page source without waiting
            html = self.driver.page_source
            
            # Use lxml parser for speed (faster than html.parser)
            return BeautifulSoup(html, 'lxml')
            
        except Exception as e:
            self.logger.error(f"Error creating fast soup: {e}")
            # Fallback to html.parser if lxml fails
            return BeautifulSoup(self.driver.page_source, 'html.parser')
    
    def fast_find_element_safe(self, by: By, value: str, timeout: int = 3) -> Optional[Any]:
        """
        Find element with reduced timeout for speed.
        
        Args:
            by: Selenium By selector type
            value: Selector value
            timeout: Reduced timeout in seconds
            
        Returns:
            WebElement if found, None otherwise
        """
        if not self.driver:
            return None
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None
        except Exception as e:
            self.logger.warning(f"Error finding element {value}: {e}")
            return None
    
    def quit(self):
        """Clean up and quit the driver."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Fast Chrome WebDriver closed")
            except Exception as e:
                self.logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None


def create_fast_driver(headless: bool = True, ultra_fast: bool = True) -> FastSeleniumDriver:
    """
    Factory function to create optimized Selenium driver.
    
    Args:
        headless: Run in headless mode
        ultra_fast: Enable most aggressive optimizations
        
    Returns:
        Configured FastSeleniumDriver instance
    """
    # Ultra-fast settings sacrifice some compatibility for maximum speed
    if ultra_fast:
        return FastSeleniumDriver(
            headless=headless,
            fast_mode=True,
            implicit_wait=2,        # Very aggressive
            page_load_timeout=10    # Very aggressive
        )
    else:
        return FastSeleniumDriver(
            headless=headless,
            fast_mode=True,
            implicit_wait=3,        # Balanced
            page_load_timeout=15    # Balanced
        )
