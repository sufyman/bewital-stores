"""
Configuration manager for loading and managing scraper settings.
"""

import os
import yaml
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigManager:
    """Manages configuration loading from YAML and environment variables."""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Path to the YAML configuration file
        """
        self.config_file = config_file
        self.config = None
        load_dotenv()  # Load environment variables
        
    def get_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration.
        
        Returns:
            Dictionary containing all configuration settings
        """
        if self.config is None:
            self.config = self._load_config()
            self._apply_env_overrides()
        
        return self.config
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {self.config_file} not found")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {str(e)}")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Browser settings
        if os.getenv('BROWSER_HEADLESS'):
            self.config['browser']['headless'] = os.getenv('BROWSER_HEADLESS').lower() == 'true'
        
        if os.getenv('BROWSER_TIMEOUT'):
            self.config['browser']['timeout'] = int(os.getenv('BROWSER_TIMEOUT'))
        
        # Logging level
        if os.getenv('LOG_LEVEL'):
            self.config['logging']['level'] = os.getenv('LOG_LEVEL')
        
        # Output directory
        if os.getenv('OUTPUT_DIR'):
            self.config['output']['directory'] = os.getenv('OUTPUT_DIR')
    
    def get_website_config(self, website_key: str) -> Dict[str, Any]:
        """
        Get configuration for a specific website.
        
        Args:
            website_key: Key identifying the website
            
        Returns:
            Dictionary containing website-specific configuration
        """
        config = self.get_config()
        if website_key not in config['websites']:
            raise ValueError(f"Website '{website_key}' not found in configuration")
        
        return config['websites'][website_key]
    
    def get_search_locations(self) -> Dict[str, Any]:
        """Get the configured search locations for Germany."""
        return self.get_config()['search_locations']
    
    def is_website_enabled(self, website_key: str) -> bool:
        """
        Check if a website scraper is enabled.
        
        Args:
            website_key: Key identifying the website
            
        Returns:
            Boolean indicating if the website is enabled
        """
        website_config = self.get_website_config(website_key)
        return website_config.get('enabled', False)
    
    def get_enabled_websites(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled websites from configuration."""
        config = self.get_config()
        enabled_websites = {}
        
        for key, website_config in config['websites'].items():
            if website_config.get('enabled', False):
                enabled_websites[key] = website_config
        
        return enabled_websites 