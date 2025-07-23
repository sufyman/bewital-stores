"""
Base scraper class providing common functionality for all pet store scrapers.
"""

import logging
import time
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

# import pandas as pd  # Temporarily commented for testing
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.config_manager import ConfigManager


class BaseScraper(ABC):
    """
    Abstract base class for all pet store scrapers.
    Provides common functionality like browser setup, data handling, and logging.
    """
    
    def __init__(self, website_key: str, config: Dict[str, Any] = None):
        """
        Initialize the base scraper.
        
        Args:
            website_key: Key identifying the website in config
            config: Optional config override
        """
        self.website_key = website_key
        self.config_manager = ConfigManager()
        self.config = config or self.config_manager.get_config()
        self.website_config = self.config['websites'][website_key]
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize browser
        self.driver = None
        self.wait = None
        
        # Data storage
        self.scraped_data = []
        self.errors = []
        
        # User agent for requests
        self.ua = UserAgent()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger(f"{self.__class__.__name__}")
        
        if not logger.handlers:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler(self.config['logging']['file'])
            file_handler.setLevel(getattr(logging, self.config['logging']['level']))
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.setLevel(getattr(logging, self.config['logging']['level']))
        
        return logger
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with optimal configuration."""
        try:
            chrome_options = Options()
            
            if self.config['browser']['headless']:
                chrome_options.add_argument('--headless')
            
            # Performance and stability options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={self.ua.random}')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize driver with correct syntax for newer Selenium
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configure timeouts
            driver.implicitly_wait(self.config['browser']['implicit_wait'])
            driver.set_page_load_timeout(self.config['browser']['page_load_timeout'])
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(driver, self.config['browser']['timeout'])
            
            self.logger.info(f"Chrome WebDriver initialized for {self.website_config['name']}")
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _safe_request(self, url: str) -> bool:
        """
        Safely navigate to URL with retries.
        
        Args:
            url: URL to navigate to
            
        Returns:
            bool: Success status
        """
        try:
            self.driver.get(url)
            time.sleep(self.config['scraping']['delay_between_requests'])
            return True
        except Exception as e:
            self.logger.warning(f"Request failed for {url}: {str(e)}")
            raise
    
    def start_session(self):
        """Start a new scraping session."""
        self.logger.info(f"Starting scraping session for {self.website_config['name']}")
        self.driver = self._setup_driver()
        self.scraped_data = []
        self.errors = []
    
    def end_session(self):
        """End the current scraping session."""
        if self.driver:
            self.driver.quit()
            self.logger.info(f"Ended scraping session for {self.website_config['name']}")
    
    def save_data(self, filename: str = None) -> str:
        """
        Save scraped data to CSV file.
        
        Args:
            filename: Optional custom filename
            
        Returns:
            str: Path to saved file
        """
        if not self.scraped_data:
            self.logger.warning("No data to save")
            return None
        
        # Create output directory if it doesn't exist
        output_dir = self.config['output']['directory']
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.website_key}_{timestamp}.csv"
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            # Simple CSV writing without pandas for now
            import csv
            
            if self.scraped_data:
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    # Collect all unique fieldnames from all records
                    all_fieldnames = set()
                    for record in self.scraped_data:
                        all_fieldnames.update(record.keys())
                    
                    fieldnames = sorted(list(all_fieldnames))  # Sort for consistent column order
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.scraped_data)
            
            self.logger.info(f"Saved {len(self.scraped_data)} records to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save data: {str(e)}")
            raise
    
    def add_store_data(self, store_data: Dict[str, Any]):
        """
        Add store data to the collection.
        
        Args:
            store_data: Dictionary containing store information
        """
        # Add metadata
        store_data['scraped_at'] = datetime.now().isoformat()
        store_data['source_website'] = self.website_config['name']
        store_data['source_url'] = self.website_config['url']
        
        self.scraped_data.append(store_data)
    
    def log_error(self, error_msg: str, store_data: Dict[str, Any] = None):
        """
        Log an error that occurred during scraping.
        
        Args:
            error_msg: Error message
            store_data: Optional store data that caused the error
        """
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'website': self.website_config['name'],
            'error': error_msg,
            'store_data': store_data
        }
        self.errors.append(error_record)
        self.logger.error(f"{self.website_config['name']}: {error_msg}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping session statistics."""
        return {
            'website': self.website_config['name'],
            'stores_found': len(self.scraped_data),
            'errors_count': len(self.errors),
            'session_duration': getattr(self, 'session_duration', 0)
        }
    
    @abstractmethod
    def scrape_stores(self) -> List[Dict[str, Any]]:
        """
        Abstract method to scrape stores from the website.
        Must be implemented by each specific scraper.
        
        Returns:
            List of dictionaries containing store data
        """
        pass
    
    def run(self) -> Dict[str, Any]:
        """
        Main method to run the complete scraping process.
        
        Returns:
            Dictionary with scraping results and statistics
        """
        start_time = time.time()
        
        try:
            self.start_session()
            stores = self.scrape_stores()
            
            # Save data
            output_file = self.save_data()
            
            # Calculate session duration
            self.session_duration = time.time() - start_time
            
            # Get final stats
            stats = self.get_stats()
            stats['output_file'] = output_file
            stats['success'] = True
            
            self.logger.info(f"Scraping completed successfully: {stats}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {str(e)}")
            return {
                'website': self.website_config['name'],
                'success': False,
                'error': str(e),
                'stores_found': len(self.scraped_data),
                'errors_count': len(self.errors)
            }
        
        finally:
            self.end_session()
    
    # Helper methods for common scraping tasks
    
    def wait_for_element(self, by: By, value: str, timeout: int = None) -> bool:
        """Wait for an element to be present."""
        try:
            timeout = timeout or self.config['browser']['timeout']
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.presence_of_element_located((by, value)))
            return True
        except TimeoutException:
            return False
    
    def wait_for_clickable(self, by: By, value: str, timeout: int = None) -> bool:
        """Wait for an element to be clickable."""
        try:
            timeout = timeout or self.config['browser']['timeout']
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.element_to_be_clickable((by, value)))
            return True
        except TimeoutException:
            return False
    
    def safe_find_element(self, by: By, value: str, parent_element=None):
        """Safely find an element without throwing exception."""
        try:
            search_context = parent_element or self.driver
            return search_context.find_element(by, value)
        except NoSuchElementException:
            return None
    
    def safe_find_elements(self, by: By, value: str, parent_element=None):
        """Safely find elements without throwing exception."""
        try:
            search_context = parent_element or self.driver
            return search_context.find_elements(by, value)
        except NoSuchElementException:
            return []
    
    def extract_text(self, element, default: str = "") -> str:
        """Safely extract text from an element."""
        try:
            return element.text.strip() if element else default
        except Exception:
            return default
    
    def extract_attribute(self, element, attribute: str, default: str = "") -> str:
        """Safely extract attribute from an element."""
        try:
            return element.get_attribute(attribute) if element else default
        except Exception:
            return default 