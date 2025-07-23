"""
Edgar & Cooper pet store scraper.
URL: https://www.edgardcooper.com/de/store-locator/
Approach: Simple requests-based scraper with search functionality discovery
"""

import requests
import time
import json
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from utils.base_scraper import BaseScraper


class EdgarCooperScraper(BaseScraper):
    """Scraper for Edgar & Cooper store finder."""
    
    def __init__(self):
        super().__init__('edgar_cooper')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Referer': self.website_config['url'],
            'DNT': '1'
        })
        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Scrape Edgar & Cooper stores.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Edgar & Cooper store scraping")
        
        try:
            # First check if there are any stores available
            stores = self._check_store_availability()
            
            if stores:
                for store in stores:
                    processed_store = self._process_store_data(store)
                    self.add_store_data(processed_store)
                    
                self.logger.info(f"Total stores found: {len(stores)}")
                return stores
            else:
                # Check if this is an online-only business or coming soon
                self._check_business_model()
                return []
                
        except Exception as e:
            self.log_error(f"Error in Edgar & Cooper scraping: {str(e)}")
            return []
    
    def _check_store_availability(self) -> List[Dict[str, Any]]:
        """
        Check if Edgar & Cooper has any physical stores available.
        
        Returns:
            List of store data if found
        """
        stores = []
        
        try:
            # Get the store locator page
            response = self.session.get(self.website_config['url'], timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for search functionality
            search_form = soup.find('form')
            address_input = soup.find('input', {'name': 'address'})
            
            if search_form and address_input:
                self.logger.info("Found search form with address input")
                stores = self._try_search_functionality(soup)
            
            if not stores:
                # Look for any embedded store data
                stores = self._extract_embedded_store_data(response.text)
            
            if not stores:
                # Check if stores are mentioned in text content
                stores = self._check_for_store_mentions(soup)
            
            return stores
            
        except Exception as e:
            self.logger.error(f"Error checking store availability: {str(e)}")
            return []
    
    def _try_search_functionality(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Try to use the search functionality to find stores.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of store data if found
        """
        stores = []
        
        try:
            # Try searching for major German cities
            test_cities = [
                'Berlin', 'München', 'Hamburg', 'Köln', 'Frankfurt',
                'Stuttgart', 'Düsseldorf', 'Leipzig', 'Dortmund', 'Essen'
            ]
            
            for city in test_cities[:3]:  # Test first 3 cities
                self.logger.info(f"Testing search for {city}")
                
                # Try to submit search form
                search_results = self._submit_search(city)
                if search_results:
                    stores.extend(search_results)
                
                # Add delay between searches
                time.sleep(2)
            
            return stores
            
        except Exception as e:
            self.logger.debug(f"Error in search functionality: {str(e)}")
            return []
    
    def _submit_search(self, location: str) -> List[Dict[str, Any]]:
        """
        Submit a search for the given location.
        
        Args:
            location: Location to search for
            
        Returns:
            List of stores found
        """
        try:
            # Try different search endpoints
            search_endpoints = [
                f"{self.website_config['url'].rstrip('/')}/search",
                f"{self.website_config['url'].rstrip('/')}/api/search",
                f"https://www.edgardcooper.com/api/store-search",
                f"https://www.edgardcooper.com/de/api/stores/search"
            ]
            
            search_data = {
                'address': location,
                'location': location,
                'city': location,
                'query': location
            }
            
            for endpoint in search_endpoints:
                try:
                    # Try POST request
                    response = self.session.post(endpoint, data=search_data, timeout=10)
                    if response.status_code == 200:
                        self.logger.info(f"Search endpoint responded: {endpoint}")
                        
                        if 'json' in response.headers.get('content-type', ''):
                            data = response.json()
                            stores = self._extract_stores_from_search_result(data)
                            if stores:
                                return stores
                    
                    # Try GET request with query parameter
                    params = {'q': location, 'address': location, 'location': location}
                    response = self.session.get(endpoint, params=params, timeout=10)
                    if response.status_code == 200 and 'json' in response.headers.get('content-type', ''):
                        data = response.json()
                        stores = self._extract_stores_from_search_result(data)
                        if stores:
                            return stores
                            
                except Exception:
                    continue
            
            return []
            
        except Exception as e:
            self.logger.debug(f"Error submitting search for {location}: {str(e)}")
            return []
    
    def _extract_stores_from_search_result(self, data: Any) -> List[Dict[str, Any]]:
        """Extract stores from search result data."""
        stores = []
        
        if isinstance(data, list):
            stores = data
        elif isinstance(data, dict):
            # Look for stores in common keys
            for key in ['stores', 'locations', 'results', 'data']:
                if key in data and isinstance(data[key], list):
                    stores = data[key]
                    break
        
        # Validate that these look like store records
        valid_stores = []
        for store in stores:
            if isinstance(store, dict) and self._looks_like_store_data(store):
                valid_stores.append(store)
        
        return valid_stores
    
    def _looks_like_store_data(self, obj: dict) -> bool:
        """Check if an object looks like store data."""
        if not isinstance(obj, dict):
            return False
        
        store_indicators = [
            'name', 'address', 'street', 'city', 'postal', 'zip', 'plz',
            'phone', 'tel', 'email', 'lat', 'lng', 'latitude', 'longitude'
        ]
        
        found_indicators = 0
        for key in obj.keys():
            if any(indicator in str(key).lower() for indicator in store_indicators):
                found_indicators += 1
        
        return found_indicators >= 2
    
    def _extract_embedded_store_data(self, html_content: str) -> List[Dict[str, Any]]:
        """Look for embedded store data in the HTML."""
        stores = []
        
        try:
            # Look for JSON data patterns
            json_patterns = [
                r'window\.__NEXT_DATA__\s*=\s*({.*?});',
                r'stores\s*[:=]\s*(\[.*?\])',
                r'locations\s*[:=]\s*(\[.*?\])',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        extracted_stores = self._extract_stores_from_json(data)
                        if extracted_stores:
                            stores.extend(extracted_stores)
                    except:
                        continue
            
            return stores
            
        except Exception as e:
            self.logger.debug(f"Error extracting embedded data: {str(e)}")
            return []
    
    def _extract_stores_from_json(self, data: Any) -> List[Dict[str, Any]]:
        """Recursively extract store data from JSON structure."""
        stores = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    if all(isinstance(item, dict) for item in value[:3]):
                        if any(self._looks_like_store_data(item) for item in value[:3]):
                            return value
                stores.extend(self._extract_stores_from_json(value))
        elif isinstance(data, list):
            for item in data:
                stores.extend(self._extract_stores_from_json(item))
        
        return stores
    
    def _check_for_store_mentions(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Check if there are any store mentions in the page text."""
        stores = []
        
        try:
            text_content = soup.get_text().lower()
            
            # Look for German store chains that might carry Edgar & Cooper
            german_chains = [
                'fressnapf', 'futterhaus', 'zoo zajac', 'hornbach', 'bauhaus',
                'dehner', 'obi', 'hagebaumarkt', 'hellweg', 'toom'
            ]
            
            found_chains = []
            for chain in german_chains:
                if chain in text_content:
                    found_chains.append(chain)
            
            if found_chains:
                self.logger.info(f"Found mentions of store chains: {found_chains}")
                
                # Create placeholder entries indicating where products might be available
                for chain in found_chains:
                    stores.append({
                        'name': f'{chain.title()} (Edgar & Cooper Retailer)',
                        'type': 'retail_chain',
                        'note': f'Edgar & Cooper products may be available at {chain.title()} stores',
                        'source': 'website_mention'
                    })
            
            return stores
            
        except Exception as e:
            self.logger.debug(f"Error checking store mentions: {str(e)}")
            return []
    
    def _check_business_model(self):
        """Check if Edgar & Cooper is online-only or has other business model info."""
        try:
            response = self.session.get(self.website_config['url'], timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text().lower()
            
            # Check for online-only indicators
            online_indicators = [
                'online only', 'nur online', 'ausschließlich online',
                'coming soon', 'bald verfügbar', 'in entwicklung'
            ]
            
            for indicator in online_indicators:
                if indicator in text_content:
                    self.logger.info(f"Business model indicator found: {indicator}")
                    break
            else:
                self.logger.info("No clear business model indicators found")
            
            # Check if there's contact information for retailers
            if any(word in text_content for word in ['händler', 'retailer', 'verkaufsstellen']):
                self.logger.info("Page mentions retailers/dealers")
                
        except Exception as e:
            self.logger.debug(f"Error checking business model: {str(e)}")
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data into standardized format.
        
        Args:
            raw_store: Raw store data
            
        Returns:
            Processed store data dictionary
        """
        processed = {
            'source': 'edgar_cooper'
        }
        
        # Copy all original fields
        for key, value in raw_store.items():
            if key and value:
                processed[key] = str(value).strip()
        
        # If this is a retail chain mention, keep it simple
        if raw_store.get('type') == 'retail_chain':
            return processed
        
        # Standard field mapping for actual store data
        field_mappings = {
            'name': ['name', 'title', 'store_name'],
            'street': ['street', 'address', 'addr'],
            'city': ['city', 'town'],
            'postal_code': ['postal_code', 'zip', 'plz'],
            'phone': ['phone', 'tel', 'telefon'],
            'email': ['email', 'mail'],
            'website': ['website', 'url'],
            'latitude': ['lat', 'latitude'],
            'longitude': ['lng', 'longitude'],
        }
        
        for standard_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                for raw_key in raw_store.keys():
                    if raw_key and key.lower() in raw_key.lower():
                        processed[f'std_{standard_field}'] = str(raw_store[raw_key]).strip()
                        break
                if f'std_{standard_field}' in processed:
                    break
        
        # Create full address
        address_parts = []
        for field in ['std_street', 'street']:
            if processed.get(field):
                address_parts.append(processed[field])
                break
        
        city_part = []
        for field in ['std_postal_code', 'postal_code']:
            if processed.get(field):
                city_part.append(processed[field])
                break
        for field in ['std_city', 'city']:
            if processed.get(field):
                city_part.append(processed[field])
                break
        
        if city_part:
            address_parts.append(' '.join(city_part))
        
        processed['full_address'] = ', '.join(address_parts)
        
        return processed
    
    def run(self) -> Dict[str, Any]:
        """
        Run the Edgar & Cooper scraper.
        
        Returns:
            Dictionary with scraping results and statistics
        """
        start_time = time.time()
        
        try:
            stores = self.scrape_stores()
            
            # Save data only if we found stores
            output_file = None
            if stores:
                output_file = self.save_data()
            
            # Calculate session duration
            self.session_duration = time.time() - start_time
            
            # Get final stats
            stats = self.get_stats()
            stats['output_file'] = output_file
            stats['success'] = True
            
            self.logger.info(f"Edgar & Cooper scraping completed: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Edgar & Cooper scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 