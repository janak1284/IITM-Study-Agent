# IITM BS Data Science - Autonomous Agentic Helper
**Architecture & Context Blueprint for AI Coding Agents**

## 1. Project Overview & Objective
This document provides the complete architectural and contextual blueprint for building an autonomous educational assistant tailored to the IIT Madras (IITM) Bachelor of Science Data Science program. 

**The Core Problem:** The user is concurrently managing a rigorous primary CSE AIML engineering degree alongside the IITM BS Data Science Diploma. The cognitive load of tracking dynamic curriculum releases, varying assignment deadlines, and retrieving lecture materials across the IITM portal is too high. 

**The Solution:** A zero-cost, Python-based agentic helper that automates curriculum extraction, downloads supplementary transcripts to local storage, filters out non-essential work, synthesizes a study schedule via LLM, and pushes AI-generated summaries and tracking metrics directly into a mobile-friendly Notion Dashboard, while managing active Telegram notifications.

---

## 2. Strict Architectural Constraints
When writing code for this project, agents MUST adhere to the following constraints:
* **Zero Cost & No Credit Cards:** The stack must rely entirely on free tiers. The Google Drive API must be accessed via a simple API Key (no OAuth 2.0 or billing account required). LLM inference will use Groq's free tier. 
* **Hybrid Storage (Notion + Local):** Notion enforces a 5MB upload limit on the free tier. Therefore, raw PDF transcripts must be stored locally on the user's hard drive. Only the AI-generated text summaries of those transcripts, along with the study schedule, are pushed to the Notion database.
* **Graded Assignments ONLY:** The user's primary CSE coursework takes priority. The agent must aggressively filter out ungraded practice work (AQs, PPAs) and focus strictly on point-earning coursework.
* **No Malpractice:** The agent is an administrative exoskeleton. It must NEVER submit assignments automatically or solve graded programming assignments. 

---

## 3. Technology Stack
* **Automation Engine:** `Playwright` + Chrome DevTools Protocol (CDP) for stealth attachment.
* **Agentic Framework:** `browser-use` (for semantic, vision-based DOM interaction).
* **Inference (Brains):** `Groq` API running open-source `Llama 3` (e.g., `llama-3.3-70b-versatile`).
* **Data Retrieval:** `Google API Python Client` (Drive REST API v3).
* **PDF Parsing:** `PyMuPDF4LLM` (for graph-based heuristic layout parsing).
* **Workspace Sync:** `notion-client` (Notion API for Python).
* **Notification Engine:** `python-telegram-bot`, `APScheduler`, and local `SQLite3`.

---

## 4. Subsystem Logic & Implementation Details

### A. Bypassing Authentication (CDP Attachment)
Do not write automated login scripts for Google SSO; they will trigger bot detection.
* **Logic:** The user will launch a native Chrome instance with `--remote-debugging-port=9222`. 
* **Agent Action:** The Python script must attach to this living browser session via a WebSocket. The script assumes it is already inside a pre-authenticated perimeter on `seek.study.iitm.ac.in`.

### B. Agentic Scraping & Graded Filter Prompt
The IITM portal DOM mutates frequently. Do not use hardcoded CSS/XPath selectors. Rely on `browser-use` with the following system instructions:
* **Agent Prompt Directive:** "Scan the course dashboard for assignment modules. Explicitly ignore any module containing the text string 'Not Graded'. Locate tabs named 'Graded Assignment X' or assignments that lack a 'Not Graded' designation. Click into these specific modules, scan the top right corner of the page for the due date, and extract that temporal metadata. Count the interactable elements prefixed with 'L' (e.g., 'L1.1') and capture the direct `seek.study.iitm.ac.in` URL from the embedded player. Ignore all Activity Questions (AQs) or Practice Programming Assignments (PPAs)."

### C. Mass Transcript Pipeline & Summarization
* **Data Retrieval:** Use the official Drive REST API v3 (`files.list` and `files.get_media`) with chunked binary retrieval (`io.BytesIO`) to download PDFs locally.
* **Parsing:** Pass downloaded PDFs to `pymupdf4llm.to_markdown()`.
* **Summarization:** Pass the parsed Markdown chunks into the Groq Llama 3 API with a map-reduce prompt to generate concise, high-density text summaries of the lectures. 

### D. LLM Scheduling & Comprehensive Notion Dashboard
* **Scheduling:** Groq calculates an optimal study distribution across the week.
* **Notion Syncing:** The Python script utilizes the Notion API to create/update a Master Tracking Database. 
* **Required Notion Database Schema:**
    * `Task Title` (Title property): e.g., "Day 1: L1.1 Machine Learning"
    * `Subject` (Select property): Maps the specific course (e.g., "Machine Learning Foundations", "Tools in Data Science").
    * `Type` (Select property): "Lecture" or "Graded Assignment".
    * `Status` (Status property): Strict pipeline including "Not Started", "Summary Read", "Video Watched", "Completed".
    * `Due Date` (Date property): Only populated for assignments.
    * `Portal Link` (URL property): Direct link to the exact video/assignment on the IITM portal.
    * `Page Body`: Injects the AI-generated lecture summary directly into the Notion page content for mobile review.

### E. Telegram Notification Pipeline
* **Logic:** The notification queue is stored in SQLite. A localized cron job polls this database.
* **Daily Brief:** At 08:00 AM, push the day's study checklist with direct video links.
* **Escalation Alerts:** Cross-reference the database for Graded Assignment deadlines. Dispatch mandatory alert payloads to the Telegram API at exactly `T-minus 48 hours`, `24 hours`, and `6 hours`.

---

## 5. The 5-Day Build Plan
When iterating with the user, follow this sequence:
* **Day 1:** Set up the CDP Playwright attachment script. Achieve seamless connection to the pre-authenticated portal.
* **Day 2:** Deploy `browser-use`, inject the Graded Assignment filter prompt, and successfully output the normalized curriculum JSON.
* **Day 3:** Build the Google Drive API v3 paginated extraction pipeline. Integrate `PyMuPDF4LLM` for Markdown conversion, and pass it to Groq for summarization.
* **Day 4:** Set up the Notion API integration. Build the Python payload to construct the comprehensive multi-subject Tracking Dashboard and inject the AI summaries into the Notion pages.
* **Day 5:** Spin up the SQLite database, configure the Telegram bot, and set up `APScheduler` for the escalation alerts. Conduct end-to-end testing.
