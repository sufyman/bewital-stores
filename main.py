#!/usr/bin/env python3
"""
Main orchestrator for Bewital Pet Store Scraper Project.
Runs individual scrapers for all configured websites.
"""

import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, List

from utils.config_manager import ConfigManager
from scrapers.bozita_scraper import BozitaScraper
from scrapers.josera_scraper import JoseraScraper
from scrapers.wolfsblut_scraper import WolfsblutScraper
from scrapers.bosch_scraper import BoschScraper
from scrapers.edgar_cooper_scraper import EdgarCooperScraper
from scrapers.mera_scraper import MeraScraper
from scrapers.finnern_scraper import FinnernScraper
from scrapers.royal_canin_scraper import RoyalCaninScraper


class ScraperOrchestrator:
    """Main orchestrator for running all pet store scrapers."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.logger = self._setup_logging()
        
        # Available scrapers mapping
        self.scrapers = {
            'bozita': BozitaScraper,
            'josera': JoseraScraper,
            'wolfsblut': WolfsblutScraper,
            'bosch': BoschScraper,
            'edgar_cooper': EdgarCooperScraper,
            'mera': MeraScraper,
            'finnern': FinnernScraper,
            'royal_canin': RoyalCaninScraper,
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup main orchestrator logging."""
        logger = logging.getLogger("ScraperOrchestrator")
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run_single_scraper(self, website_key: str) -> Dict[str, Any]:
        """
        Run a single scraper for the specified website.
        
        Args:
            website_key: Key identifying the website to scrape
            
        Returns:
            Dictionary with scraping results
        """
        if website_key not in self.scrapers:
            error_msg = f"Scraper for '{website_key}' not implemented yet"
            self.logger.error(error_msg)
            return {
                'website': website_key,
                'success': False,
                'error': error_msg
            }
        
        if not self.config_manager.is_website_enabled(website_key):
            error_msg = f"Scraper for '{website_key}' is disabled in configuration"
            self.logger.warning(error_msg)
            return {
                'website': website_key,
                'success': False,
                'error': error_msg
            }
        
        try:
            self.logger.info(f"Starting scraper for {website_key}")
            scraper_class = self.scrapers[website_key]
            scraper = scraper_class()
            
            result = scraper.run()
            return result
            
        except Exception as e:
            error_msg = f"Failed to run scraper for {website_key}: {str(e)}"
            self.logger.error(error_msg)
            return {
                'website': website_key,
                'success': False,
                'error': error_msg
            }
    
    def run_all_scrapers(self) -> List[Dict[str, Any]]:
        """
        Run all enabled scrapers.
        
        Returns:
            List of dictionaries with results from each scraper
        """
        self.logger.info("Starting all enabled scrapers")
        
        enabled_websites = self.config_manager.get_enabled_websites()
        results = []
        
        for website_key in enabled_websites.keys():
            if website_key in self.scrapers:
                result = self.run_single_scraper(website_key)
                results.append(result)
            else:
                self.logger.warning(f"Scraper for '{website_key}' not implemented yet")
                results.append({
                    'website': website_key,
                    'success': False,
                    'error': 'Scraper not implemented'
                })
        
        return results
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print a summary of scraping results."""
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        
        total_stores = 0
        successful_scrapers = 0
        failed_scrapers = 0
        
        for result in results:
            website = result.get('website', 'Unknown')
            success = result.get('success', False)
            stores_found = result.get('stores_found', 0)
            
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{website:<20} {status:<12} Stores: {stores_found}")
            
            if success:
                successful_scrapers += 1
                total_stores += stores_found
                if result.get('output_file'):
                    print(f"{'':>20} Output: {result['output_file']}")
            else:
                failed_scrapers += 1
                print(f"{'':>20} Error: {result.get('error', 'Unknown error')}")
            
            print()
        
        print("-"*60)
        print(f"Total stores found: {total_stores}")
        print(f"Successful scrapers: {successful_scrapers}")
        print(f"Failed scrapers: {failed_scrapers}")
        print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bewital Pet Store Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run all enabled scrapers
  python main.py --website bozita   # Run only Bozita scraper
  python main.py --list             # List available scrapers
        """
    )
    
    parser.add_argument(
        '--website', '-w',
        help='Run scraper for specific website only'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available scrapers'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    orchestrator = ScraperOrchestrator()
    
    # List available scrapers
    if args.list:
        print("Available scrapers:")
        print("-" * 30)
        for website_key, scraper_class in orchestrator.scrapers.items():
            enabled = orchestrator.config_manager.is_website_enabled(website_key)
            status = "✅ Enabled" if enabled else "❌ Disabled"
            website_name = orchestrator.config['websites'][website_key]['name']
            print(f"{website_key:<15} {status:<12} {website_name}")
        return
    
    # Run specific scraper
    if args.website:
        if args.website not in orchestrator.scrapers:
            print(f"Error: Scraper '{args.website}' not available")
            print("Use --list to see available scrapers")
            sys.exit(1)
        
        result = orchestrator.run_single_scraper(args.website)
        orchestrator.print_summary([result])
        
        if not result.get('success', False):
            sys.exit(1)
        return
    
    # Run all scrapers
    results = orchestrator.run_all_scrapers()
    orchestrator.print_summary(results)
    
    # Exit with error code if any scraper failed
    if any(not result.get('success', False) for result in results):
        sys.exit(1)


if __name__ == "__main__":
    main() 