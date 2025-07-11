# Wolt.Com Scraper Configuration

## Website Information
- **Domain**: wolt.com
- **Base URL**: https://wolt.com
- **Scraping Method**: requests
- **JavaScript Required**: No
- **Anti-bot Protection**: none

## Selectors

### base_url
`https://wolt.com`

### item_selector
```css
.restaurant-card
```

### title_selector
```css
.restaurant-name
```

### price_selector
```css
.delivery-fee
```

### category_selector
```css
.cuisine-tag
```

## Custom Rules
- **Rating Selector**: `.rating-value`
- **Delivery Time Selector**: `.delivery-time`
- **Minimum Order Selector**: `.minimum-order`

## Testing URLs
- URL 1: https://wolt.com/en/discovery
- URL 2: https://wolt.com/en/restaurants
