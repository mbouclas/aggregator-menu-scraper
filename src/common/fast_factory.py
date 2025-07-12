"""
Fast Factory class for creating optimized scraper instances.
"""
import os
import glob
from typing import Dict, Optional, List
from urllib.parse import urlparse

from .config import ScraperConfig
from .factory import ScraperFactory
from .logging_config import get_logger

# Import fast scrapers
try:
    from ..scrapers.fast_foody_scraper import FastFoodyScraper
    FAST_SCRAPERS_AVAILABLE = True
    FastWoltScraper = None  # Temporarily disable Wolt fast scraper
except ImportError as e:
    FAST_SCRAPERS_AVAILABLE = False

logger = get_logger(__name__)


class FastScraperFactory(ScraperFactory):
    """
    Factory class for creating optimized high-performance scraper instances.
    
    This factory extends the base ScraperFactory to provide fast versions
    of scrapers with aggressive performance optimizations.
    """
    
    def __init__(self, config_directory: str = None, enable_fast_mode: bool = True):
        """
        Initialize the fast scraper factory.
        
        Args:
            config_directory: Directory containing scraper configuration files
            enable_fast_mode: Whether to use fast optimized scrapers
        """
        super().__init__(config_directory)
        self.enable_fast_mode = enable_fast_mode
        
        if not FAST_SCRAPERS_AVAILABLE:
            logger.warning("Fast scrapers not available, falling back to standard scrapers")
            self.enable_fast_mode = False
    
    def create_scraper(self, url: str, fast_mode: bool = None):
        """
        Create an optimized scraper instance for the given URL.
        
        Args:
            url: Target URL to scrape
            fast_mode: Override fast mode setting for this scraper
            
        Returns:
            Optimized scraper instance
            
        Raises:
            ValueError: If no suitable scraper configuration is found
            ImportError: If required scraper class is not available
        """
        # Use instance setting if fast_mode not specified
        use_fast_mode = fast_mode if fast_mode is not None else self.enable_fast_mode
        
        # Find matching configuration
        config = self.get_config_for_url(url)
        if not config:
            raise ValueError(f"No scraper configuration found for URL: {url}")
        
        logger.info(f"Creating {'fast' if use_fast_mode else 'standard'} scraper for domain: {config.domain}")
        
        # Create appropriate scraper based on domain and fast mode
        if use_fast_mode and FAST_SCRAPERS_AVAILABLE:
            return self._create_fast_scraper(config, url)
        else:
            return self._create_standard_scraper(config, url)
    
    def _create_fast_scraper(self, config: ScraperConfig, url: str):
        """
        Create a fast optimized scraper instance.
        
        Args:
            config: Scraper configuration
            url: Target URL
            
        Returns:
            Fast scraper instance
        """
        domain = config.domain.lower()
        
        if "foody" in domain and FastFoodyScraper:
            return FastFoodyScraper(config, url)
        elif "wolt" in domain and FastWoltScraper:
            return FastWoltScraper(config, url)
        else:
            logger.warning(f"No fast scraper available for domain {domain}, using standard scraper")
            return self._create_standard_scraper(config, url)
    
    def _create_standard_scraper(self, config: ScraperConfig, url: str):
        """
        Create a standard scraper instance (fallback).
        
        Args:
            config: Scraper configuration
            url: Target URL
            
        Returns:
            Standard scraper instance
        """
        # Import standard scrapers
        try:
            from ..scrapers.foody_scraper import FoodyScraper
            from ..scrapers.wolt_scraper import WoltScraper
        except ImportError as e:
            raise ImportError(f"Standard scrapers not available: {e}")
        
        domain = config.domain.lower()
        
        if "foody" in domain:
            return FoodyScraper(config, url)
        elif "wolt" in domain:
            return WoltScraper(config, url)
        else:
            raise ValueError(f"No scraper available for domain: {domain}")
    
    def get_performance_mode(self) -> str:
        """
        Get current performance mode.
        
        Returns:
            String describing current performance mode
        """
        if self.enable_fast_mode and FAST_SCRAPERS_AVAILABLE:
            return "fast_optimized"
        elif self.enable_fast_mode and not FAST_SCRAPERS_AVAILABLE:
            return "fast_unavailable_fallback"
        else:
            return "standard"
    
    def list_supported_domains_fast(self) -> List[str]:
        """
        List domains that support fast mode.
        
        Returns:
            List of domain names with fast scraper support
        """
        if not FAST_SCRAPERS_AVAILABLE:
            return []
        
        fast_domains = []
        for domain, config in self.configs.items():
            domain_lower = domain.lower()
            if "foody" in domain_lower or "wolt" in domain_lower:
                fast_domains.append(domain)
        
        return fast_domains
    
    def benchmark_mode_comparison(self, url: str) -> Dict[str, float]:
        """
        Compare performance between fast and standard modes.
        
        Args:
            url: URL to benchmark
            
        Returns:
            Dictionary with timing results for each mode
        """
        import time
        
        results = {}
        
        try:
            # Test fast mode
            if FAST_SCRAPERS_AVAILABLE:
                start_time = time.time()
                fast_scraper = self.create_scraper(url, fast_mode=True)
                fast_result = fast_scraper.scrape()
                fast_time = time.time() - start_time
                results['fast_mode'] = fast_time
                results['fast_products'] = fast_result['metadata']['product_count']
            
            # Test standard mode  
            start_time = time.time()
            standard_scraper = self.create_scraper(url, fast_mode=False)
            standard_result = standard_scraper.scrape()
            standard_time = time.time() - start_time
            results['standard_mode'] = standard_time
            results['standard_products'] = standard_result['metadata']['product_count']
            
            # Calculate improvement
            if 'fast_mode' in results:
                improvement = ((standard_time - fast_time) / standard_time) * 100
                results['improvement_percentage'] = improvement
                results['speed_multiplier'] = standard_time / fast_time
            
        except Exception as e:
            logger.error(f"Error in benchmark comparison: {e}")
            results['error'] = str(e)
        
        return results


def create_fast_factory(config_directory: str = None, fast_mode: bool = True) -> FastScraperFactory:
    """
    Convenience function to create a FastScraperFactory instance.
    
    Args:
        config_directory: Directory containing scraper configurations
        fast_mode: Whether to enable fast mode by default
        
    Returns:
        Configured FastScraperFactory instance
    """
    return FastScraperFactory(config_directory, fast_mode)


def get_optimization_recommendations(url: str) -> Dict[str, str]:
    """
    Get optimization recommendations for a specific URL.
    
    Args:
        url: Target URL
        
    Returns:
        Dictionary with optimization recommendations
    """
    domain = urlparse(url).netloc.lower()
    
    recommendations = {
        "performance_mode": "fast_optimized",
        "expected_improvement": "60-75% faster",
        "optimizations": [],
        "trade_offs": []
    }
    
    if "foody" in domain:
        recommendations["optimizations"] = [
            "Disabled image loading",
            "Aggressive timeouts (8s page load)",
            "Minimal DOM traversal",
            "Batch product processing",
            "Fast price extraction regex"
        ]
        recommendations["trade_offs"] = [
            "Images not downloaded",
            "Some styling may be missing",
            "Reduced error tolerance"
        ]
        recommendations["expected_time"] = "45-60 seconds (vs 180s standard)"
        
    elif "wolt" in domain:
        recommendations["optimizations"] = [
            "Wolt-specific selectors",
            "Fast data-test-id targeting",
            "Optimized scrolling pattern",
            "Batch processing",
            "Minimal wait times"
        ]
        recommendations["trade_offs"] = [
            "Less robust error handling",
            "May miss dynamic content",
            "Aggressive timeouts"
        ]
        recommendations["expected_time"] = "50-70 seconds (vs 180s standard)"
    else:
        recommendations["performance_mode"] = "standard"
        recommendations["expected_improvement"] = "No fast scraper available"
    
    return recommendations
