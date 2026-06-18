# 🎓 IITM Study Agent

A zero-cost, fully autonomous Python-based agentic pipeline designed to manage the cognitive load of the IITM BS Data Science Diploma. 

This hybrid-cloud architecture automates curriculum extraction, downloads supplementary transcripts to local storage, synthesizes cohesive study guides via an LLM Map-Reduce pipeline, pushes tracking metrics directly into a mobile
-friendly Notion Dashboard, and alerts you to deadlines via a serverless Telegram webhook.

---

## 🌟 Key Features

* **Intelligent Curriculum Extractor:** Bypasses Angular DOM elements to intercept raw network requests, filtering out non-essential reading materials and extracting only the true video lectures and graded assignments.
* **Map-Reduce Llama 3 Summarizer:** Uses Groq's high-speed API to process dense, auto-generated YouTube transcripts and PDF slides. It translates Hinglish to technical English, breaks text into manageable chunks, and forces a final "Reduce" pass to build beautiful, highly-scannable Markdown files without hallucinated headers or fake assignments.
* **Deterministic LLM Scheduler:** Automatically assigns every single lecture and assignment evenly across a 7-day study week, catching any AI hallucinations with a hardcoded Python fallback to guarantee no deadline is ever dropped.
* **Notion Dashboard Sync:** Binds everything into a centralized, mobile-friendly Notion Board View. Automatically tracks completion status (Not Started, In Progress, Completed) and scheduled dates.
* **Serverless Telegram Webhook:** A 24/7 cloud-hosted Telegram bot that sends an `08:00 AM` Tactical Brief of your daily tasks, and evaluates an active Escalation Matrix to warn you `48`, `24`, and `6` hours before a deadline strikes.
* **100% Free Stack:** Designed under strict constraints to utilize absolutely zero paid services (Groq Free Tier, PythonAnywhere Free Tier, Notion Free Tier, Telegram Free API).

---

## 🏗 Architecture

The pipeline uses a **Hybrid-Cloud Execution Model**:
1. **The Heavy Lifting (Local):** Scraping the IITM portal, downloading 5MB+ PDF files (bypassing Notion's upload limits), and generating AI text is all done locally via a scheduled Orchestrator that wakes your machine, executes, and hibernates.
2. **The Active Monitor (Cloud):** The Telegram bot is a lightweight Flask API hosted on PythonAnywhere. It remains 100% stateless by reading and patching the `Alert_Level` property directly on your Notion database.

---

## 🚀 The 6-Phase Pipeline

* **Phase 1: Authentication** - Playwright intercepts and injects Google SSO tokens to bypass the IITM login portal.
* **Phase 2: Curriculum Extraction** - Dynamically extracts the weekly syllabus, Google Drive folders, and assignment portals.
* **Phase 3: Deep AI Summarization** - Converts PyMuPDF streams and YouTube Captions into pristine `.md` Obsidian notes.
* **Phase 4: Notion & Obsidian Sync** - Pushes the dynamically generated JSON study schedule to your cloud Notion workspace.
* **Phase 5: Cloud Telegram Bot** - Evaluates deadlines and pings your mobile device contextually.
* **Phase 6: Sleep Orchestrator** - Triggered by Windows Task Scheduler, this wrapper executes the pipeline and physically hibernates the hardware.

---

## 🛠 Setup & Installation

### Prerequisites
- Python 3.10+
- A Telegram Bot Token & Chat ID
- A Notion API Key & Database ID
- A Groq API Key
- A Google Drive API Key (Simple Key, no OAuth)

### 1. Environment Setup
Create a `.env` file in the root directory:
```env
TELEGRAM_BOT_TOKEN="your_token"
TELEGRAM_CHAT_ID="your_chat_id"
NOTION_API_KEY="your_notion_key"
NOTION_DATABASE_ID="your_notion_db_id"
GROQ_API_KEY="your_groq_key"
GOOGLE_DRIVE_API_KEY="your_drive_key"
```

### 2. Install Dependencies
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Deploy the Cloud Telegram Bot
1. Create a free account on [PythonAnywhere](https://www.pythonanywhere.com/).
2. Upload `phase5_telegram_bot.py` and your `.env` file to your home directory.
3. Edit the WSGI Configuration file to point to the Flask `app` object.
4. Set up an external free pinging service (like `cron-job.org`) to hit `https://your-username.pythonanywhere.com/trigger-check` every 60 minutes.

### 4. Automate the Local Orchestrator
1. Open Windows Task Scheduler.
2. Create a basic task pointing to `.\venv\Scripts\python.exe orchestrator.py`.
3. Set it to trigger at **11:00 PM on Sundays**.
4. Check **"Wake the computer to run this task"** under the Conditions tab.

---
