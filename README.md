# 🕵️‍♀️ PrivaSee — Your Privacy Policy Translator

> A Chrome extension that helps users understand **what they're agreeing to** when they open long, confusing privacy policies.

---

## 🚀 Overview

**PrivaSee** automatically summarizes and scores privacy policies to make them transparent and accessible.  
Users can highlight any section of a policy — or analyze the entire page — and instantly get:

- ✅ **Plain-language summary** ("What is this saying?")
- 🔒 **Trust Score (0–100)** — how transparent and privacy-friendly the policy is
- ⚠️ **Category breakdown** (e.g., Data Sharing, User Control, Security)
- 🧾 **Specific risks** such as "sells data to third parties" or "retains data indefinitely"

Our mission: **make privacy understandable.**

---

## 🧠 How It Works

### 🧩 Architecture
User highlights policy text
        ↓
PrivaSee Chrome Extension (popup)
        ↓
→ sends text → backend API
        ↓
FastAPI / Flask backend
        ↓
→ Uses NLP heuristics + Gemini summarizer
→ Scores transparency, data risk, fairness
        ↓
Returns JSON → React popup displays results



### 🔍 Example Output
| Category | Score | Explanation |
|-----------|--------|-------------|
| Data Sharing | 40% | Mentions “partners” and “advertising use” |
| User Control | 80% | Clearly explains how to delete account |
| Security | 70% | Mentions encryption and limited access |
| **Overall Trust Score** | **65% (Medium)** | Some data sharing, moderate transparency |

---

## 🧰 Tech Stack

### Frontend (Chrome Extension)
- ⚛️ **React + Vite** (lightweight, fast build)
- 🧩 **Manifest v3** for Chrome
- 🔄 Communicates with backend via REST API
- 📦 Built into `/frontend/dist` → loaded into Chrome via `chrome://extensions`

### Backend (API)
- 🐍 **Python (FastAPI or Flask)**
- 🧠 **Gemini / LLM-powered summarizer**
- 🧮 **Custom heuristics** for detecting:
  - third-party sharing
  - retention & deletion policies
  - user rights & control
  - minors’ data and sensitive info
- 🔍 Returns structured JSON to the extension

---


## 🧑‍🤝‍🧑 Team PrivaSee
| Name | Role | Focus |
|------|------|-------|
| Akshaya S. | Frontend + Integration| API connection, + React UI |
| Sneha A. | Frontend | Chrome Extension, UI testing |
| Lineesha K. | Backend | Heuristics + Analysis |
| Rishita P. | Backend | Preferences + NLP Policy |




## 🧑‍💻 Setup Instructions

### 🔹 Clone the Repository
```bash
git clone https://github.com/lineeshakam/PrivaSee.git
cd PrivaSee

