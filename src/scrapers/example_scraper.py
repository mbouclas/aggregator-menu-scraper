"""
Example implementation of BaseScraper for demonstration purposes.

This shows how to extend the BaseScraper class with placeholder implementations.
"""
from typing import Dict, List, Any

from .base_scraper import BaseScraper


class ExampleScraper(BaseScraper):
    """
    Example scraper implementation with placeholder data.
    
    This demonstrates the structure and methods required when
    extending the BaseScraper class.
    """
    
    def extract_restaurant_info(self) -> Dict[str, Any]:
        """
        Extract restaurant information (placeholder implementation).
        
        In a real implementation, this would parse the website's HTML
        to extract restaurant details using the configured selectors.
        """
        self.logger.info("Extracting restaurant information")
        
        try:
            # Placeholder implementation - would use actual parsing logic
            restaurant_info = {
                "name": "Example Restaurant",
                "brand": "Example Brand",
                "address": "123 Example Street, Example City",
                "phone": "+1234567890",
                "rating": 4.5,
                "delivery_fee": 2.50,
                "minimum_order": 15.00,
                "delivery_time": "30-45 min",
                "cuisine_types": ["Italian", "Pizza"]
            }
            
            self.logger.debug(f"Extracted restaurant: {restaurant_info['name']}")
            return restaurant_info
            
        except Exception as e:
            self.logger.error(f"Failed to extract restaurant info: {e}")
            self._add_error("restaurant_extraction_failed", str(e))
            
            # Return default structure with empty values
            return {
                "name": "",
                "brand": "",
                "address": "",
                "phone": "",
                "rating": 0.0,
                "delivery_fee": 0.0,
                "minimum_order": 0.0,
                "delivery_time": "",
                "cuisine_types": []
            }
    
    def extract_categories(self) -> List[Dict[str, Any]]:
        """
        Extract product categories (placeholder implementation).
        
        In a real implementation, this would parse the website's category
        structure using the configured selectors.
        """
        self.logger.info("Extracting categories")
        
        try:
            # Placeholder implementation - would use actual parsing logic
            categories = [
                {
                    "id": "cat_1",
                    "name": "Appetizers",
                    "description": "Start your meal with these delicious appetizers",
                    "product_count": 5
                },
                {
                    "id": "cat_2", 
                    "name": "Main Courses",
                    "description": "Our signature main dishes",
                    "product_count": 12
                },
                {
                    "id": "cat_3",
                    "name": "Desserts",
                    "description": "Sweet treats to end your meal",
                    "product_count": 8
                }
            ]
            
            self.logger.debug(f"Extracted {len(categories)} categories")
            return categories
            
        except Exception as e:
            self.logger.error(f"Failed to extract categories: {e}")
            self._add_error("category_extraction_failed", str(e))
            return []
    
    def extract_products(self) -> List[Dict[str, Any]]:
        """
        Extract product information (placeholder implementation).
        
        In a real implementation, this would parse product listings
        using the configured selectors for title, price, etc.
        """
        self.logger.info("Extracting products")
        
        try:
            # Placeholder implementation - would use actual parsing logic
            products = [
                {
                    "id": "prod_1",
                    "name": "Margherita Pizza",
                    "description": "Classic pizza with tomato sauce, mozzarella, and fresh basil",
                    "price": 12.50,
                    "original_price": 15.00,
                    "currency": "EUR",
                    "discount_percentage": 16.67,
                    "category": "Main Courses",
                    "image_url": "https://example.com/images/margherita.jpg",
                    "availability": True,
                    "options": [
                        {"name": "Size", "choices": ["Small", "Medium", "Large"]},
                        {"name": "Crust", "choices": ["Thin", "Thick"]}
                    ]
                },
                {
                    "id": "prod_2",
                    "name": "Caesar Salad",
                    "description": "Fresh romaine lettuce with caesar dressing and croutons",
                    "price": 8.50,
                    "original_price": 8.50,
                    "currency": "EUR",
                    "discount_percentage": 0.0,
                    "category": "Appetizers",
                    "image_url": "https://example.com/images/caesar.jpg",
                    "availability": True,
                    "options": [
                        {"name": "Protein", "choices": ["Chicken", "Shrimp", "None"]}
                    ]
                },
                {
                    "id": "prod_3",
                    "name": "Tiramisu",
                    "description": "Traditional Italian dessert with coffee and mascarpone",
                    "price": 6.00,
                    "original_price": 6.00,
                    "currency": "EUR",
                    "discount_percentage": 0.0,
                    "category": "Desserts",
                    "image_url": "https://example.com/images/tiramisu.jpg",
                    "availability": False,
                    "options": []
                }
            ]
            
            self.logger.debug(f"Extracted {len(products)} products")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to extract products: {e}")
            self._add_error("product_extraction_failed", str(e))
            return []
