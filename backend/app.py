from fastapi import FastAPI, Query, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from services.hr_service import HRService
from pydantic import BaseModel
import uvicorn
import os
import time
import threading
from utils.logger import get_logger

# Initialize logger
logger = get_logger('api')
logger.info("Initializing FastAPI application")

app = FastAPI()
logger.info("FastAPI application created successfully")

# Global progress tracking
progress_store = {}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    return response

logger.info("Adding CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware added successfully")

logger.info("Initializing HR service")
hr_service = HRService()
logger.info("HR service initialized successfully")

@app.get("/")
def read_root():
    return {"message": "OCR Backend API", "status": "running", "frontend": "http://localhost:3000"}

class MonthProcess(BaseModel):
    month_year: str

@app.get("/api/dashboard/users-uploaded")
def get_users_uploaded(year: str = None, month: str = None):
    logger.info(f"Getting users uploaded count for year={year}, month={month}")
    try:
        count = hr_service.get_users_uploaded_count(year, month)
        logger.info(f"Users uploaded count retrieved: {count}")
        return {"users_uploaded": count}
    except Exception as e:
        logger.error(f"Error getting users uploaded count: {str(e)}", exc_info=True)
        raise

@app.get("/api/dashboard/metrics")
def get_metrics(year: str = None, month: str = None):
    logger.info(f"Getting dashboard metrics for year={year}, month={month}")
    try:
        result = hr_service.get_dashboard_metrics(year, month)
        logger.info(f"Dashboard metrics retrieved successfully")
        return result
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {str(e)}", exc_info=True)
        raise

@app.get("/api/dashboard/summary")
def get_summary(year: str = None, month: str = None):
    logger.info(f"Getting dashboard summary for year={year}, month={month}")
    try:
        result = hr_service.get_monthly_summary(year, month)
        logger.info("Dashboard summary retrieved successfully")
        return result
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}", exc_info=True)
        raise

@app.get("/api/dashboard/employees")
def get_employees(year: str = None, month: str = None):
    logger.info(f"Getting employee reimbursements for year={year}, month={month}")
    try:
        result = hr_service.get_employee_reimbursements(year, month)
        logger.info("Employee reimbursements retrieved successfully")
        return result
    except Exception as e:
        logger.error(f"Error getting employee reimbursements: {str(e)}", exc_info=True)
        raise

@app.get("/api/records")
def get_all_records(year: str = None, month: str = None):
    logger.info(f"Getting all records for year={year}, month={month}")
    try:
        result = hr_service.get_all_records(year, month)
        logger.info("All records retrieved successfully")
        return result
    except Exception as e:
        logger.error(f"Error getting all records: {str(e)}", exc_info=True)
        raise

@app.get("/api/download/images")
def download_images(type: str = Query(None), value: str = Query(None), year: str = None, month: str = None):
    logger.info(f"Downloading images for type={type}, value={value}, year={year}, month={month}")
    try:
        zip_path = hr_service.download_images(type, value, year, month)
        logger.info(f"Images zip created at: {zip_path}")
        return FileResponse(zip_path, media_type='application/zip', filename=f'images_{type}_{value}.zip')
    except Exception as e:
        logger.error(f"Error downloading images: {str(e)}", exc_info=True)
        raise

@app.get("/api/debug/data")
def debug_data():
    logger.info("Debug data request received")
    try:
        import os
        logger.info(f"Changing directory to: {hr_service.ocr_project_dir}")
        os.chdir(hr_service.ocr_project_dir)
        
        logger.info(f"Reading sheet data from: {hr_service.spreadsheet_title}")
        df = hr_service.processor.read_sheet_data(hr_service.spreadsheet_title, hr_service.archive_sheet)
        
        logger.info(f"Changing directory back to: {hr_service.original_dir}")
        os.chdir(hr_service.original_dir)
        
        if df is not None and not df.empty:
            logger.info(f"Debug data retrieved successfully - {len(df)} rows")
            return {
                "total_rows": len(df),
                "columns": df.columns.tolist(),
                "sample_month_year": df['Month Year'].unique().tolist() if 'Month Year' in df.columns else [],
                "first_5_rows": df.head().to_dict('records')
            }
        logger.warning("No data found in debug request")
        return {"message": "No data found"}
    except Exception as e:
        logger.error(f"Error in debug data: {str(e)}", exc_info=True)
        raise

@app.post("/api/export/csv")
def export_csv(year: str = None, month: str = None):
    logger.info(f"Exporting CSV report for year={year}, month={month}")
    try:
        csv_path = hr_service.export_csv_report(year, month)
        logger.info(f"CSV export completed, path: {csv_path}")
        
        if csv_path and os.path.exists(csv_path):
            filename = f"{year}_{month}_reimbursement_report.csv" if year and month else "reimbursement_report.csv"
            logger.info(f"Returning CSV file: {filename}")
            return FileResponse(csv_path, media_type='text/csv', filename=filename)
        
        logger.warning("No CSV data found for the specified period")
        return {"message": "No data found for the specified period"}
    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}", exc_info=True)
        raise

@app.post("/api/process/month")
def process_month(request: MonthProcess, background_tasks: BackgroundTasks):
    logger.info(f"Processing month data request: {request.month_year}")
    
    job_id = f"{request.month_year}_{int(time.time())}"
    progress_store[job_id] = {
        'progress': 0,
        'status': 'Starting...',
        'completed': False,
        'error': None
    }
    
    background_tasks.add_task(process_month_background, request.month_year, job_id)
    
    return {'job_id': job_id, 'message': 'Processing started'}

@app.get("/api/process/progress/{job_id}")
def get_progress(job_id: str):
    if job_id not in progress_store:
        return {'error': 'Job not found'}
    return progress_store[job_id]

def process_month_background(month_year: str, job_id: str):
    try:
        result = hr_service.process_month_data_with_progress(month_year, job_id, progress_store)
        progress_store[job_id].update({
            'progress': 100,
            'status': 'Completed',
            'completed': True,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error processing month {month_year}: {str(e)}", exc_info=True)
        progress_store[job_id].update({
            'progress': 0,
            'status': f'Error: {str(e)}',
            'completed': True,
            'error': str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting FastAPI server on host=0.0.0.0, port={port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
