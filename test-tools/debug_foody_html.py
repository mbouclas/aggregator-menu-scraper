#!/usr/bin/env python3
"""
Debug script to inspect the HTML structure of foody.com.cy page.
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_foody_html():
    """Debug the HTML structure to understand why products aren't being found."""
    
    url = 'https://www.foody.com.cy/delivery/menu/costa-coffee'
    
    print(f"Debugging HTML structure for: {url}")
    
    # Setup session with proper headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    })
    
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"\nPage loaded successfully - {response.status_code}")
        print(f"Content length: {len(response.content)} bytes")
        
        # Debug: Look for h3 elements
        print(f"\n=== ALL H3 ELEMENTS ===")
        h3_elements = soup.find_all('h3')
        print(f"Found {len(h3_elements)} h3 elements:")
        for i, h3 in enumerate(h3_elements[:10]):  # Show first 10
            classes = h3.get('class', [])
            text = h3.get_text(strip=True)
            print(f"{i+1}. Classes: {classes}, Text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Debug: Look for elements with 'name' in class
        print(f"\n=== ELEMENTS WITH 'name' IN CLASS ===")
        name_elements = soup.find_all(class_=re.compile(r'name', re.IGNORECASE))
        print(f"Found {len(name_elements)} elements with 'name' in class:")
        for i, elem in enumerate(name_elements[:10]):
            classes = elem.get('class', [])
            text = elem.get_text(strip=True)
            tag = elem.name
            print(f"{i+1}. Tag: {tag}, Classes: {classes}, Text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Debug: Look for elements with 'price' in class
        print(f"\n=== ELEMENTS WITH 'price' IN CLASS ===")
        price_elements = soup.find_all(class_=re.compile(r'price', re.IGNORECASE))
        print(f"Found {len(price_elements)} elements with 'price' in class:")
        for i, elem in enumerate(price_elements[:10]):
            classes = elem.get('class', [])
            text = elem.get_text(strip=True)
            tag = elem.name
            print(f"{i+1}. Tag: {tag}, Classes: {classes}, Text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Debug: Look for elements with Euro symbol
        print(f"\n=== ELEMENTS WITH € SYMBOL ===")
        euro_elements = soup.find_all(string=re.compile(r'€'))
        print(f"Found {len(euro_elements)} elements with € symbol:")
        for i, text in enumerate(euro_elements[:10]):
            parent = text.parent if hasattr(text, 'parent') else None
            parent_classes = parent.get('class', []) if parent else []
            print(f"{i+1}. Text: '{str(text).strip()}', Parent: {parent.name if parent else 'None'}, Classes: {parent_classes}")
        
        # Debug: Look for common menu/product container patterns
        print(f"\n=== POTENTIAL PRODUCT CONTAINERS ===")
        container_selectors = [
            'div[class*="menu"]',
            'div[class*="item"]', 
            'div[class*="product"]',
            'div[class*="card"]',
            '[class*="cc-"]'  # Costa Coffee specific classes
        ]
        
        for selector in container_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"\nSelector '{selector}' found {len(elements)} elements:")
                for i, elem in enumerate(elements[:5]):
                    classes = elem.get('class', [])
                    text = elem.get_text(strip=True)
                    print(f"  {i+1}. Classes: {classes}, Text: '{text[:100]}{'...' if len(text) > 100 else ''}'")
        
        # Debug: Check if page contains JavaScript loading indicators
        print(f"\n=== JAVASCRIPT INDICATORS ===")
        script_tags = soup.find_all('script')
        print(f"Found {len(script_tags)} script tags")
        
        # Look for loading/dynamic content indicators
        loading_indicators = [
            'loading', 'spinner', 'skeleton', 'placeholder',
            'react', 'vue', 'angular', 'app-root'
        ]
        
        for indicator in loading_indicators:
            elements = soup.find_all(class_=re.compile(indicator, re.IGNORECASE))
            if elements:
                print(f"Found {len(elements)} elements with '{indicator}' in class - indicates dynamic content")
        
        # Check page text for indications of JavaScript requirement
        page_text = soup.get_text().lower()
        js_keywords = ['javascript', 'js', 'enable javascript', 'requires javascript']
        for keyword in js_keywords:
            if keyword in page_text:
                print(f"Page text contains '{keyword}' - may require JavaScript")
        
        print(f"\n=== DEBUG COMPLETE ===")
        
    except Exception as e:
        print(f"Error debugging page: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_foody_html()
