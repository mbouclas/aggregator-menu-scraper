#!/usr/bin/env python3
"""
Script to analyze the categories in the scraper output to see what's wrong.
"""
import json

def analyze_categories():
    # Load the Coffee Island scraping results
    with open('output/foody_coffee-island.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print('=== CATEGORIES ANALYSIS ===')
    print(f'Total categories in JSON: {len(data["categories"])}')
    
    print('\n=== ALL CATEGORIES IN JSON ===')
    for i, cat in enumerate(data['categories']):
        print(f'{i+1:3d}. "{cat["name"]}" (source: {cat.get("source", "unknown")})')
    
    print('\n=== ANALYSIS BY SOURCE ===')
    sources = {}
    for cat in data['categories']:
        source = cat.get('source', 'unknown')
        if source not in sources:
            sources[source] = []
        sources[source].append(cat['name'])
    
    for source, cats in sources.items():
        print(f'\n{source.upper()}: {len(cats)} categories')
        for cat in cats[:5]:  # Show first 5
            print(f'  - "{cat}"')
        if len(cats) > 5:
            print(f'  ... and {len(cats) - 5} more')

if __name__ == "__main__":
    analyze_categories()
