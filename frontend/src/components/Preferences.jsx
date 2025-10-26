import React, { useState, useEffect } from 'react';

const PREFERENCE_SCHEMA = {
  protect_location: {
    title: "Keep my precise location private",
    category: "Children/Minors + Sensitive Data",
    default: true,
    icon: "📍"
  },
  opt_out_targeted_ads: {
    title: "Opt out of targeted/behavioral advertising",
    category: "User Control & Rights",
    default: true,
    icon: "🎯"
  },
  no_sale_or_sharing: {
    title: "Do not sell or share my personal data",
    category: "Third-Party Sharing/Selling",
    default: true,
    icon: "🔄"
  },
  limit_data_collection: {
    title: "Limit the types of data collected (only necessary)",
    category: "Data Collection",
    default: false,
    icon: "📊"
  },
  short_retention: {
    title: "Do not retain my data indefinitely (short retention only)",
    category: "Retention & Deletion",
    default: true,
    icon: "🗑️"
  },
  restrict_cross_border: {
    title: "Avoid cross-border transfers unless strong safeguards",
    category: "International Transfers & Jurisdiction",
    default: false,
    icon: "🌍"
  },
  strong_security: {
    title: "Require strong security (encryption, access controls, breach notice)",
    category: "Security Practices",
    default: true,
    icon: "🔒"
  },
  child_privacy: {
    title: "Protect minors' data and sensitive categories",
    category: "Children/Minors + Sensitive Data",
    default: true,
    icon: "👶"
  }
};

function Preferences({ onClose, onSave }) {
  const [preferences, setPreferences] = useState({});
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    // Load saved preferences or use defaults
    chrome.storage.local.get(['userPreferences'], (data) => {
      const saved = data.userPreferences || {};
      const defaults = {};
      Object.keys(PREFERENCE_SCHEMA).forEach(key => {
        defaults[key] = saved[key] ?? PREFERENCE_SCHEMA[key].default;
      });
      setPreferences(defaults);
    });
  }, []);

  const handleToggle = (key) => {
    setPreferences(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
    setHasChanges(true);
  };

  const handleSave = () => {
    chrome.storage.local.set({ userPreferences: preferences }, () => {
      console.log('Preferences saved:', preferences);
      setHasChanges(false);
      if (onSave) onSave(preferences);
    });
  };

  const handleReset = () => {
    const defaults = {};
    Object.keys(PREFERENCE_SCHEMA).forEach(key => {
      defaults[key] = PREFERENCE_SCHEMA[key].default;
    });
    setPreferences(defaults);
    setHasChanges(true);
  };

  return (
    <div className="preferences-overlay">
      <div className="preferences-modal">
        <div className="preferences-header">
          <h2>Privacy Preferences</h2>
          <button onClick={onClose} className="close-button">✕</button>
        </div>

        <div className="preferences-description">
          <p>Set your privacy preferences. We'll highlight mismatches in the analysis.</p>
        </div>

        <div className="preferences-list">
          {Object.entries(PREFERENCE_SCHEMA).map(([key, schema]) => (
            <div key={key} className="preference-item">
              <div className="preference-left">
                <span className="preference-icon">{schema.icon}</span>
                <div className="preference-info">
                  <label htmlFor={key} className="preference-title">
                    {schema.title}
                  </label>
                  <span className="preference-category">{schema.category}</span>
                </div>
              </div>
              <div className="preference-toggle">
                <input
                  type="checkbox"
                  id={key}
                  checked={preferences[key] || false}
                  onChange={() => handleToggle(key)}
                  className="toggle-checkbox"
                />
                <label htmlFor={key} className="toggle-label">
                  <span className="toggle-slider"></span>
                </label>
              </div>
            </div>
          ))}
        </div>

        <div className="preferences-footer">
          <button onClick={handleReset} className="reset-button">
            Reset to Defaults
          </button>
          <div className="footer-right">
            <button onClick={onClose} className="cancel-button">
              Cancel
            </button>
            <button 
              onClick={handleSave} 
              className="save-button"
              disabled={!hasChanges}
            >
              Save Preferences
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Preferences;