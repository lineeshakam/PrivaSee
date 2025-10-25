// content.js - Extract text from privacy policies

console.log("PrivaSee: Content script loaded");

function getSelectedOrFullText() {
  const sel = window.getSelection?.().toString().trim();
  if (sel) return sel;
  const candidates = Array.from(document.querySelectorAll('main, article, [role="main"]'));
  const text = (candidates[0]?.innerText || document.body.innerText || "").trim();
  return text.slice(0, 200000); // cap payload
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  console.log("Content script received message:", msg.type);
  
  if (msg.type === "GET_POLICY_TEXT") {
    const text = getSelectedOrFullText();
    console.log(`Returning ${text.length} characters`);
    sendResponse({ 
      text: text, 
      url: location.href, 
      title: document.title 
    });
    return true; // Important for async response
  }
});

// Optional: Add visual feedback when text is selected
let analyzeButton = null;

document.addEventListener('mouseup', () => {
  const selection = window.getSelection().toString().trim();
  
  if (selection.length > 50) {
    showAnalyzeButton();
  } else {
    hideAnalyzeButton();
  }
});

function showAnalyzeButton() {
  if (analyzeButton) return;
  
  analyzeButton = document.createElement('div');
  analyzeButton.innerHTML = `
    <button style="
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: #4f46e5;
      color: white;
      padding: 12px 24px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-family: system-ui, sans-serif;
      font-size: 14px;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 999999;
      display: flex;
      align-items: center;
      gap: 8px;
    ">
      🔍 Analyze Privacy Policy
    </button>
  `;
  
  analyzeButton.querySelector('button').addEventListener('click', () => {
    // Just open the extension popup
    console.log("Please click the PrivaSee extension icon to analyze");
    hideAnalyzeButton();
  });
  
  document.body.appendChild(analyzeButton);
}

function hideAnalyzeButton() {
  if (analyzeButton) {
    analyzeButton.remove();
    analyzeButton = null;
  }
}

console.log("PrivaSee: Ready!");