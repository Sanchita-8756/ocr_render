import React from 'react';

const EmployeeTable = ({ employees, onDownload }) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg p-6 mb-8 border border-blue-100">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent flex items-center">
          📊 Employee Reimbursements
        </h2>
        <div className="bg-blue-50 px-4 py-2 rounded-xl border border-blue-200">
          <p className="text-sm font-medium text-blue-700">Total Employees: <span className="font-bold">{employees.length}</span></p>
        </div>
      </div>
      <div className="overflow-x-auto rounded-xl border border-blue-100">
        <table className="min-w-full divide-y divide-blue-100">
          <thead className="bg-gradient-to-r from-blue-50 to-cyan-50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-bold text-blue-700 uppercase tracking-wider">Emp ID</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-blue-700 uppercase tracking-wider">Name</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-blue-700 uppercase tracking-wider">Total Reimbursement</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-blue-700 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white/50 divide-y divide-blue-50">
            {employees.map((emp, idx) => (
              <tr key={idx} className="hover:bg-blue-50/50 transition-colors">
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{emp.emp_id}</td>
                <td className="px-6 py-4 text-sm text-gray-900">{emp.name}</td>
                <td className="px-6 py-4 text-sm font-bold text-green-600">₹{emp.total_reimbursement}</td>
                <td className="px-6 py-4 text-sm">
                  <button 
                    onClick={() => onDownload('employee', emp.emp_id)}
                    className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-4 py-2 rounded-lg hover:from-blue-600 hover:to-cyan-600 transition-all transform hover:scale-105 shadow-md hover:shadow-lg">
                    💾 Download Images
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default EmployeeTable;
