"""
Configuration classes for web scrapers.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ScraperConfig:
    """
    Base configuration class for website scrapers.
    
    This class handles loading and parsing markdown configuration files
    for different websites.
    """
    domain: str
    base_url: str = ""
    item_selector: str = ""
    title_selector: str = ""
    price_selector: str = ""
    category_selector: str = ""
    restaurant_name_selector: str = ""
    brand_name_selector: str = ""
    url_pattern: str = ""
    requires_javascript: bool = False
    anti_bot_protection: str = "none"
    scraping_method: str = "requests"
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    testing_urls: List[str] = field(default_factory=list)
    
    @classmethod
    def from_markdown_file(cls, file_path: str) -> 'ScraperConfig':
        """
        Load configuration from a markdown file.
        
        Args:
            file_path: Path to the markdown configuration file
            
        Returns:
            ScraperConfig instance with loaded configuration
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration file is malformed
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        logger.info(f"Loading configuration from {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract domain from filename
        filename = os.path.basename(file_path)
        domain = filename.replace('.md', '').replace('_', '.')
        
        # Try to extract domain from content first
        domain_from_content = cls._extract_domain_from_content(content)
        if domain_from_content:
            domain = domain_from_content
        
        config = cls(domain=domain)
        config._parse_markdown_content(content)
        
        logger.info(f"Successfully loaded configuration for domain: {domain}")
        return config
    
    @classmethod
    def _extract_domain_from_content(cls, content: str) -> Optional[str]:
        """
        Extract domain from markdown content.
        
        Args:
            content: Raw markdown content
            
        Returns:
            Domain string if found, None otherwise
        """
        # Look for domain in various patterns
        patterns = [
            r'\*\*Domain\*\*:\s*([^\n\s]+)',  # **Domain**: example.com
            r'- \*\*Domain\*\*:\s*([^\n\s]+)',  # - **Domain**: example.com
            r'## Website Information.*?\*\*Domain\*\*:\s*([^\n\s]+)',  # In website info section
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _parse_markdown_content(self, content: str) -> None:
        """
        Parse markdown content and extract configuration values.
        
        Args:
            content: Raw markdown content from configuration file
        """
        # Parse simple template format (key-value pairs)
        self._parse_simple_format(content)
        
        # Parse detailed format (structured markdown)
        self._parse_detailed_format(content)
    
    def _parse_simple_format(self, content: str) -> None:
        """
        Parse simple template format with ### headers and code blocks.
        
        Example:
        ### base_url
        `https://example.com`
        
        ### item_selector
        ```css
        .product-card
        ```
        """
        # Pattern for ### header followed by code block or inline code
        pattern = r'###\s+(\w+)\s*\n(?:```[\w]*\n)?(.*?)(?:\n```|$)'
        
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        for key, value in matches:
            # Clean up the value
            value = value.strip().strip('`').strip()
            
            # Map to config attributes
            if hasattr(self, key):
                setattr(self, key, value)
                logger.debug(f"Set {key} = {value}")
    
    def _parse_detailed_format(self, content: str) -> None:
        """
        Parse detailed markdown format with structured sections.
        
        This handles the more complex foody.md format with sections
        like "## Scraping Strategy" and bullet points.
        """
        # Extract domain from URL Pattern if available
        url_pattern_match = re.search(r'\*\*URL Pattern\*\*:\s*`([^`]+)`', content)
        if url_pattern_match:
            self.url_pattern = url_pattern_match.group(1)
        
        # Extract scraping method
        method_match = re.search(r'\*\*Method\*\*:\s*([^\n]+)', content)
        if method_match:
            method = method_match.group(1).strip()
            if 'selenium' in method.lower():
                self.scraping_method = 'selenium'
                self.requires_javascript = True
        
        # Extract JavaScript requirement
        js_match = re.search(r'\*\*JavaScript Required\*\*:\s*([^\n]+)', content)
        if js_match:
            js_required = js_match.group(1).strip().lower()
            self.requires_javascript = js_required in ['yes', 'true']
        
        # Extract anti-bot protection info
        antibot_match = re.search(r'\*\*Anti-bot Protection\*\*:\s*([^\n]+)', content)
        if antibot_match:
            self.anti_bot_protection = antibot_match.group(1).strip()
        
        # Extract testing URLs
        testing_section = re.search(r'## Testing URLs\s*\n(.*?)(?=\n##|$)', content, re.DOTALL)
        if testing_section:
            url_lines = testing_section.group(1).strip().split('\n')
            for line in url_lines:
                url_match = re.search(r'https?://[^\s]+', line)
                if url_match:
                    self.testing_urls.append(url_match.group(0))
        
        # Extract custom selectors from detailed descriptions
        self._extract_custom_selectors(content)
    
    def _extract_custom_selectors(self, content: str) -> None:
        """
        Extract selector information from detailed descriptions.
        
        Args:
            content: Markdown content to parse
        """
        # Restaurant name selector
        restaurant_match = re.search(r'\*\*Restaurant Name\*\*:\s*([^*]+)', content)
        if restaurant_match:
            desc = restaurant_match.group(1).strip()
            # Try to extract CSS selector from description
            selector_match = re.search(r'`([^`]+)`', desc)
            if selector_match:
                self.restaurant_name_selector = selector_match.group(1)
        
        # Product title selector
        title_match = re.search(r'\*\*Title\*\*:\s*([^*]+)', content)
        if title_match:
            desc = title_match.group(1).strip()
            selector_match = re.search(r'`([^`]+)`', desc)
            if selector_match:
                self.title_selector = selector_match.group(1)
        
        # Category selector
        category_match = re.search(r'\*\*Category\*\*:\s*([^*]+)', content)
        if category_match:
            desc = category_match.group(1).strip()
            # Store the full description as custom rule
            self.custom_rules['category_extraction'] = desc
    
    def get_selector(self, selector_type: str) -> str:
        """
        Get a CSS selector for the given type.
        
        Args:
            selector_type: Type of selector (item, title, price, etc.)
            
        Returns:
            CSS selector string or empty string if not found
        """
        selector_map = {
            'item': self.item_selector,
            'title': self.title_selector,
            'price': self.price_selector,
            'category': self.category_selector,
            'restaurant_name': self.restaurant_name_selector,
            'brand_name': self.brand_name_selector,
        }
        
        return selector_map.get(selector_type, "")
    
    def matches_url(self, url: str) -> bool:
        """
        Check if this configuration matches the given URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if this config should be used for the URL
        """
        parsed_url = urlparse(url)
        domain_matches = self.domain in parsed_url.netloc
        
        if self.url_pattern:
            pattern_matches = re.match(self.url_pattern, url) is not None
            return domain_matches and pattern_matches
        
        return domain_matches
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return f"ScraperConfig(domain={self.domain}, method={self.scraping_method})"
