"""
Bozita pet store scraper using WordPress AJAX endpoint.
URL: https://bozita.com/de/fachhandler-suchen/
API: https://bozita.com/de/wp-admin/admin-ajax.php
"""

import requests
import time
import json
from typing import List, Dict, Any

from utils.base_scraper import BaseScraper


class BozitaScraper(BaseScraper):
    """Scraper for Bozita store finder using WordPress AJAX API."""
    
    def __init__(self):
        super().__init__('bozita')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'DNT': '1',
            'Origin': 'https://bozita.com',
            'Referer': self.website_config['url'],
            'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'Sec-Ch-Ua-Mobile': '?1',
            'Sec-Ch-Ua-Platform': '"Android"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Scrape all Bozita stores using the WordPress AJAX endpoint.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Bozita store scraping via AJAX API")
        
        try:
            # Initialize session
            self._initialize_session()
            
            # Get all stores from AJAX endpoint
            stores = self._fetch_all_stores()
            
            for store in stores:
                # For HTML parsed stores, we don't need additional processing
                # as the data is already extracted and structured
                self.add_store_data(store)
                
            self.logger.info(f"Total stores found: {len(stores)}")
            return stores
            
        except Exception as e:
            self.log_error(f"Error in Bozita scraping: {str(e)}")
            return []
    
    def _initialize_session(self):
        """Initialize session by visiting the main page."""
        try:
            response = self.session.get(self.website_config['url'], timeout=30)
            response.raise_for_status()
            self.logger.info("Session initialized with Bozita website")
            
            # Add a small delay
            time.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize session: {str(e)}")
            # Continue anyway, might still work
    
    def _fetch_all_stores(self) -> List[Dict[str, Any]]:
        """
        Fetch all stores from the WordPress AJAX endpoint.
        
        Returns:
            List of raw store data from API
        """
        stores = []
        
        # WordPress AJAX endpoint discovered from browser dev tools
        ajax_url = "https://bozita.com/de/wp-admin/admin-ajax.php"
        
        try:
            self.logger.info(f"Fetching stores from WordPress AJAX: {ajax_url}")
            
            # Prepare the POST data
            post_data = {
                'action': 'find_a_stockist',
                'userLoc': '',
                'searchedLoc': '',
                'pageId': '7104'
            }
            
            # Make the AJAX request
            response = self.session.post(ajax_url, data=post_data, timeout=30)
            response.raise_for_status()
            
            self.logger.info(f"AJAX response status: {response.status_code}")
            self.logger.info(f"Response content length: {len(response.text)} characters")
            
            # Try to parse JSON response
            try:
                data = response.json()
                self.logger.info(f"JSON response type: {type(data)}")
                
                if isinstance(data, list):
                    stores = data
                    self.logger.info(f"Found {len(stores)} stores in list response")
                elif isinstance(data, dict):
                    # Look for stores in various possible keys
                    possible_keys = ['stores', 'stockists', 'dealers', 'data', 'results', 'items']
                    for key in possible_keys:
                        if key in data and isinstance(data[key], list):
                            stores = data[key]
                            self.logger.info(f"Found {len(stores)} stores in data.{key}")
                            break
                    
                    # If no stores found in expected keys, log the structure
                    if not stores:
                        self.logger.warning("No stores found in expected keys. Response structure:")
                        for key, value in data.items():
                            if isinstance(value, (list, dict)):
                                self.logger.info(f"  {key}: {type(value)} with {len(value) if hasattr(value, '__len__') else 'unknown'} items")
                            else:
                                self.logger.info(f"  {key}: {type(value)} - {str(value)[:100]}")
                
            except json.JSONDecodeError:
                # Response is HTML, parse it for store data
                self.logger.info("Response is HTML, parsing for store data...")
                response_text = response.text.strip()
                
                # Parse HTML using BeautifulSoup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response_text, 'html.parser')
                
                # Find store containers - look for elements with 'store-' class or similar
                store_containers = soup.find_all(['div', 'li'], class_=lambda x: x and ('store-' in x or 'stock-listing' in x))
                
                if not store_containers:
                    # Try alternative selectors
                    store_containers = soup.find_all('div', class_=lambda x: x and 'stock-listing' in x)
                
                if not store_containers:
                    # Try to find any div with store information
                    store_containers = soup.find_all('div', string=lambda text: text and any(keyword in text.lower() for keyword in ['str', 'strasse', 'street', 'plz']))
                    # Get parent containers
                    if store_containers:
                        store_containers = [container.find_parent('div') for container in store_containers]
                
                self.logger.info(f"Found {len(store_containers)} store containers in HTML")
                
                # Extract store data from HTML containers
                for i, container in enumerate(store_containers):
                    try:
                        store_data = self._extract_html_store_data(container)
                        if store_data and store_data.get('name'):
                            # Ensure all stores have consistent fields
                            standardized_store = self._standardize_store_fields(store_data)
                            stores.append(standardized_store)
                    except Exception as e:
                        self.logger.debug(f"Error extracting store {i}: {str(e)}")
                        continue
                
                self.logger.info(f"Successfully extracted {len(stores)} stores from HTML")
            
            return stores
            
        except Exception as e:
            self.logger.error(f"Error fetching from AJAX endpoint: {str(e)}")
            return []
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data from AJAX API into standardized format.
        
        Args:
            raw_store: Raw store data from API
            
        Returns:
            Processed store data dictionary
        """
        # Process the AJAX response data
        processed = {}
        
        # Copy all original fields first
        for key, value in raw_store.items():
            if key:  # Only if key is not empty
                processed[key] = str(value).strip() if value else ''
        
        # Try to map common fields based on typical WordPress store finder patterns
        field_mappings = {
            'name': ['name', 'title', 'store_name', 'business_name', 'company'],
            'address': ['address', 'full_address', 'street', 'location'],
            'city': ['city', 'town', 'place'],
            'postal_code': ['postal_code', 'zip', 'postcode', 'plz'],
            'country': ['country', 'land'],
            'phone': ['phone', 'telephone', 'tel'],
            'email': ['email', 'mail'],
            'website': ['website', 'url', 'web'],
            'latitude': ['lat', 'latitude', 'y'],
            'longitude': ['lng', 'longitude', 'x'],
            'description': ['description', 'desc', 'info']
        }
        
        # Map fields to standardized names
        for standard_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                # Check both exact match and case-insensitive
                for api_key in raw_store.keys():
                    if api_key and (api_key.lower() == key.lower() or key.lower() in api_key.lower()):
                        processed[f'std_{standard_field}'] = str(raw_store[api_key]).strip() if raw_store[api_key] else ''
                        break
                if f'std_{standard_field}' in processed:
                    break
        
        # Add source metadata
        processed['original_api_data'] = json.dumps(raw_store)
        
        return processed
    
    def _extract_html_store_data(self, container) -> Dict[str, Any]:
        """
        Extract store data from HTML container element.
        
        Args:
            container: BeautifulSoup element containing store information
            
        Returns:
            Dictionary with store data
        """
        store_data = {}
        
        try:
            # Extract store name from h3 tag
            name_element = container.find('h3')
            if name_element:
                store_data['name'] = name_element.get_text(strip=True)
                # Clean up HTML entities
                store_data['name'] = store_data['name'].replace('&#038;', '&').replace('&amp;', '&')
            
            # Extract address from p tag
            address_element = container.find('p')
            if address_element:
                full_address = address_element.get_text(strip=True)
                store_data['full_address'] = full_address
                
                # Try to parse address components (street, postal code, city)
                address_parts = [part.strip() for part in full_address.split(',')]
                if len(address_parts) >= 2:
                    store_data['street'] = address_parts[0]
                    
                    # Last part is usually postal code + city
                    if len(address_parts) >= 3:
                        postal_city = address_parts[-1].strip()
                    else:
                        postal_city = address_parts[1].strip()
                    
                    # Split postal code and city
                    postal_city_parts = postal_city.split()
                    if len(postal_city_parts) >= 2:
                        store_data['postal_code'] = postal_city_parts[0]
                        store_data['city'] = ' '.join(postal_city_parts[1:])
                    else:
                        store_data['city'] = postal_city
            
            # Extract product tags (dog/cat indicators)
            product_tags = []
            tag_elements = container.find_all('span', class_=lambda x: x and ('is_' in x if x else False))
            for tag in tag_elements:
                if tag.get_text(strip=True):
                    product_tags.append(tag.get_text(strip=True))
            store_data['product_categories'] = ', '.join(product_tags) if product_tags else ''
            
            # Extract Google Maps link if available
            maps_link = container.find('a', href=lambda x: x and 'google.com/maps' in x)
            if maps_link:
                store_data['google_maps_url'] = maps_link.get('href')
            
            # Extract store ID from class name
            store_id_match = None
            classes = container.get('class', [])
            for cls in classes:
                if cls.startswith('store-'):
                    store_id_match = cls.replace('store-', '')
                    break
            
            if store_id_match:
                store_data['store_id'] = store_id_match
            
            # Check if store is hidden (has d-none class)
            store_data['is_visible'] = 'd-none' not in container.get('class', [])
            
            # Add metadata
            store_data['source'] = 'bozita_ajax_api'
            store_data['original_html'] = str(container)
            
        except Exception as e:
            self.logger.debug(f"Error extracting HTML store data: {str(e)}")
        
        return store_data
    
    def _standardize_store_fields(self, store_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure all stores have the same set of fields for consistent CSV output.
        
        Args:
            store_data: Raw store data dictionary
            
        Returns:
            Standardized store data dictionary
        """
        # Define standard fields that all stores should have
        standard_fields = {
            'name': '',
            'full_address': '',
            'street': '',
            'postal_code': '',
            'city': '',
            'product_categories': '',
            'google_maps_url': '',
            'store_id': '',
            'is_visible': True,
            'source': 'bozita_ajax_api'
        }
        
        # Start with standard fields and update with actual data
        standardized = standard_fields.copy()
        for key, value in store_data.items():
            if key in standard_fields:
                standardized[key] = value
        
        return standardized
    
    def run(self) -> Dict[str, Any]:
        """
        Override run method to use requests instead of Selenium for API calls.
        
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
            
            self.logger.info(f"Bozita scraping completed successfully: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Bozita scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 