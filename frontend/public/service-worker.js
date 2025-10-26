/**
 * SERVICE WORKER - Works WITH or WITHOUT Backend
 * Set USE_MOCK_DATA = true to test without backend
 */

//const BACKEND_URL = 'http://localhost:5000';
//const USE_MOCK_DATA = true; // ← Set to false when backend is ready

const BACKEND_URL = 'https://unplacatory-lashell-unproffered.ngrok-free.dev';
const USE_MOCK_DATA = false;

console.log('PrivaSee Service Worker: initialized');
console.log(`Mode: ${USE_MOCK_DATA ? 'MOCK DATA (no backend needed)' : 'BACKEND API'}`);

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
    let result;
    
    if (USE_MOCK_DATA) {
      // Use mock data for testing without backend
      result = await getMockAnalysis(text, url);
    } else {
      // Call real backend
      result = await analyzeWithBackend(text, url);
    }
    
    // Transform to frontend format
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
// MOCK DATA (For testing without backend)
// ============================================

async function getMockAnalysis(text, url) {
  console.log('Using MOCK data (backend not needed)');
  
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1500));
  
  // Analyze text to make it more realistic
  const textLower = text.toLowerCase();
  const hasSharing = textLower.includes('share') || textLower.includes('third party');
  const hasSell = textLower.includes('sell') || textLower.includes('sale');
  const hasEncryption = textLower.includes('encrypt') || textLower.includes('secure');
  const hasRights = textLower.includes('access') || textLower.includes('delete');
  
  // Generate semi-realistic scores
  return {
    trust_score: hasSharing || hasSell ? 35 : 65,
    risk_level: hasSharing || hasSell ? "High" : "Medium",
    categories: {
      "Data Collection": {
        score: 0.60,
        reason: "Policy describes what data is collected, but lacks specifics on sensitive data limits.",
        heuristics: { delta: 0.0, flags: ["collects personal information"] },
        spacy_prob: 0.65
      },
      "Third-Party Sharing/Selling": {
        score: hasSell ? 0.20 : 0.35,
        reason: hasSell ? "May sell data to third parties without clear opt-out." : hasSharing ? "Shares with third parties for marketing." : "Limited third-party sharing mentioned.",
        heuristics: { delta: hasSell ? -0.35 : -0.15, flags: hasSell ? ["may sell data"] : hasSharing ? ["shares with third parties"] : [] },
        spacy_prob: 0.40
      },
      "Purpose Limitation": {
        score: 0.55,
        reason: "States general purposes but includes vague 'compatible purposes' language.",
        heuristics: { delta: -0.10, flags: ["compatible purposes clause"] },
        spacy_prob: 0.50
      },
      "User Control & Rights": {
        score: hasRights ? 0.75 : 0.50,
        reason: hasRights ? "Provides access and deletion rights; CCPA compliant." : "Limited user control options mentioned.",
        heuristics: { delta: hasRights ? 0.20 : 0.0, flags: hasRights ? ["provides access/deletion rights"] : [] },
        spacy_prob: 0.70
      },
      "Retention & Deletion": {
        score: 0.35,
        reason: "No specific retention period; retains data 'as long as necessary'.",
        heuristics: { delta: -0.30, flags: ["indefinite retention"] },
        spacy_prob: 0.30
      },
      "Security Practices": {
        score: hasEncryption ? 0.80 : 0.60,
        reason: hasEncryption ? "Mentions encryption and secure transmission." : "Some security measures mentioned.",
        heuristics: { delta: hasEncryption ? 0.25 : 0.10, flags: hasEncryption ? ["encryption mentioned", "secure transmission"] : [] },
        spacy_prob: 0.75
      },
      "International Transfers & Jurisdiction": {
        score: 0.50,
        reason: "Mentions international data transfers but lacks specific safeguards.",
        heuristics: { delta: 0.0, flags: [] },
        spacy_prob: 0.45
      },
      "Children/Minors + Sensitive Data": {
        score: 0.80,
        reason: "COPPA compliant; does not knowingly collect from children under 13.",
        heuristics: { delta: 0.15, flags: ["COPPA compliant"] },
        spacy_prob: 0.85
      }
    },
    evidence: {
      "Data Collection": [
        {
          text: "We collect information you provide directly, such as your name, email address, and payment information.",
          start: 100,
          end: 200,
          score: 0.75,
          matched: ["collect", "information", "email", "payment"]
        }
      ],
      "Third-Party Sharing/Selling": hasSharing || hasSell ? [
        {
          text: hasSell ? "We may sell your personal data to third-party advertisers." : "We share your information with our partners for marketing purposes.",
          start: 500,
          end: 600,
          score: 0.85,
          matched: hasSell ? ["sell", "personal data", "third-party"] : ["share", "partners", "marketing"]
        }
      ] : [],
      "User Control & Rights": hasRights ? [
        {
          text: "You can request access to or deletion of your personal data by contacting us.",
          start: 1000,
          end: 1100,
          score: 0.80,
          matched: ["access", "deletion", "personal data"]
        }
      ] : [],
      "Security Practices": hasEncryption ? [
        {
          text: "We use industry-standard encryption to protect your data during transmission and storage.",
          start: 1500,
          end: 1600,
          score: 0.90,
          matched: ["encryption", "protect", "data"]
        }
      ] : []
    },
    weights: {
      "Data Collection": 0.15,
      "Third-Party Sharing/Selling": 0.20,
      "Purpose Limitation": 0.10,
      "User Control & Rights": 0.15,
      "Retention & Deletion": 0.10,
      "Security Practices": 0.10,
      "International Transfers & Jurisdiction": 0.10,
      "Children/Minors + Sensitive Data": 0.10
    }
  };
}

// ============================================
// BACKEND API COMMUNICATION (For when backend is ready)
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
    analyzedTextLength: 0
  };
}

// ============================================
// HELPER: HIGHLIGHT KEYWORDS IN TEXT
// ============================================

function highlightKeywords(text, keywords) {
  if (!keywords || keywords.length === 0) return text;
  
  let highlighted = text;
  keywords.forEach(keyword => {
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
  if (USE_MOCK_DATA) {
    console.log('Using mock data - backend health check skipped');
    return true;
  }
  
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
    console.warn('⚠️ Set USE_MOCK_DATA = true to test without backend');
    return false;
  }
}

// Check backend on startup
checkBackendHealth();

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

console.log('Service worker ready!');
console.log(`Backend: ${BACKEND_URL} | Mock Mode: ${USE_MOCK_DATA}`);
