import sys
import os
import pandas as pd
import zipfile
import tempfile

from modules.post_processing import PostProcessor
from modules.utils import load_config
from modules.gdrive_downloader import GDriveDownloader
from modules.ocr_engine import OCREngine
from modules.utils import list_files_recursive

class HRService:
    def __init__(self):
        self.backend_dir = os.path.dirname(__file__)
        self.original_dir = os.getcwd()
        
        config_path = os.path.join(self.backend_dir, '../config/config.yaml')
        self.config = load_config(config_path)
        self.processor = PostProcessor(self.config)
        self.spreadsheet_title = self.config['gsheets']['spreadsheet_title']
        self.archive_sheet = self.config['gsheets']['archive_sheet']
    
    def _get_filtered_data(self, year=None, month=None):
        df = self.processor.read_sheet_data(self.spreadsheet_title, self.archive_sheet)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        if 'Image_name' in df.columns:
            df['Image_name'] = df['Image_name'].apply(
                lambda x: x.replace('\\output\\output\\', '\\output\\') if pd.notna(x) and '\\output\\output\\' in str(x) else x
            )
        
        if 'Month Year' in df.columns and (year or month):
            if year and month:
                # Match both short and full month names: 2025-Oct or 2025-October
                pattern = f"{year}-{month}"
                df = df[df['Month Year'].astype(str).str.contains(pattern, case=False, na=False)]
            elif year:
                df = df[df['Month Year'].astype(str).str.contains(year, case=False, na=False)]
        
        return df
    
    def _get_users_from_drive(self, year=None, month=None):
        """Check Google Drive folders to count users who have uploaded receipts"""
        try:
            if not year or not month:
                return 0
            
            # Get month name mapping
            month_names = {
                'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April',
                'May': 'May', 'Jun': 'June', 'Jul': 'July', 'Aug': 'August', 
                'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'
            }
            month_year = f"{month_names.get(month, month)} {year}"
            
            downloader = GDriveDownloader(self.config)
            
            # Count users without downloading
            users_count = downloader.count_users_with_uploads(
                self.config['gdrive']['root_folder_name'],
                month_year
            )
            
            return users_count
            
        except Exception as e:
            return 0
    def get_users_uploaded_count(self, year=None, month=None):
        """Get count of users who uploaded receipts to Drive"""
        return self._get_users_from_drive(year, month)
    def get_dashboard_metrics(self, year=None, month=None):
        df = self._get_filtered_data(year, month)
        
        if df.empty:
            return {
                'total_receipts': 0,
                'total_approvals': 0,
                'pending_approvals': 0,
                'rejected_receipts': 0
            }
        
        total_receipts = len(df)
        approved = len(df[df['Eligible for Reimbursement'] == 'Yes'])
        rejected = len(df[df['Eligible for Reimbursement'] == 'No'])
        pending = len(df[df['Category'].astype(str) == '3'])
        
        return {
            'total_receipts': total_receipts,
            'total_approvals': approved,
            'pending_approvals': pending,
            'rejected_receipts': rejected
        }
    
    def get_monthly_summary(self, year=None, month=None):
        df = self._get_filtered_data(year, month)
        
        if df.empty:
            return []
        
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df['Reimbursement Amount'] = pd.to_numeric(df['Reimbursement Amount'], errors='coerce').fillna(0)
        
        summary = df.groupby('Date').agg({
            'Reimbursement Amount': 'sum',
            'UserID': 'count'
        }).reset_index()
        
        summary.columns = ['date', 'total_amount', 'receipt_count']
        summary['date'] = summary['date'].dt.strftime('%Y-%m-%d')
        
        return summary.to_dict('records')
    
    def get_employee_reimbursements(self, year=None, month=None):
        df = self._get_filtered_data(year, month)
        
        if df.empty:
            return {'total_employees': 0, 'employees': []}
        
        df['Reimbursement Amount'] = pd.to_numeric(df['Reimbursement Amount'], errors='coerce').fillna(0)
        
        employee_summary = df.groupby(['Emp ID', 'Emp Name']).agg({
            'Reimbursement Amount': 'sum'
        }).reset_index()
        
        employee_summary.columns = ['emp_id', 'name', 'total_reimbursement']
        
        return {
            'total_employees': len(employee_summary),
            'employees': employee_summary.to_dict('records')
        }
    
    def get_all_records(self, year=None, month=None):
        df = self._get_filtered_data(year, month)
        
        if df.empty:
            return []
        
        return df.to_dict('records')
    
    def download_images(self, filter_type, filter_value, year=None, month=None):
        from utils.logger import get_logger
        logger = get_logger('hr_service')
        
        df = self._get_filtered_data(year, month)
        
        if df.empty:
            logger.warning("No data found for download")
            return None
        
        if filter_type == 'employee':
            df = df[df['Emp ID'] == filter_value]
            logger.info(f"Filtered to employee {filter_value}, found {len(df)} records")
        
        image_paths = df['Image_name'].tolist()
        logger.info(f"Image paths to download: {image_paths}")
        
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        files_added = 0
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for img_path in image_paths:
                if pd.notna(img_path) and os.path.exists(img_path):
                    zip_file.write(img_path, os.path.basename(img_path))
                    files_added += 1
                    logger.info(f"Added to zip: {img_path}")
                else:
                    logger.warning(f"Image not found: {img_path}")
        
        logger.info(f"Created zip with {files_added} files at: {temp_zip.name}")
        return temp_zip.name
    
    def export_csv_report(self, year=None, month=None):
        df = self._get_filtered_data(year, month)
        
        if df.empty:
            return None
        
        # Create CSV filename similar to archive format
        filename = f"{year}_{month}_reimbursement_report.csv" if year and month else "reimbursement_report.csv"
        csv_path = os.path.join(self.backend_dir, '../output', 'csv', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # Save with same columns as archive
        df.to_csv(csv_path, index=False)
        
        return csv_path

    def process_month_data_with_progress(self, month_year, job_id, progress_store):
        try:
            def update_progress(progress, status):
                progress_store[job_id].update({
                    'progress': progress,
                    'status': status
                })
            
            update_progress(5, 'Initializing components...')
            
            # Initialize components
            downloader = GDriveDownloader(self.config)
            ocr_engine = OCREngine(self.config)
            
            # Setup paths
            download_folder = self.config['paths']['download_base']
            csv_output_path = os.path.join(self.config['paths']['output_csv'], f"{month_year}.csv")
            
            update_progress(15, 'Downloading from Google Drive...')
            
            # Step 1: Download from Google Drive (auth disabled)
            employee_names = downloader.download_employee_data(
                self.config['gdrive']['root_folder_name'],
                download_folder,
                month_year
            )
            
            update_progress(25, 'Scanning employee folders...')
            
            # Step 2: Get image files from specific employee month folders
            image_files = []
            for employee_name in employee_names:
                employee_month_folder = os.path.join(download_folder, employee_name, month_year)
                if os.path.exists(employee_month_folder):
                    employee_files = list_files_recursive(employee_month_folder, self.config['ocr']['supported_formats'])
                    image_files.extend(employee_files)
            
            if not image_files:
                return {"message": "No images found for processing", "processed_count": 0}
            
            # Step 3: Process with OCR with progress updates
            if os.path.exists(csv_output_path):
                os.remove(csv_output_path)
            
            def create_batches(items, batch_size):
                for i in range(0, len(items), batch_size):
                    yield items[i:i + batch_size]

            from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
            from threading import Lock
            import gc
            import threading
            
            processed_count = 0
            BATCH_SIZE = 20 
            csv_lock = Lock()

            def process_single_image(image_path):
                try:
                    result = ocr_engine.process_image(image_path)
                    if result:
                        with csv_lock:
                            ocr_engine.save_to_csv(result, csv_output_path)
                        return image_path
                    return None
                except Exception as e:
                    return None
            
            batches = list(create_batches(image_files, BATCH_SIZE))
            total_batches = len(batches)
            
            for batch_idx, batch in enumerate(batches, start=1):
                progress = 35 + (batch_idx - 1) * 10  # 35% to 85%
                update_progress(progress, f'Processing OCR batch {batch_idx}/{total_batches}...')

                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {
                       executor.submit(process_single_image, image): image
                        for image in batch
                    }

                    for future in as_completed(futures):
                        try:
                            result = future.result(timeout=30)
                            if result:
                                processed_count += 1
                        except:
                            pass

                    gc.collect()
            
            update_progress(90, 'Post-processing data...')
            
            # Step 4: Post-processing
            df = pd.read_csv(csv_output_path)
            employee_df = self.processor.read_sheet()
            
            df = self.processor.fill_missing_amount_with_mode(df)
            df = self.processor.replace_characters_in_code(df)
            df = self.processor.add_reimbursement_column(df)
            df = self.processor.add_reimbursement_amount(df)
            print(">>>>>>>>>>>>>>>>>>>>>>>1",employee_df)
            print(">>>>>>>>>>>>>>>>>>>>>>>2",df)
            df = self.processor.fill_employee_names(employee_df, df)
            print(">>>>>>>>>>>>>>>>>>>>>>>3",df)
            df = self.processor.extract_day(df)
            df = self.processor.extract_month_year(df)
            
            update_progress(95, 'Matching employee data...')
            
            # Step 5: Employee matching
            emp_data_df = self.processor.read_sheet_data(
                self.spreadsheet_title, 'Employee Data'
            )
            final_df = self.processor.process_employee_matching(df, emp_data_df, month_year)
            
            update_progress(98, 'Pushing to archive sheet...')
            
            # Step 6: Push to archive
            self.processor.push_to_sheet(final_df, self.spreadsheet_title, self.archive_sheet, append=True)
            
            # Remove duplicates
            archive_data = self.processor.read_sheet_data(self.spreadsheet_title, self.archive_sheet)
            if archive_data is not None:
                archive_no_dup = self.processor.remove_duplicates(archive_data, ['Date', 'UserID'])
                self.processor.push_to_sheet(archive_no_dup, self.spreadsheet_title, self.archive_sheet, append=False)
            
            return {
                "message": "Processing completed successfully",
                "processed_count": processed_count,
                "month_year": month_year
            }
            
        except Exception as e:
            return {"message": f"Error during processing: {str(e)}", "processed_count": 0}
