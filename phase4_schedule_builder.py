import os
import json
import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
groq_api_key = os.environ.get("GROQ_API_KEY")

if not groq_api_key:
    print("Error: GROQ_API_KEY missing from .env")
    exit(1)

client = Groq(api_key=groq_api_key)

def build_schedule():
    if not os.path.exists("curriculum_extracted.json"):
        print("No curriculum_extracted.json found.")
        return
        
    with open("curriculum_extracted.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Get current week's dates
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday()) # Monday
    week_dates = [(start_of_week + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    prompt = f"""
You are an expert study scheduler for a student taking IITM online courses.
Here is the curriculum extracted for this week:
{json.dumps(data)}

The 7 days of this week are: {', '.join(week_dates)}.
Please create a balanced study schedule that assigns EVERY single item (including all lectures, all tutorials, and all graded assignments) from the JSON to a specific date from this week. Do NOT schedule more than 4 items per day. Group related items together if possible.

Your output MUST be ONLY valid JSON matching this schema exactly:
{{
    "schedule": [
        {{
            "date": "YYYY-MM-DD",
            "subject": "May 2026 - MLT",
            "item_title": "1.1 Introduction to Machine Learning",
            "url": "https://www.youtube.com/watch?v=..."
        }}
    ]
}}
Return ONLY JSON. Do not include markdown codeblocks or any conversational text.
"""

    print("Requesting study schedule from Groq...")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        response_content = completion.choices[0].message.content
        schedule_json = json.loads(response_content)
        
        # Fallback: Check if Llama 3 hallucinated and dropped any items
        scheduled_titles = [item.get("item_title") for item in schedule_json.get("schedule", [])]
        last_day = week_dates[-1] # Sunday
        
        for subject in data.get("subjects", []):
            subj_name = subject["subject_name"]
            for week in subject.get("weeks", []):
                # Check lectures
                for lecture in week.get("lectures", []):
                    if lecture["title"] not in scheduled_titles:
                        schedule_json["schedule"].append({
                            "date": last_day,
                            "subject": subj_name,
                            "item_title": lecture["title"],
                            "url": lecture["url"]
                        })
                # Check assignments
                for assignment in week.get("graded_assignments", []):
                    if assignment["title"] not in scheduled_titles:
                        schedule_json["schedule"].append({
                            "date": last_day,
                            "subject": subj_name,
                            "item_title": assignment["title"],
                            "url": assignment["url"]
                        })
        
        with open("weekly_study_schedule.json", "w", encoding="utf-8") as f:
            json.dump(schedule_json, f, indent=4)
            
        # Create a markdown version for obsidian/telegram
        with open("weekly_study_schedule.md", "w", encoding="utf-8") as md_file:
            md_file.write("# Weekly Study Schedule\n\n")
            
            # Group by date
            by_date = {}
            for item in schedule_json.get("schedule", []):
                d = item["date"]
                by_date.setdefault(d, []).append(item)
                
            for d in sorted(by_date.keys()):
                md_file.write(f"## {d}\n")
                for item in by_date[d]:
                    md_file.write(f"- **{item['subject']}**: {item['item_title']}\n")
                md_file.write("\n")
                
        print("Successfully generated weekly_study_schedule.json and weekly_study_schedule.md")
    except Exception as e:
        print(f"Failed to generate schedule: {e}")

if __name__ == "__main__":
    build_schedule()
