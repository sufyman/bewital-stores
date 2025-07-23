# Bewital Pet Store Scraper

Automated web scrapers to create and maintain a comprehensive database of pet food retailers/shops in Germany for Bewital's sales team. The system identifies potential customers and enables data-driven outreach prioritization.

## 🎯 Project Overview

### Business Context
- **Target Market**: Pet food-selling stores across Germany
- **End Use**: Sales lead generation and management in Salesforce
- **Key Challenge**: Store finders typically require location-based searches with radius parameters

### Technical Approach
- **Primary Sources**: Scrape competitor store finder websites
- **Data Strategy**: Extract all available store data without normalization
- **Output**: Raw CSV files for manual processing in Google Sheets
- **Future Enhancement**: Google Places API integration for additional data validation

## 🏗️ Architecture

```
bewital-stores/
├── scrapers/           # Individual website scrapers
│   ├── __init__.py
│   ├── bozita_scraper.py
│   └── [other_scrapers].py
├── utils/              # Common utilities and base classes
│   ├── __init__.py
│   ├── base_scraper.py
│   └── config_manager.py
├── data/               # Output directories
│   ├── raw/           # CSV files from scrapers
│   └── processed/     # Future processed data
├── logs/              # Application logs
├── docs/              # Documentation
├── tests/             # Test files
├── config.yaml        # Main configuration
├── requirements.txt   # Python dependencies
├── main.py           # Main orchestrator
└── README.md         # This file
```

## 🎯 Target Websites (Priority 1)

| Website | URL | Status |
|---------|-----|--------|
| Bozita | https://bozita.com/de/fachhandler-suchen/ | ✅ Implemented |
| Josera | https://fachhandel.josera.de/ | 🔄 Planned |
| Bosch/Sanabelle | https://www.bosch-tiernahrung.de/haendlersuche | 🔄 Planned |
| Edgar & Cooper | https://www.edgardcooper.com/en/store-locator/ | 🔄 Planned |
| Finnern | https://www.finnern.de/ | 🔄 Planned |
| Meradog/Meracat | https://www.mera-petfood.com/de/haendlersuche/ | 🔄 Planned |
| Royal Canin | https://www.royalcanin.com/de/find-a-retailer | 🔄 Planned |
| Wolfsblut | https://www.wolfsblut.com/haendler/ | 🔄 Planned |

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Chrome browser (for Selenium WebDriver)
- Internet connection

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bewital-stores
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (optional)**
   ```bash
   cp env.example .env
   # Edit .env file with your specific settings
   ```

5. **Test installation**
   ```bash
   python main.py --list
   ```

## 📋 Usage

### Basic Commands

```bash
# List all available scrapers
python main.py --list

# Run all enabled scrapers
python main.py

# Run specific scraper
python main.py --website bozita

# Enable verbose logging
python main.py --verbose

# Run specific scraper with verbose output
python main.py --website bozita --verbose
```

### Configuration

Edit `config.yaml` to customize:

- **Browser settings**: Headless mode, timeouts
- **Scraping parameters**: Delays, retry attempts
- **Search locations**: German cities to search
- **Output settings**: File formats, directories
- **Website enablement**: Enable/disable specific scrapers

### Output Files

- **Location**: `data/raw/` directory
- **Format**: CSV files with timestamp
- **Naming**: `{website_key}_{timestamp}.csv`
- **Content**: All available store data without normalization

### Example Output Structure

```csv
name,address,postal_code,city_actual,phone,email,website,search_city,source_website,scraped_at
"Futterhaus München","Maximilianstr. 12","80539","München","+49 89 123456","info@futterhaus.de","https://futterhaus.de","München","Bozita","2024-01-15T10:30:00"
```

## 🔧 Technical Details

### Base Scraper Architecture

All scrapers inherit from `BaseScraper` which provides:

- **Browser management**: Chrome WebDriver setup with anti-detection
- **Error handling**: Retry logic and graceful failure handling
- **Data management**: Consistent CSV output and logging
- **Configuration**: Unified configuration management

### Location-Based Search Strategy

Many store finders require location input, so the system:

1. **Iterates through major German cities** (configurable in `config.yaml`)
2. **Performs radius-based searches** for each location
3. **Deduplicates results** based on store name and address
4. **Captures all available data** without field standardization

### Anti-Detection Measures

- **Rotating user agents**
- **Realistic delays between requests**
- **Headless browser configuration**
- **Request retry mechanisms**

## 📊 Data Collection Strategy

### Raw Data Extraction
- Extract **all available fields** from each website
- **No field standardization** - preserve original data structure
- **Website-specific column names** maintained
- **Metadata addition**: source, timestamp, search parameters

### Duplicate Handling
- **Store-level deduplication** within each scraper run
- **Cross-website duplicates** handled in post-processing
- **Key generation** based on name + address combination

## 🔄 Automation & Scheduling

### Future Implementation
The system is designed for automated scheduling:

```yaml
automation:
  enabled: true
  schedule: "weekly"  # daily, weekly, monthly
  time: "02:00"
```

### Integration Options
- **Cron jobs** for Unix systems
- **Task Scheduler** for Windows
- **Cloud functions** for serverless execution

## 🧪 Testing & Validation

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_bozita_scraper.py

# Run with coverage
python -m pytest --cov=scrapers tests/
```

### Manual Validation
1. **Sample verification**: Manually check random stores
2. **Address validation**: Verify addresses exist
3. **Contact information**: Test phone numbers and emails
4. **Website accessibility**: Check store websites

## 🐛 Troubleshooting

### Common Issues

1. **ChromeDriver not found**
   ```bash
   # The webdriver-manager should handle this automatically
   # If issues persist, manually install ChromeDriver
   ```

2. **Timeout errors**
   ```yaml
   # Increase timeouts in config.yaml
   browser:
     timeout: 60
     page_load_timeout: 60
   ```

3. **Rate limiting**
   ```yaml
   # Increase delays in config.yaml
   scraping:
     delay_between_requests: 5
   ```

4. **No results found**
   - Check if website structure changed
   - Verify search selectors in scraper code
   - Enable verbose logging for debugging

### Debug Mode

```bash
# Enable verbose logging
python main.py --website bozita --verbose

# Check log files
tail -f logs/scraper.log
```

## 📈 Monitoring & Maintenance

### Log Analysis
- **Location**: `logs/scraper.log`
- **Rotation**: Automatic rotation when files exceed 10MB
- **Levels**: INFO, WARNING, ERROR, DEBUG

### Performance Metrics
Each scraper run provides:
- **Stores found count**
- **Error count**
- **Session duration**
- **Success/failure status**

### Regular Maintenance Tasks

1. **Weekly**: Review error logs and success rates
2. **Monthly**: Update search locations if needed
3. **Quarterly**: Review and update website selectors
4. **As needed**: Add new target websites

## 🔮 Future Enhancements

### Phase 2: Google Places API Integration
- **Enhanced validation**: Verify store existence
- **Additional data**: Customer reviews, ratings, photos
- **Address normalization**: Standardized address formats

### Phase 3: Database Integration
- **Centralized storage**: PostgreSQL or similar
- **Data deduplication**: Advanced matching algorithms
- **Change tracking**: Monitor store updates over time

### Phase 4: Salesforce Integration
- **Direct data import**: Automated lead creation
- **Duplicate prevention**: Cross-reference with existing data
- **Lead scoring**: Prioritization based on collected metrics

### Phase 5: Real-time Updates
- **Change detection**: Monitor website updates
- **Incremental updates**: Only process new/changed data
- **Alert system**: Notify of significant changes

## 🤝 Contributing

### Adding New Scrapers

1. **Create scraper file**: `scrapers/{website_key}_scraper.py`
2. **Inherit from BaseScraper**: Implement `scrape_stores()` method
3. **Update configuration**: Add website to `config.yaml`
4. **Register in main**: Add to `ScraperOrchestrator.scrapers`
5. **Test thoroughly**: Verify data extraction accuracy

### Code Standards
- **PEP 8 compliance**: Use consistent formatting
- **Type hints**: Add type annotations
- **Documentation**: Comprehensive docstrings
- **Error handling**: Graceful failure management

## 📄 License

This project is proprietary software developed for Bewital. All rights reserved.

## 📞 Support

For technical issues or questions:
- **Internal team**: Contact development team
- **Documentation**: Check this README and code comments
- **Logs**: Review log files for detailed error information

---

*Last updated: January 2024* 