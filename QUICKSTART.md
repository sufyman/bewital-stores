# 🚀 Quick Start Guide

Get the Bewital Pet Store Scraper running in under 5 minutes!

## Prerequisites
- Python 3.8+ installed
- Google Chrome browser
- Internet connection

## 1-Command Setup

```bash
python setup.py
```

This will:
- ✅ Check Python version compatibility  
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Test the installation

## Activate Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

## Basic Usage

```bash
# List available scrapers
python main.py --list

# Run the Bozita scraper (currently implemented)
python main.py --website bozita

# Run all enabled scrapers
python main.py

# Get help
python main.py --help
```

## First Run

Try the Bozita scraper to test everything works:

```bash
python main.py --website bozita --verbose
```

This will:
1. Search major German cities for Bozita stores
2. Extract store data (name, address, contact info)
3. Save results to `data/raw/bozita_TIMESTAMP.csv`
4. Show progress and summary

## Output

Results are saved as CSV files in `data/raw/`:
- Timestamped filenames: `bozita_20240115_143022.csv`
- All available store data preserved
- Ready for import to Google Sheets

## Configuration

Edit `config.yaml` to:
- Enable/disable specific scrapers
- Adjust search cities
- Modify browser settings
- Change output directory

## Next Steps

1. **Review the output CSV** in `data/raw/`
2. **Check logs** in `logs/scraper.log` for any issues
3. **Customize config.yaml** for your needs
4. **Add automation** by enabling scheduling in config
5. **Import to Google Sheets** for data processing

## Need Help?

- Check `README.md` for complete documentation
- Review `config.yaml` for all options
- Check logs in `logs/` directory
- Run with `--verbose` flag for detailed output

## What's Next?

The system is designed for expansion:
- Additional scrapers for 7 more websites
- Google Places API integration
- Automated scheduling
- Salesforce integration

Currently implemented: **Bozita** ✅  
Coming soon: Josera, Bosch, Edgar & Cooper, Finnern, Mera, Royal Canin, Wolfsblut

---

**Ready to start? Run: `python main.py --website bozita`** 🎯 