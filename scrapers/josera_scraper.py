"""
Josera pet store scraper using JSON API endpoint.
URL: https://fachhandel.josera.de/
API: Discovered via browser dev tools - loads store data as JSON
"""

import requests
import time
import json
from typing import List, Dict, Any
from urllib.parse import urljoin

from utils.base_scraper import BaseScraper


class JoseraScraper(BaseScraper):
    """Scraper for Josera store finder using JSON API."""
    
    def __init__(self):
        super().__init__('josera')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Referer': self.website_config['url'],
            'Origin': 'https://fachhandel.josera.de'
        })
        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Scrape all Josera stores using the JSON API endpoint.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Josera store scraping via JSON API")
        
        # First, navigate to the site to get any necessary cookies/tokens
        try:
            self._initialize_session()
            stores = self._fetch_all_stores()
            
            for store in stores:
                processed_store = self._process_store_data(store)
                self.add_store_data(processed_store)
                
            self.logger.info(f"Total stores found: {len(stores)}")
            return stores
            
        except Exception as e:
            self.log_error(f"Error in Josera scraping: {str(e)}")
            return []
    
    def _initialize_session(self):
        """Initialize session by visiting the main page to get cookies."""
        try:
            response = self.session.get(self.website_config['url'], timeout=30)
            response.raise_for_status()
            self.logger.info("Session initialized with Josera website")
            
            # Add a small delay
            time.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize session: {str(e)}")
            # Continue anyway, might still work
    
    def _fetch_all_stores(self) -> List[Dict[str, Any]]:
        """
        Fetch all stores from the Next.js JSON API endpoint.
        
        Returns:
            List of raw store data from API
        """
        stores = []
        
        # Use the discovered Next.js API endpoint
        api_url = "https://fachhandel.josera.de/_next/data/tC2WS-5m6zxCBNQ4qR1HB/index.json"
        
        try:
            self.logger.info(f"Fetching data from Next.js API: {api_url}")
            
            # Add Next.js specific headers
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
                'X-Nextjs-Data': '1',
                'Purpose': 'prefetch',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Referer': self.website_config['url']
            }
            
            # Update session headers
            self.session.headers.update(headers)
            
            response = self.session.get(api_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.logger.info(f"API response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Navigate through Next.js data structure
            if isinstance(data, dict) and 'pageProps' in data:
                page_props = data['pageProps']
                self.logger.info(f"PageProps keys: {list(page_props.keys()) if isinstance(page_props, dict) else 'Not a dict'}")
                
                # Look for store data in various possible keys
                possible_store_keys = [
                    'shops', 'stores', 'dealers', 'partners', 'locations', 'data', 
                    'storeData', 'dealerData', 'partnerData', 'mapData',
                    'initialData', 'props', 'content'
                ]
                
                for key in possible_store_keys:
                    if key in page_props:
                        potential_stores = page_props[key]
                        if isinstance(potential_stores, list) and potential_stores:
                            stores = potential_stores
                            self.logger.info(f"Found {len(stores)} stores in pageProps.{key}")
                            break
                        elif isinstance(potential_stores, dict):
                            # Maybe stores are nested deeper
                            for sub_key in ['stores', 'data', 'items', 'results']:
                                if sub_key in potential_stores and isinstance(potential_stores[sub_key], list):
                                    stores = potential_stores[sub_key]
                                    self.logger.info(f"Found {len(stores)} stores in pageProps.{key}.{sub_key}")
                                    break
                            if stores:
                                break
                
                # If no stores found in known keys, log all available data for debugging
                if not stores:
                    self.logger.warning("No stores found in expected keys. Available pageProps structure:")
                    for key, value in page_props.items():
                        if isinstance(value, (list, dict)):
                            self.logger.info(f"  {key}: {type(value)} with {len(value) if hasattr(value, '__len__') else 'unknown'} items")
                        else:
                            self.logger.info(f"  {key}: {type(value)}")
            
            if stores:
                self.logger.info(f"Successfully fetched {len(stores)} stores from Next.js API")
                return stores
            else:
                self.logger.warning("No stores found in API response")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching from Next.js API: {str(e)}")
            # Fallback to discovery method
            return self._discover_api_endpoint()
    
    def _discover_api_endpoint(self) -> List[Dict[str, Any]]:
        """
        Try to discover the actual API endpoint by analyzing the website.
        
        Returns:
            List of store data if found
        """
        try:
            # Navigate to the site with browser to find the actual API calls
            self.start_session()
            
            # Go to the store finder page
            self._safe_request(self.website_config['url'])
            
            # Wait for page to load and look for network requests
            time.sleep(5)
            
            # Try to find JavaScript that makes API calls
            # Look for common patterns in the page source
            page_source = self.driver.page_source
            
            # Search for API URLs in the page source
            import re
            api_patterns = [
                r'"(/api/[^"]*)"',
                r"'/api/[^']*'",
                r'fetch\s*\(\s*[\'"]([^\'"]*)[\'"]',
                r'axios\.get\s*\(\s*[\'"]([^\'"]*)[\'"]',
                r'\.json\([\'"]([^\'"]*)[\'"]',
            ]
            
            found_urls = set()
            for pattern in api_patterns:
                matches = re.findall(pattern, page_source)
                found_urls.update(matches)
            
            # Try each discovered URL
            for url in found_urls:
                if 'store' in url.lower() or 'dealer' in url.lower() or 'partner' in url.lower():
                    full_url = urljoin("https://fachhandel.josera.de", url)
                    try:
                        response = self.session.get(full_url, timeout=30)
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, (list, dict)) and data:
                                self.logger.info(f"Discovered working API endpoint: {full_url}")
                                if isinstance(data, list):
                                    return data
                                elif isinstance(data, dict) and 'stores' in data:
                                    return data['stores']
                    except Exception:
                        continue
            
            self.logger.warning("Could not discover API endpoint automatically")
            return []
            
        except Exception as e:
            self.log_error(f"Error in API discovery: {str(e)}")
            return []
        finally:
            self.end_session()
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data from API into standardized format.
        
        Args:
            raw_store: Raw store data from JSON API
            
        Returns:
            Processed store data dictionary
        """
        # Based on the JSON structure you showed, extract the fields
        processed = {
            'id': raw_store.get('id', ''),
            'name': raw_store.get('name', ''),
            'address_street': raw_store.get('addressStreet', ''),
            'address_city': raw_store.get('addressCity', ''),
            'address_postcode': raw_store.get('addressPostcode', ''),
            'address_region': raw_store.get('addressRegion', ''),
            'address_country': raw_store.get('addressCountry', ''),
            'latitude': raw_store.get('latitude', ''),
            'longitude': raw_store.get('longitude', ''),
            'contact_phone': raw_store.get('contactPhone', ''),
            'contact_mobile': raw_store.get('contactMobile', ''),
            'contact_email': raw_store.get('contactEmail', ''),
            'website_main': raw_store.get('websiteMain', ''),
            'website_card': raw_store.get('websiteCard', ''),
            'website_ecommerce': raw_store.get('websiteEcommerce', ''),
            'website_gpf': raw_store.get('websiteGPF', ''),
            
            # Opening hours
            'opening_monday': raw_store.get('openingMon', ''),
            'opening_tuesday': raw_store.get('openingTue', ''),
            'opening_wednesday': raw_store.get('openingWed', ''),
            'opening_thursday': raw_store.get('openingThu', ''),
            'opening_friday': raw_store.get('openingFri', ''),
            'opening_saturday': raw_store.get('openingSat', ''),
            'opening_sunday': raw_store.get('openingSun', ''),
            
            # Additional info from the JSON
            'is_partner': raw_store.get('partner', False),
            'has_delivery': raw_store.get('delivery', False),
            'pos_available': raw_store.get('pos', False),
            'dog_category': raw_store.get('dog', False),
            'cat_category': raw_store.get('cat', False),
            'horse_category': raw_store.get('horse', False),
            'opening_enabled': raw_store.get('openingEnabled', False),
            
            # Formatted full address
            'full_address': self._format_full_address(raw_store),
            
            # Opening hours summary
            'opening_hours_summary': self._format_opening_hours(raw_store),
            
            # Store raw JSON for reference
            'raw_data': json.dumps(raw_store)
        }
        
        return processed
    
    def _format_full_address(self, store_data: Dict[str, Any]) -> str:
        """Format complete address from components."""
        address_parts = []
        
        if store_data.get('addressStreet'):
            address_parts.append(store_data['addressStreet'])
        
        city_part = []
        if store_data.get('addressPostcode'):
            city_part.append(store_data['addressPostcode'])
        if store_data.get('addressCity'):
            city_part.append(store_data['addressCity'])
        
        if city_part:
            address_parts.append(' '.join(city_part))
        
        if store_data.get('addressCountry'):
            address_parts.append(store_data['addressCountry'])
        
        return ', '.join(address_parts)
    
    def _format_opening_hours(self, store_data: Dict[str, Any]) -> str:
        """Format opening hours into readable summary."""
        days = [
            ('Mo', store_data.get('openingMon')),
            ('Di', store_data.get('openingTue')),
            ('Mi', store_data.get('openingWed')),
            ('Do', store_data.get('openingThu')),
            ('Fr', store_data.get('openingFri')),
            ('Sa', store_data.get('openingSat')),
            ('So', store_data.get('openingSun'))
        ]
        
        hours_summary = []
        for day, hours in days:
            if hours and hours != 'null':
                hours_summary.append(f"{day}: {hours}")
        
        return '; '.join(hours_summary)
    
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
            
            self.logger.info(f"Josera scraping completed successfully: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Josera scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 