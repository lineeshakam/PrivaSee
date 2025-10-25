/**
 * SERVICE WORKER - Person A
 * Handles background logic and API communication
 */

console.log('Privacy Policy Analyzer: Service worker initialized');

// Backend API configuration
const BACKEND_URL = 'http://localhost:5000'; // Update this to your backend URL

// ============================================
// MESSAGE LISTENER
// ============================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Service worker received message:', message.type);
  
  if (message.type === 'analyze_selection' || message.type === 'analyze_page') {
    handleAnalysisRequest(message, sender)
      .then(result => {
        sendResponse({ success: true, data: result });
      })
      .catch(error => {
        console.error('Analysis error:', error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true; // Keep channel open for async response
  }
  
  if (message.type === 'get_cached_analysis') {
    getCachedAnalysis()
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    
    return true;
  }
});

// ============================================
// ANALYSIS REQUEST HANDLER
// ============================================

async function handleAnalysisRequest(message, sender) {
  const { text, url, type } = message;
  const isWholePage = type === 'analyze_page';
  
  console.log(`Analyzing ${isWholePage ? 'whole page' : 'selection'}: ${text.length} characters`);
  
  try {
    // Optional: Redact sensitive info (emails, phones) before sending
    const sanitizedText = redactSensitiveInfo(text);
    
    // Call backend API
    const result = await analyzeWithBackend(sanitizedText, url, isWholePage);
    
    // Cache the result
    await cacheAnalysis(result);
    
    // Send result to popup (if open)
    notifyPopup({
      type: 'analysis_result',
      data: result
    });
    
    return result;
    
  } catch (error) {
    console.error('Failed to analyze:', error);
    
    // Send error to popup
    notifyPopup({
      type: 'error',
      error: error.message,
      details: error.stack
    });
    
    throw error;
  }
}

// ============================================
// BACKEND API COMMUNICATION
// ============================================

async function analyzeWithBackend(text, url, isWholePage) {
  const endpoint = `${BACKEND_URL}/analyze`;
  
  console.log(`Calling backend: ${endpoint}`);
  
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: text,
      url: url,
      isWholePage: isWholePage
    })
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend error (${response.status}): ${errorText}`);
  }
  
  const result = await response.json();
  
  // Add metadata
  result.timestamp = Date.now();
  result.analyzedText = text.substring(0, 200); // First 200 chars for reference
  result.analyzedTextLength = text.length;
  result.isWholePage = isWholePage;
  
  console.log('Backend analysis complete:', result);
  
  return result;
}

// ============================================
// CACHING
// ============================================

async function cacheAnalysis(result) {
  return new Promise((resolve) => {
    chrome.storage.local.set({
      lastAnalysis: result,
      lastAnalysisTime: Date.now()
    }, () => {
      console.log('Analysis cached');
      resolve();
    });
  });
}

async function getCachedAnalysis() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['lastAnalysis', 'lastAnalysisTime'], (data) => {
      if (data.lastAnalysis) {
        const age = Date.now() - (data.lastAnalysisTime || 0);
        const ageMinutes = Math.floor(age / 60000);
        console.log(`Retrieved cached analysis (${ageMinutes} minutes old)`);
        resolve(data.lastAnalysis);
      } else {
        console.log('No cached analysis found');
        resolve(null);
      }
    });
  });
}

async function clearCache() {
  return new Promise((resolve) => {
    chrome.storage.local.remove(['lastAnalysis', 'lastAnalysisTime'], () => {
      console.log('Cache cleared');
      resolve();
    });
  });
}

// ============================================
// POPUP NOTIFICATION
// ============================================

function notifyPopup(message) {
  // Send message to popup if it's open
  chrome.runtime.sendMessage(message, (response) => {
    if (chrome.runtime.lastError) {
      // Popup is not open, that's okay
      console.log('Popup not open, message not sent');
    } else {
      console.log('Popup notified:', message.type);
    }
  });
}

// ============================================
// DATA SANITIZATION
// ============================================

function redactSensitiveInfo(text) {
  // Redact email addresses
  let sanitized = text.replace(
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    '[EMAIL_REDACTED]'
  );
  
  // Redact phone numbers (basic patterns)
  sanitized = sanitized.replace(
    /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g,
    '[PHONE_REDACTED]'
  );
  
  // Redact credit card numbers (basic pattern)
  sanitized = sanitized.replace(
    /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g,
    '[CARD_REDACTED]'
  );
  
  // Redact SSN patterns
  sanitized = sanitized.replace(
    /\b\d{3}-\d{2}-\d{4}\b/g,
    '[SSN_REDACTED]'
  );
  
  return sanitized;
}

// ============================================
// HEALTH CHECK
// ============================================

async function checkBackendHealth() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (response.ok) {
      console.log('Backend is healthy ✓');
      return true;
    } else {
      console.warn('Backend health check failed');
      return false;
    }
  } catch (error) {
    console.error('Cannot connect to backend:', error.message);
    return false;
  }
}

// Check backend on startup
checkBackendHealth().then(isHealthy => {
  if (!isHealthy) {
    console.warn('⚠️ Backend is not available. Make sure Flask/FastAPI server is running.');
  }
});

// ============================================
// INSTALL/UPDATE HANDLERS
// ============================================

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('Privacy Policy Analyzer installed!');
    // Clear any existing cache
    clearCache();
  } else if (details.reason === 'update') {
    console.log('Privacy Policy Analyzer updated!');
  }
});

// ============================================
// EXTENSION ICON CLICK HANDLER
// ============================================

chrome.action.onClicked.addListener((tab) => {
  // This fires if no popup is defined, or as a fallback
  console.log('Extension icon clicked on tab:', tab.id);
});

console.log('Service worker ready!');