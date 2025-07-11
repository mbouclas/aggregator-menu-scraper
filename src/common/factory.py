"""
Factory class for creating and managing scraper configurations.
"""
import os
import glob
from typing import Dict, Optional, List
from urllib.parse import urlparse

from .config import ScraperConfig
from .logging_config import get_logger

logger = get_logger(__name__)


class ScraperFactory:
    """
    Factory class for loading and managing scraper configurations.
    
    This class handles loading all available scraper configurations
    and selecting the appropriate one based on URL matching.
    """
    
    def __init__(self, config_directory: str = None):
        """
        Initialize the scraper factory.
        
        Args:
            config_directory: Directory containing scraper configuration files.
                            If None, uses the default scrapers/ directory.
        """
        if config_directory is None:
            # Default to scrapers/ directory relative to project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_directory = os.path.join(project_root, 'scrapers')
        
        self.config_directory = config_directory
        self.configs: Dict[str, ScraperConfig] = {}
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """
        Load all configuration files from the config directory.
        """
        if not os.path.exists(self.config_directory):
            logger.warning(f"Configuration directory not found: {self.config_directory}")
            return
        
        # Find all .md files in the config directory
        config_files = glob.glob(os.path.join(self.config_directory, "*.md"))
        
        # Filter out template.md
        config_files = [f for f in config_files if not f.endswith('template.md')]
        
        logger.info(f"Found {len(config_files)} configuration files")
        
        for config_file in config_files:
            try:
                config = ScraperConfig.from_markdown_file(config_file)
                self.configs[config.domain] = config
                logger.info(f"Loaded configuration for {config.domain}")
            except Exception as e:
                logger.error(f"Failed to load configuration from {config_file}: {e}")
    
    def get_config_for_url(self, url: str) -> Optional[ScraperConfig]:
        """
        Get the appropriate scraper configuration for a given URL.
        
        Args:
            url: The URL to find a configuration for
            
        Returns:
            ScraperConfig instance if a matching configuration is found,
            None otherwise
        """
        if not url:
            logger.warning("Empty URL provided")
            return None
        
        logger.debug(f"Finding configuration for URL: {url}")
        
        # Try to find a config that matches the URL
        for domain, config in self.configs.items():
            if config.matches_url(url):
                logger.info(f"Found matching configuration: {domain}")
                return config
        
        # Try to extract domain and find exact match
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Look for direct domain match
            if domain in self.configs:
                logger.info(f"Found direct domain match: {domain}")
                return self.configs[domain]
            
            # Look for partial domain matches
            for config_domain, config in self.configs.items():
                if domain in config_domain or config_domain in domain:
                    logger.info(f"Found partial domain match: {config_domain}")
                    return config
                    
        except Exception as e:
            logger.error(f"Error parsing URL {url}: {e}")
        
        logger.warning(f"No configuration found for URL: {url}")
        return None
    
    def get_config_by_domain(self, domain: str) -> Optional[ScraperConfig]:
        """
        Get configuration by domain name.
        
        Args:
            domain: Domain name to look up
            
        Returns:
            ScraperConfig instance if found, None otherwise
        """
        return self.configs.get(domain.lower())
    
    def list_available_domains(self) -> List[str]:
        """
        Get a list of all available domain configurations.
        
        Returns:
            List of domain names that have configurations
        """
        return list(self.configs.keys())
    
    def reload_configs(self) -> None:
        """
        Reload all configurations from the config directory.
        
        This is useful if configuration files have been updated.
        """
        logger.info("Reloading all configurations")
        self.configs.clear()
        self._load_all_configs()
    
    def add_config(self, config: ScraperConfig) -> None:
        """
        Add a configuration programmatically.
        
        Args:
            config: ScraperConfig instance to add
        """
        self.configs[config.domain] = config
        logger.info(f"Added configuration for domain: {config.domain}")
    
    def get_config_summary(self) -> Dict[str, Dict[str, any]]:
        """
        Get a summary of all loaded configurations.
        
        Returns:
            Dictionary with domain as key and config summary as value
        """
        summary = {}
        for domain, config in self.configs.items():
            summary[domain] = {
                'domain': config.domain,
                'base_url': config.base_url,
                'scraping_method': config.scraping_method,
                'requires_javascript': config.requires_javascript,
                'anti_bot_protection': config.anti_bot_protection,
                'has_testing_urls': len(config.testing_urls) > 0,
                'url_pattern': config.url_pattern or 'Not specified'
            }
        return summary
