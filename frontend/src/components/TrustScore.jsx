import React from 'react';

function TrustScore({ score, riskLevel }) {
  const getColor = () => {
    if (score >= 70) return '#22c55e';
    if (score >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const color = getColor();

  const getRiskText = () => {
    switch (riskLevel) {
      case 'low': return 'Low Risk';
      case 'medium': return 'Medium Risk';
      case 'high': return 'High Risk';
      default: return 'Unknown';
    }
  };

  const getRiskEmoji = () => {
    switch (riskLevel) {
      case 'low': return '✅';
      case 'medium': return '⚠️';
      case 'high': return '❌';
      default: return '❓';
    }
  };

  return (
    <div className="trust-score-container">
      <div className="trust-score-card" style={{ borderColor: color }}>
        <div className="score-display">
          <div className="score-label">Trust Score</div>
          <div className="score-number" style={{ color: color }}>
            {Math.round(score)}
          </div>
          <div className="score-range">out of 100</div>
        </div>

        <div className="risk-badge" style={{ backgroundColor: color }}>
          <span className="risk-emoji">{getRiskEmoji()}</span>
          <span className="risk-text">{getRiskText()}</span>
        </div>

        <div className="score-interpretation">
          {score >= 70 && <p>This privacy policy demonstrates strong privacy practices.</p>}
          {score >= 40 && score < 70 && <p>This privacy policy has some concerns. Review categories below.</p>}
          {score < 40 && <p>This privacy policy has significant privacy concerns.</p>}
        </div>
      </div>
    </div>
  );
}

export default TrustScore;