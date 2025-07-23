"""
Finnern pet store scraper using retailer search API endpoint.
URL: https://www.finnern.de/haendlersuche
API: Discovered via browser dev tools - uses TYPO3 backend API for retailer search
"""

import requests
import time
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urlencode

from utils.base_scraper import BaseScraper


class FinnernScraper(BaseScraper):
    """Scraper for Finnern retailer search using POST API with systematic location search."""
    
    def __init__(self):
        super().__init__('finnern')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'DNT': '1',
            'Origin': 'https://www.finnern.de',
            'Referer': 'https://www.finnern.de/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        })
        
        # API endpoint and parameters discovered from browser dev tools
        self.api_url = "https://www.finnern.de/haendlersuche"
        self.api_params = {
            'tx_auwfinnern_retailersearchresult[action]': 'searchResult',
            'tx_auwfinnern_retailersearchresult[controller]': 'Retailer',
            'cHash': '61673a04e20cae0f07d5831ec420c580'
        }
        

        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Scrape all Finnern stores using systematic postal code searches across Germany.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Finnern store scraping via retailer search API")
        
        try:
            # Initialize session
            self._initialize_session()
            
            # Get all stores using systematic postal code searches
            all_stores = self._fetch_all_stores_systematic()
            
            # Process and add store data
            for store in all_stores:
                processed_store = self._process_store_data(store)
                self.add_store_data(processed_store)
                
            self.logger.info(f"Total unique stores found: {len(all_stores)}")
            return all_stores
            
        except Exception as e:
            self.log_error(f"Error in Finnern scraping: {str(e)}")
            return []
            
    def _initialize_session(self):
        """Initialize session by visiting the main page."""
        try:
            response = self.session.get(self.website_config['url'], timeout=30)
            response.raise_for_status()
            self.logger.info("Session initialized with Finnern website")
            time.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize session: {str(e)}")
            # Continue anyway, might still work
    
    def _fetch_all_stores_systematic(self) -> List[Dict[str, Any]]:
        """
        Fetch all Finnern stores using the session reset hack.
        
        Key insight: Navigate back to homepage between searches to reset session state.
        This allows multiple postal code searches across Germany.
        """
        all_stores = []
        seen_stores = set()  # Track unique stores by name + address
        
        # Strategic postal codes covering ALL German regions
        postal_code_searches = [
            ("10119", 20),  # Berlin/Brandenburg - Region 1
            ("10963", 20),  # Berlin (different area) - Region 1
            ("20095", 20),  # Hamburg/North Germany - Region 2
            ("80333", 20),  # Munich/Bavaria - Region 8
            ("80794", 5),   # Munich (smaller radius for different coverage) - Region 8
            ("50667", 20),  # Cologne/North Rhine-Westphalia - Region 5
            ("60311", 20),  # Frankfurt/Hesse - Region 6
            # Additional postal codes for complete German coverage
            ("01067", 20),  # Dresden/East Germany - Region 0
            ("30159", 20),  # Hannover/Central North - Region 3
            ("40210", 20),  # Düsseldorf/Western Ruhr - Region 4
            ("70173", 20),  # Stuttgart/Southwest - Region 7
            ("90403", 20),  # Nürnberg/Southeast - Region 9
        ]
        
        self.logger.info(f"Using session reset hack to search {len(postal_code_searches)} postal codes for COMPLETE German coverage")
        self.logger.info("Covering all 10 German postal regions: 0-9 (East to South)")
        
        for i, (postal_code, radius) in enumerate(postal_code_searches):
            try:
                self.logger.info(f"Searching postal code {postal_code} with {radius}km radius ({i+1}/{len(postal_code_searches)})")
                
                # Use session reset hack for each postal code
                stores = self._search_with_session_reset(postal_code, radius)
                
                new_stores_count = 0
                for store in stores:
                    # Create unique identifier for deduplication
                    store_id = f"{store.get('name', '')}-{store.get('address', '')}"
                    if store_id not in seen_stores:
                        seen_stores.add(store_id)
                        all_stores.append(store)
                        new_stores_count += 1
                
                if new_stores_count > 0:
                    self.logger.info(f"PLZ {postal_code}: Added {new_stores_count} new stores (total: {len(all_stores)})")
                else:
                    self.logger.info(f"PLZ {postal_code}: No new unique stores found")
                
                # Wait between searches to be respectful
                if i < len(postal_code_searches) - 1:
                    time.sleep(3)
                
            except Exception as e:
                self.logger.warning(f"Search for postal code {postal_code} failed: {str(e)}")
                continue
        
        self.logger.info(f"Enhanced search completed. Found {len(all_stores)} unique stores across Germany")
        unique_cities = len(set(store.get('city', '') for store in all_stores if store.get('city')))
        self.logger.info(f"Coverage: {unique_cities} unique cities across major German regions")
        
        return all_stores
    
    def _search_with_session_reset(self, postal_code: str, radius: int) -> List[Dict[str, Any]]:
        """
        Search for stores using the session reset hack.
        
        Steps:
        1. Navigate to homepage to reset session
        2. Navigate to search page 
        3. Perform search with new postal code
        
        Args:
            postal_code: German postal code to search
            radius: Search radius in kilometers
            
        Returns:
            List of store dictionaries
        """
        try:
            # Step 1: Reset session by visiting homepage
            self.session.headers['Referer'] = 'https://www.finnern.de/haendlersuche?tx_auwfinnern_retailersearchresult%5Baction%5D=searchResult&tx_auwfinnern_retailersearchresult%5Bcontroller%5D=Retailer&cHash=61673a04e20cae0f07d5831ec420c580'
            self.session.get('https://www.finnern.de/', timeout=30)
            time.sleep(1)
            
            # Step 2: Navigate to search page
            self.session.headers['Referer'] = 'https://www.finnern.de/'
            self.session.get('https://www.finnern.de/haendlersuche', timeout=30)
            time.sleep(1)
            
            # Step 3: Update headers for POST request
            self.session.headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cache-Control': 'max-age=0',
                'Origin': 'https://www.finnern.de',
                'Referer': 'https://www.finnern.de/'
            })
            
            # Step 4: Prepare POST data for this postal code
            post_data = {
                'tx_auwfinnern_retailersearchresult[__referrer][@extension]': 'AuwFinnern',
                'tx_auwfinnern_retailersearchresult[__referrer][@controller]': 'Retailer',
                'tx_auwfinnern_retailersearchresult[__referrer][@action]': 'searchBox',
                'tx_auwfinnern_retailersearchresult[__referrer][arguments]': 'YTowOnt9358e279a80a07b0ceae3147a3f1318177c99b416',
                'tx_auwfinnern_retailersearchresult[__referrer][@request]': '{"@extension":"AuwFinnern","@controller":"Retailer","@action":"searchBox"}2a40683d551441c9a9231e9a006bf6930ae45f20',
                'tx_auwfinnern_retailersearchresult[__trustedProperties]': '{"plz":1,"radius":1,"country":1}9b0e44876f2e28160d846ded4f7fb1f2a559a20a',
                'tx_auwfinnern_retailersearchresult[plz]': postal_code,
                'tx_auwfinnern_retailersearchresult[radius]': str(radius),
                'tx_auwfinnern_retailersearchresult[country]': 'D'
            }
            
            # Step 5: Make the API request
            response = self.session.post(
                self.api_url,
                params=self.api_params,
                data=post_data,
                timeout=30
            )
            response.raise_for_status()
            
            # Step 6: Parse the HTML response
            stores = self._parse_store_response(response.text)
            self.logger.debug(f"Found {len(stores)} stores for postal code {postal_code}")
            return stores
            
        except Exception as e:
            self.logger.error(f"Error searching postal code {postal_code} with session reset: {str(e)}")
            return []
    
    def _get_baseline_stores(self) -> List[Dict[str, Any]]:
        """
        Get stores using the original working request (PLZ 10119).
        This is our fallback that should always work.
        """
        post_data = {
            'tx_auwfinnern_retailersearchresult[__referrer][@extension]': 'AuwFinnern',
            'tx_auwfinnern_retailersearchresult[__referrer][@controller]': 'Retailer',
            'tx_auwfinnern_retailersearchresult[__referrer][@action]': 'searchBox',
            'tx_auwfinnern_retailersearchresult[__referrer][arguments]': 'YTowOnt9358e279a80a07b0ceae3147a3f1318177c99b416',
            'tx_auwfinnern_retailersearchresult[__referrer][@request]': '{"@extension":"AuwFinnern","@controller":"Retailer","@action":"searchBox"}2a40683d551441c9a9231e9a006bf6930ae45f20',
            'tx_auwfinnern_retailersearchresult[__trustedProperties]': '{"plz":1,"radius":1,"country":1}9b0e44876f2e28160d846ded4f7fb1f2a559a20a',
            'tx_auwfinnern_retailersearchresult[plz]': '10119',
            'tx_auwfinnern_retailersearchresult[radius]': '20',
            'tx_auwfinnern_retailersearchresult[country]': 'D'
        }
        
        # Use the main session for the baseline request
        response = self.session.post(
            self.api_url,
            params=self.api_params,
            data=post_data,
            timeout=30
        )
        response.raise_for_status()
        
        # Parse the HTML response
        stores = self._parse_store_response(response.text)
        return stores
    

    

    
    def _parse_store_response(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse HTML response to extract store information.
        
        Args:
            html_content: HTML response from the API
            
        Returns:
            List of store dictionaries
        """
        stores = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all store rows with class="initial"
            store_rows = soup.find_all('tr', class_='initial')
            
            for row in store_rows:
                store_data = self._extract_store_from_row(row)
                if store_data:
                    stores.append(store_data)
                    
        except Exception as e:
            self.logger.debug(f"Error parsing store response: {str(e)}")
            
        return stores
    
    def _extract_store_from_row(self, row) -> Dict[str, Any]:
        """
        Extract store information from a single table row.
        
        Args:
            row: BeautifulSoup table row element
            
        Returns:
            Dictionary with store data or None if extraction fails
        """
        try:
            store_data = {}
            
            # Get all table cells
            cells = row.find_all('td')
            if len(cells) < 1:
                return None
            
            # First cell contains store name and contact details
            first_cell = cells[0]
            
            # Extract store name from div with class="color-prim"
            name_div = first_cell.find('div', class_='color-prim')
            if name_div:
                store_data['name'] = name_div.get_text(strip=True)
            
            # Extract additional details from the details div
            details_div = first_cell.find('div', class_='details')
            if details_div:
                # Extract company name from span with class="small"
                company_span = details_div.find('span', class_='small')
                if company_span:
                    store_data['company'] = company_span.get_text(strip=True)
                
                # Extract phone numbers - look for text containing phone icons
                phone_pattern = re.compile(r'\+49\s*\([^)]+\)\s*[\d\s]+')
                details_text = details_div.get_text()
                phone_matches = phone_pattern.findall(details_text)
                if phone_matches:
                    store_data['phone'] = phone_matches[0].strip()
                
                # Extract fax numbers
                if 'fax' in details_text.lower():
                    fax_matches = phone_pattern.findall(details_text)
                    if len(fax_matches) > 1:
                        store_data['fax'] = fax_matches[1].strip()
            
            # Second cell contains address information (if present)
            if len(cells) > 1:
                second_cell = cells[1]
                # Get the text content, stopping before any <a> tag
                address_text = ""
                for content in second_cell.contents:
                    if hasattr(content, 'name') and content.name == 'a':
                        break
                    if hasattr(content, 'strip'):
                        address_text += content.strip()
                
                if address_text:
                    store_data['address'] = address_text.strip()
                    
                    # Parse postal code and city from address
                    # Format: "12169 Berlin / Steglitzer Damm 29"
                    address_match = re.match(r'(\d{5})\s+([^/]+)\s*/\s*(.+)', address_text.strip())
                    if address_match:
                        store_data['postal_code'] = address_match.group(1)
                        store_data['city'] = address_match.group(2).strip()
                        store_data['street'] = address_match.group(3).strip()
            
            # Only return if we have at least a name
            if store_data.get('name'):
                return store_data
                
        except Exception as e:
            self.logger.debug(f"Error extracting store from row: {str(e)}")
            
        return None
    
    def _process_store_data(self, store_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and standardize store data.
        
        Args:
            store_data: Raw store data dictionary
            
        Returns:
            Processed store data with standardized fields
        """
        processed = {
            'scraped_timestamp': time.time()
        }
        
        # Copy all original fields
        for key, value in store_data.items():
            if key and value:
                processed[key] = str(value).strip()
        
        # Standardize field names
        field_mapping = {
            'std_name': store_data.get('name', ''),
            'std_company': store_data.get('company', ''),
            'std_phone': store_data.get('phone', ''),
            'std_fax': store_data.get('fax', ''),
            'std_street': store_data.get('street', ''),
            'std_city': store_data.get('city', ''),
            'std_postal_code': store_data.get('postal_code', ''),
            'std_country': 'Germany',
            'std_full_address': store_data.get('address', '')
        }
        
        processed.update(field_mapping)
        
        return processed
    
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
            output_file = self.save_data() if stores else None
            
            # Calculate session duration
            self.session_duration = time.time() - start_time
            
            # Get final stats
            stats = self.get_stats()
            stats['output_file'] = output_file
            stats['success'] = True
            
            self.logger.info(f"Finnern scraping completed successfully: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Finnern scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 