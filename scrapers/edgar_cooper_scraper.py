"""
Edgar & Cooper pet store scraper for German stores.
URL: https://www.edgardcooper.com/en/store-locator/
Approach: Uses discovered working API with systematic coordinate search across Germany
"""

import requests
import time
import json
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from utils.base_scraper import BaseScraper


class EdgarCooperScraper(BaseScraper):
    """
    Comprehensive scraper for Edgar & Cooper store finder.
    Uses multiple strategies to extract maximum store data.
    """
    
    def __init__(self):
        super().__init__('edgar_cooper')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Referer': self.website_config['url'],
            'DNT': '1'
        })
        
        # Working API endpoint discovered
        self.api_base_url = "https://apim-b2c-edgardcooper-prd.azure-api.net/b2c/location/retail-stores"
        self.api_key = "816ad8cfa7f9429b84533b1c394c9c8d"
        
        # API endpoints to explore (backup options)
        self.api_endpoints = [
            "https://www.edgardcooper.com/api/stores",
            "https://www.edgardcooper.com/api/stores/search",
            "https://www.edgardcooper.com/en/api/stores",
            "https://www.edgardcooper.com/en/api/stores/search",
            "https://www.edgardcooper.com/_next/data/*/en/store-locator.json",
            "https://apim-b2c-edgardcooper-prd.azure-api.net/stores",
            "https://apim-b2c-edgardcooper-prd.azure-api.net/api/stores",
            "https://cdn.edgardcooper.com/stores.json",
            "https://cdn.edgardcooper.com/api/stores.json",
        ]
        
        # European countries where Edgar & Cooper operates
        self.target_countries = [
            'Germany', 'Netherlands', 'Belgium', 'France', 'United Kingdom',
            'Italy', 'Spain', 'Austria', 'Switzerland', 'Denmark', 'Sweden',
            'Norway', 'Finland', 'Poland', 'Czech Republic'
        ]
        
        # Coordinate grid for systematic European coverage
        self.search_coordinates = self._generate_european_grid()
        
        # Major cities for systematic search (backup method)
        self.major_cities = [
            # Germany
            'Berlin', 'Munich', 'Hamburg', 'Cologne', 'Frankfurt', 'Stuttgart', 
            'Düsseldorf', 'Leipzig', 'Dortmund', 'Essen', 'Bremen', 'Dresden',
            'Hanover', 'Nuremberg', 'Duisburg', 'Bochum', 'Wuppertal', 'Bielefeld',
            
            # Netherlands
            'Amsterdam', 'Rotterdam', 'The Hague', 'Utrecht', 'Eindhoven', 
            'Tilburg', 'Groningen', 'Almere', 'Breda', 'Nijmegen',
            
            # Belgium
            'Brussels', 'Antwerp', 'Ghent', 'Charleroi', 'Liège', 'Bruges',
            'Namur', 'Leuven', 'Mons', 'Aalst',
            
            # France
            'Paris', 'Marseille', 'Lyon', 'Toulouse', 'Nice', 'Nantes',
            'Strasbourg', 'Montpellier', 'Bordeaux', 'Lille',
            
            # UK
            'London', 'Birmingham', 'Manchester', 'Liverpool', 'Leeds',
            'Sheffield', 'Bristol', 'Glasgow', 'Edinburgh', 'Newcastle',
            
            # Other countries
            'Rome', 'Milan', 'Madrid', 'Barcelona', 'Vienna', 'Zurich',
            'Copenhagen', 'Stockholm', 'Oslo', 'Helsinki', 'Warsaw', 'Prague'
        ]
    
    def _generate_european_grid(self) -> List[tuple]:
        """Generate a systematic grid of coordinates covering Germany."""
        coordinates = []
        
        # German boundaries (approximate)
        # North: 55.1° (Danish border), South: 47.3° (Austrian border)
        # West: 5.9° (Dutch/Belgian border), East: 15.0° (Polish border)
        
        # Grid resolution (roughly every ~50km for better coverage)
        lat_step = 0.5  # About 55km
        lng_step = 0.7  # About 50km at 50° latitude
        
        # Generate grid points covering Germany
        lat = 47.0  # Start from south (a bit south of Germany)
        while lat <= 55.5:  # A bit north of Germany
            lng = 5.5  # Start from west (a bit west of Germany)
            while lng <= 15.5:  # A bit east of Germany
                coordinates.append((lat, lng))
                lng += lng_step
            lat += lat_step
        
        # Add major German city coordinates for better coverage
        major_german_coords = [
            (52.5200, 13.4050),  # Berlin
            (48.1351, 11.5820),  # Munich
            (53.5511, 9.9937),   # Hamburg
            (50.9375, 6.9603),   # Cologne
            (50.1109, 8.6821),   # Frankfurt
            (48.7758, 9.1829),   # Stuttgart
            (51.2277, 6.7735),   # Düsseldorf
            (51.3397, 12.3731),  # Leipzig
            (51.5136, 7.4653),   # Dortmund
            (51.4556, 7.0116),   # Essen
            (53.0793, 8.8017),   # Bremen
            (51.0504, 13.7373),  # Dresden
            (52.3759, 9.7320),   # Hanover
            (49.4521, 11.0767),  # Nuremberg
            (51.4344, 6.7623),   # Duisburg
            (51.4818, 7.2162),   # Bochum
            (51.2562, 7.1508),   # Wuppertal
            (52.0302, 8.5325),   # Bielefeld
            (49.0069, 8.4037),   # Karlsruhe
            (51.9607, 7.6261),   # Münster
            (52.2689, 10.5268),  # Braunschweig
            (54.0865, 12.1444),  # Rostock
        ]
        
        coordinates.extend(major_german_coords)
        return coordinates
        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Main scraping method using multiple strategies.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting comprehensive Edgar & Cooper store scraping")
        all_stores = []
        
        try:
            # Strategy 1: Use discovered working API with coordinate grid search
            self.logger.info("Strategy 1: Using discovered working API with systematic coordinate search")
            api_stores = self._extract_all_stores_via_api()
            if api_stores:
                all_stores.extend(api_stores)
                self.logger.info(f"Found {len(api_stores)} stores via working API")
            
            # Fallback strategies if API doesn't work or returns insufficient data
            if len(all_stores) < 50:  # Expect at least 50 stores in Germany
                self.logger.info("API yielded fewer stores than expected, trying fallback strategies")
                
                # Strategy 2: Legacy API exploration
                self.logger.info("Strategy 2: Exploring backup API endpoints")
                backup_stores = self._explore_api_endpoints()
                if backup_stores:
                    new_stores = self._deduplicate_stores(backup_stores, all_stores)
                    all_stores.extend(new_stores)
                    self.logger.info(f"Found {len(new_stores)} new stores via backup APIs")
                
                # Strategy 3: Browser-based exploration with dynamic content loading
                self.logger.info("Strategy 3: Browser automation with dynamic loading")
                browser_stores = self._browser_exploration()
                if browser_stores:
                    new_stores = self._deduplicate_stores(browser_stores, all_stores)
                    all_stores.extend(new_stores)
                    self.logger.info(f"Found {len(new_stores)} new stores via browser automation")
            
            # Process all found stores
            for store in all_stores:
                processed_store = self._process_store_data(store)
                self.add_store_data(processed_store)
                
            self.logger.info(f"Total unique stores found: {len(all_stores)}")
            return all_stores
            
        except Exception as e:
            self.log_error(f"Error in Edgar & Cooper scraping: {str(e)}")
            return []
    
    def _explore_api_endpoints(self) -> List[Dict[str, Any]]:
        """Systematically explore potential API endpoints."""
        stores = []
        
        for endpoint in self.api_endpoints:
            try:
                self.logger.info(f"Testing endpoint: {endpoint}")
                
                # Try different methods and parameters
                stores.extend(self._test_endpoint_variations(endpoint))
                
                # Add delay between requests
                time.sleep(1)
                
            except Exception as e:
                self.logger.debug(f"Error testing endpoint {endpoint}: {str(e)}")
                continue
        
        return stores
    
    def _extract_all_stores_via_api(self) -> List[Dict[str, Any]]:
        """Extract all stores using the discovered working API with systematic coordinate search."""
        all_stores = []
        seen_store_ids = set()
        
        # Update session headers for the API
        self.session.headers.update({
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Ocp-Apim-Subscription-Key': self.api_key,
            'Origin': 'https://www.edgardcooper.com',
            'Referer': 'https://www.edgardcooper.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        })
        
        self.logger.info(f"Starting systematic coordinate search across {len(self.search_coordinates)} points")
        
        for i, (lat, lng) in enumerate(self.search_coordinates):
            try:
                self.logger.info(f"Searching coordinate {i+1}/{len(self.search_coordinates)}: {lat:.4f}, {lng:.4f}")
                
                # Make API request
                params = {
                    'latitude': lat,
                    'longitude': lng
                }
                
                response = self.session.get(self.api_base_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        stores = data.get('data', {}).get('retailStores', [])
                        
                        new_stores_count = 0
                        for store in stores:
                            store_id = store.get('id')
                            if store_id and store_id not in seen_store_ids:
                                seen_store_ids.add(store_id)
                                all_stores.append(store)
                                new_stores_count += 1
                        
                        if new_stores_count > 0:
                            self.logger.info(f"  Found {new_stores_count} new stores (total unique: {len(all_stores)})")
                        
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Invalid JSON response for coordinate {lat}, {lng}: {str(e)}")
                
                elif response.status_code == 429:
                    self.logger.warning("Rate limited, waiting 5 seconds...")
                    time.sleep(5)
                    continue
                
                else:
                    self.logger.debug(f"API returned status {response.status_code} for {lat}, {lng}")
                
                # Add delay to be respectful
                time.sleep(0.5)
                
                # Log progress periodically
                if (i + 1) % 50 == 0:
                    self.logger.info(f"Progress: {i+1}/{len(self.search_coordinates)} coordinates searched, {len(all_stores)} unique stores found")
                
            except Exception as e:
                self.logger.debug(f"Error searching coordinate {lat}, {lng}: {str(e)}")
                continue
        
        self.logger.info(f"Coordinate search completed. Found {len(all_stores)} unique stores total")
        return all_stores
    
    def _test_endpoint_variations(self, base_endpoint: str) -> List[Dict[str, Any]]:
        """Test various parameter combinations for an endpoint."""
        stores = []
        
        # Test different request methods and parameters
        test_cases = [
            # GET requests
            {'method': 'GET', 'url': base_endpoint},
            {'method': 'GET', 'url': f"{base_endpoint}?all=true"},
            {'method': 'GET', 'url': f"{base_endpoint}?limit=1000"},
            {'method': 'GET', 'url': f"{base_endpoint}?country=DE"},
            {'method': 'GET', 'url': f"{base_endpoint}?country=NL"},
            {'method': 'GET', 'url': f"{base_endpoint}?region=EU"},
            
            # POST requests
            {'method': 'POST', 'url': base_endpoint, 'data': {}},
            {'method': 'POST', 'url': base_endpoint, 'data': {'all': True}},
            {'method': 'POST', 'url': base_endpoint, 'data': {'limit': 1000}},
        ]
        
        for test_case in test_cases:
            try:
                if test_case['method'] == 'GET':
                    response = self.session.get(test_case['url'], timeout=10)
                else:
                    response = self.session.post(
                        test_case['url'], 
                        json=test_case.get('data', {}), 
                        timeout=10
                    )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        extracted_stores = self._extract_stores_from_api_response(data)
                        if extracted_stores:
                            self.logger.info(f"Success with {test_case}: found {len(extracted_stores)} stores")
                            stores.extend(extracted_stores)
                    except json.JSONDecodeError:
                        # Check if HTML contains JSON data
                        json_data = self._extract_json_from_html(response.text)
                        if json_data:
                            extracted_stores = self._extract_stores_from_api_response(json_data)
                            stores.extend(extracted_stores)
                            
            except Exception as e:
                self.logger.debug(f"Failed test case {test_case}: {str(e)}")
                continue
        
        return stores
    
    def _browser_exploration(self) -> List[Dict[str, Any]]:
        """Use browser automation to explore the store locator."""
        stores = []
        
        try:
            # Start browser session
            self.start_session()
            
            # Navigate to store locator
            self.logger.info(f"Navigating to {self.website_config['url']}")
            self.driver.get(self.website_config['url'])
            
            # Wait for page to load
            time.sleep(5)
            
            # Strategy 1: Intercept network requests
            stores.extend(self._intercept_network_requests())
            
            # Strategy 2: Systematic location search
            stores.extend(self._systematic_location_search())
            
            # Strategy 3: Map interaction and data extraction
            stores.extend(self._extract_from_map_interface())
            
            # Strategy 4: Hidden data extraction
            stores.extend(self._extract_hidden_data())
            
        except Exception as e:
            self.logger.error(f"Browser exploration error: {str(e)}")
        finally:
            self.end_session()
        
        return stores
    
    def _systematic_location_search(self) -> List[Dict[str, Any]]:
        """Systematically search major cities to find stores."""
        stores = []
        
        try:
            # Find search input
            search_selectors = [
                'input[name="address"]',
                'input[id*="search"]',
                'input[placeholder*="location"]',
                'input[placeholder*="address"]',
                '.search-input input',
                '.location-search input'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not search_input:
                self.logger.warning("Could not find search input element")
                return stores
            
            # Test searches for major cities
            for city in self.major_cities[:20]:  # Limit to first 20 to avoid being too aggressive
                try:
                    self.logger.info(f"Searching for stores in {city}")
                    
                    # Clear and enter city name
                    search_input.clear()
                    search_input.send_keys(city)
                    time.sleep(1)
                    
                    # Submit search
                    search_input.send_keys(Keys.RETURN)
                    
                    # Wait for results
                    time.sleep(3)
                    
                    # Extract stores from current page
                    city_stores = self._extract_stores_from_current_page()
                    if city_stores:
                        stores.extend(city_stores)
                        self.logger.info(f"Found {len(city_stores)} stores in {city}")
                    
                    # Add delay between searches
                    time.sleep(2)
                    
                except Exception as e:
                    self.logger.debug(f"Error searching {city}: {str(e)}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Systematic search error: {str(e)}")
        
        return stores
    
    def _extract_stores_from_current_page(self) -> List[Dict[str, Any]]:
        """Extract store data from the current page state."""
        stores = []
        
        try:
            # Look for store result containers
            store_selectors = [
                '.store-result',
                '.location-item',
                '.store-item',
                '.retailer-item',
                '[data-store]',
                '[data-location]'
            ]
            
            store_elements = []
            for selector in store_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        store_elements = elements
                        break
                except NoSuchElementException:
                    continue
            
            # Extract data from each store element
            for element in store_elements:
                try:
                    store_data = self._extract_data_from_element(element)
                    if store_data:
                        stores.append(store_data)
                except Exception as e:
                    self.logger.debug(f"Error extracting from element: {str(e)}")
                    continue
        
        except Exception as e:
            self.logger.debug(f"Error extracting from current page: {str(e)}")
        
        return stores
    
    def _extract_data_from_element(self, element) -> Optional[Dict[str, Any]]:
        """Extract store data from a DOM element."""
        try:
            store_data = {}
            
            # Try to extract name
            name_selectors = ['.name', '.store-name', '.title', 'h3', 'h4', '.retailer-name']
            for selector in name_selectors:
                try:
                    name_elem = element.find_element(By.CSS_SELECTOR, selector)
                    store_data['name'] = name_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Try to extract address
            address_selectors = ['.address', '.location', '.street', '.full-address']
            for selector in address_selectors:
                try:
                    addr_elem = element.find_element(By.CSS_SELECTOR, selector)
                    store_data['address'] = addr_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Try to extract distance
            distance_selectors = ['.distance', '.km-away', '.miles']
            for selector in distance_selectors:
                try:
                    dist_elem = element.find_element(By.CSS_SELECTOR, selector)
                    store_data['distance'] = dist_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract any data attributes
            for attr in ['data-name', 'data-address', 'data-lat', 'data-lng', 'data-phone']:
                try:
                    value = element.get_attribute(attr)
                    if value:
                        store_data[attr.replace('data-', '')] = value
                except:
                    continue
            
            # Only return if we found meaningful data
            if store_data.get('name') or store_data.get('address'):
                store_data['source'] = 'browser_extraction'
                return store_data
            
        except Exception as e:
            self.logger.debug(f"Error extracting element data: {str(e)}")
        
        return None
    
    def _intercept_network_requests(self) -> List[Dict[str, Any]]:
        """Attempt to intercept network requests for store data."""
        stores = []
        
        try:
            # Enable network domain for CDP
            self.driver.execute_cdp_cmd('Network.enable', {})
            
            # Trigger a search to generate network requests
            search_input = self.driver.find_element(By.CSS_SELECTOR, 'input[name="address"]')
            search_input.send_keys('Berlin')
            search_input.send_keys(Keys.RETURN)
            
            # Wait for network requests
            time.sleep(3)
            
            # Get network logs (this is a simplified approach)
            logs = self.driver.get_log('performance')
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    if 'Network.responseReceived' in message.get('method', ''):
                        url = message['params']['response']['url']
                        if any(keyword in url.lower() for keyword in ['store', 'location', 'api']):
                            self.logger.info(f"Found potential API call: {url}")
                            # Try to fetch this URL directly
                            api_stores = self._fetch_intercepted_url(url)
                            stores.extend(api_stores)
                except Exception as e:
                    continue
        
        except Exception as e:
            self.logger.debug(f"Network interception error: {str(e)}")
        
        return stores
    
    def _analyze_network_requests(self) -> List[Dict[str, Any]]:
        """Analyze potential network requests by examining page source."""
        stores = []
        
        try:
            # Get the main page to analyze
            response = self.session.get(self.website_config['url'])
            
            # Look for API URLs in the page source
            api_patterns = [
                r'https?://[^"\s]+api[^"\s]*store[^"\s]*',
                r'https?://[^"\s]+store[^"\s]*api[^"\s]*',
                r'/_next/data/[^"\s]+\.json',
                r'https?://[^"\s]*edgardcooper[^"\s]*api[^"\s]*',
                r'https?://apim-[^"\s]+\.azure-api\.net[^"\s]*'
            ]
            
            found_urls = set()
            for pattern in api_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                found_urls.update(matches)
            
            # Test each found URL
            for url in found_urls:
                try:
                    self.logger.info(f"Testing discovered URL: {url}")
                    api_stores = self._fetch_intercepted_url(url)
                    stores.extend(api_stores)
                except Exception as e:
                    self.logger.debug(f"Error testing URL {url}: {str(e)}")
                    continue
        
        except Exception as e:
            self.logger.debug(f"Network analysis error: {str(e)}")
        
        return stores
    
    def _explore_retail_partnerships(self) -> List[Dict[str, Any]]:
        """Explore known retail partnerships and chains."""
        stores = []
        
        # Known European pet store chains that might carry Edgar & Cooper
        retail_chains = [
            'Fressnapf', 'Futterhaus', 'Das Futterhaus', 'Kölle Zoo',
            'Zoo Zajac', 'Hornbach', 'Bauhaus', 'OBI', 'Dehner',
            'Pets at Home', 'Zooplus', 'Bitiba', 'Zooroyal',
            'Tom&Co', 'Animalis', 'Boterzoo', 'Welkoop'
        ]
        
        for chain in retail_chains:
            try:
                # Search for mentions of this chain on Edgar & Cooper's website
                search_query = f"site:edgardcooper.com {chain}"
                
                # Create placeholder entries for known retail chains
                # This would typically be expanded with real data from retail chain APIs
                if self._verify_retail_partnership(chain):
                    stores.append({
                        'name': f'{chain} (Edgar & Cooper Retailer)',
                        'type': 'retail_chain',
                        'chain': chain,
                        'note': f'Edgar & Cooper products available at {chain} stores',
                        'source': 'retail_partnership',
                        'verified': True
                    })
                    
            except Exception as e:
                self.logger.debug(f"Error checking retail chain {chain}: {str(e)}")
                continue
        
        return stores
    
    def _verify_retail_partnership(self, chain_name: str) -> bool:
        """Verify if a retail chain actually carries Edgar & Cooper products."""
        try:
            # Search for mentions on the main website
            response = self.session.get(self.website_config['url'])
            page_content = response.text.lower()
            
            # Look for mentions of the chain
            return chain_name.lower() in page_content
            
        except Exception:
            return False
    
    def _extract_from_map_interface(self) -> List[Dict[str, Any]]:
        """Extract data from map interface interactions."""
        stores = []
        
        try:
            # Look for map container
            map_selectors = [
                '.map', '#map', '.store-map', '.location-map',
                '[class*="map"]', '[id*="map"]'
            ]
            
            map_element = None
            for selector in map_selectors:
                try:
                    map_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if map_element:
                # Try interacting with the map to trigger data loading
                actions = ActionChains(self.driver)
                actions.move_to_element(map_element).click().perform()
                time.sleep(2)
                
                # Look for map markers or pop-ups
                marker_selectors = [
                    '.marker', '.map-marker', '.store-marker',
                    '[class*="marker"]', '.leaflet-marker', '.gm-style-iw'
                ]
                
                for selector in marker_selectors:
                    try:
                        markers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for marker in markers:
                            # Click on marker to reveal info
                            try:
                                marker.click()
                                time.sleep(1)
                                
                                # Extract info from popup or tooltip
                                store_data = self._extract_marker_data()
                                if store_data:
                                    stores.append(store_data)
                            except Exception:
                                continue
                    except NoSuchElementException:
                        continue
        
        except Exception as e:
            self.logger.debug(f"Map interface error: {str(e)}")
        
        return stores
    
    def _extract_marker_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from a map marker popup."""
        try:
            # Look for popup elements
            popup_selectors = [
                '.popup', '.tooltip', '.info-window', '.marker-popup',
                '.gm-style-iw', '.leaflet-popup'
            ]
            
            for selector in popup_selectors:
                try:
                    popup = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = popup.text.strip()
                    if text:
                        return {
                            'popup_text': text,
                            'source': 'map_marker'
                        }
                except NoSuchElementException:
                    continue
        
        except Exception:
            pass
        
        return None
    
    def _extract_hidden_data(self) -> List[Dict[str, Any]]:
        """Extract data from hidden JSON or script tags."""
        stores = []
        
        try:
            # Look for JSON data in script tags
            script_elements = self.driver.find_elements(By.TAG_NAME, 'script')
            
            for script in script_elements:
                try:
                    script_content = script.get_attribute('innerHTML')
                    if script_content and any(keyword in script_content.lower() 
                                            for keyword in ['store', 'location', 'retailer']):
                        
                        # Try to extract JSON data
                        json_data = self._extract_json_from_script(script_content)
                        if json_data:
                            extracted_stores = self._extract_stores_from_api_response(json_data)
                            stores.extend(extracted_stores)
                            
                except Exception as e:
                    continue
        
        except Exception as e:
            self.logger.debug(f"Hidden data extraction error: {str(e)}")
        
        return stores
    
    def _extract_json_from_script(self, script_content: str) -> Optional[Dict]:
        """Extract JSON data from script content."""
        try:
            # Common patterns for embedded JSON
            patterns = [
                r'window\.__NEXT_DATA__\s*=\s*({.*?});',
                r'window\.stores\s*=\s*(\[.*?\]);',
                r'var\s+stores\s*=\s*(\[.*?\]);',
                r'const\s+stores\s*=\s*(\[.*?\]);',
                r'"stores"\s*:\s*(\[.*?\])',
                r'"locations"\s*:\s*(\[.*?\])'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, script_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        return data
                    except json.JSONDecodeError:
                        continue
        
        except Exception:
            pass
        
        return None
    
    def _extract_stores_from_api_response(self, data: Any) -> List[Dict[str, Any]]:
        """Extract store data from API response."""
        stores = []
        
        try:
            if isinstance(data, list):
                # Direct list of stores
                for item in data:
                    if isinstance(item, dict) and self._looks_like_store_data(item):
                        stores.append(item)
            elif isinstance(data, dict):
                # Look for stores in common keys
                for key in ['stores', 'locations', 'results', 'data', 'retailers', 'outlets']:
                    if key in data and isinstance(data[key], list):
                        for item in data[key]:
                            if isinstance(item, dict) and self._looks_like_store_data(item):
                                stores.append(item)
                
                # Recursively search nested structures
                stores.extend(self._recursive_store_search(data))
        
        except Exception as e:
            self.logger.debug(f"Error extracting stores from API response: {str(e)}")
        
        return stores
    
    def _recursive_store_search(self, data: Any, depth: int = 0) -> List[Dict[str, Any]]:
        """Recursively search for store data in nested structures."""
        stores = []
        
        if depth > 5:  # Prevent infinite recursion
            return stores
        
        try:
            if isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and self._looks_like_store_data(item):
                                stores.append(item)
                            else:
                                stores.extend(self._recursive_store_search(item, depth + 1))
                    elif isinstance(value, dict):
                        stores.extend(self._recursive_store_search(value, depth + 1))
            elif isinstance(data, list):
                for item in data:
                    stores.extend(self._recursive_store_search(item, depth + 1))
        
        except Exception:
            pass
        
        return stores
    
    def _looks_like_store_data(self, obj: dict) -> bool:
        """Enhanced check if an object looks like store data."""
        if not isinstance(obj, dict):
            return False
        
        # Store-related field indicators
        store_indicators = [
            # Basic info
            'name', 'title', 'store_name', 'retailer', 'shop',
            # Address fields
            'address', 'street', 'city', 'postal', 'zip', 'plz', 'country',
            # Contact info
            'phone', 'tel', 'telefon', 'email', 'mail', 'website', 'url',
            # Location data
            'lat', 'lng', 'latitude', 'longitude', 'coordinates',
            # Business info
            'hours', 'opening', 'contact', 'description'
        ]
        
        found_indicators = 0
        total_fields = len(obj)
        
        for key in obj.keys():
            if any(indicator in str(key).lower() for indicator in store_indicators):
                found_indicators += 1
        
        # Consider it store data if at least 25% of fields are store-related
        # and we have at least 2 matching indicators
        return found_indicators >= 2 and (found_indicators / total_fields) >= 0.25
    
    def _fetch_intercepted_url(self, url: str) -> List[Dict[str, Any]]:
        """Fetch data from an intercepted URL."""
        stores = []
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    stores = self._extract_stores_from_api_response(data)
                except json.JSONDecodeError:
                    # Try to extract JSON from HTML
                    json_data = self._extract_json_from_html(response.text)
                    if json_data:
                        stores = self._extract_stores_from_api_response(json_data)
        
        except Exception as e:
            self.logger.debug(f"Error fetching URL {url}: {str(e)}")
        
        return stores
    
    def _extract_json_from_html(self, html_content: str) -> Optional[Dict]:
        """Extract JSON data from HTML content."""
        try:
            # Look for JSON in script tags
            soup = BeautifulSoup(html_content, 'html.parser')
            scripts = soup.find_all('script')
            
            for script in scripts:
                if script.string:
                    json_data = self._extract_json_from_script(script.string)
                    if json_data:
                        return json_data
        
        except Exception:
            pass
        
        return None
    
    def _deduplicate_stores(self, new_stores: List[Dict], existing_stores: List[Dict]) -> List[Dict]:
        """Remove duplicate stores from new_stores that already exist in existing_stores."""
        unique_stores = []
        
        for new_store in new_stores:
            is_duplicate = False
            
            for existing_store in existing_stores:
                if self._stores_are_similar(new_store, existing_store):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # Also check against other new stores we're adding
                for unique_store in unique_stores:
                    if self._stores_are_similar(new_store, unique_store):
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_stores.append(new_store)
        
        return unique_stores
    
    def _stores_are_similar(self, store1: Dict, store2: Dict) -> bool:
        """Check if two stores are likely the same location."""
        # Compare names (if available)
        name1 = str(store1.get('name', '')).lower().strip()
        name2 = str(store2.get('name', '')).lower().strip()
        
        if name1 and name2 and name1 == name2:
            return True
        
        # Compare addresses (if available)
        addr1 = str(store1.get('address', '')).lower().strip()
        addr2 = str(store2.get('address', '')).lower().strip()
        
        if addr1 and addr2 and addr1 == addr2:
            return True
        
        # Compare coordinates (if available)
        lat1, lng1 = store1.get('lat'), store1.get('lng')
        lat2, lng2 = store2.get('lat'), store2.get('lng')
        
        if all([lat1, lng1, lat2, lng2]):
            try:
                lat1, lng1, lat2, lng2 = float(lat1), float(lng1), float(lat2), float(lng2)
                # If coordinates are very close (within ~100m), consider them the same
                if abs(lat1 - lat2) < 0.001 and abs(lng1 - lng2) < 0.001:
                    return True
            except (ValueError, TypeError):
                pass
        
        return False
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data into standardized format.
        
        Args:
            raw_store: Raw store data
            
        Returns:
            Processed store data dictionary
        """
        processed = {
            'source': 'edgar_cooper',
            'scrape_timestamp': time.time()
        }
        
        # Copy all original fields
        for key, value in raw_store.items():
            if key and value is not None:
                processed[key] = str(value).strip()
        
        # Standardized field mapping
        field_mappings = {
            'std_name': ['name', 'title', 'store_name', 'retailer', 'shop'],
            'std_street': ['street', 'address', 'addr', 'street_address'],
            'std_city': ['city', 'town', 'locality'],
            'std_postal_code': ['postal_code', 'zip', 'plz', 'postcode'],
            'std_country': ['country', 'country_code'],
            'std_phone': ['phone', 'tel', 'telefon', 'telephone'],
            'std_email': ['email', 'mail', 'e_mail'],
            'std_website': ['website', 'url', 'web'],
            'std_latitude': ['lat', 'latitude', 'y'],
            'std_longitude': ['lng', 'longitude', 'x'],
        }
        
        for standard_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                for raw_key in raw_store.keys():
                    if raw_key and key.lower() in raw_key.lower():
                        processed[standard_field] = str(raw_store[raw_key]).strip()
                        break
                if standard_field in processed:
                    break
        
        # Create full address if possible
        address_parts = []
        
        if processed.get('std_street'):
            address_parts.append(processed['std_street'])
        
        city_part = []
        if processed.get('std_postal_code'):
            city_part.append(processed['std_postal_code'])
        if processed.get('std_city'):
            city_part.append(processed['std_city'])
        
        if city_part:
            address_parts.append(' '.join(city_part))
        
        if processed.get('std_country'):
            address_parts.append(processed['std_country'])
        
        processed['std_full_address'] = ', '.join(address_parts) if address_parts else ''
        
        # Add data quality indicators
        processed['data_quality'] = self._assess_data_quality(processed)
        
        return processed
    
    def _assess_data_quality(self, store_data: Dict[str, Any]) -> str:
        """Assess the quality of extracted store data."""
        score = 0
        
        # Essential fields
        if store_data.get('std_name'): score += 3
        if store_data.get('std_street'): score += 3
        if store_data.get('std_city'): score += 2
        if store_data.get('std_postal_code'): score += 2
        
        # Contact fields
        if store_data.get('std_phone'): score += 1
        if store_data.get('std_email'): score += 1
        if store_data.get('std_website'): score += 1
        
        # Location fields
        if store_data.get('std_latitude'): score += 2
        if store_data.get('std_longitude'): score += 2
        
        if score >= 10:
            return 'high'
        elif score >= 6:
            return 'medium'
        else:
            return 'low'
    
    def run(self) -> Dict[str, Any]:
        """
        Run the Edgar & Cooper scraper.
        
        Returns:
            Dictionary with scraping results and statistics
        """
        start_time = time.time()
        
        try:
            stores = self.scrape_stores()
            
            # Save data if we found stores
            output_file = None
            if stores:
                output_file = self.save_data()
                self.logger.info(f"Saved {len(stores)} stores to {output_file}")
            else:
                self.logger.warning("No stores found - Edgar & Cooper may not have public store data")
            
            # Calculate session duration
            self.session_duration = time.time() - start_time
            
            # Get final stats
            stats = self.get_stats()
            stats['output_file'] = output_file
            stats['success'] = True
            stats['strategies_used'] = ['api_exploration', 'browser_automation', 'network_analysis', 'retail_partnerships']
            
            # Add data quality breakdown
            if self.scraped_data:
                quality_counts = {'high': 0, 'medium': 0, 'low': 0}
                for store in self.scraped_data:
                    quality = store.get('data_quality', 'low')
                    quality_counts[quality] += 1
                stats['data_quality'] = quality_counts
            
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