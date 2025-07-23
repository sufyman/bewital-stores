"""
Royal Canin pet store scraper for German stores.
URL: https://www.royalcanin.com/de/store-locator
Approach: Uses discovered working API with systematic coordinate search across Germany
"""

import requests
import time
import json
from typing import List, Dict, Any, Optional
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from utils.base_scraper import BaseScraper


class RoyalCaninScraper(BaseScraper):
    """
    Comprehensive scraper for Royal Canin store finder using discovered API.
    """
    
    def __init__(self):
        super().__init__('royal_canin')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'DNT': '1',
            'Referer': 'https://www.royalcanin.com/',
            'Origin': 'https://www.royalcanin.com'
        })
        
        # Working API endpoint discovered
        self.api_base_url = "https://prd-eus2-rcapi-apim.azure-api.net/internal/location/location/getNearbyLocations"
        self.api_key = "7c1a02858da34b96b92203ee23163ffb"
        
        # Coordinate grid for systematic German coverage
        self.search_coordinates = self._generate_german_grid()
        
    def _generate_german_grid(self) -> List[tuple]:
        """Generate a systematic grid of coordinates covering Germany."""
        coordinates = []
        
        # German boundaries (approximate)
        # North: 55.1° (Danish border), South: 47.3° (Austrian border) 
        # West: 5.9° (Dutch/Belgian border), East: 15.0° (Polish border)
        
        # Grid resolution for optimal coverage with API radius limits
        lat_step = 1.0  # About 111km - good for 100km radius searches
        lng_step = 1.4  # About 100km at 50° latitude
        
        # Generate grid points covering Germany
        lat = 47.0  # Start from south
        while lat <= 55.5:  # A bit north of Germany
            lng = 5.5  # Start from west
            while lng <= 15.5:  # A bit east of Germany
                coordinates.append((lat, lng))
                lng += lng_step
            lat += lat_step
        
        # Add major German city coordinates for comprehensive coverage
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
        Main scraping method using the discovered Royal Canin API.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Royal Canin store scraping using discovered API")
        all_stores = []
        
        try:
            # Use discovered working API with coordinate grid search
            self.logger.info("Using discovered working API with systematic coordinate search")
            api_stores = self._extract_all_stores_via_api()
            if api_stores:
                all_stores.extend(api_stores)
                self.logger.info(f"Found {len(api_stores)} stores via working API")
            
            # Process all found stores
            for store in all_stores:
                processed_store = self._process_store_data(store)
                self.add_store_data(processed_store)
                
            self.logger.info(f"Total unique stores found: {len(all_stores)}")
            return all_stores
            
        except Exception as e:
            self.log_error(f"Error in Royal Canin scraping: {str(e)}")
            return []
    
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
            'ocp-apim-subscription-key': self.api_key,
            'Origin': 'https://www.royalcanin.com',
            'Referer': 'https://www.royalcanin.com/',
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
                
                # Make API request with optimal parameters
                params = {
                    'lat': lat,
                    'long': lng,
                    'radius': 150,  # 150km radius for good coverage
                    'page': 0,
                    'limit': 500,  # Maximum limit observed
                    'locationType': 'pos'
                }
                
                response = self.session.get(self.api_base_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    try:
                        stores = response.json()
                        
                        if isinstance(stores, list):
                            new_stores_count = 0
                            for store in stores:
                                store_id = store.get('_id') or store.get('externalId')
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
                if (i + 1) % 20 == 0:
                    self.logger.info(f"Progress: {i+1}/{len(self.search_coordinates)} coordinates searched, {len(all_stores)} unique stores found")
                
            except Exception as e:
                self.logger.debug(f"Error searching coordinate {lat}, {lng}: {str(e)}")
                continue
        
        self.logger.info(f"Coordinate search completed. Found {len(all_stores)} unique stores total")
        return all_stores
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data into standardized format.
        
        Args:
            raw_store: Raw store data from API
            
        Returns:
            Processed store data dictionary
        """
        processed = {
            'source': 'royal_canin',
            'scrape_timestamp': time.time()
        }
        
        # Copy all original fields with consistent handling
        for key, value in raw_store.items():
            if key and value is not None:
                if key == 'location' and isinstance(value, dict):
                    # Handle GeoJSON location format
                    coordinates = value.get('coordinates', [])
                    if len(coordinates) >= 2:
                        processed['longitude'] = coordinates[0]
                        processed['latitude'] = coordinates[1]
                elif isinstance(value, (list, dict)):
                    # Convert complex objects to strings for CSV compatibility
                    processed[key] = json.dumps(value)
                else:
                    processed[key] = str(value).strip() if isinstance(value, str) else value
        
        # Standardized field mapping for Royal Canin data structure
        field_mappings = {
            'std_name': ['name'],
            'std_street': ['addressLine1'],
            'std_street2': ['addressLine2'],
            'std_city': ['city'],
            'std_postal_code': ['postalCode'],
            'std_country': ['country'],
            'std_phone': ['phoneNumber'],
            'std_email': ['email'],
            'std_latitude': ['latitude'],
            'std_longitude': ['longitude'],
        }
        
        for standard_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                if raw_store.get(key):
                    processed[standard_field] = str(raw_store[key]).strip()
                    break
        
        # Create full address
        address_parts = []
        
        if processed.get('std_street'):
            address_parts.append(processed['std_street'])
        
        if processed.get('std_street2'):
            address_parts.append(processed['std_street2'])
        
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
        
        # Add additional Royal Canin specific fields
        processed['royal_canin_id'] = raw_store.get('_id', '')
        processed['external_id'] = raw_store.get('externalId', '')
        processed['active'] = raw_store.get('active', True)
        processed['source_type'] = raw_store.get('sourceType', '')
        processed['location_type'] = raw_store.get('locationType', '')
        processed['species'] = json.dumps(raw_store.get('species', []))
        
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
        if store_data.get('std_phone'): score += 2
        if store_data.get('std_email'): score += 1
        
        # Location fields
        if store_data.get('std_latitude'): score += 2
        if store_data.get('std_longitude'): score += 2
        
        # Royal Canin specific
        if store_data.get('royal_canin_id'): score += 1
        
        if score >= 12:
            return 'high'
        elif score >= 8:
            return 'medium'
        else:
            return 'low'
    
    def run(self) -> Dict[str, Any]:
        """
        Run the Royal Canin scraper.
        
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
                self.logger.warning("No stores found")
            
            # Calculate session duration
            self.session_duration = time.time() - start_time
            
            # Get final stats
            stats = self.get_stats()
            stats['output_file'] = output_file
            stats['success'] = True
            stats['strategies_used'] = ['api_coordinate_search']
            
            # Add data quality breakdown
            if self.scraped_data:
                quality_counts = {'high': 0, 'medium': 0, 'low': 0}
                for store in self.scraped_data:
                    quality = store.get('data_quality', 'low')
                    quality_counts[quality] += 1
                stats['data_quality'] = quality_counts
            
            self.logger.info(f"Royal Canin scraping completed: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Royal Canin scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 