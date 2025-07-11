# Foody.com.cy Scraper Configuration

## Website Information
- **Domain**: foody.com.cy
- **Type**: Restaurant delivery platform
- **Last Updated**: 2025-07-11

## Scraping Strategy
- **Method**: Selenium (JavaScript heavy site)
- **JavaScript Required**: Yes
- **Anti-bot Protection**: Basic rate limiting

## Selectors & Extraction Rules

### Restaurant Information
- **Restaurant Name**: wrapped in `<h1>` like `<h1 class="cc-title_58e9e8">Costa Coffee Stavrou</h1>` or `<h1 class="cc-title_58e9e8">KFC Nikis</h1>`
- **Brand Name**: Extract from restaurant name or use same value
- **URL Pattern**: `^https://www\.foody\.com\.cy/delivery/menu/.*`

### Product Extraction
- **Title**: Titles look like: `<h3 class="cc-name_acd53e">Freddo Espresso Massimo</h3>` or <h3 class="cc-name_acd53e">Cold Brew with Milk Primo</h3>
- **Category**: Categories are always the first `<h2>` parent of each product. For example `<h2 class="sc-cOweyZ gFOLxB">Offers</h2>`

### Category Extraction
- **Category List**: Look for an `h2` element with innerText of `Categories` followed by a `ul` element. The categories list is the `li` elements of that list
- **Category Names**: Remove numbers and clean whitespace

### Price extraction
- Prices are always followed by the € sign
- They might have the word `From` as a prefix, ignore that word
- There's an offer when a div with a style property follows the price, usually in the format of `<div style="color: rgb(0, 188, 139); background-color: rgb(237, 247, 238);">up to -37%</div>`. We care about the `-37%` and can ignore the `up to ` string
- Convert prices into floats, regard the €

### Example prices
- <div class="cc-price_a7d252">19.45€</div> The price is 19.45
- <div class="cc-price_a7d252">From 20.90€</div> The price is 20.90

### Example offer tags
- `<div class="sn-wrapper_6bd59d cc-badge_e1275b" style="color: rgb(0, 188, 139); background-color: rgb(237, 247, 238);"><span class="sn-title_522dc0">up to -37%</span></div>` The number is -37%
- `<div class="sn-wrapper_6bd59d cc-badge_e1275b" style="color: rgb(0, 188, 139); background-color: rgb(237, 247, 238);"><span class="sn-title_522dc0">up to -51%</span></div>`The number is -51%
- `<div class="sn-wrapper_6bd59d cc-badge_e1275b" style="color: rgb(0, 188, 139); background-color: rgb(237, 247, 238);"><span class="sn-title_522dc0">up to -43%</span></div>` The number is -43%

## Example Categories
- Offers
- Cold Coffees
- Hot Coffees

## Testing URLs
- Primary: https://www.foody.com.cy/delivery/menu/costa-coffee
- Secondary: https://www.foody.com.cy/delivery/menu/pasta-strada