# HR Reimbursement Dashboard

A full-stack application for managing HR reimbursements with OCR processing capabilities.

## Architecture
- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Deployment**: Render

## Render Deployment

### Automatic Deployment Setup:

1. **Push to Git**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Deploy Backend**:
   - Create new Web Service on Render
   - Connect your Git repository
   - Set Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `chmod +x start.sh && ./start.sh`
   - Add environment variables as needed

3. **Deploy Frontend**:
   - Create new Static Site on Render
   - Connect your Git repository
   - Set Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `build`

### Environment Variables:
Set these in your Render dashboard:
- Backend: Add any required environment variables
- Frontend: `REACT_APP_API_URL=<your-backend-url>`

## Local Development

### Backend:
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend:
```bash
cd frontend
npm install
npm start
```