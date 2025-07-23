"""
Mera pet store scraper using browser automation with targeted container scrolling.
URL: https://www.mera-petfood.com/de/haendlersuche/
Approach: Scroll within the .location-list container to load all stores
"""

import time
import json
import re
from typing import List, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

from utils.base_scraper import BaseScraper


class MeraScraper(BaseScraper):
    """Scraper for Mera store finder using targeted container scrolling."""
    
    def __init__(self):
        super().__init__('mera')
        
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Scrape all Mera stores using targeted container scrolling.
        
        Returns:
            List of dictionaries containing store data
        """
        self.logger.info("Starting Mera store scraping with targeted container scrolling")
        
        try:
            # Start browser session
            self.start_session()
            
            # Navigate to the store locator
            self.logger.info(f"Navigating to {self.website_config['url']}")
            self._safe_request(self.website_config['url'])
            
            # Load all stores by scrolling the location list
            stores = self._load_all_stores_targeted()
            
            for store in stores:
                processed_store = self._process_store_data(store)
                self.add_store_data(processed_store)
                
            self.logger.info(f"Total stores found: {len(stores)}")
            return stores
            
        except Exception as e:
            self.log_error(f"Error in Mera scraping: {str(e)}")
            return []
        finally:
            self.end_session()
    
    def _load_all_stores_targeted(self) -> List[Dict[str, Any]]:
        """
        Load all stores by scrolling within the .location-list container.
        
        Returns:
            List of store data
        """
        try:
            # Wait for page to load
            self.logger.info("Waiting for page to load...")
            time.sleep(8)
            
            # Find the location list container
            wait = WebDriverWait(self.driver, 30)
            location_list = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".location-list"))
            )
            self.logger.info("Found .location-list container")
            
            # Scroll within the container to load all stores
            total_stores = self._scroll_location_list(location_list)
            
            # Extract all stores from the loaded container
            stores = self._extract_stores_from_container(location_list)
            
            self.logger.info(f"Loaded {len(stores)} stores from container (expected ~{total_stores})")
            return stores
            
        except Exception as e:
            self.logger.error(f"Error loading stores with targeted approach: {str(e)}")
            return []
    
    def _scroll_location_list(self, container) -> int:
        """
        Scroll within the location list container to load all stores.
        
        Args:
            container: The .location-list element
            
        Returns:
            Estimated total number of stores loaded
        """
        try:
            self.logger.info("Starting targeted scroll within .location-list container...")
            
            scroll_attempts = 0
            max_scrolls = 200  # Increased for 2117 stores
            previous_height = 0
            no_change_count = 0
            
            while scroll_attempts < max_scrolls:
                # Scroll within the container
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight;", 
                    container
                )
                
                # Wait for content to load
                time.sleep(1.5)
                
                # Check current container height
                current_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight;", 
                    container
                )
                
                # Count current store elements
                store_elements = container.find_elements(By.CSS_SELECTOR, ".location-item, .store-item, [class*='location']")
                
                if current_height > previous_height:
                    self.logger.info(f"Scroll {scroll_attempts + 1}: {len(store_elements)} stores, height: {current_height}px")
                    previous_height = current_height
                    no_change_count = 0
                    
                    # Check if we're approaching the target
                    if len(store_elements) >= 2100:
                        self.logger.info(f"Reached target store count: {len(store_elements)}")
                        break
                else:
                    no_change_count += 1
                    
                    # If no change for several attempts, we might be done
                    if no_change_count >= 8:
                        self.logger.info(f"No height change after 8 scrolls. Final count: {len(store_elements)}")
                        break
                
                scroll_attempts += 1
            
            # Final count
            final_elements = container.find_elements(By.CSS_SELECTOR, ".location-item, .store-item, [class*='location']")
            self.logger.info(f"Scroll completed. Total elements in container: {len(final_elements)}")
            
            return len(final_elements)
            
        except Exception as e:
            self.logger.error(f"Error during container scrolling: {str(e)}")
            return 0
    
    def _extract_stores_from_container(self, container) -> List[Dict[str, Any]]:
        """Extract individual stores from the loaded container."""
        stores = []
        
        try:
            # Look for individual store elements within the container
            store_selectors = [
                ".location-item", ".store-item", ".dealer-item",
                ".location", ".dealer", ".retailer",
                "[data-location]", "[data-store]",
                "li", "div[class*='location']"
            ]
            
            for selector in store_selectors:
                try:
                    elements = container.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 50:  # Should have many stores
                        self.logger.info(f"Extracting from {len(elements)} elements with selector: {selector}")
                        
                        for i, element in enumerate(elements):
                            try:
                                store_data = self._parse_store_element_targeted(element, i)
                                if store_data and store_data.get('name'):
                                    stores.append(store_data)
                            except Exception as e:
                                self.logger.debug(f"Error parsing element {i}: {str(e)}")
                                continue
                        
                        # Use the first successful selector that gives us good data
                        if len(stores) > 100:
                            break
                
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {str(e)}")
                    continue
            
            # If no element-based extraction worked, try text-based
            if not stores:
                stores = self._extract_from_container_text(container)
            
            return stores
            
        except Exception as e:
            self.logger.error(f"Error extracting stores from container: {str(e)}")
            return []
    
    def _parse_store_element_targeted(self, element, index: int) -> Dict[str, Any]:
        """Parse a single store element with improved logic."""
        try:
            # Get text content
            text = element.text.strip()
            if not text or len(text) < 10:
                return {}
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if not lines:
                return {}
            
            store_data = {'index': index}
            
            # Filter out UI text
            skip_patterns = [
                r'route berechnen', r'zur website', r'meinen standort',
                r'^\d+\s*(km|ergebnisse)', r'laden', r'mehr anzeigen'
            ]
            
            filtered_lines = []
            for line in lines:
                is_skip = any(re.search(pattern, line.lower()) for pattern in skip_patterns)
                if not is_skip:
                    filtered_lines.append(line)
            
            if not filtered_lines:
                return {}
            
            # Parse store information
            name_line = None
            street_line = None
            city_line = None
            
            for i, line in enumerate(filtered_lines):
                # Postal code + city pattern
                if re.match(r'^\d{5}\s+\w+', line):
                    city_line = line
                    parts = line.split(' ', 1)
                    store_data['postal_code'] = parts[0]
                    store_data['city'] = parts[1] if len(parts) > 1 else ''
                    
                    # Previous line should be street address
                    if i > 0:
                        street_line = filtered_lines[i-1]
                        store_data['street'] = street_line
                    
                    # Line before street should be store name
                    if i > 1:
                        name_line = filtered_lines[i-2]
                        store_data['name'] = name_line
                    elif i > 0 and not street_line:
                        # Sometimes there's no street, just name and city
                        name_line = filtered_lines[i-1]
                        store_data['name'] = name_line
                
                # Distance pattern
                elif 'km' in line and any(c.isdigit() for c in line):
                    distance_match = re.search(r'([\d,\.]+)\s*km', line)
                    if distance_match:
                        store_data['distance_km'] = distance_match.group(1)
                
                # Phone pattern
                elif re.search(r'[\+\d\s\-\(\)]{8,}', line):
                    if any(keyword in line.lower() for keyword in ['tel', 'phone', 'fon']):
                        store_data['phone'] = re.sub(r'[^\d\s\-\+\(\)]', '', line).strip()
                
                # Email pattern
                elif '@' in line:
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
                    if email_match:
                        store_data['email'] = email_match.group(0)
            
            # If we haven't found a name yet, use the first substantial line
            if not store_data.get('name') and filtered_lines:
                for line in filtered_lines:
                    if len(line) > 5 and not re.match(r'^\d{5}\s+\w+', line) and 'km' not in line:
                        store_data['name'] = line
                        break
            
            # Only return if we have essential information
            if store_data.get('name') and (store_data.get('city') or store_data.get('postal_code')):
                return store_data
            else:
                return {}
            
        except Exception as e:
            self.logger.debug(f"Error parsing store element {index}: {str(e)}")
            return {}
    
    def _extract_from_container_text(self, container) -> List[Dict[str, Any]]:
        """Extract stores from container text using pattern matching."""
        stores = []
        
        try:
            text = container.text
            self.logger.info("Extracting stores from container text as fallback")
            
            # Enhanced patterns for German pet store chains
            patterns = [
                # Pattern: Name \n Street \n PostalCode City
                r'([A-ZÄÖÜ][^\n]{5,50})\n([^\n]{5,50})\n(\d{5}\s+[^\n]+)',
                # Pattern: Store chain patterns
                r'(Fressnapf[^\n]*)\n([^\n]*)\n(\d{5}\s+[^\n]+)',
                r'(Das Futterhaus[^\n]*)\n([^\n]*)\n(\d{5}\s+[^\n]+)',
                r'(Dehner[^\n]*)\n([^\n]*)\n(\d{5}\s+[^\n]+)',
                r'(Zoo\s+\w+[^\n]*)\n([^\n]*)\n(\d{5}\s+[^\n]+)',
                r'(\w+\s+Tier[^\n]*)\n([^\n]*)\n(\d{5}\s+[^\n]+)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.MULTILINE)
                for match in matches:
                    if len(match) >= 3:
                        name, street, city_line = match
                        
                        # Clean up the data
                        name = name.strip()
                        street = street.strip()
                        city_line = city_line.strip()
                        
                        # Skip if this looks like UI text
                        if any(skip in name.lower() for skip in ['route', 'website', 'standort', 'ergebnisse']):
                            continue
                        
                        # Parse city line
                        city_parts = city_line.split(' ', 1)
                        postal_code = city_parts[0] if city_parts else ''
                        city = city_parts[1] if len(city_parts) > 1 else ''
                        
                        # Look for distance nearby
                        distance = ''
                        distance_pattern = rf'{re.escape(city_line)}[^\n]*?([\d,\.]+)\s*km'
                        distance_match = re.search(distance_pattern, text)
                        if distance_match:
                            distance = distance_match.group(1)
                        
                        store_data = {
                            'name': name,
                            'street': street,
                            'postal_code': postal_code,
                            'city': city,
                            'distance_km': distance
                        }
                        
                        if name and postal_code:
                            stores.append(store_data)
            
            # Remove duplicates
            unique_stores = []
            seen = set()
            for store in stores:
                key = f"{store['name']}_{store['postal_code']}"
                if key not in seen:
                    seen.add(key)
                    unique_stores.append(store)
            
            self.logger.info(f"Extracted {len(unique_stores)} unique stores from text patterns")
            return unique_stores
            
        except Exception as e:
            self.logger.error(f"Error extracting from container text: {str(e)}")
            return []
    
    def _process_store_data(self, raw_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw store data into standardized format.
        
        Args:
            raw_store: Raw store data
            
        Returns:
            Processed store data dictionary
        """
        processed = {
            'source': 'mera_targeted_v3'
        }
        
        # Copy all original fields
        for key, value in raw_store.items():
            if key and value:
                processed[key] = str(value).strip()
        
        # Standard field mapping
        field_mappings = {
            'name': ['name', 'title', 'store_name'],
            'street': ['street', 'address', 'addr'],
            'city': ['city', 'town', 'ort'],
            'postal_code': ['postal_code', 'zip', 'plz'],
            'phone': ['phone', 'tel', 'telefon'],
            'email': ['email', 'mail'],
            'latitude': ['lat', 'latitude', 'y'],
            'longitude': ['lng', 'longitude', 'x'],
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
        Run the Mera scraper.
        
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
            
            self.logger.info(f"Mera scraping completed: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Mera scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            } 