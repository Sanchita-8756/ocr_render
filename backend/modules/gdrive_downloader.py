import os
import pandas as pd
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from .utils import load_config

class GDriveDownloader:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.drive = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive"""
        gauth = GoogleAuth() 
        print(GoogleDrive(gauth))
        return GoogleDrive(gauth)
    
    def download_folder_contents(self, folder_id, download_path):
        """Download files and subfolders from specified folder"""
        file_list = self.drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
        
        for item in file_list:
            item_path = os.path.join(download_path, item['title'])
            
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                self.download_folder_contents(item['id'], item_path)
            else:
                print(f"Downloading file: {item['title']} to {item_path}")
                item.GetContentFile(item_path)
    
    def download_employee_data(self, root_folder_name, download_folder, target_subfolder_name):
        """Download employee data from Google Drive"""
        os.makedirs(download_folder, exist_ok=True)
        employee_names = []

        # Find root folder
        root_folder_query = f"title='{root_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        root_folder_list = self.drive.ListFile({'q': root_folder_query}).GetList()
        
        if not root_folder_list:
            print(f"Root folder '{root_folder_name}' not found.")
            return employee_names
        
        root_folder = root_folder_list[0]
        
        # Get employee folders
        employee_folders_query = f"'{root_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        employee_folders = self.drive.ListFile({'q': employee_folders_query}).GetList()
        
        # Download from each employee folder
        for employee_folder in employee_folders:
            employee_name = employee_folder['title']
            
            employee_folder_query = f"'{employee_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            date_folders = self.drive.ListFile({'q': employee_folder_query}).GetList()
            
            for date_folder in date_folders:
                if date_folder['title'].lower() == target_subfolder_name.lower():
                    date_folder_path = os.path.join(download_folder, employee_name, date_folder['title'])
                    os.makedirs(date_folder_path, exist_ok=True)
                    
                    print(f"Downloading data from {employee_name}'s folder, {date_folder['title']}")
                    self.download_folder_contents(date_folder['id'], date_folder_path)
                    employee_names.append(employee_name)
                    break  # Only add once per employee
        
        print("Download completed.")
        return employee_names
    
    def count_users_with_uploads(self, root_folder_name, target_subfolder_name):
        """Count users who have uploaded files without downloading"""
        try:
            # Find root folder
            root_folder_query = f"title='{root_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            root_folder_list = self.drive.ListFile({'q': root_folder_query}).GetList()
            
            if not root_folder_list:
                return 0
            
            root_folder = root_folder_list[0]
            
            # Get employee folders
            employee_folders_query = f"'{root_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            employee_folders = self.drive.ListFile({'q': employee_folders_query}).GetList()
            
            users_with_uploads = 0
            
            # Check each employee folder for target month folder with files
            for employee_folder in employee_folders:
                employee_folder_query = f"'{employee_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                date_folders = self.drive.ListFile({'q': employee_folder_query}).GetList()
                
                for date_folder in date_folders:
                    if date_folder['title'].lower() == target_subfolder_name.lower():
                        # Check if this folder has any files
                        files_query = f"'{date_folder['id']}' in parents and trashed=false"
                        files = self.drive.ListFile({'q': files_query}).GetList()
                        
                        if files:  # If folder has any files
                            users_with_uploads += 1
                        break
            
            return users_with_uploads
            
        except Exception as e:
            print(f"Error counting users: {e}")
            return 0
        """Get DataFrame of employee names who have data"""
        downloaded_data = []
        
        # Find root folder
        root_folder_query = f"title='{root_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        root_folder_list = self.drive.ListFile({'q': root_folder_query}).GetList()
        
        if not root_folder_list:
            print(f"Root folder '{root_folder_name}' not found.")
            return pd.DataFrame()
        
        root_folder = root_folder_list[0]
        
        # Get employee folders
        employee_folders_query = f"'{root_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        employee_folders = self.drive.ListFile({'q': employee_folders_query}).GetList()
        
        for employee_folder in employee_folders:
            employee_name = employee_folder['title']
            downloaded_data.append(employee_name)
        
        return pd.DataFrame({'Employee Name': downloaded_data})