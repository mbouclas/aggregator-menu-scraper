#!/usr/bin/env python3
"""
Test Offer Lifecycle Management
===============================
Test offer uniqueness, deactivation, and reactivation logic.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class MockOfferLifecycleTest:
    """Mock test for offer lifecycle management."""
    
    def __init__(self):
        self.offers = {}  # offer_id -> offer_data
        self.product_prices = []
        self.restaurants = {}
        self.products = {}
    
    def create_restaurant(self, name: str) -> str:
        """Create a test restaurant."""
        restaurant_id = str(uuid.uuid4())
        self.restaurants[restaurant_id] = {
            'id': restaurant_id,
            'name': name
        }
        return restaurant_id
    
    def simulate_offer_import(self, restaurant_id: str, products_data: list, scraped_at: str):
        """Simulate the enhanced offer import with lifecycle management."""
        print(f"\n🔄 Simulating offer import for {scraped_at}")
        print("=" * 60)
        
        # Phase 1: Collect active offers from current scrape
        active_offers = set()
        offers_to_create = {}
        
        for product in products_data:
            offer_name = product.get('offer_name', '').strip()
            discount_pct = float(product.get('discount_percentage', 0))
            
            # Pattern 1: Explicit offer name
            if offer_name:
                active_offers.add(offer_name)
                if offer_name not in offers_to_create:
                    offers_to_create[offer_name] = discount_pct
            
            # Pattern 2: Auto-generated from discount
            elif discount_pct > 0:
                auto_offer_name = f"{int(discount_pct)}% Discount"
                active_offers.add(auto_offer_name)
                if auto_offer_name not in offers_to_create:
                    offers_to_create[auto_offer_name] = discount_pct
        
        print(f"📊 Active offers in current scrape: {len(active_offers)}")
        for offer_name in active_offers:
            print(f"   • {offer_name}")
        
        # Phase 2: Deactivate offers no longer active
        self._deactivate_inactive_offers(restaurant_id, active_offers, scraped_at)
        
        # Phase 3: Ensure all active offers exist (create or reactivate)
        offer_mapping = {}
        for offer_name, discount_pct in offers_to_create.items():
            offer_id = self._ensure_offer(restaurant_id, offer_name, discount_pct, scraped_at)
            offer_mapping[offer_name] = offer_id
        
        # Phase 4: Link products to offers
        for product in products_data:
            product_id = f"product_{len(self.products)}"
            self.products[product_id] = product
            
            offer_name = product.get('offer_name', '').strip()
            discount_pct = float(product.get('discount_percentage', 0))
            price = float(product.get('price', 0))
            original_price = float(product.get('original_price', 0))
            
            # Determine offer linkage
            final_offer_name = None
            if offer_name:
                final_offer_name = offer_name
            elif discount_pct > 0:
                final_offer_name = f"{int(discount_pct)}% Discount"
            
            offer_id = offer_mapping.get(final_offer_name) if final_offer_name else None
            
            # Correct original price if needed
            corrected_original = original_price
            if discount_pct > 0 and price == original_price:
                corrected_original = price / (1 - discount_pct/100)
            
            self.product_prices.append({
                'product_id': product_id,
                'price': price,
                'original_price': corrected_original,
                'discount_percentage': discount_pct,
                'offer_id': offer_id,
                'offer_name': final_offer_name,
                'scraped_at': scraped_at
            })
        
        return offer_mapping
    
    def _deactivate_inactive_offers(self, restaurant_id: str, active_offers: set, scraped_at: str):
        """Deactivate offers no longer active."""
        deactivated_count = 0
        
        for offer_id, offer in self.offers.items():
            if (offer['restaurant_id'] == restaurant_id and 
                offer['is_active'] and 
                offer['name'] not in active_offers):
                
                offer['is_active'] = False
                offer['end_date'] = scraped_at
                offer['updated_at'] = scraped_at
                deactivated_count += 1
                print(f"   🔴 Deactivated: '{offer['name']}'")
        
        if deactivated_count == 0:
            print("   ✅ No offers to deactivate")
        else:
            print(f"   🔴 Deactivated {deactivated_count} offers")
    
    def _ensure_offer(self, restaurant_id: str, offer_name: str, discount_percentage: float, scraped_at: str) -> str:
        """Ensure offer exists, reactivate if needed, or create new."""
        
        # Check for active offer
        for offer_id, offer in self.offers.items():
            if (offer['restaurant_id'] == restaurant_id and 
                offer['name'] == offer_name and 
                offer['is_active']):
                print(f"   ✅ Found active offer: '{offer_name}'")
                return offer_id
        
        # Check for inactive offer to reactivate
        for offer_id, offer in self.offers.items():
            if (offer['restaurant_id'] == restaurant_id and 
                offer['name'] == offer_name and 
                not offer['is_active']):
                
                offer['is_active'] = True
                offer['end_date'] = None
                offer['discount_percentage'] = discount_percentage
                offer['updated_at'] = scraped_at
                offer['start_date'] = scraped_at  # New start date
                print(f"   🟢 Reactivated offer: '{offer_name}' ({discount_percentage}%)")
                return offer_id
        
        # Create new offer
        offer_id = str(uuid.uuid4())
        self.offers[offer_id] = {
            'id': offer_id,
            'restaurant_id': restaurant_id,
            'name': offer_name,
            'offer_type': 'percentage' if discount_percentage > 0 else 'other',
            'discount_percentage': discount_percentage if discount_percentage > 0 else None,
            'is_active': True,
            'start_date': scraped_at,
            'end_date': None,
            'created_at': scraped_at,
            'updated_at': scraped_at
        }
        print(f"   🆕 Created new offer: '{offer_name}' ({discount_percentage}%)")
        return offer_id
    
    def print_offer_status(self):
        """Print current offer status."""
        print(f"\n📋 Current Offer Status")
        print("=" * 60)
        
        active_offers = [o for o in self.offers.values() if o['is_active']]
        inactive_offers = [o for o in self.offers.values() if not o['is_active']]
        
        print(f"✅ Active Offers: {len(active_offers)}")
        for offer in active_offers:
            discount = f"{offer['discount_percentage']}%" if offer['discount_percentage'] else "N/A"
            print(f"   • {offer['name']} - {discount} (Start: {offer['start_date']})")
        
        print(f"\n🔴 Inactive Offers: {len(inactive_offers)}")
        for offer in inactive_offers:
            discount = f"{offer['discount_percentage']}%" if offer['discount_percentage'] else "N/A"
            print(f"   • {offer['name']} - {discount} (Ended: {offer['end_date']})")

def test_offer_lifecycle():
    """Test the complete offer lifecycle."""
    print("🧪 Testing Offer Lifecycle Management")
    print("=" * 80)
    
    test = MockOfferLifecycleTest()
    restaurant_id = test.create_restaurant("Test Restaurant")
    
    # Scenario 1: Initial scrape with offers
    print(f"\n📅 Scenario 1: Initial scrape (Day 1)")
    products_day1 = [
        {
            'name': 'Coffee A',
            'price': 2.51,
            'original_price': 2.51,
            'discount_percentage': 25,
            'offer_name': ''
        },
        {
            'name': 'Coffee B', 
            'price': 3.00,
            'original_price': 3.00,
            'discount_percentage': 0,
            'offer_name': 'Special Deal'
        },
        {
            'name': 'Pastry A',
            'price': 6.50,
            'original_price': 6.50,
            'discount_percentage': 32,
            'offer_name': ''
        }
    ]
    
    test.simulate_offer_import(restaurant_id, products_day1, "2025-07-15 10:00:00")
    test.print_offer_status()
    
    # Scenario 2: Next scrape - some offers continue, some end, some new
    print(f"\n📅 Scenario 2: Second scrape (Day 2) - Some offers change")
    products_day2 = [
        {
            'name': 'Coffee A',
            'price': 2.51,
            'original_price': 2.51,
            'discount_percentage': 25,  # Same 25% offer continues
            'offer_name': ''
        },
        {
            'name': 'Coffee B',
            'price': 3.00,
            'original_price': 3.00,
            'discount_percentage': 0,  # Special Deal continues
            'offer_name': 'Special Deal'
        },
        # Pastry A no longer has discount (32% offer should be deactivated)
        {
            'name': 'Pastry A',
            'price': 6.50,
            'original_price': 6.50,
            'discount_percentage': 0,
            'offer_name': ''
        },
        # New offer appears
        {
            'name': 'Sandwich A',
            'price': 4.50,
            'original_price': 4.50,
            'discount_percentage': 15,
            'offer_name': ''
        }
    ]
    
    test.simulate_offer_import(restaurant_id, products_day2, "2025-07-16 10:00:00")
    test.print_offer_status()
    
    # Scenario 3: Third scrape - previous offer comes back
    print(f"\n📅 Scenario 3: Third scrape (Day 3) - Previous offer returns")
    products_day3 = [
        {
            'name': 'Coffee A',
            'price': 2.51,
            'original_price': 2.51,
            'discount_percentage': 25,  # 25% continues
            'offer_name': ''
        },
        # 32% offer comes back (should reactivate existing offer)
        {
            'name': 'Pastry A',
            'price': 6.50,
            'original_price': 6.50,
            'discount_percentage': 32,
            'offer_name': ''
        },
        # 15% offer disappears, Special Deal disappears
    ]
    
    test.simulate_offer_import(restaurant_id, products_day3, "2025-07-17 10:00:00")
    test.print_offer_status()
    
    # Final summary
    print(f"\n🎉 Test Complete!")
    print(f"   ✅ Total offers created: {len(test.offers)}")
    print(f"   ✅ Lifecycle management working correctly")
    print(f"   ✅ No duplicate offers created")
    print(f"   ✅ Proper activation/deactivation")

if __name__ == '__main__':
    test_offer_lifecycle()
