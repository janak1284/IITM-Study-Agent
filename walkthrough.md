# IITM Study Agent Walkthrough

## Phase 1 & 2: Environment Setup and Curriculum Extraction

### What We Accomplished
We successfully completed the automated curriculum extraction for the IITM Portal. 
Because the portal is an Angular Single Page Application (SPA), direct HTML scraping resulted in "Link hidden/embedded" issues. To overcome this, we implemented a hybrid approach using Playwright's network interception alongside dynamic DOM interaction.

### Key Features Implemented

1. **API Interception for Clean Data**
   - The script intercepts the `/api/v2/user/course/` network requests.
   - It parses the raw JSON `outline` to extract genuine video lectures (checking for `video_type` and `video` keys), automatically filtering out non-video reading materials.
   - All extracted lectures are accurately grouped by "Week", completely ignoring unwanted sections like "Disciplinary & Non Academic Conduct".

2. **Dynamic DOM Scraping**
   - **Assignment Deadlines:** For any graded assignments found in the API, the script physically clicks into the assignment page and extracts the literal text for the due date (e.g., `Due Jun 21, 2026 11:59 PM IST`).
   - **Google Drive Folders:** The script navigates to the "Supplementary Contents" tab, clicks into "Lecture Transcripts", and extracts the exact Google Drive folder URL for the course's PDFs.

3. **Intelligent Caching System**
   - To make weekly re-runs lightning-fast, the script checks the existing `curriculum_extracted.json`. 
   - It will **not** attempt to re-scrape the DOM for Google Drive links if they are already known.
   - It will **not** click into Graded Assignments to read due dates if they have already been scraped previously.
   - It will only perform deep scraping on **brand new** weekly content.

### What Was Tested
- The scraper was successfully executed against the user's live Chrome session profile.
- We validated the extraction against three courses: `MLT`, `BDM`, and `ML Foundations`.
- The final output in [curriculum_extracted.json](file:///c:/janak/projects/IITM-Study-Agent/curriculum_extracted.json) correctly structures the subjects, weeks, filtered lectures, assignments, and Google Drive links.

> [!TIP]
> **Weekly Maintenance**
> Simply run `python phase2_extractor.py` each week. The caching logic ensures it runs incredibly quickly, only spending time on the newly released week!

### Next Steps: Phase 3
With the Google Drive URLs automatically extracted, we are ready to move on to Phase 3: the automated pipeline to download, parse (`pymupdf4llm`), and mass-summarize (`Groq`) the lecture transcripts. Ensure your `.env` file is populated with your API keys to begin!
