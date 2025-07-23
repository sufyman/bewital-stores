"""
Bosch pet store scraper using Amasty Store Locator API.
URL: https://www.bosch-tiernahrung.de/haendlersuche
API: https://www.bosch-tiernahrung.de/bosch_de_de/amlocator/index/ajax/
"""

import requests
import time
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from utils.base_scraper import BaseScraper


class BoschScraper(BaseScraper):
    """Scraper for Bosch store finder using Amasty Store Locator API."""
    
    def __init__(self):
        super().__init__('bosch')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Referer': self.website_config['url'],
            'X-Requested-With': 'XMLHttpRequest',
            'DNT': '1'
        })
        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Scrape all Bosch stores using the Amasty Store Locator API.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Bosch store scraping via Amasty API")
        
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
            self.log_error(f"Error in Bosch scraping: {str(e)}")
            return []
    
    def _initialize_session(self):
        """Initialize session by visiting the main page."""
        try:
            response = self.session.get(self.website_config['url'], timeout=30)
            response.raise_for_status()
            self.logger.info("Session initialized with Bosch website")
            
            # Add a small delay
            time.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize session: {str(e)}")
            # Continue anyway, might still work
    
    def _fetch_all_stores(self) -> List[Dict[str, Any]]:
        """
        Fetch all stores from the Amasty Store Locator API.
        
        Returns:
            List of raw store data from API
        """
        stores = []
        
        # Amasty Store Locator API endpoint
        api_url = "https://www.bosch-tiernahrung.de/bosch_de_de/amlocator/index/ajax/"
        
        try:
            self.logger.info(f"Fetching stores from Amasty API: {api_url}")
            
            # Make the API request
            response = self.session.get(api_url, timeout=30)
            response.raise_for_status()
            
            self.logger.info(f"API response status: {response.status_code}")
            
            # Parse JSON response
            data = response.json()
            self.logger.info(f"API response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if isinstance(data, dict) and 'items' in data:
                stores = data['items']
                total_records = data.get('totalRecords', len(stores))
                self.logger.info(f"Found {len(stores)} stores (totalRecords: {total_records})")
            else:
                self.logger.error("Unexpected API response structure")
                return []
            
            return stores
            
        except Exception as e:
            self.logger.error(f"Error fetching from Amasty API: {str(e)}")
            return []
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data from Amasty API into standardized format.
        
        Args:
            raw_store: Raw store data from API
            
        Returns:
            Processed store data dictionary
        """
        processed = {
            'store_id': raw_store.get('id', ''),
            'latitude': raw_store.get('lat', ''),
            'longitude': raw_store.get('lng', ''),
            'source': 'bosch_amasty_api'
        }
        
        # Parse HTML popup content to extract store details
        popup_html = raw_store.get('popup_html', '')
        if popup_html:
            store_details = self._parse_popup_html(popup_html)
            processed.update(store_details)
        
        # Ensure we have a full address
        processed['full_address'] = self._format_full_address(processed)
        
        # Store raw data for reference
        processed['raw_data'] = str(raw_store)
        
        return processed
    
    def _parse_popup_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parse the HTML popup content to extract store information.
        
        Args:
            html_content: HTML content from popup_html field
            
        Returns:
            Dictionary with extracted store information
        """
        store_data = {}
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract store name
            name_elem = soup.find(class_='amlocator-title')
            if name_elem:
                store_data['name'] = name_elem.get_text(strip=True)
            
            # Remove structured elements to get the raw address/contact text
            # Remove the name and image containers
            for elem in soup.find_all(['h3', 'div'], class_=['amlocator-name', 'amlocator-image']):
                elem.decompose()
            
            # Get remaining text and parse address/contact info
            remaining_text = soup.get_text()
            lines = [line.strip() for line in remaining_text.split('\n') if line.strip()]
            
            # Also try splitting by <br> tags in original HTML
            br_split = re.split(r'<br\s*/?>', html_content, flags=re.IGNORECASE)
            br_lines = [line.strip() for line in br_split if line.strip()]
            
            # Combine both approaches to get all text lines
            all_lines = []
            for line in lines + br_lines:
                # Clean up HTML tags and entities
                clean_line = re.sub(r'<[^>]+>', '', line).strip()
                clean_line = clean_line.replace('&nbsp;', ' ').strip()
                if clean_line and clean_line not in all_lines:
                    all_lines.append(clean_line)
            
            # Parse the lines to extract address components
            street = ''
            city = ''
            postal_code = ''
            phone = ''
            email = ''
            website = ''
            
            for line in all_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip the store name if it appears again
                if store_data.get('name') and store_data['name'].lower() in line.lower():
                    continue
                
                # Email detection
                if '@' in line:
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
                    if email_match:
                        email = email_match.group(0)
                    continue
                
                # Phone detection
                if any(keyword in line.lower() for keyword in ['telefon:', 'tel:', 'phone:']):
                    phone = self._extract_phone(line)
                    continue
                
                # Website detection
                if any(keyword in line.lower() for keyword in ['website:', 'www.', 'http']):
                    website = self._extract_website(line)
                    continue
                
                # Postal code + city pattern (German format: 12345 City Name)
                postal_match = re.match(r'^(\d{5})\s+(.+)$', line)
                if postal_match:
                    postal_code = postal_match.group(1)
                    city = postal_match.group(2).strip()
                    continue
                
                # Street address (if no postal code found yet and doesn't match other patterns)
                if not postal_code and not street and not any(keyword in line.lower() for keyword in ['telefon', 'email', 'website', '@']):
                    street = line
            
            # Assign parsed data
            store_data.update({
                'street': street,
                'city': city,
                'postal_code': postal_code,
                'phone': phone,
                'email': email,
                'website': website
            })
            
        except Exception as e:
            self.logger.debug(f"Error parsing HTML popup: {str(e)}")
            # Store raw HTML for debugging
            store_data['raw_html'] = html_content
        
        return store_data
    
    def _extract_phone(self, line: str) -> str:
        """Extract phone number from a line."""
        # Remove common prefixes
        cleaned = re.sub(r'^(telefon|tel|phone):\s*', '', line, flags=re.IGNORECASE)
        
        # Extract phone number pattern
        phone_match = re.search(r'[\d\s\-\+\(\)\/]+', cleaned)
        if phone_match:
            return phone_match.group(0).strip()
        
        return ''
    
    def _extract_website(self, line: str) -> str:
        """Extract website from a line."""
        # Remove common prefixes
        cleaned = re.sub(r'^website:\s*', '', line, flags=re.IGNORECASE)
        
        # Extract URL
        url_match = re.search(r'https?://[^\s]+', cleaned)
        if url_match:
            return url_match.group(0)
        
        # Check for www. pattern
        www_match = re.search(r'www\.[^\s]+', cleaned)
        if www_match:
            return f'http://{www_match.group(0)}'
        
        return cleaned.strip()
    
    def _format_full_address(self, store_data: Dict[str, Any]) -> str:
        """Format full address from components."""
        address_parts = []
        
        if store_data.get('street'):
            address_parts.append(store_data['street'])
        
        if store_data.get('postal_code') and store_data.get('city'):
            address_parts.append(f"{store_data['postal_code']} {store_data['city']}")
        elif store_data.get('city'):
            address_parts.append(store_data['city'])
        
        return ', '.join(address_parts)
    
    def run(self) -> Dict[str, Any]:
        """
        Run the Bosch API scraper.
        
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
            
            self.logger.info(f"Bosch scraping completed successfully: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Bosch scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 