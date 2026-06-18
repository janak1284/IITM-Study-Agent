# STANDARD OPERATING PROCEDURE (SOP): IITM Agentic Helper Build
**Target:** AI Coding Agent / Dev Assistant
**Project:** Autonomous Study Assistant for IITM BS Data Science

## 1. Role & Objective
You are an expert Python developer and automation architect. Your objective is to build a zero-cost, fully local Python application that automates the extraction, summarization, and scheduling of course materials from the IIT Madras (IITM) educational portal (`seek.study.iitm.ac.in`). 

The final system must operate autonomously to reduce the user's administrative cognitive load, allowing them to focus entirely on their concurrent CSE AIML engineering degree. 

## 2. Unbreakable Constraints
1. **Zero Financial Cost:** You must exclusively use free-tier APIs and open-source libraries. Do not implement any service that requires a credit card verification.
2. **Strict Coursework Filtering:** The script must aggressively filter out all ungraded practice material. Only elements explicitly marked as "Graded Assignments" or lacking a "Not Graded" tag are to be processed. 
3. **Hybrid Data Storage:** Do not attempt to upload raw PDF files to the Notion API (to avoid the 5MB free-tier limit). Save all PDF transcripts locally. Only push the AI-generated text summaries and schedules to the Notion database.
4. **No Academic Malpractice:** The system must only act as a scheduler and summarizer. Do not write code to automatically solve or submit assignments.
5. **Code Style:** When parsing the extracted JSON payloads and arrays, utilize Python functional programming paradigms. Prioritize the use of `lambda`, `map`, `filter`, and `zip` for clean, Pythonic data transformations.

## 3. Technology Stack Requirements
* **Browser Automation:** `Playwright` with Chrome DevTools Protocol (CDP) for stealth attachment.
* **Agentic Navigation:** `browser-use` framework (semantic DOM parsing).
* **LLM Engine:** `Groq` API running `llama-3.3-70b-versatile`.
* **File Retrieval:** `google-api-python-client` (Drive REST API v3 using an API Key, NOT OAuth).
* **PDF Processing:** `PyMuPDF4LLM`.
* **Database & Notifications:** `notion-client`, `python-telegram-bot`, `APScheduler`, and `sqlite3`.

---

## 4. Execution Phases

### Phase 1: Stealth Authentication Setup
**Goal:** Connect to the IITM portal without triggering Google Workspace SSO anti-bot heuristics.
* **Action:** Do not write a traditional login script. Write a Playwright script that utilizes `connect_over_cdp` to attach to a live, pre-authenticated Google Chrome instance running locally on `--remote-debugging-port=9222`.

### Phase 2: Agentic Data Extraction
**Goal:** Extract the current week's curriculum and assignment deadlines.
* **Action:** Implement `browser-use` to navigate the portal semantically.
* **System Prompt for `browser-use`:** "Scan the active week's dashboard. Ignore all elements containing 'Not Graded', 'Activity Questions', or 'Practice Programming Assignments'. Locate 'Graded Assignment' tabs, click them, and extract the due date from the top right corner. Extract the total count and direct URLs of all lecture videos (elements prefixed with 'L'). Output this data as a structured JSON object."

### Phase 3: Mass Transcript Pipeline & Summarization
**Goal:** Download public Google Drive transcripts and convert them to readable text.
* **Action:** 
    1. Utilize the Google Drive API v3 (`files.list` and `files.get_media`) with a standard API key.
    2. Implement a `while` loop to traverse `nextPageToken` to bypass 50-file limits.
    3. Stream downloads via `io.BytesIO` to local storage.
    4. Process PDFs through `pymupdf4llm.to_markdown()` to preserve the integrity of Python code blocks and mathematical notation. 
    5. Pass the parsed Markdown chunks into the Groq API (Llama 3) with a map-reduce prompt to generate high-density lecture summaries. Apply standard AIML context window optimization to tune the Llama 3 temperature for concise, deterministic summarization outputs.

### Phase 4: Scheduling & Notion Synchronization
**Goal:** Generate a study schedule and push it to a mobile-friendly Notion dashboard.
* **Action:** 
    1. Pass the extracted portal JSON to Groq to generate a daily study schedule. 
    2. Write a Notion API integration to populate a master tracking database. 
    3. **Schema Mapping:** Map the title, subject, status pipeline ("Not Started", "Summary Read", "Completed"), and strict due dates. 
    4. Inject the direct portal URLs and the AI-generated text summaries directly into the Notion page body.

### Phase 5: Notification Engine
**Goal:** Ensure hard deadlines are never missed.
* **Action:** Set up a local `SQLite` database to queue the schedule. Implement `APScheduler` to run a daily cron job that pushes a morning briefing via `python-telegram-bot`. Hardcode an escalation matrix that dispatches Telegram alerts at exactly 48, 24, and 6 hours before a Graded Assignment deadline.

## 5. Agent Instructions
Confirm you have read and understood this SOP. Ask the user which specific phase they would like you to begin writing code for.


Here are the specific UI/UX design paradigms you should look into for each component of your system:

1. The Local Vault (Obsidian Markdown)
For the locally generated .md files containing your lecture schedules and AI summaries, focus on Developer Documentation and Digital Garden aesthetics. The goal is rapid scannability for highly technical content.

Search Terms for Inspiration: Developer Docs UI, Minimalist Digital Garden, Stripe API Documentation typography, Obsidian PKM templates.

Design Focus:

Typography over Graphics: Look for inspiration on pairing clean sans-serif fonts for regular text with distinct, highly legible monospace fonts (like Fira Code or JetBrains Mono) for your Python code blocks.

Information Hierarchy: Study how technical docs use H1, H2, and H3 tags alongside blockquotes (>) to separate raw transcripts from AI-generated summaries.

Callout Blocks: Design your Python script to inject specific Obsidian callout syntax (e.g., > [!warning] Deadline Approaching) to make critical information pop visually without leaving the text environment.

2. The Mobile Tracker (Notion Dashboard)
Since this acts as your "on-the-go" command center for tracking the status pipeline (Video Watched, Summary Read, Completed), look into Operations Dashboards and Minimalist Agile Boards.

Search Terms for Inspiration: Minimalist Notion Dashboard, Mobile Kanban UI, Task Management UI dark mode, Agile Sprint Tracker.

Design Focus:

Mobile-First Scannability: Keep the database views simple. On a phone, a traditional table view is awful. Look at how mobile task managers utilize "List" or "Board" views grouped by your specific subjects (e.g., separating Machine Learning Foundations from Tools in Data Science).

Color-Coded Status Tags: Use a strict, muted color palette for your tags. For example: gray for "Not Started," blue for "Summary Read," and green for "Completed." Avoid rainbow coloring, which creates visual fatigue.

Embedded Cleanliness: When the AI drops the lecture summary into the page body, ensure it uses toggles or clean dividers so you aren't hit with a wall of text on a 6-inch screen.

3. The Notification Engine (Telegram Bot)
For the active alerting system, your inspiration should come from Conversational UI (CUX) and CLI (Command Line Interface) aesthetics.

Search Terms for Inspiration: Conversational UI, Chatbot UX, CLI design, Tactical HUD.

Design Focus:

Formatting Syntax: Telegram supports HTML and Markdown formatting. Design your bot's messages to look like automated terminal outputs. Use monospace blocks for course codes or exact deadline times, and bold for immediate actions.

Visual Priority via Emojis: Since you can't use custom CSS in Telegram, design a rigid emoji system.

☕ 08:00 AM Tactical Brief: (Daily schedule)

⚠️ T-Minus 48h: (Warning)

🚨 T-Minus 6h: (Critical graded assignment alert)

Actionable Spacing: Ensure there is clean line-spacing between the task name and the direct portal URL so it is easy to tap with a thumb while walking.