# Wolt.Com Scraper Configuration

## Website Information
- **Domain**: wolt.com
- **Base URL**: https://wolt.com
- **Type**: Restaurant delivery platform

## Scraping Strategy
- **Method**: Selenium (JavaScript heavy site)
- **JavaScript Required**: Yes
- **Anti-bot Protection**: Basic rate limiting

## Selectors & Extraction Rules

### Restaurant Information
- **Restaurant Name**: wrapped in `<h1>` like `<h1 class="habto2o"><span data-test-id="venue-hero.venue-title" class="h15mb7zs">Wagamama Themistokli Dervi</span></h1>` or `<h1 class="habto2o"><span data-test-id="venue-hero.venue-title" class="h15mb7zs">TGI Fridays Diagorou</span></h1>`
- **Brand Name**: Extract from restaurant name from the `alt` property of an image which looks like so
`<img loading="lazy" decoding="async" src="https://imageproxy.wolt.com/assets/673208edf45db57ef6004a87" alt="TGI Fridays" style="object-fit:cover" draggable="true" class="s1siin91">` or `<img loading="lazy" decoding="async" src="https://imageproxy.wolt.com/assets/673214e91f2eff71374fc6e7" alt="Wagamama" style="object-fit:cover" draggable="true" class="s1siin91">`

### Product Extraction
- **Title**: Titles look like: `<h3 data-test-id="horizontal-item-card-header" class="tj9ydql">104. Edamame</h3>` or `<h3 data-test-id="horizontal-item-card-header" class="tj9ydql">241. Thai Roti Sausage Wrap</h3>`
- **Category**: Categories are always the first `<h2>` parent of each product. For example `<h2 class="h129y4wz">EXTRAS</h2>`
- Some product titles might contain emoji characters like `🆕, 🌶️, 🍔, etc.`

### Category Extraction
- **Category List**: Look for `<h2>` tags that look like this `<h2 class="h129y4wz">EXTRAS</h2>` or `<h2 class="h129y4wz">FRESH JUICES</h2>`
- **Category Names**: Remove numbers and clean whitespace. Also remove any non standard character like 🆕


### Price extraction
- Prices are always preceded by the € sign
- They might have the word `From` as a prefix, ignore that word
- If there's an offer, it would look like `<div class="f1qz10hl" style="--f1qz10hl-0: wrap; --f1qz10hl-1: auto;"><p class="t11807jm"><span data-test-id="horizontal-item-card-discounted-price" aria-label="Discounted price €21.99" class="dhz2cdy">€21.99</span><span data-test-id="horizontal-item-card-original-price" aria-label="Old price 29.75" class="orc6gge">29.75</span></p></div>` or `<div class="f1qz10hl" style="--f1qz10hl-0: wrap; --f1qz10hl-1: auto;"><p class="t11807jm"><span data-test-id="horizontal-item-card-discounted-price" aria-label="Discounted price €31.99" class="dhz2cdy">€31.99</span><span data-test-id="horizontal-item-card-original-price" aria-label="Old price 40.50" class="orc6gge">40.50</span></p></div>`. Use the `aria-label` property to get the price and the original_price. The price would contain the wording `Discounted price` while the original_price would contain the wording `Old price` both followed by the actual price.
- Convert prices into floats, regard the €
- There could be a `popular` wording like so `<div class="t13mcxn0"><div data-size="small" data-variant="primaryBrand" class="cb_Tag_Root_7dc"><div class="cb_typographyClassName_bodyBase_6f5 cb_typographyClassName_SmallSemiBold_6f5 cb_Tag_Label_7dc">Popular</div></div></div>`. Ignore it.

## Example Categories
- Offers
- Cold Coffees
- Hot Coffees

## Testing URLs
- Primary: https://wolt.com/en/cyp/nicosia/restaurant/wagamama-themistokli-dervi
- Secondary: https://wolt.com/en/cyp/nicosia/restaurant/tgi-fridays-nicosia-diagorou
