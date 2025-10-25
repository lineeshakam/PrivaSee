/**
 * SERVICE WORKER - Integrates with Flask Backend
 */

const BACKEND_URL = 'http://localhost:5000'; // Flask backend

console.log('PrivaSee Service Worker: initialized');

// ============================================
// MESSAGE LISTENER
// ============================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Service worker received message:', message.type);
  
  if (message.type === 'ANALYZE_TEXT') {
    handleAnalysisRequest(message)
      .then(result => {
        sendResponse({ success: true, data: result });
      })
      .catch(error => {
        console.error('Analysis error:', error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true; // Keep channel open for async response
  }
  
  if (message.type === 'GET_CACHED') {
    getCachedAnalysis()
      .then(result => sendResponse({ data: result }))
      .catch(error => sendResponse({ data: null }));
    
    return true;
  }
  
  if (message.type === 'CLEAR_CACHE') {
    clearCache()
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false }));
    
    return true;
  }
});

// ============================================
// ANALYSIS REQUEST HANDLER
// ============================================

async function handleAnalysisRequest(message) {
  const { text, url } = message;
  
  console.log(`Analyzing ${text.length} characters from ${url}...`);
  
  try {
    // Call Flask backend
    const result = await analyzeWithBackend(text, url);
    
    // Transform backend response to frontend format
    const transformed = transformBackendResponse(result);
    
    // Cache the result
    await cacheAnalysis(transformed);
    
    return transformed;
    
  } catch (error) {
    console.error('Failed to analyze:', error);
    throw error;
  }
}

// ============================================
// BACKEND API COMMUNICATION
// ============================================

async function analyzeWithBackend(text, url) {
  const endpoint = `${BACKEND_URL}/analyze`;
  
  console.log(`Calling backend: ${endpoint}`);
  console.log(`Text length: ${text.length} chars`);
  
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: text,
      mode: text.length > 10000 ? 'page' : 'selection',
      return_snippets: true,
      snippets_top_k: 3,
      include_spacy_probs: true
    })
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend error (${response.status}): ${errorText}`);
  }
  
  const result = await response.json();
  console.log('Backend analysis complete:', result);
  
  return result;
}

// ============================================
// TRANSFORM BACKEND RESPONSE TO FRONTEND FORMAT
// ============================================

function transformBackendResponse(backendResult) {
  /**
   * Backend returns:
   * {
   *   trust_score: 68.4,
   *   risk_level: "Medium",
   *   categories: {
   *     "Third-Party Sharing/Selling": {
   *       score: 0.32,
   *       reason: "...",
   *       heuristics: {...},
   *       spacy_prob: 0.41
   *     },
   *     ...
   *   },
   *   evidence: {
   *     "Third-Party Sharing/Selling": [
   *       {text: "...", start: 1234, end: 1298, score: 0.82, matched: ["..."]}
   *     ],
   *     ...
   *   },
   *   weights: {...}
   * }
   * 
   * Frontend expects:
   * {
   *   trustScore: 68.4,
   *   riskLevel: "medium",
   *   categories: [
   *     {
   *       name: "Third-Party Sharing/Selling",
   *       score: 32,  // 0-100 scale
   *       weight: 0.20,
   *       reasons: ["..."],
   *       evidence: [{text: "...", keywords: [...], highlighted: "..."}]
   *     },
   *     ...
   *   ],
   *   timestamp: Date.now(),
   *   analyzedTextLength: 1234
   * }
   */
  
  const categories = [];
  const categoryNames = [
    'Data Collection',
    'Third-Party Sharing/Selling',
    'Purpose Limitation',
    'User Control & Rights',
    'Retention & Deletion',
    'Security Practices',
    'International Transfers & Jurisdiction',
    'Children/Minors + Sensitive Data'
  ];
  
  for (const catName of categoryNames) {
    const backendCat = backendResult.categories?.[catName] || {};
    const backendEvidence = backendResult.evidence?.[catName] || [];
    
    // Convert score from 0-1 to 0-100
    const score = Math.round((backendCat.score || 0) * 100);
    
    // Extract reasons (from LLM reason + heuristic flags)
    const reasons = [];
    if (backendCat.reason) {
      reasons.push(backendCat.reason);
    }
    if (backendCat.heuristics?.flags?.length > 0) {
      reasons.push(...backendCat.heuristics.flags.map(f => `Detected: ${f}`));
    }
    
    // Transform evidence with highlighted keywords
    const evidence = backendEvidence.map(ev => ({
      text: ev.text || '',
      keywords: ev.matched || [],
      highlighted: highlightKeywords(ev.text || '', ev.matched || [])
    }));
    
    categories.push({
      name: catName,
      score: score,
      weight: backendResult.weights?.[catName] || 0.10,
      reasons: reasons.length > 0 ? reasons : ['No specific issues detected'],
      evidence: evidence
    });
  }
  
  return {
    trustScore: Math.round(backendResult.trust_score || 0),
    riskLevel: (backendResult.risk_level || 'medium').toLowerCase(),
    categories: categories,
    timestamp: Date.now(),
    analyzedTextLength: 0 // Backend doesn't return this, but we could calculate it
  };
}

// ============================================
// HELPER: HIGHLIGHT KEYWORDS IN TEXT
// ============================================

function highlightKeywords(text, keywords) {
  if (!keywords || keywords.length === 0) return text;
  
  let highlighted = text;
  keywords.forEach(keyword => {
    // Case-insensitive replacement with <mark> tags
    const regex = new RegExp(`(${escapeRegex(keyword)})`, 'gi');
    highlighted = highlighted.replace(regex, '<mark>$1</mark>');
  });
  
  return highlighted;
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
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
// HEALTH CHECK
// ============================================

async function checkBackendHealth() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('Backend is healthy ✓', data);
      return true;
    } else {
      console.warn('Backend health check failed:', response.status);
      return false;
    }
  } catch (error) {
    console.error('Cannot connect to backend:', error.message);
    console.warn('⚠️ Make sure Flask server is running: python run.py');
    return false;
  }
}

// Check backend on startup
checkBackendHealth();

// Periodic health check (every 5 minutes)
setInterval(checkBackendHealth, 5 * 60 * 1000);

// ============================================
// INSTALL/UPDATE HANDLERS
// ============================================

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('PrivaSee installed!');
    clearCache();
  } else if (details.reason === 'update') {
    console.log('PrivaSee updated!');
  }
});

console.log('Service worker ready! Backend: ' + BACKEND_URL);

