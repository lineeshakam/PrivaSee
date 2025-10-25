/**
 * CONTENT SCRIPT - Person A
 * Handles text selection and page interaction
 */

console.log('Privacy Policy Analyzer: Content script loaded');

// Track selected text
let currentSelection = '';

// ============================================
// TEXT SELECTION HANDLER
// ============================================

document.addEventListener('mouseup', handleTextSelection);
document.addEventListener('keyup', handleTextSelection);

function handleTextSelection() {
  const selection = window.getSelection();
  currentSelection = selection.toString().trim();
  
  // Only show analyze option if meaningful text is selected
  if (currentSelection.length > 50) {
    showAnalyzeButton(selection);
  } else {
    hideAnalyzeButton();
  }
}

// ============================================
// ANALYZE BUTTON (Floating UI)
// ============================================

let analyzeButton = null;

function showAnalyzeButton(selection) {
  // Remove old button if it exists
  hideAnalyzeButton();
  
  // Get selection position
  const range = selection.getRangeAt(0);
  const rect = range.getBoundingClientRect();
  
  // Create button
  analyzeButton = document.createElement('div');
  analyzeButton.id = 'privacy-analyzer-button';
  analyzeButton.innerHTML = `
    <div style="
      position: fixed;
      top: ${rect.top + window.scrollY - 40}px;
      left: ${rect.left + window.scrollX}px;
      background: #4f46e5;
      color: white;
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
      font-family: system-ui, -apple-system, sans-serif;
      font-size: 14px;
      font-weight: 500;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      z-index: 999999;
      display: flex;
      align-items: center;
      gap: 8px;
    ">
      <span>🔍</span>
      <span>Analyze Privacy Policy</span>
    </div>
  `;
  
  analyzeButton.addEventListener('click', analyzeSelection);
  document.body.appendChild(analyzeButton);
}

function hideAnalyzeButton() {
  if (analyzeButton) {
    analyzeButton.remove();
    analyzeButton = null;
  }
}

// ============================================
// ANALYSIS TRIGGER
// ============================================

function analyzeSelection() {
  if (!currentSelection || currentSelection.length < 50) {
    alert('Please select at least 50 characters to analyze.');
    return;
  }
  
  // Hide button
  hideAnalyzeButton();
  
  // Show loading indicator
  showLoadingIndicator();
  
  // Send to service worker
  chrome.runtime.sendMessage({
    type: 'analyze_selection',
    text: currentSelection,
    url: window.location.href,
    timestamp: Date.now()
  }, (response) => {
    hideLoadingIndicator();
    
    if (chrome.runtime.lastError) {
      console.error('Error sending message:', chrome.runtime.lastError);
      showError('Failed to connect to analyzer. Please try again.');
    }
  });
}

function analyzeWholePage() {
  // Get all text from the page (excluding scripts, styles, etc.)
  const pageText = document.body.innerText;
  
  if (pageText.length < 100) {
    showError('Page content too short to analyze.');
    return;
  }
  
  showLoadingIndicator();
  
  // Send to service worker
  chrome.runtime.sendMessage({
    type: 'analyze_page',
    text: pageText,
    url: window.location.href,
    timestamp: Date.now()
  }, (response) => {
    hideLoadingIndicator();
    
    if (chrome.runtime.lastError) {
      console.error('Error sending message:', chrome.runtime.lastError);
      showError('Failed to connect to analyzer. Please try again.');
    }
  });
}

// ============================================
// LOADING INDICATOR
// ============================================

let loadingIndicator = null;

function showLoadingIndicator() {
  // Remove old indicator if exists
  hideLoadingIndicator();
  
  loadingIndicator = document.createElement('div');
  loadingIndicator.id = 'privacy-analyzer-loading';
  loadingIndicator.innerHTML = `
    <div style="
      position: fixed;
      top: 20px;
      right: 20px;
      background: white;
      padding: 16px 24px;
      border-radius: 12px;
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
      z-index: 999999;
      font-family: system-ui, -apple-system, sans-serif;
      display: flex;
      align-items: center;
      gap: 12px;
    ">
      <div style="
        width: 20px;
        height: 20px;
        border: 3px solid #e5e7eb;
        border-top-color: #4f46e5;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      "></div>
      <span style="font-weight: 500; color: #374151;">Analyzing...</span>
    </div>
    <style>
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
    </style>
  `;
  
  document.body.appendChild(loadingIndicator);
}

function hideLoadingIndicator() {
  if (loadingIndicator) {
    loadingIndicator.remove();
    loadingIndicator = null;
  }
}

// ============================================
// ERROR HANDLING
// ============================================

function showError(message) {
  const errorDiv = document.createElement('div');
  errorDiv.innerHTML = `
    <div style="
      position: fixed;
      top: 20px;
      right: 20px;
      background: #fee;
      color: #c00;
      padding: 16px 24px;
      border-radius: 12px;
      border: 1px solid #fcc;
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
      z-index: 999999;
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 300px;
    ">
      <strong>Error:</strong> ${message}
    </div>
  `;
  
  document.body.appendChild(errorDiv);
  
  // Auto-remove after 5 seconds
  setTimeout(() => errorDiv.remove(), 5000);
}

// ============================================
// LISTEN FOR MESSAGES FROM POPUP
// ============================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'analyzeSelection') {
    analyzeSelection();
    sendResponse({ success: true });
  } else if (message.action === 'analyzeWholePage') {
    analyzeWholePage();
    sendResponse({ success: true });
  }
  
  return true; // Keep message channel open for async response
});

// ============================================
// KEYBOARD SHORTCUT (Optional)
// ============================================

document.addEventListener('keydown', (e) => {
  // Ctrl+Shift+A or Cmd+Shift+A
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'A') {
    e.preventDefault();
    if (currentSelection && currentSelection.length > 50) {
      analyzeSelection();
    } else {
      analyzeWholePage();
    }
  }
});

console.log('Privacy Policy Analyzer: Ready! Select text or press Ctrl+Shift+A');