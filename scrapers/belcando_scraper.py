"""
Belcando pet store scraper using Bewital store finder API.
URL: https://www.bewital-petfood.de/storefinder/iframe?tag=Belcando
API: https://www.bewital-petfood.de/storefinder/search?q=0:0:0::0:2:Belcando&iframe=1
"""

import requests
import time
import json
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from utils.base_scraper import BaseScraper


class BelcandoScraper(BaseScraper):
    """Scraper for Belcando store finder using Bewital API."""
    
    def __init__(self):
        super().__init__('belcando')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'DNT': '1',
            'Referer': 'https://www.bewital-petfood.de/storefinder/iframe?tag=Belcando',
            'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        
        # API endpoint discovered from user's curl command
        self.api_url = "https://www.bewital-petfood.de/storefinder/search"
        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Scrape all Belcando stores using the Bewital store finder API.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Belcando store scraping via Bewital API")
        
        try:
            # Initialize session by visiting the main page
            self._initialize_session()
            
            # Get all stores from the API
            stores = self._fetch_all_stores()
            
            for store in stores:
                processed_store = self._process_store_data(store)
                self.add_store_data(processed_store)
                
            self.logger.info(f"Total stores found: {len(stores)}")
            return stores
            
        except Exception as e:
            self.log_error(f"Error in Belcando scraping: {str(e)}")
            return []
    
    def _initialize_session(self):
        """Initialize session by visiting the main page."""
        try:
            response = self.session.get(self.website_config['url'], timeout=30)
            response.raise_for_status()
            self.logger.info("Session initialized with Bewital website")
            
            # Add a small delay
            time.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize session: {str(e)}")
            # Continue anyway, might still work
    
    def _fetch_all_stores(self) -> List[Dict[str, Any]]:
        """
        Fetch all stores from the Bewital store finder API.
        
        Returns:
            List of raw store data from API
        """
        stores = []
        
        try:
            # API parameters from the user's curl command
            params = {
                'q': '0:0:0::0:2:Belcando',
                'iframe': '1'
            }
            
            self.logger.info(f"Fetching stores from Bewital API: {self.api_url}")
            
            # Make the API request
            response = self.session.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            
            self.logger.info(f"API response status: {response.status_code}")
            
            # The response contains JSON with HTML content for each store
            try:
                data = response.json()
                self.logger.info(f"API response type: {type(data)}")
                
                if isinstance(data, dict) and 'branches' in data:
                    # Extract branches from the response
                    branches = data['branches']
                    if isinstance(branches, list):
                        for item in branches:
                            if isinstance(item, dict) and 'markerHtml' in item:
                                stores.append(item)
                        self.logger.info(f"Found {len(stores)} stores in API response")
                    else:
                        self.logger.error(f"Branches is not a list: {type(branches)}")
                        return []
                elif isinstance(data, list):
                    # Fallback: if it's still a list format
                    for item in data:
                        if isinstance(item, dict) and 'markerHtml' in item:
                            stores.append(item)
                    self.logger.info(f"Found {len(stores)} stores in API response")
                else:
                    self.logger.error(f"Unexpected API response format: {type(data)}")
                    self.logger.error(f"Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    return []
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {str(e)}")
                # Try to extract from HTML response if JSON parsing fails
                stores = self._parse_html_response(response.text)
            
            return stores
            
        except Exception as e:
            self.logger.error(f"Error fetching from Bewital API: {str(e)}")
            return []
    
    def _parse_html_response(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse HTML response as fallback if JSON parsing fails.
        
        Args:
            html_content: Raw HTML response
            
        Returns:
            List of store data dictionaries
        """
        stores = []
        
        try:
            # Look for JavaScript data or embedded JSON
            json_match = re.search(r'(\[.*\])', html_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            stores.append(item)
                            
        except Exception as e:
            self.logger.debug(f"Failed to parse HTML for JSON data: {str(e)}")
            
        return stores
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data from Bewital API into standardized format.
        
        Args:
            raw_store: Raw store data from API
            
        Returns:
            Processed store data dictionary
        """
        processed = {
            'store_id': raw_store.get('id', ''),
            'latitude': raw_store.get('latitude', ''),
            'longitude': raw_store.get('longitude', ''),
            'source': 'belcando_bewital_api',
            'scraped_timestamp': time.time()
        }
        
        # Parse HTML content from markerHtml to extract store details
        marker_html = raw_store.get('markerHtml', '')
        if marker_html:
            store_details = self._parse_marker_html(marker_html)
            processed.update(store_details)
        
        # Use direct address field if available
        if raw_store.get('address'):
            processed['full_address'] = raw_store['address']
        
        # Use direct name field if available
        if raw_store.get('name'):
            processed['name'] = raw_store['name']
        
        # Ensure we have a full address if not already set
        if not processed.get('full_address'):
            processed['full_address'] = self._format_full_address(processed)
        
        # Store raw data for reference
        processed['raw_data'] = json.dumps(raw_store)
        
        return processed
    
    def _parse_marker_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parse the HTML marker content to extract store information.
        
        Args:
            html_content: HTML content from markerHtml field
            
        Returns:
            Dictionary with extracted store information
        """
        store_data = {}
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract store name from h5 tag
            name_elem = soup.find('h5')
            if name_elem:
                # Remove any links and get clean text
                for link in name_elem.find_all('a'):
                    link.replace_with(link.get_text())
                store_data['name'] = name_elem.get_text(strip=True)
            
            # Extract brands/products from the first p tag
            brands_elem = soup.find('p')
            if brands_elem:
                brands_text = brands_elem.get_text(strip=True)
                store_data['brands'] = brands_text
                
                # Extract individual brand names
                brand_names = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', brands_text)
                if brand_names:
                    store_data['brand_list'] = ', '.join(brand_names)
            
            # Extract address from address tag
            address_elem = soup.find('address')
            if address_elem:
                address_text = address_elem.get_text('\n', strip=True)
                address_lines = [line.strip() for line in address_text.split('\n') if line.strip()]
                
                if len(address_lines) >= 2:
                    store_data['street'] = address_lines[0]
                    
                    # Parse city and postal code from second line (format: "12345 City")
                    city_line = address_lines[1]
                    postal_match = re.match(r'^(\d{5})\s+(.+)$', city_line)
                    if postal_match:
                        store_data['postal_code'] = postal_match.group(1)
                        store_data['city'] = postal_match.group(2)
                    else:
                        store_data['city'] = city_line
                        
                    if len(address_lines) >= 3:
                        store_data['country'] = address_lines[2]
                
                store_data['full_address'] = ', '.join(address_lines)
            
            # Extract contact information
            contact_info = self._extract_contact_info(soup)
            store_data.update(contact_info)
            
            # Extract opening hours
            hours_elem = soup.find('h6', string=re.compile(r'Öffnungszeiten|Opening'))
            if hours_elem:
                hours_p = hours_elem.find_next_sibling('p')
                if hours_p:
                    store_data['opening_hours'] = hours_p.get_text(strip=True)
            
            # Extract website
            website_elem = soup.find('a', class_='btn btn-secondary')
            if website_elem and website_elem.get('href'):
                href = website_elem.get('href')
                if href.startswith('http'):
                    store_data['website'] = href
            
        except Exception as e:
            self.logger.debug(f"Error parsing marker HTML: {str(e)}")
            # Store raw HTML for debugging
            store_data['raw_html'] = html_content
        
        return store_data
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract phone and email from soup."""
        contact_info = {}
        
        # Find phone numbers
        phone_links = soup.find_all('a', href=re.compile(r'^tel:'))
        if phone_links:
            contact_info['phone'] = phone_links[0].get_text(strip=True)
        
        # Find email addresses
        email_links = soup.find_all('a', href=re.compile(r'^mailto:'))
        if email_links:
            contact_info['email'] = email_links[0].get_text(strip=True)
        
        return contact_info
    
    def _format_full_address(self, store_data: Dict[str, Any]) -> str:
        """Format full address from components."""
        address_parts = []
        
        if store_data.get('street'):
            address_parts.append(store_data['street'])
        
        if store_data.get('postal_code') and store_data.get('city'):
            address_parts.append(f"{store_data['postal_code']} {store_data['city']}")
        elif store_data.get('city'):
            address_parts.append(store_data['city'])
        
        if store_data.get('country'):
            address_parts.append(store_data['country'])
        
        return ', '.join(address_parts)
    
    def run(self) -> Dict[str, Any]:
        """
        Run the Belcando API scraper.
        
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
            
            self.logger.info(f"Belcando scraping completed successfully: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Belcando scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 