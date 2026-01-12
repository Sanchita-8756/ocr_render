import React from 'react';

const MetricsCard = ({ metrics, usersUploaded }) => {
  const cards = [
    { title: 'Total Receipts', value: metrics.total_receipts, gradient: 'from-blue-500 to-blue-600', icon: '📊' },
    { title: 'Approved', value: metrics.total_approvals, gradient: 'from-green-500 to-emerald-600', icon: '✅' },
    { title: 'Rejected', value: metrics.rejected_receipts, gradient: 'from-red-500 to-pink-600', icon: '❌' }
  ];

  // Add users uploaded card if data is available
  if (usersUploaded !== null) {
    cards.splice(1, 0, { title: 'Users Uploaded', value: usersUploaded, gradient: 'from-purple-500 to-indigo-600', icon: '👥' });
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      {cards.map((card, idx) => (
        <div key={idx} className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg p-6 border border-blue-100 hover:shadow-xl transition-all transform hover:scale-105">
          <div className={`w-16 h-16 bg-gradient-to-br ${card.gradient} rounded-2xl mb-4 flex items-center justify-center shadow-lg`}>
            <span className="text-white text-2xl">{card.icon}</span>
          </div>
          <h3 className="text-blue-600 text-sm font-bold uppercase tracking-wider">{card.title}</h3>
          <p className="text-3xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent mt-2">{card.value}</p>
        </div>
      ))}
    </div>
  );
};

export default MetricsCard;
