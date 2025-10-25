import { useState } from "react";

export default function App() {
  const [status, setStatus] = useState("Highlight policy text on the page, then click Analyze.");
  const [preview, setPreview] = useState("");

  async function analyze() {
    setStatus("Reading selection…");
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const res = await chrome.tabs.sendMessage(tab.id, { type: "GET_POLICY_TEXT" });
      if (!res?.text) { setStatus("No text found on this page."); return; }
      setPreview(res.text.slice(0, 400));
      setStatus(`Captured ${res.text.length.toLocaleString()} characters.`);
      // Later: POST res.text to your backend /analyze and render scores.
    } catch (e) {
      console.error(e);
      setStatus("Could not access the page. Is content script loaded?");
    }
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 12, width: 330 }}>
      <h3 style={{ marginTop: 0 }}>PrivaSee</h3>
      <button onClick={analyze} style={{ padding: "8px 10px", border: 0, borderRadius: 8, cursor: "pointer" }}>
        Analyze selection
      </button>
      <p style={{ fontSize: 12, color: "#555" }}>{status}</p>
      {preview && (
        <>
          <div style={{ fontWeight: 600, marginTop: 8 }}>Preview</div>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, background: "#f6f6f6", padding: 8, borderRadius: 8 }}>
            {preview}{preview.length === 400 ? "…" : ""}
          </pre>
        </>
      )}
    </div>
  );
}
