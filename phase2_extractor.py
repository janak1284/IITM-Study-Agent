import asyncio
import json
import os
# pyrefly: ignore [missing-import]
from playwright.async_api import async_playwright

async def main():
    print("Attaching to Chrome CDP session on 127.0.0.1:9222...")
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            contexts = browser.contexts
            if not contexts:
                print("No browser context found!")
                return
            context = contexts[0]
            
            pages = context.pages
            page = pages[0] if pages else await context.new_page()
            
            # Load existing cache to avoid re-scraping
            existing_cache = {}
            if os.path.exists("curriculum_extracted.json"):
                try:
                    with open("curriculum_extracted.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for subj in data.get("subjects", []):
                            existing_cache[subj["subject_name"]] = subj
                except Exception:
                    pass
            
            subjects_data = []
            
            # Setup API interceptor
            course_responses = {}
            async def handle_response(response):
                if "api/v2/user/course/" in response.url:
                    try:
                        data = await response.json()
                        namespace = response.url.split("namespace=")[-1].split("&")[0]
                        course_responses[namespace] = data
                    except Exception:
                        pass
            
            page.on("response", handle_response)
            
            await page.goto("https://app.onlinedegree.iitm.ac.in/student_dashboard/current_courses", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            links = await page.locator("a:has-text('Go to Course Page'), a:has-text('go to course page')").evaluate_all("els => els.map(e => e.href)")
            print(f"Found {len(links)} active course links.")
            
            for link in links:
                print(f"\nNavigating to course: {link}")
                await page.goto(link, wait_until="networkidle")
                await page.wait_for_timeout(4000) 
                
                title_elem = page.locator(".top-bar-title, .course-title, h1").first
                subject_name = await title_elem.inner_text() if await title_elem.count() > 0 else "Unknown Subject"
                subject_name = subject_name.strip()
                print(f"Subject Name: {subject_name}")
                
                namespace = link.split("courses/")[-1].split("?")[0]
                course_data = course_responses.get(namespace)
                
                cached_subject = existing_cache.get(subject_name, {})
                cached_drive_url = cached_subject.get("drive_folder_url", "Not Found")
                
                cached_assignments = {}
                for w in cached_subject.get("weeks", []):
                    for ga in w.get("graded_assignments", []):
                        if ga.get("due_date") != "Check Portal":
                            cached_assignments[ga["title"]] = ga
                
                weeks = []
                
                def process_course_data(c_data):
                    if c_data and "outline" in c_data:
                        for unit in c_data["outline"]:
                            unit_title = unit.get("title", "Unknown Unit")
                            
                            # Filter out Disciplinary
                            if "Disciplinary" in unit_title:
                                continue
                                
                            lectures = []
                            graded_assignments = []
                            
                            def extract_unit_items(children):
                                for child in children:
                                    title = child.get("title", "")
                                    if child.get("type") == "L":
                                        video_id = child.get("video", "")
                                        v_type = child.get("video_type", "")
                                        
                                        if video_id and v_type != "none":
                                            url = f"https://www.youtube.com/watch?v={video_id}" if v_type == "youtube" else f"https://seek.study.iitm.ac.in/video/{video_id}"
                                            if "Activity Question" not in title and "Not Graded" not in title:
                                                lectures.append({"title": title, "url": url})
                                                
                                    elif child.get("type") == "A" and "Graded" in title and "Not Graded" not in title:
                                        graded_assignments.append({
                                            "title": title,
                                            "due_date": "Check Portal", 
                                            "url": "Available in Portal Dashboard", 
                                            "child_id": child.get("id") 
                                        })
                                        
                                    if "children" in child:
                                        extract_unit_items(child["children"])
                            
                            if "children" in unit:
                                extract_unit_items(unit["children"])
                                
                            if lectures or graded_assignments:
                                weeks.append({
                                    "week_name": unit_title,
                                    "lectures": lectures,
                                    "graded_assignments": graded_assignments
                                })

                process_course_data(course_data)
                if not weeks:
                    print("  [Warning] API payload not captured or empty. Retrying...")
                    await page.reload(wait_until="networkidle")
                    await page.wait_for_timeout(4000)
                    course_data = course_responses.get(namespace)
                    process_course_data(course_data)
                
                # --- DYNAMIC DOM EXTRACTION WITH CACHE ---
                
                assignments_to_scrape = False
                for w in weeks:
                    for ga in w["graded_assignments"]:
                        title = ga["title"]
                        if title in cached_assignments:
                            ga["due_date"] = cached_assignments[title].get("due_date", "Check Portal")
                            ga["url"] = cached_assignments[title].get("url", ga["url"])
                            del ga["child_id"] # Safe since we restored from cache
                        else:
                            assignments_to_scrape = True
                            
                if assignments_to_scrape:
                    print("  Extracting NEW Assignment Due Dates from DOM...")
                    await page.locator("button.unit-header").evaluate_all("els => els.forEach(e => { if(e.getAttribute('aria-expanded') === 'false') e.click() })")
                    await page.wait_for_timeout(2000)
                    
                    for w in weeks:
                        for ga in w["graded_assignments"]:
                            if "child_id" not in ga:
                                continue # Already cached
                            
                            title = ga["title"]
                            btn = page.locator(f"button.child-row:has-text('{title}')").first
                            if await btn.count() > 0:
                                await btn.click(force=True)
                                await page.wait_for_timeout(3000)
                                ga["url"] = page.url
                                
                                text = await page.locator("body").inner_text()
                                lines = [l.strip() for l in text.split('\n')]
                                due_str = ""
                                for i, l in enumerate(lines):
                                    if "Due " in l or "Due:" in l:
                                        due_str = l
                                        if i+1 < len(lines) and ("AM" in lines[i+1] or "PM" in lines[i+1]):
                                            due_str += " " + lines[i+1]
                                        break
                                if due_str:
                                    ga["due_date"] = due_str
                                    
                            del ga["child_id"] # Cleanup
                
                drive_link = cached_drive_url
                if drive_link == "Not Found":
                    print("  Extracting Supplementary Google Drive Folder...")
                    await page.goto(link, wait_until="networkidle")
                    await page.wait_for_timeout(4000)
                    
                    supp_tab = page.locator("text='Supplementary Content'").first
                    if await supp_tab.count() == 0:
                        supp_tab = page.locator("text='Supplementary Contents'").first
                        
                    if await supp_tab.count() > 0:
                        await supp_tab.click(force=True)
                        await page.wait_for_timeout(2000)
                        
                        transcript_elem = page.locator("text='Lecture Transcripts'").first
                        if await transcript_elem.count() > 0:
                            await transcript_elem.click(force=True)
                            await page.wait_for_timeout(3000)
                            
                        links_elems = await page.locator("a[href*='drive.google.com']").evaluate_all("els => els.map(e => e.href)")
                        if links_elems:
                            drive_link = links_elems[0]
                            print(f"    Found Drive Link: {drive_link}")
                else:
                    print(f"  Using cached Drive Link: {drive_link}")
                
                total_lectures = sum(len(w["lectures"]) for w in weeks)
                total_assignments = sum(len(w["graded_assignments"]) for w in weeks)
                print(f"  Found {total_lectures} lectures, {total_assignments} assignments.")
                
                subjects_data.append({
                    "subject_name": subject_name,
                    "drive_folder_url": drive_link or "Not Found",
                    "weeks": weeks,
                    "total_lecture_count": total_lectures
                })
            
            final_data = {"subjects": subjects_data}
            
            print("\n=== EXTRACTION COMPLETE ===")
            with open("curriculum_extracted.json", "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2)
                print("Saved results to curriculum_extracted.json")
                
        except Exception as e:
            print(f"Extraction failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
