"""
Automation scheduler for periodic scraping runs.
Supports daily, weekly, and monthly scheduling.
"""

import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Callable
import threading

from utils.config_manager import ConfigManager


class ScrapingScheduler:
    """Handles automated scheduling of scraping tasks."""
    
    def __init__(self, scraper_function: Callable = None):
        """
        Initialize the scheduler.
        
        Args:
            scraper_function: Function to call for scraping (usually orchestrator.run_all_scrapers)
        """
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.scraper_function = scraper_function
        self.is_running = False
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for scheduler."""
        logger = logging.getLogger("ScrapingScheduler")
        
        if not logger.handlers:
            file_handler = logging.FileHandler(self.config['logging']['file'])
            file_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _run_scrapers(self):
        """Execute the scraping function with error handling."""
        try:
            self.logger.info("Starting scheduled scraping run")
            start_time = datetime.now()
            
            if self.scraper_function:
                results = self.scraper_function()
                
                # Log summary
                total_stores = sum(r.get('stores_found', 0) for r in results if r.get('success'))
                successful = sum(1 for r in results if r.get('success'))
                failed = len(results) - successful
                
                duration = datetime.now() - start_time
                
                self.logger.info(
                    f"Scheduled scraping completed: {total_stores} stores found, "
                    f"{successful} successful, {failed} failed, "
                    f"duration: {duration}"
                )
                
            else:
                self.logger.warning("No scraper function provided")
                
        except Exception as e:
            self.logger.error(f"Error in scheduled scraping: {str(e)}")
    
    def setup_schedule(self):
        """Setup the schedule based on configuration."""
        automation_config = self.config.get('automation', {})
        
        if not automation_config.get('enabled', False):
            self.logger.info("Automation is disabled in configuration")
            return False
        
        schedule_type = automation_config.get('schedule', 'weekly')
        schedule_time = automation_config.get('time', '02:00')
        
        # Clear any existing schedules
        schedule.clear()
        
        # Setup schedule based on type
        if schedule_type == 'daily':
            schedule.every().day.at(schedule_time).do(self._run_scrapers)
            self.logger.info(f"Scheduled daily scraping at {schedule_time}")
            
        elif schedule_type == 'weekly':
            # Run every Monday at specified time
            schedule.every().monday.at(schedule_time).do(self._run_scrapers)
            self.logger.info(f"Scheduled weekly scraping on Mondays at {schedule_time}")
            
        elif schedule_type == 'monthly':
            # Run on the 1st of every month
            # Note: This is a simplified monthly schedule
            schedule.every().day.at(schedule_time).do(self._check_monthly)
            self.logger.info(f"Scheduled monthly scraping on 1st of month at {schedule_time}")
            
        else:
            self.logger.error(f"Unknown schedule type: {schedule_type}")
            return False
        
        return True
    
    def _check_monthly(self):
        """Check if it's the first day of the month for monthly scheduling."""
        if datetime.now().day == 1:
            self._run_scrapers()
    
    def start(self):
        """Start the scheduler in a background thread."""
        if not self.setup_schedule():
            self.logger.error("Failed to setup schedule")
            return False
        
        self.is_running = True
        
        def run_scheduler():
            self.logger.info("Scheduler started")
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            self.logger.info("Scheduler stopped")
        
        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        return True
    
    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        schedule.clear()
        self.logger.info("Scheduler stop requested")
    
    def get_next_run(self) -> str:
        """Get the next scheduled run time."""
        if not schedule.jobs:
            return "No jobs scheduled"
        
        next_run = schedule.next_run()
        if next_run:
            return next_run.strftime("%Y-%m-%d %H:%M:%S")
        return "Unknown"
    
    def list_jobs(self) -> list:
        """List all scheduled jobs."""
        return [str(job) for job in schedule.jobs]


def create_cron_job(config_file: str = "config.yaml") -> str:
    """
    Generate a cron job command for Unix systems.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        Cron job command string
    """
    config_manager = ConfigManager(config_file)
    config = config_manager.get_config()
    
    automation_config = config.get('automation', {})
    schedule_type = automation_config.get('schedule', 'weekly')
    schedule_time = automation_config.get('time', '02:00')
    
    # Parse time
    hour, minute = schedule_time.split(':')
    
    # Build cron expression
    if schedule_type == 'daily':
        cron_expr = f"{minute} {hour} * * *"
    elif schedule_type == 'weekly':
        cron_expr = f"{minute} {hour} * * 1"  # Monday
    elif schedule_type == 'monthly':
        cron_expr = f"{minute} {hour} 1 * *"  # 1st of month
    else:
        cron_expr = f"{minute} {hour} * * 1"  # Default to weekly
    
    # Get current working directory for the command
    import os
    current_dir = os.getcwd()
    
    cron_command = f"{cron_expr} cd {current_dir} && python main.py >> logs/cron.log 2>&1"
    
    return cron_command


if __name__ == "__main__":
    # Example usage
    def example_scraper():
        """Example scraper function for testing."""
        print("Running example scraper...")
        return [{'success': True, 'stores_found': 10}]
    
    scheduler = ScrapingScheduler(example_scraper)
    
    print("Available cron job command:")
    print(create_cron_job())
    
    print("\nTo add to crontab, run:")
    print("crontab -e")
    print("Then add the line above.") 