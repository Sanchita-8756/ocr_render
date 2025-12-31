import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const API_URL = `${API_BASE_URL}/api`;

export const getMetrics = (year, month) => 
  axios.get(`${API_URL}/dashboard/metrics`, { params: { year, month } });

export const getSummary = (year, month) => 
  axios.get(`${API_URL}/dashboard/summary`, { params: { year, month } });

export const getEmployees = (year, month) => 
  axios.get(`${API_URL}/dashboard/employees`, { params: { year, month } });

export const getRecords = (year, month) => 
  axios.get(`${API_URL}/records`, { params: { year, month } });

export const downloadImages = (type, value, year, month) => 
  axios.get(`${API_URL}/download/images`, { 
    params: { type, value, year, month },
    responseType: 'blob'
  });

export const processMonth = (monthYear, onProgress) => {
  return new Promise((resolve, reject) => {
    // Start the backend process
    axios.post(`${API_URL}/process/month`, { month_year: monthYear })
      .then(response => {
        const jobId = response.data.job_id;
        
        // Poll for progress
        const pollInterval = setInterval(() => {
          axios.get(`${API_URL}/process/progress/${jobId}`)
            .then(progressResponse => {
              const { progress, status, completed, error } = progressResponse.data;
              
              if (onProgress) {
                onProgress(progress, status);
              }
              
              if (completed) {
                clearInterval(pollInterval);
                if (error) {
                  reject(new Error(error));
                } else {
                  resolve(progressResponse.data);
                }
              }
            })
            .catch(pollError => {
              clearInterval(pollInterval);
              reject(pollError);
            });
        }, 2000); // Poll every 2 seconds
      })
      .catch(reject);
  });
};

export const exportCSV = (year, month) => 
  axios.post(`${API_URL}/export/csv`, null, { 
    params: { year, month },
    responseType: 'blob'
  });