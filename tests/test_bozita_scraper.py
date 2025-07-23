"""
Unit tests for Bozita scraper.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from scrapers.bozita_scraper import BozitaScraper


class TestBozitaScraper(unittest.TestCase):
    """Test cases for BozitaScraper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the config to avoid loading actual config file
        self.mock_config = {
            'websites': {
                'bozita': {
                    'name': 'Bozita',
                    'url': 'https://bozita.com/de/fachhandler-suchen/',
                    'enabled': True
                }
            },
            'browser': {
                'headless': True,
                'timeout': 30,
                'implicit_wait': 10,
                'page_load_timeout': 30
            },
            'scraping': {
                'delay_between_requests': 1,
                'retry_attempts': 3
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/test_scraper.log'
            },
            'output': {
                'directory': 'test_output'
            },
            'search_locations': {
                'major_cities': ['Berlin', 'München']
            }
        }
    
    @patch('scrapers.bozita_scraper.ConfigManager')
    def test_scraper_initialization(self, mock_config_manager):
        """Test scraper initialization."""
        mock_config_manager.return_value.get_config.return_value = self.mock_config
        mock_config_manager.return_value.get_search_locations.return_value = self.mock_config['search_locations']
        
        scraper = BozitaScraper()
        
        self.assertEqual(scraper.website_key, 'bozita')
        self.assertEqual(scraper.website_config['name'], 'Bozita')
    
    @patch('scrapers.bozita_scraper.ConfigManager')
    def test_extract_single_store(self, mock_config_manager):
        """Test single store data extraction."""
        mock_config_manager.return_value.get_config.return_value = self.mock_config
        mock_config_manager.return_value.get_search_locations.return_value = self.mock_config['search_locations']
        
        scraper = BozitaScraper()
        
        # Mock WebElement
        mock_element = MagicMock()
        mock_name_element = MagicMock()
        mock_name_element.text = "Test Pet Store"
        mock_address_element = MagicMock()
        mock_address_element.text = "Test Street 123"
        
        # Mock the safe_find_element method to return our mock elements
        def mock_safe_find_element(by, selector, parent=None):
            if 'name' in selector or selector in ['h3', 'h4', 'h2']:
                return mock_name_element
            elif 'address' in selector:
                return mock_address_element
            return None
        
        scraper.safe_find_element = Mock(side_effect=mock_safe_find_element)
        scraper.extract_text = Mock(side_effect=lambda elem: elem.text if elem else "")
        
        result = scraper._extract_single_store(mock_element, "Berlin")
        
        self.assertEqual(result['name'], "Test Pet Store")
        self.assertEqual(result['address'], "Test Street 123")
        self.assertEqual(result['search_city'], "Berlin")
    
    @patch('scrapers.bozita_scraper.ConfigManager')
    def test_data_validation(self, mock_config_manager):
        """Test data validation and cleaning."""
        mock_config_manager.return_value.get_config.return_value = self.mock_config
        mock_config_manager.return_value.get_search_locations.return_value = self.mock_config['search_locations']
        
        scraper = BozitaScraper()
        
        # Test store data with all fields
        test_store = {
            'name': 'Test Store',
            'address': 'Main St 123',
            'phone': '+49 123 456789',
            'email': 'test@store.com',
            'website': 'https://teststore.com',
            'search_city': 'Berlin'
        }
        
        scraper.add_store_data(test_store)
        
        # Check that metadata was added
        stored_data = scraper.scraped_data[0]
        self.assertIn('scraped_at', stored_data)
        self.assertIn('source_website', stored_data)
        self.assertEqual(stored_data['source_website'], 'Bozita')


class TestScraperIntegration(unittest.TestCase):
    """Integration tests for scraper functionality."""
    
    @patch('scrapers.bozita_scraper.ConfigManager')
    @patch('scrapers.bozita_scraper.webdriver.Chrome')
    def test_scraper_run_flow(self, mock_webdriver, mock_config_manager):
        """Test the complete scraper run flow."""
        # Mock configuration
        mock_config = {
            'websites': {
                'bozita': {
                    'name': 'Bozita',
                    'url': 'https://bozita.com/de/fachhandler-suchen/',
                    'enabled': True
                }
            },
            'browser': {'headless': True, 'timeout': 30, 'implicit_wait': 10, 'page_load_timeout': 30},
            'scraping': {'delay_between_requests': 1},
            'logging': {'level': 'INFO', 'file': 'logs/test.log'},
            'output': {'directory': tempfile.mkdtemp()},
            'search_locations': {'major_cities': ['Berlin']}
        }
        
        mock_config_manager.return_value.get_config.return_value = mock_config
        mock_config_manager.return_value.get_search_locations.return_value = mock_config['search_locations']
        
        # Mock WebDriver
        mock_driver = MagicMock()
        mock_webdriver.return_value = mock_driver
        
        # Create scraper and mock its methods
        scraper = BozitaScraper()
        scraper.scrape_stores = Mock(return_value=[])
        
        # Run the scraper
        result = scraper.run()
        
        # Verify results
        self.assertIn('success', result)
        self.assertIn('website', result)
        self.assertEqual(result['website'], 'Bozita')


if __name__ == '__main__':
    unittest.main() 