import React, { useState } from 'react';

function CategoryItem({ category }) {
  const [expanded, setExpanded] = useState(false);

  const getScoreColor = (score) => {
    if (score >= 70) return '#22c55e';
    if (score >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const scoreColor = getScoreColor(category.score);

  const getIcon = (name) => {
    const icons = {
      'Data Collection': '📊',
      'Third-Party Sharing/Selling': '🔄',
      'Purpose Limitation': '🎯',
      'User Control & Rights': '⚙️',
      'Retention & Deletion': '🗑️',
      'Security Practices': '🔒',
      'International Transfers & Jurisdiction': '🌍',
      'Children/Minors + Sensitive Data': '👶'
    };
    return icons[name] || '📋';
  };

  return (
    <div className="category-item" data-expanded={expanded}>
      <div className="category-header" onClick={() => setExpanded(!expanded)}>
        <div className="category-left">
          <span className="category-icon">{getIcon(category.name)}</span>
          <div className="category-info">
            <h3 className="category-name">{category.name}</h3>
            <span className="category-weight">
              Weight: {Math.round(category.weight * 100)}%
            </span>
          </div>
        </div>

        <div className="category-right">
          <div className="category-score-badge" style={{ backgroundColor: scoreColor, color: 'white' }}>
            {Math.round(category.score)}
          </div>
          <span className="expand-icon">{expanded ? '▼' : '▶'}</span>
        </div>
      </div>

      {expanded && (
        <div className="category-details">
          {category.reasons && category.reasons.length > 0 && (
            <div className="category-reasons">
              <h4>Why this score:</h4>
              <ul>
                {category.reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          )}

          {category.evidence && category.evidence.length > 0 && (
            <div className="category-evidence">
              <h4>Evidence from policy:</h4>
              <div className="evidence-list">
                {category.evidence.map((item, idx) => (
                  <blockquote key={idx} className="evidence-item">
                    <div dangerouslySetInnerHTML={{ __html: item.highlighted || item.text }} />
                    {item.keywords && item.keywords.length > 0 && (
                      <div className="evidence-keywords">
                        {item.keywords.map((keyword, kidx) => (
                          <span key={kidx} className="keyword-tag">{keyword}</span>
                        ))}
                      </div>
                    )}
                  </blockquote>
                ))}
              </div>
            </div>
          )}

          {(!category.evidence || category.evidence.length === 0) && (
            <div className="no-evidence">
              <p>No specific evidence found in the analyzed text.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CategoryItem;