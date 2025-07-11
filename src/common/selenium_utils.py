"""
Selenium utilities for web scraping JavaScript-heavy websites.

This module provides common Selenium functionality including
driver setup, page waiting, and JavaScript execution.
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


class SeleniumDriver:
    """
    Selenium WebDriver wrapper for JavaScript-heavy website scraping.
    
    Provides Chrome driver setup with anti-detection features,
    intelligent waiting, and BeautifulSoup integration.
    """
    
    def __init__(self, headless: bool = True, implicit_wait: int = 10, page_load_timeout: int = 30):
        """
        Initialize the Selenium driver.
        
        Args:
            headless: Run browser in headless mode
            implicit_wait: Implicit wait timeout in seconds
            page_load_timeout: Page load timeout in seconds
        """
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless
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
        Start Chrome WebDriver with optimized settings.
        
        Returns:
            Configured Chrome WebDriver instance
            
        Raises:
            WebDriverException: If driver cannot be started
        """
        try:
            # Chrome options for anti-detection and performance
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            # Anti-detection options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Performance options
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Skip image loading for speed
            chrome_options.add_argument('--disable-javascript-harmony-shipping')
            
            # User agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Window size
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Try to use system Chrome installation or webdriver-manager
            try:
                if WEBDRIVER_MANAGER_AVAILABLE:
                    # Use webdriver-manager for automatic driver management
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    # Try system Chrome first
                    self.driver = webdriver.Chrome(options=chrome_options)
            except WebDriverException:
                # If both fail, try with basic service
                self.logger.info("Auto driver management failed, trying basic service...")
                service = Service()  # Basic service
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configure timeouts
            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("Chrome WebDriver started successfully")
            return self.driver
            
        except Exception as e:
            self.logger.error(f"Failed to start Chrome WebDriver: {e}")
            raise WebDriverException(f"Could not start Chrome WebDriver: {e}")
    
    def get_page(self, url: str, wait_for_content: bool = True, max_wait: int = 30) -> BeautifulSoup:
        """
        Load a page and wait for content to load.
        
        Args:
            url: URL to load
            wait_for_content: Whether to wait for dynamic content
            max_wait: Maximum time to wait for content
            
        Returns:
            BeautifulSoup object of the loaded page
            
        Raises:
            TimeoutException: If page doesn't load in time
        """
        if not self.driver:
            raise RuntimeError("Driver not started. Call start_driver() first.")
        
        self.logger.info(f"Loading page: {url}")
        
        try:
            # Load the page
            self.driver.get(url)
            
            if wait_for_content:
                # Wait for basic page structure
                WebDriverWait(self.driver, max_wait).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Wait for JavaScript to load content (check for spinners, skeletons)
                self._wait_for_dynamic_content(max_wait)
            
            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            self.logger.debug(f"Page loaded successfully, content length: {len(page_source)}")
            return soup
            
        except TimeoutException as e:
            self.logger.warning(f"Page load timeout: {e}")
            # Still try to return content even if timeout
            page_source = self.driver.page_source
            return BeautifulSoup(page_source, 'html.parser')
        
        except Exception as e:
            self.logger.error(f"Failed to load page: {e}")
            raise
    
    def _wait_for_dynamic_content(self, max_wait: int = 30):
        """
        Wait for dynamic content to load by checking for loading indicators.
        
        Args:
            max_wait: Maximum time to wait
        """
        wait = WebDriverWait(self.driver, max_wait)
        
        try:
            # Wait for spinners to disappear
            wait.until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='spinner'], [class*='loading']"))
            )
        except TimeoutException:
            self.logger.debug("No spinners found or timeout waiting for spinners to disappear")
        
        try:
            # Wait for skeleton loaders to disappear
            wait.until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='skeleton'], [class*='placeholder']"))
            )
        except TimeoutException:
            self.logger.debug("No skeleton loaders found or timeout waiting for skeletons to disappear")
        
        # Additional wait for content to stabilize
        time.sleep(2)
        
        # Check if we have meaningful content
        body = self.driver.find_element(By.TAG_NAME, "body")
        if body and len(body.text.strip()) > 100:
            self.logger.debug("Dynamic content appears to be loaded")
        else:
            self.logger.warning("Page may still be loading - limited text content found")
    
    def wait_for_element(self, selector: str, timeout: int = 10, by: str = "css") -> bool:
        """
        Wait for an element to be present.
        
        Args:
            selector: CSS selector or XPath
            timeout: Timeout in seconds
            by: Selector type ("css" or "xpath")
            
        Returns:
            True if element found, False otherwise
        """
        if not self.driver:
            return False
        
        try:
            by_type = By.CSS_SELECTOR if by == "css" else By.XPATH
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
            return True
        except TimeoutException:
            return False
    
    def scroll_to_load_content(self, scroll_pause_time: float = 2, max_scrolls: int = 5):
        """
        Scroll down the page to trigger lazy loading.
        
        Args:
            scroll_pause_time: Time to wait between scrolls
            max_scrolls: Maximum number of scrolls
        """
        if not self.driver:
            return
        
        self.logger.debug("Scrolling to load lazy content")
        
        for i in range(max_scrolls):
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            
            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if i == 0:
                last_height = new_height
            elif new_height == last_height:
                self.logger.debug(f"No new content after scroll {i+1}, stopping")
                break
            else:
                last_height = new_height
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
    
    def execute_script(self, script: str) -> Any:
        """
        Execute JavaScript in the browser.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result of script execution
        """
        if not self.driver:
            raise RuntimeError("Driver not started")
        
        return self.driver.execute_script(script)
    
    def quit(self):
        """Close the browser and quit the driver."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Chrome WebDriver closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None


def get_env_selenium_config() -> Dict[str, Any]:
    """
    Get Selenium configuration from environment variables.
    
    Returns:
        Dictionary with Selenium configuration
    """
    return {
        'headless': os.getenv('SELENIUM_HEADLESS', 'true').lower() == 'true',
        'implicit_wait': int(os.getenv('SELENIUM_IMPLICIT_WAIT', '10')),
        'page_load_timeout': int(os.getenv('SELENIUM_PAGE_LOAD_TIMEOUT', '30')),
    }
