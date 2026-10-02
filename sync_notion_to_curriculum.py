#!/usr/bin/env python3
"""
sync_notion_to_curriculum.py

Pulls the full curriculum (Weeks 1 to 4) directly from the Notion database
and updates `curriculum_extracted.json` so that all 4 weeks are available locally
for generating study prompts or schedule building.
"""

import json
import os
import requests
from dotenv import load_dotenv

def main():
    load_dotenv()
    notion_api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    if not notion_api_key or not database_id:
        print("Error: NOTION_API_KEY or NOTION_DATABASE_ID missing from .env")
        return

    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    print("Fetching all entries from Notion database...")
    results = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
            json=payload,
            timeout=20
        )
        if resp.status_code != 200:
            print("Error querying database:", resp.text)
            break
            
        data = resp.json()
        results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    # Group by subject -> week -> items
    subjects_map = {}

    # Load existing drive urls if available
    existing_drive_urls = {}
    if os.path.exists("curriculum_extracted.json"):
        try:
            with open("curriculum_extracted.json", "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for s in old_data.get("subjects", []):
                    existing_drive_urls[s["subject_name"]] = s.get("drive_folder_url", "Not Found")
        except Exception:
            pass

    for page in results:
        props = page.get("properties", {})
        
        # Title
        title_list = props.get("Title", {}).get("title", [])
        if not title_list:
            continue
        title = title_list[0]["text"]["content"].strip()

        # Subject
        subj_obj = props.get("Subject", {}).get("select")
        subject_name = subj_obj.get("name", "").strip() if subj_obj else "Unknown Course"
        if not subject_name or subject_name == "Unknown Course":
            continue

        # Week
        week_obj = props.get("Week", {}).get("select")
        week_name = week_obj.get("name", "").strip() if week_obj else "Week 1"

        # Type
        type_obj = props.get("Type", {}).get("select")
        item_type = type_obj.get("name", "").strip() if type_obj else "Lecture"

        # URL
        url = props.get("URL", {}).get("url") or ""

        if subject_name not in subjects_map:
            subjects_map[subject_name] = {}
        if week_name not in subjects_map[subject_name]:
            subjects_map[subject_name][week_name] = {"lectures": [], "graded_assignments": []}

        if item_type == "Lecture":
            subjects_map[subject_name][week_name]["lectures"].append({"title": title, "url": url})
        elif item_type == "Assignment":
            subjects_map[subject_name][week_name]["graded_assignments"].append({
                "title": title,
                "due_date": "Check Portal",
                "url": url
            })

    # Sort weeks properly (Week 1, Week 2, Week 3, Week 4, etc.)
    def week_sort_key(w_name):
        num_part = "".join([c for c in w_name if c.isdigit()])
        return int(num_part) if num_part else 99

    # Build final curriculum JSON structure
    subjects_list = []
    for subj_name in sorted(subjects_map.keys()):
        weeks_list = []
        total_lectures = 0

        for w_name in sorted(subjects_map[subj_name].keys(), key=week_sort_key):
            # Sort lectures by title (or preserve logical number ordering)
            def lec_sort_key(lec):
                # Try sorting by leading numbers like '1.2' or 'L3.1'
                t = lec["title"]
                parts = []
                for token in t.replace("L", "").replace("AQ", "").split()[:2]:
                    for p in token.split("."):
                        if p.isdigit():
                            parts.append(int(p))
                return parts if parts else [999]

            lectures = sorted(subjects_map[subj_name][w_name]["lectures"], key=lec_sort_key)
            assignments = subjects_map[subj_name][w_name]["graded_assignments"]
            total_lectures += len(lectures)

            weeks_list.append({
                "week_name": w_name,
                "lectures": lectures,
                "graded_assignments": assignments
            })

        subjects_list.append({
            "subject_name": subj_name,
            "drive_folder_url": existing_drive_urls.get(subj_name, "Not Found"),
            "weeks": weeks_list,
            "total_lecture_count": total_lectures
        })

    final_payload = {"subjects": subjects_list}

    with open("curriculum_extracted.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2)

    print(f"Successfully synced {len(subjects_list)} subjects (including Weeks 1 to 4) from Notion into `curriculum_extracted.json`!")

if __name__ == "__main__":
    main()
