"""
Wolfsblut pet store scraper using direct CSV download.
URL: https://www.wolfsblut.com/haendler/
CSV: https://www.wolfsblut.com/media/sb8pnsb5-q9rw-ehwz-dcxk-uk6s62nhjncq-wb.csv
"""

import requests
import time
import csv
import io
from typing import List, Dict, Any

from utils.base_scraper import BaseScraper


class WolfsblutScraper(BaseScraper):
    """Scraper for Wolfsblut store finder using direct CSV download."""
    
    def __init__(self):
        super().__init__('wolfsblut')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36',
            'Referer': self.website_config['url'],
            'DNT': '1',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"'
        })
        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Scrape all Wolfsblut stores by downloading the CSV file.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Wolfsblut store scraping via CSV download")
        
        try:
            # First, visit the main page to establish session
            self._initialize_session()
            
            # Download and parse the CSV file
            stores = self._download_csv()
            
            for store in stores:
                processed_store = self._process_store_data(store)
                self.add_store_data(processed_store)
                
            self.logger.info(f"Total stores found: {len(stores)}")
            return stores
            
        except Exception as e:
            self.log_error(f"Error in Wolfsblut scraping: {str(e)}")
            return []
    
    def _initialize_session(self):
        """Initialize session by visiting the main page."""
        try:
            response = self.session.get(self.website_config['url'], timeout=30)
            response.raise_for_status()
            self.logger.info("Session initialized with Wolfsblut website")
            
            # Add a small delay
            time.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize session: {str(e)}")
            # Continue anyway, might still work
    
    def _download_csv(self) -> List[Dict[str, Any]]:
        """
        Download and parse the CSV file from Wolfsblut.
        
        Returns:
            List of raw store data from CSV
        """
        stores = []
        
        # Direct CSV URL discovered from browser dev tools
        csv_url = "https://www.wolfsblut.com/media/sb8pnsb5-q9rw-ehwz-dcxk-uk6s62nhjncq-wb.csv"
        
        try:
            self.logger.info(f"Downloading CSV from: {csv_url}")
            
            response = self.session.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Parse CSV content
            csv_content = response.text
            self.logger.info(f"Downloaded CSV content length: {len(csv_content)} characters")
            
            # Use csv.DictReader to parse the CSV
            csv_file = io.StringIO(csv_content)
            
            # Try different delimiters in case it's not comma-separated
            possible_delimiters = [';', ',', '\t', '|']
            
            for delimiter in possible_delimiters:
                csv_file.seek(0)  # Reset to beginning
                try:
                    reader = csv.DictReader(csv_file, delimiter=delimiter)
                    stores = list(reader)
                    
                    # Check if we got meaningful data
                    if stores and len(stores) > 5:  # At least some stores
                        first_row = stores[0]
                        # Check if we have expected fields
                        if any(key for key in first_row.keys() if key and len(str(key).strip()) > 1):
                            self.logger.info(f"Successfully parsed CSV with delimiter '{delimiter}' - found {len(stores)} stores")
                            break
                except Exception as e:
                    self.logger.debug(f"Failed to parse with delimiter '{delimiter}': {str(e)}")
                    continue
            
            if not stores:
                self.logger.error("Failed to parse CSV with any delimiter")
                return []
            
            # Log the column names for debugging
            if stores:
                columns = list(stores[0].keys())
                self.logger.info(f"CSV columns: {columns}")
            
            return stores
            
        except Exception as e:
            self.logger.error(f"Error downloading CSV: {str(e)}")
            return []
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data from CSV into standardized format.
        
        Args:
            raw_store: Raw store data from CSV
            
        Returns:
            Processed store data dictionary
        """
        # Based on typical CSV structure, map the fields
        # We'll use the raw field names and also create standardized ones
        processed = {}
        
        # Copy all original fields first
        for key, value in raw_store.items():
            if key:  # Only if key is not empty
                processed[key.strip()] = str(value).strip() if value else ''
        
        # Try to map to standardized field names based on common patterns
        field_mappings = {
            'id': ['fid', 'id', 'store_id', 'dealer_id'],
            'name': ['name', 'store_name', 'dealer_name', 'company'],
            'address': ['address', 'street', 'full_address', 'location'],
            'latitude': ['latitude', 'lat', 'y', 'coord_lat'],
            'longitude': ['longitude', 'lng', 'lon', 'x', 'coord_lng'],
            'phone': ['phone', 'telephone', 'tel'],
            'email': ['email', 'mail'],
            'website': ['website', 'url', 'web'],
            'city': ['city', 'town', 'place'],
            'postal_code': ['postal_code', 'zip', 'plz'],
            'country': ['country', 'land']
        }
        
        # Map fields to standardized names
        for standard_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                # Check both exact match and case-insensitive
                for csv_key in raw_store.keys():
                    if csv_key and (csv_key.lower() == key.lower() or key.lower() in csv_key.lower()):
                        processed[f'std_{standard_field}'] = str(raw_store[csv_key]).strip() if raw_store[csv_key] else ''
                        break
                if f'std_{standard_field}' in processed:
                    break
        
        # Try to parse combined address field if available
        address_field = processed.get('std_address', processed.get('address', ''))
        if address_field and ',' in address_field:
            parts = [part.strip() for part in address_field.split(',')]
            if len(parts) >= 2:
                # Try to extract postal code and city from last part
                last_part = parts[-1].strip()
                if last_part:
                    # Look for postal code pattern (numbers at the beginning)
                    import re
                    postal_match = re.match(r'(\d{4,5})\s+(.+)', last_part)
                    if postal_match:
                        processed['parsed_postal_code'] = postal_match.group(1)
                        processed['parsed_city'] = postal_match.group(2)
                    else:
                        processed['parsed_city'] = last_part
                
                # Street address might be in earlier parts
                if len(parts) >= 2:
                    processed['parsed_street'] = ', '.join(parts[:-1])
        
        # Add source metadata
        processed['original_csv_data'] = str(raw_store)
        
        return processed
    
    def run(self) -> Dict[str, Any]:
        """
        Override run method to use requests instead of Selenium for CSV download.
        
        Returns:
            Dictionary with scraping results and statistics
        """
        start_time = time.time()
        
        try:
            stores = self.scrape_stores()
            
            # Save data
            output_file = self.save_data()
            
            # Calculate session duration
            self.session_duration = time.time() - start_time
            
            # Get final stats
            stats = self.get_stats()
            stats['output_file'] = output_file
            stats['success'] = True
            
            self.logger.info(f"Wolfsblut scraping completed successfully: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Wolfsblut scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 