# Project Requirements

## Project Overview
- create a web scraper app in python.
- Each web site we're to scraping should have it's own config file holding site specific config options, like the site url, css selector values etc.
- The output of the scrape will be in a unified format regardless of the site and will be saved as a json file
- Common tools should be kept in libraries under a directory named common. Make sure to reuse this code between scrapers
- The json structure


## Technical Stack
- **Language**: Python 3.9+
- **Framework**: Flask/Django/FastAPI
- **Database**: PostgreSQL/MySQL/SQLite


## Architecture Requirements
- Follow MVC pattern
- Use dependency injection
- Implement proper error handling
- Include logging throughout

## Code Standards
- **Style**: Follow PEP 8 (Python) / ESLint (JavaScript)
- **Documentation**: All functions must have docstrings
- **Testing**: 80%+ code coverage required
- **Type Hints**: Use type annotations where applicable


## File Structure
```
project/
├── src/
├── tests/
├── docs/
├── output/
└── requirements.txt
```

## Specific Implementation Rules
1. All database queries must use parameterized statements
2. API responses must follow REST conventions
3. Environment variables for all configuration
4. No hardcoded secrets or API keys

## Testing Requirements
- Unit tests for all business logic
- Integration tests for API endpoints
- Mock external dependencies

## Security Requirements
- Input validation on all user inputs
- SQL injection prevention
- Authentication/authorization where needed

## Performance Requirements
- API response time < 200ms
- Database queries optimized
- Proper caching implementation



### Error Handling
- If a required field cannot be extracted, use appropriate default:
  - Empty string for missing text fields
  - Empty array for missing categories/products
  - 0.0 for missing prices
- Log all missing/defaulted fields for debugging

## Website-Specific Scraper Configuration

### Configuration Structure
Each target website requires its own configuration file in the `scrapers/` directory:

```
project/
├── scrapers/
│   ├── foody.md
│   ├── wolt.md
│   └── template.md
├── src/
└── PROJECT_REQUIREMENTS.md
```

### Configuration File Naming
- Use lowercase with underscores: `{domain}.md`
- Examples: `foody.md`, `wolt.md`

### How to Reference Configurations
When implementing scrapers, the program should:
1. Extract domain from target URL
2. Load corresponding configuration file
3. Follow website-specific instructions
4. Fall back to generic scraping if no config exists

### Configuration File Template
Each scraper config must follow the template in `scrapers/template.md`
