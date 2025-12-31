import os
import logging
import yaml
from datetime import datetime

def load_config(config_path="config/config.yaml"):
    """Load configuration from YAML file"""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def setup_logger(config=None):
    """Setup logger with configuration"""
    if config is None:
        config = load_config()
    
    logger = logging.getLogger('Lunch Reimbursement')
    logger.setLevel(getattr(logging, config['logging']['level']))
    
    # Create logs folder if it doesn't exist
    log_folder = config['paths']['logs']
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    log_file_path = os.path.join(log_folder, f"{timestamp}.log")
    
    # Create file handler
    handler = logging.FileHandler(log_file_path, mode='a')
    formatter = logging.Formatter(config['logging']['format'])
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

def ensure_directory_exists(directory_path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def list_files_recursive(root_dir, extensions=None):
    """Get all files recursively with specified extensions"""
    if extensions is None:
        extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.heic']
    
    file_paths = []
    try:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    file_paths.append(os.path.join(root, file))
    except Exception as e:
        logging.error(f"Error walking directory {root_dir}: {e}")
    
    return file_paths

def get_month_input():
    """Get month input from user with validation"""
    from datetime import datetime, timedelta
    
    while True:
        try:
            current_month_year = input("Enter month in format -> (January 2024): ")
            if not current_month_year:
                current_month_year = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
            
            month, year = current_month_year.split()
            if not year.isdigit() or len(year) != 4:
                raise ValueError("Invalid year format. Please enter a 4-digit year.")
            
            valid_months = ["January", "February", "March", "April", "May", "June", 
                          "July", "August", "September", "October", "November", "December"]
            if month.capitalize() not in valid_months:
                raise ValueError("Invalid month format. Please enter a valid month.")
            
            return current_month_year
        except ValueError as e:
            print("Invalid input format:", e)