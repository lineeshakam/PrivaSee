import { useState, useEffect } from "react";
import TrustScore from "./components/TrustScore";
import CategoryList from "./components/CategoryList";
import LoadingSpinner from "./components/LoadingSpinner";
import { MESSAGE_TYPES, MOCK_ANALYSIS } from "./utils/messaging";
import "./App.css";

export default function App() {
  const [status, setStatus] = useState("loading");
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Try to load cached analysis
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      chrome.runtime.sendMessage({ type: 'GET_CACHED' }, (response) => {
        if (chrome.runtime.lastError) {
          console.log('No cached data');
          setStatus("no-data");
          return;
        }
        if (response?.data) {
          setAnalysis(response.data);
          setStatus("ready");
        } else {
          setStatus("no-data");
        }
      });
    } else {
      setStatus("no-data");
    }
  }, []);

  async function analyze() {
    setStatus("analyzing");
    setError(null);
    
    try {
      // Check if Chrome APIs are available
      if (typeof chrome === 'undefined' || !chrome.tabs || !chrome.runtime) {
        throw new Error("Chrome extension APIs not available");
      }

      // Get text from content script
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      if (!tab || !tab.id) {
        throw new Error("No active tab found");
      }

      chrome.tabs.sendMessage(tab.id, { type: "GET_POLICY_TEXT" }, (textRes) => {
        if (chrome.runtime.lastError) {
          setError("Could not access page. Try refreshing the page and reopening the extension.");
          setStatus("error");
          return;
        }

        if (!textRes?.text) {
          setError("No text found on this page.");
          setStatus("error");
          return;
        }

        // Send to service worker for analysis
        chrome.runtime.sendMessage(
          { type: 'ANALYZE_TEXT', text: textRes.text, url: textRes.url },
          (response) => {
            if (chrome.runtime.lastError) {
              setError("Service worker error: " + chrome.runtime.lastError.message);
              setStatus("error");
              return;
            }

            if (response?.success) {
              setAnalysis(response.data);
              setStatus("ready");
            } else {
              setError(response?.error || "Analysis failed");
              setStatus("error");
            }
          }
        );
      });
      
    } catch (e) {
      console.error(e);
      setError(e.message || "Could not access the page. Try refreshing and reopening the extension.");
      setStatus("error");
    }
  }

  // Use mock data for development
  function useMockData() {
    console.log("Loading mock data...");
    setAnalysis(MOCK_ANALYSIS);
    setStatus("ready");
  }

  // LOADING STATE
  if (status === "loading" || status === "analyzing") {
    return (
      <div className="app loading-state">
        <LoadingSpinner />
        <p>{status === "analyzing" ? "Analyzing privacy policy..." : "Loading..."}</p>
      </div>
    );
  }

  // ERROR STATE
  if (status === "error") {
    return (
      <div className="app error-state">
        <div className="error-icon">⚠️</div>
        <h3>Error</h3>
        <p>{error}</p>
        <button onClick={analyze} className="retry-button">Retry</button>
        <button onClick={useMockData} className="mock-button">Use Mock Data (Dev)</button>
      </div>
    );
  }

  // NO DATA STATE
  if (status === "no-data" || !analysis) {
    return (
      <div className="app no-data-state">
        <div className="empty-icon">🔍</div>
        <h3>PrivaSee</h3>
        <p>Analyze privacy policies with AI-powered trust scores</p>
        <button onClick={analyze} className="analyze-button">
          Analyze This Page
        </button>
        <div className="instructions">
          <p><strong>How it works:</strong></p>
          <ol>
            <li>Navigate to a privacy policy page</li>
            <li>Highlight specific text (optional)</li>
            <li>Click "Analyze This Page"</li>
          </ol>
        </div>
        <button onClick={useMockData} className="mock-button">Use Mock Data (Dev)</button>
      </div>
    );
  }

  // RESULTS STATE
  return (
    <div className="app">
      <header className="app-header">
        <h1>PrivaSee Analysis</h1>
        <button onClick={analyze} className="reanalyze-button">↻</button>
      </header>

      <TrustScore score={analysis.trustScore} riskLevel={analysis.riskLevel} />
      
      <CategoryList categories={analysis.categories} />

      <footer className="app-footer">
        <p>🔒 Analysis runs locally. We don't store your data.</p>
        <p className="disclaimer">Informational only. Not legal advice.</p>
        <p className="timestamp">
          Analyzed: {new Date(analysis.timestamp).toLocaleTimeString()}
        </p>
      </footer>
    </div>
  );
}