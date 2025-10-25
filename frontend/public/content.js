function getSelectedOrFullText() {
    const sel = window.getSelection?.().toString().trim();
    if (sel) return sel;
    const candidates = Array.from(document.querySelectorAll('main, article, [role="main"]'));
    const text = (candidates[0]?.innerText || document.body.innerText || "").trim();
    return text.slice(0, 200000); // cap payload
  }
  
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type === "GET_POLICY_TEXT") {
      sendResponse({ text: getSelectedOrFullText(), url: location.href, title: document.title });
    }
  });
  