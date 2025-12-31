import os
import pandas as pd
import numpy as np
import gspread
from dateutil import parser as date_parser
from oauth2client.service_account import ServiceAccountCredentials
from .utils import load_config

class PostProcessor:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.gc = self._authenticate_gspread()
    
    def _authenticate_gspread(self):
        """Authenticate with Google Sheets"""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials_path = self.config['gsheets']['credentials_path']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        return gspread.authorize(credentials)
    
    def open_google_sheet(self, spreadsheet_title, worksheet_title):
        """Open Google Sheet and worksheet"""
        try:
            spreadsheet = self.gc.open(spreadsheet_title)
            worksheet = spreadsheet.worksheet(worksheet_title)
            return worksheet
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Spreadsheet '{spreadsheet_title}' not found.")
            return None
        except gspread.exceptions.WorksheetNotFound:
            print(f"Worksheet '{worksheet_title}' not found. Creating new worksheet.")
            spreadsheet = self.gc.open(spreadsheet_title)
            worksheet = spreadsheet.add_worksheet(title=worksheet_title, rows=1, cols=1)
            return worksheet
    
    def read_sheet(self):
        """Read data from Quark City Emp Id - Grazitti Data sheet"""
        worksheet = self.open_google_sheet('Quark City Emp Id', 'Grazitti Data')
        if worksheet:
            data = worksheet.get_all_values()
            return pd.DataFrame(data[1:], columns=data[0])
        return None
    
    
    
    def read_sheet_data(self, spreadsheet_title=None, worksheet_title=None):
        """Read data from Google Sheet"""
        # if not spreadsheet_title:
        #     spreadsheet_title = self.config['gsheets']['spreadsheet_title']
        # if not worksheet_title:
        #     worksheet_title = self.config['gsheets']['employee_data_sheet']
        
        worksheet = self.open_google_sheet(spreadsheet_title, worksheet_title)
        if worksheet:
            data = worksheet.get_all_values()
            return pd.DataFrame(data[1:], columns=data[0])
        return None
    
    # def push_to_sheet(self, df, spreadsheet_title, worksheet_title, append=True):
    #     """Push DataFrame to Google Sheet"""
    #     try:
    #         worksheet = self.open_google_sheet(spreadsheet_title, worksheet_title)
    #         data = [df.columns.tolist()] + df.astype(str).values.tolist()

    #         if not append:
    #             worksheet.clear()
            
    #         if append:
    #             worksheet.append_rows(data[1:], value_input_option='USER_ENTERED')
    #         else:
    #             worksheet.append_rows(data, value_input_option='USER_ENTERED')
            
    #         print("Data inserted successfully.")
    #     except Exception as e:
    #         print(f"Error pushing data: {e}")

    def push_to_sheet(self, df, spreadsheet_title, worksheet_title, append=True):
        """Push DataFrame to Google Sheet"""
        try:
            worksheet = self.open_google_sheet(spreadsheet_title, worksheet_title)

            df_columns = df.columns.tolist()
            df_data = df.astype(str).values.tolist()

            existing_values = worksheet.get_all_values()

            # Case 1: Sheet is empty → write headers + data
            if not existing_values:
                worksheet.append_rows(
                    [df_columns] + df_data,
                    value_input_option='USER_ENTERED'
                )
                print("Sheet empty. Headers and data inserted.")
                return

            existing_headers = existing_values[0]

            # Case 2: Headers match → append only data rows
            if existing_headers == df_columns and append:
                worksheet.append_rows(
                    df_data,
                    value_input_option='USER_ENTERED'
                )
                print("Headers match. Data appended.")
                return

            # Case 3: Headers mismatch or append=False → clear and rewrite
            worksheet.clear()
            worksheet.append_rows(
                [df_columns] + df_data,
                value_input_option='USER_ENTERED'
            )
            print("Headers mismatched or overwrite requested. Sheet rewritten.")

        except Exception as e:
            print(f"Error pushing data: {e}")

    
    def fill_missing_amount_with_mode(self, df):
        """Fill missing amounts with mode values based on meal type"""
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Meal'] = df['Meal'].astype(str)
        
        # Identify rows with missing/invalid amounts
        mask = (df['Amount'].isnull()) | (df['Amount'] == '') | (df['Amount'].astype(str).str.len() > 3)
        
        # Calculate modes for different meal types
        meal_types = {
            'special packed m': df[df['Meal'].str.lower() == 'special packed m']['Amount'].mode(),
            'special veg thali': df[df['Meal'].str.lower() == 'special veg thali']['Amount'].mode(),
            'special non veg thali': df[df['Meal'].str.lower() == 'special non veg thali']['Amount'].mode()
        }
        
        # Fill missing values with respective modes
        for meal_type, mode_series in meal_types.items():
            if not mode_series.empty:
                mode_value = mode_series.iloc[0]
                df.loc[mask & (df['Meal'].str.lower() == meal_type), 'Amount'] = mode_value
        
        return df
    
    def replace_characters_in_code(self, df):
        """Replace characters in employee code"""
        df['Code'] = df.apply(
            lambda row: row['Code'].replace('o', '0').replace('s', '5')
            if pd.notna(row['Code']) and row['Code'].lower().startswith(('tglp', 'tgzm', 'gzm', 'glp'))
            else row['Code'], axis=1
        )
        return df
    
    def add_reimbursement_column(self, df):
        """Add reimbursement eligibility column"""
        eligible_meals = self.config['processing']['meal_types']
        df['Eligible for Reimbursement'] = df.apply(
            lambda row: 'Yes' if pd.notna(row['Meal']) and row['Meal'] in eligible_meals else 'No',
            axis=1
        )
        return df
    
    def add_reimbursement_amount(self, df):
        """Add reimbursement amount column"""
        reimbursement_amount = self.config['processing']['reimbursement_amount']
        df['Reimbursement Amount'] = df['Eligible for Reimbursement'].apply(
            lambda x: reimbursement_amount if isinstance(x, str) and x.lower() == 'yes' else 0
        )
        return df
    
    def fill_employee_names(self, employee_df, result_df):
        """Fill employee names from employee data"""
        try:
            if 'Emp Name' not in result_df.columns:
                result_df['Emp Name'] = ''
            
            employee_df['Name'] = employee_df['First Name'].fillna('') + ' ' + employee_df['Last Name'].fillna('')
            merged_df = pd.merge(result_df, employee_df, left_on='Code', right_on='Emp ID', how='left')
            result_df['Emp Name'] = merged_df['Name'].fillna(result_df['Emp Name'])
            
            return result_df
        except Exception as e:
            print(f"Error in fill_employee_names: {str(e)}")
            return result_df
    
    def extract_day(self, df, date_column='Date'):
        """Extract day from date column"""
        try:
            df[date_column] = df[date_column].replace("0", None)
            df[date_column] = pd.to_datetime(df[date_column], format='mixed')
            df['day'] = df[date_column].dt.day
            return df
        except Exception as e:
            print(f"Error extracting day: {e}")
            return df
    
    def extract_month_year(self, df, date_column='Date'):
        """Extract month and year from date column"""
        try:
            df[date_column] = df[date_column].replace("0", None)
            df[date_column] = pd.to_datetime(df[date_column], format='mixed')
            df[date_column] = df[date_column].dt.date
            
            # Reorder columns to match old format
            df = df[['Date', 'Code', 'Emp Name', 'Eligible for Reimbursement', 'Reimbursement Amount', 'Amount', 'Meal', 'Company', 'Image_name', 'day']]
            
            # Rename columns to match old format
            df.rename(columns={'Amount': 'Amount Paid', 'Meal': 'Meal type'}, inplace=True)
            
            df[date_column] = pd.to_datetime(df[date_column])
            df['Month Year'] = df[date_column].dt.strftime('%Y-%b')
            
            return df
        except Exception as e:
            print(f"Error in extract_month_year: {e}")
            return df
    
    def process_employee_matching(self, df, emp_data_df, current_month_year):
        """Process employee code matching with database"""
        from .ocr_engine import OCREngine
        
        ocr_engine = OCREngine(self.config)
        
        # Try the extraction - pattern: images\username\October 2025
        df["UserID"] = df['Image_name'].str.extract(r'images[/\\]([^/\\]+)[/\\]')
        merged_df = pd.merge(df, emp_data_df, on='UserID', how='left')
        
        if "Emp ID" in merged_df.columns:
            merged_df["Emp ID"].replace("nan", None, inplace=True)
        if "Meal type" in merged_df.columns:
            merged_df["Meal type"].replace("nan", None, inplace=True)    
        
        # Add comment and category columns
        merged_df["Comment"] = None
        merged_df["Category"] = None
        
        # Process each row for matching
        for index, row in merged_df.iterrows():
            # Check if we have valid meal data
            meal_type = row.get("Meal type", None) if "Meal type" in merged_df.columns else None
            
            if pd.isna(meal_type):
                merged_df.loc[index, "Comment"] = "Not a Meal"
                merged_df.loc[index, "Category"] = 2
            
            elif pd.notna(row.get('Code')) and pd.notna(row.get('Emp ID')):
                _, similarity = ocr_engine.find_similar_words(row['Code'], row['Emp ID'])
                # print(f"id1= {row['Code']}  id2 = {row['Emp ID']}  similarity = {similarity} ")
                
                if similarity > self.config['processing']['similarity_threshold']:
                    merged_df.loc[index, "Comment"] = ""
                    merged_df.loc[index, "Category"] = 1
                    
                elif similarity < self.config['processing']['similarity_threshold']:
                    merged_df.loc[index, "Comment"] = "Not Eligible (Employee code mismatched)"
                    merged_df.loc[index, "Eligible for Reimbursement"] = "No"
                    merged_df.loc[index, "Reimbursement Amount"] = 0
                    merged_df.loc[index, "Category"] = 4
                    
            elif pd.isna(row.get('Code')):
                merged_df.loc[index, 'Code'] = row['Emp ID']
                merged_df.loc[index, "Comment"] = "Employee code not found from Slip (Code replaced from Employee Data sheet)"
                merged_df.loc[index, "Category"] = 3
                
            elif pd.isna(row.get('Emp ID')):
                merged_df.loc[index, "Comment"] = "Emp ID not Found Please update Employee Data."
                
            else:
                print("error")
        
        return merged_df
    
    def remove_duplicates(self, df, subset_columns=['Date', 'UserID']):
        """Remove duplicate entries"""
        return df.drop_duplicates(subset=subset_columns, keep='last')