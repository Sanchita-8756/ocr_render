import React, { useState, useEffect } from 'react';
import { getMetrics, getSummary, getEmployees, downloadImages, processMonth, exportCSV, getUsersUploaded } from '../services/api';
import MetricsCard from './MetricsCard';
import EmployeeTable from './EmployeeTable';
import SummaryChart from './SummaryChart';
import ProgressBar from './ProgressBar';

const Dashboard = () => {
  const [year, setYear] = useState('2025');
  const [month, setMonth] = useState('Oct');
  const [metrics, setMetrics] = useState(null);
  const [summary, setSummary] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [usersUploaded, setUsersUploaded] = useState(null);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [progressStatus, setProgressStatus] = useState('');

  const handleCheckUsersUploaded = async () => {
    setLoadingUsers(true);
    try {
      const response = await getUsersUploaded(year, month);
      setUsersUploaded(response.data.users_uploaded);
    } catch (error) {
      console.error('Error fetching users uploaded:', error);
      setUsersUploaded(0);
    }
    setLoadingUsers(false);
  };

  useEffect(() => {
    fetchData();
  }, [year, month]);

  const fetchData = async () => {
    setLoading(true);
    setUsersUploaded(null); // Reset users uploaded when changing filters
    try {
      const [metricsRes, summaryRes, employeesRes] = await Promise.all([
        getMetrics(year, month),
        getSummary(year, month),
        getEmployees(year, month)
      ]);
      setMetrics(metricsRes.data);
      setSummary(summaryRes.data);
      setEmployees(employeesRes.data.employees);
      
      // Debug logging
      console.log('Summary data:', summaryRes.data);
      console.log('Summary length:', summaryRes.data.length);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
    setLoading(false);
  };

  const handleDownload = async (type, value) => {
    try {
      const response = await downloadImages(type, value, year, month);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `images_${type}_${value}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading images:', error);
    }
  };

  const handleProcessMonth = async () => {
    setProcessing(true);
    setProgress(0);
    setProgressStatus('Initializing...');
    
    try {
      const monthYear = `${getMonthName(month)} ${year}`;
      await processMonth(monthYear, (progressValue, status) => {
        setProgress(progressValue);
        setProgressStatus(status);
      });
      
      setTimeout(() => {
        setProcessing(false);
        fetchData(); // Refresh data
      }, 2000);
    } catch (error) {
      console.error('Error processing month:', error);
      setProgressStatus('Processing failed!');
      setTimeout(() => {
        setProcessing(false);
      }, 2000);
    }
  };

  const getMonthName = (monthAbbr) => {
    const months = {
      'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April',
      'May': 'May', 'Jun': 'June', 'Jul': 'July', 'Aug': 'August',
      'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'
    };
    return months[monthAbbr] || monthAbbr;
  };

  const handleExportCSV = async () => {
    try {
      const response = await exportCSV(year, month);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${year}_${month}_reimbursement_report.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('Error exporting CSV data');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-100">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8 bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-blue-100">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent mb-2">HR Reimbursement Dashboard</h1>
          <p className="text-blue-600 mb-6">Manage and track employee reimbursements with ease</p>
          <div className="flex gap-4 flex-wrap">
            <select value={year} onChange={(e) => setYear(e.target.value)} 
              className="px-4 py-3 border-2 border-blue-200 rounded-xl bg-white/90 focus:border-blue-400 focus:ring-2 focus:ring-blue-200 transition-all">
              <option value="2026">2026</option>
              <option value="2025">2025</option>
              <option value="2024">2024</option>
            </select>
            <select value={month} onChange={(e) => setMonth(e.target.value)} 
              className="px-4 py-3 border-2 border-blue-200 rounded-xl bg-white/90 focus:border-blue-400 focus:ring-2 focus:ring-blue-200 transition-all">
              {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <button onClick={fetchData} className="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl hover:from-blue-600 hover:to-blue-700 shadow-lg hover:shadow-xl transition-all transform hover:scale-105">
              🔄 Refresh
            </button>
            <button 
              onClick={handleCheckUsersUploaded}
              disabled={loadingUsers}
              className="px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-xl hover:from-purple-600 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 shadow-lg hover:shadow-xl transition-all transform hover:scale-105 disabled:transform-none">
              {loadingUsers ? '⏳ Checking...' : '👥 Check Users Uploaded'}
            </button>
            <button 
              onClick={handleProcessMonth} 
              disabled={processing}
              className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl hover:from-green-600 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 shadow-lg hover:shadow-xl transition-all transform hover:scale-105 disabled:transform-none">
              {processing ? '⏳ Processing...' : '🚀 Process Month'}
            </button>
            <button 
              onClick={handleExportCSV}
              className="px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-xl hover:from-purple-600 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all transform hover:scale-105">
              📊 Export CSV
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-flex items-center px-6 py-4 bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
              <span className="text-blue-600 font-medium">Loading dashboard data...</span>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {metrics && <MetricsCard metrics={metrics} usersUploaded={usersUploaded} />}
            {summary.length > 0 && <SummaryChart data={summary} />}
            {employees.length > 0 && <EmployeeTable employees={employees} onDownload={handleDownload} />}
          </div>
        )}
      </div>
      
      <ProgressBar 
        isVisible={processing}
        progress={progress}
        status={progressStatus}
      />
    </div>
  );
};

export default Dashboard;
