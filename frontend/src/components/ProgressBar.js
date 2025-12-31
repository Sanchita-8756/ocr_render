import React from 'react';

const ProgressBar = ({ isVisible, progress, status }) => {
  if (!isVisible) return null;

  return (
    <div className="fixed top-4 right-4 bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl p-6 min-w-80 z-50 border-2 border-blue-200">
      <div className="flex items-center justify-between mb-4">
        <span className="text-lg font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">🚀 Processing</span>
        <span className="text-xl font-bold text-blue-600">{progress}%</span>
      </div>
      <div className="w-full bg-blue-100 rounded-full h-3 mb-4 overflow-hidden">
        <div 
          className="bg-gradient-to-r from-blue-500 to-cyan-500 h-3 rounded-full transition-all duration-500 ease-out shadow-sm"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
      <div className="flex items-center">
        <div className="animate-pulse w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
        <p className="text-sm text-blue-700 font-medium">{status}</p>
      </div>
    </div>
  );
};

export default ProgressBar;