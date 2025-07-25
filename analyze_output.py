#!/usr/bin/env python3
"""
Script to analyze scraper output and understand category assignments.
"""
import json

def analyze_scraper_output():
    # Load the Caffè Nero scraping results
    with open('output/foody_caffè-nero.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print('=== SCRAPER OUTPUT ANALYSIS ===')
    print(f'Restaurant: {data["restaurant"]["name"]}')
    print(f'Total categories: {len(data["categories"])}')
    print(f'Total products: {len(data["products"])}')

    print('\n=== CATEGORIES FROM SCRAPER ===')
    for cat in data['categories'][:10]:
        print(f'- "{cat["name"]}" (id: {cat["id"]})')

    print('\n=== SAMPLE PRODUCTS AND THEIR CATEGORIES ===')
    for prod in data['products'][:10]:
        print(f'- "{prod["name"]}" -> category: "{prod["category"]}"')

    print('\n=== UNIQUE CATEGORIES ASSIGNED TO PRODUCTS ===')
    product_categories = set(prod['category'] for prod in data['products'])
    for cat in sorted(product_categories):
        count = sum(1 for prod in data['products'] if prod['category'] == cat)
        print(f'- "{cat}": {count} products')

if __name__ == "__main__":
    analyze_scraper_output()
