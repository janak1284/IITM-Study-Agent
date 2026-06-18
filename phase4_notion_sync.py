import json
import os
import time
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
notion_api_key = os.environ.get("NOTION_API_KEY")
database_id = os.environ.get("NOTION_DATABASE_ID")

if not notion_api_key or not database_id:
    print("Error: NOTION_API_KEY or NOTION_DATABASE_ID missing from .env")
    exit(1)

notion = Client(auth=notion_api_key)

import requests

def get_existing_pages():
    print("Fetching existing Notion database entries...")
    existing = set()
    has_more = True
    next_cursor = None
    
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
            json=payload
        )
        if resp.status_code != 200:
            print("Error querying database:", resp.text)
            break
            
        data = resp.json()
        for page in data.get("results", []):
            try:
                title = page["properties"]["Title"]["title"][0]["text"]["content"]
                existing.add(title)
            except (KeyError, IndexError):
                pass
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
    return existing

def parse_md_to_notion(markdown_text):
    """Translates strictly formatted Markdown into Notion JSON blocks."""
    blocks = []
    in_code_block = False
    code_content = ""

    for line in markdown_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Handle Python Code Fences
        if line.startswith('```'):
            if in_code_block:
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": code_content.strip()}}], 
                        "language": "python"
                    }
                })
                in_code_block = False
                code_content = ""
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_content += line + "\n"
            continue

        # Handle H2 Headers
        if line.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": line[3:]}}]}
            })
        # Handle Bullet Points
        elif line.startswith('- ') or line.startswith('* '):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": line[2:]}}]}
            })
        # Handle Standard Paragraph Text
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": line}}]}
            })
            
    return blocks

def push_to_notion(item_type, title, subject, week, url, due_date=None, scheduled_date=None, summary_text=None):
    properties = {
        "Title": {"title": [{"text": {"content": title}}]},
        "Type": {"select": {"name": item_type}},
        "Subject": {"select": {"name": subject}},
        "Week": {"select": {"name": week}},
        "Status": {"status": {"name": "Not Started"}}
    }
    
    if url and url != "Not Found":
        properties["URL"] = {"url": url}
        
    if due_date:
        properties["Due Date"] = {"rich_text": [{"text": {"content": due_date}}]}
        
    if scheduled_date:
        properties["Scheduled Date"] = {"date": {"start": scheduled_date}}
        
    children = []
    if summary_text:
        children = parse_md_to_notion(summary_text)
        
    try:
        notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=children[:100] # Notion limits to 100 blocks per request
        )
        print(f"  [Success] Pushed to Notion: {title}")
    except Exception as e:
        print(f"  [Error] Failed to push {title}: {e}")

def main():
    if not os.path.exists("curriculum_extracted.json"):
        print("No curriculum_extracted.json found.")
        return
        
    with open("curriculum_extracted.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Load Schedule Mapping
    schedule_map = {}
    if os.path.exists("weekly_study_schedule.json"):
        with open("weekly_study_schedule.json", "r", encoding="utf-8") as f:
            sched_data = json.load(f)
            for item in sched_data.get("schedule", []):
                # Map by item title to date
                schedule_map[item["item_title"]] = item["date"]
                
    existing_titles = get_existing_pages()
    
    for subject in data.get("subjects", []):
        subject_name = subject["subject_name"]
        print(f"\n=== Syncing {subject_name} to Notion ===")
        
        summaries_dir = os.path.join("summaries", subject_name.replace(":", ""))
        
        for week in subject.get("weeks", []):
            week_name = week["week_name"]
            
            # Sync Lectures
            for lecture in week.get("lectures", []):
                title = lecture["title"]
                if title in existing_titles:
                    print(f"  [Skip] {title} already in Notion.")
                    continue
                    
                safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in ' ._-']).rstrip()
                summary_file = os.path.join(summaries_dir, week_name, f"{safe_title}.md")
                
                summary_text = None
                if os.path.exists(summary_file):
                    with open(summary_file, "r", encoding="utf-8") as sf:
                        summary_text = sf.read()
                        
                scheduled_date = schedule_map.get(title)
                push_to_notion("Lecture", title, subject_name, week_name, lecture["url"], scheduled_date=scheduled_date, summary_text=summary_text)
                time.sleep(0.5) # Rate limit protection
                
            # Sync Assignments
            for assignment in week.get("graded_assignments", []):
                title = assignment["title"]
                if title in existing_titles:
                    print(f"  [Skip] {title} already in Notion.")
                    continue
                scheduled_date = schedule_map.get(title)
                push_to_notion("Assignment", title, subject_name, week_name, assignment["url"], due_date=assignment.get("due_date"), scheduled_date=scheduled_date)
                time.sleep(0.5)

if __name__ == "__main__":
    main()
