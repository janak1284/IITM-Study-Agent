import os
import datetime
from dotenv import load_dotenv
import requests
from flask import Flask, jsonify
import pytz

load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NOTION_API_KEY, NOTION_DATABASE_ID]):
    print("Error: Missing credentials in .env")
    exit(1)

app = Flask(__name__)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

IST = pytz.timezone('Asia/Kolkata')

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def update_notion_alert_level(page_id, level):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Alert_Level": {
                "number": level
            }
        }
    }
    requests.patch(url, headers=NOTION_HEADERS, json=payload)

@app.route('/trigger-check', methods=['GET'])
def trigger_check():
    now = datetime.datetime.now(IST)
    today_str = now.strftime("%Y-%m-%d")
    logs = []
    
    # 0. Smart Re-assign incomplete tasks
    has_more = True
    next_cursor = None
    incomplete_tasks = []
    
    # Fetch ALL incomplete tasks
    while has_more:
        query_payload = {
            "filter": {
                "property": "Status",
                "status": {
                    "does_not_equal": "Completed"
                }
            }
        }
        if next_cursor:
            query_payload["start_cursor"] = next_cursor
            
        resp = requests.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", headers=NOTION_HEADERS, json=query_payload)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            for r in results:
                props = r.get("properties", {})
                title = props.get("Title", {}).get("title", [{}])
                title_str = title[0].get("text", {}).get("content", "") if title else ""
                
                subject = props.get("Subject", {}).get("select", {})
                subject_str = subject.get("name", "") if subject else ""
                
                week = props.get("Week", {}).get("select", {})
                week_str = week.get("name", "") if week else ""
                
                due_date_str = None
                due_date_rich = props.get("Due Date", {}).get("rich_text", [])
                if due_date_rich:
                    due_date_str = due_date_rich[0].get("text", {}).get("content")
                    
                sched_date_str = None
                sched_date_obj = props.get("Scheduled Date", {}).get("date")
                if sched_date_obj:
                    sched_date_str = sched_date_obj.get("start")
                
                incomplete_tasks.append({
                    "id": r["id"],
                    "title": title_str,
                    "subject": subject_str,
                    "week": week_str,
                    "due_date_str": due_date_str,
                    "sched_date_str": sched_date_str
                })
                
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
        else:
            logs.append(f"Notion query failed for task fetching: {resp.text}")
            break
            
    if incomplete_tasks:
        import re
        def natural_sort_key(s):
            if not s:
                return []
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]
            
        # Group by subject
        subjects_tasks = {}
        for task in incomplete_tasks:
            subj = task['subject']
            if subj not in subjects_tasks:
                subjects_tasks[subj] = []
            subjects_tasks[subj].append(task)
            
        # Sort tasks within each subject using natural sort on week + title
        for subj in subjects_tasks:
            subjects_tasks[subj].sort(key=lambda x: (natural_sort_key(x['week']), natural_sort_key(x['title'])))
            
        subject_keys = list(subjects_tasks.keys())
        
        current_date = now.date()
        daily_count = {}
        MAX_PER_DAY = 4
        round_robin_idx = 0
        reassigned_count = 0
        
        while True:
            # Check if all subjects are empty
            if all(len(subjects_tasks[subj]) == 0 for subj in subject_keys):
                break
                
            subj = subject_keys[round_robin_idx % len(subject_keys)]
            round_robin_idx += 1
            
            if not subjects_tasks[subj]:
                continue
                
            task = subjects_tasks[subj].pop(0)
            
            # Find earliest available date
            search_date = current_date
            while daily_count.get(search_date.strftime("%Y-%m-%d"), 0) >= MAX_PER_DAY:
                search_date += datetime.timedelta(days=1)
                
            # Respect Due Date for assignments
            if task['due_date_str']:
                try:
                    match = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", task['due_date_str'])
                    if match:
                        due_date_obj = datetime.datetime.strptime(match.group(1), "%b %d, %Y").date()
                        # If normal schedule pushes it past the due date, force it to due date (or current date if due date passed)
                        if search_date > due_date_obj:
                            search_date = max(current_date, due_date_obj)
                except Exception:
                    pass
                    
            date_str = search_date.strftime("%Y-%m-%d")
            daily_count[date_str] = daily_count.get(date_str, 0) + 1
            
            if task['sched_date_str'] != date_str:
                update_payload = {
                    "properties": {
                        "Scheduled Date": {
                            "date": {
                                "start": date_str
                            }
                        }
                    }
                }
                update_url = f"https://api.notion.com/v1/pages/{task['id']}"
                requests.patch(update_url, headers=NOTION_HEADERS, json=update_payload)
                reassigned_count += 1
                
        if reassigned_count > 0:
            logs.append(f"Smartly re-assigned {reassigned_count} incomplete tasks starting from {current_date}.")

    # 1. 08:00 AM Daily Briefing
    if now.hour == 8:
        query_payload = {
            "filter": {
                "property": "Scheduled Date",
                "date": {
                    "equals": today_str
                }
            }
        }
        resp = requests.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", headers=NOTION_HEADERS, json=query_payload)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            tasks_today = []
            for r in results:
                props = r.get("properties", {})
                title = props.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")
                subject = props.get("Subject", {}).get("select", {}).get("name", "Unknown")
                tasks_today.append(f"- **{subject}**: {title}")
                
            if tasks_today:
                payload = "☕ *08:00 AM Tactical Brief:*\n\n" + "\n".join(tasks_today)
                send_telegram_message(payload)
                logs.append("Daily briefing sent.")
            else:
                logs.append("No tasks scheduled for today.")
        else:
            logs.append(f"Notion query failed for briefing: {resp.text}")

    # 2. Escalation Matrix for Assignments
    query_payload = {
        "filter": {
            "and": [
                {
                    "property": "Type",
                    "select": {
                        "equals": "Assignment"
                    }
                },
                {
                    "property": "Status",
                    "status": {
                        "does_not_equal": "Completed"
                    }
                }
            ]
        }
    }
    resp = requests.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", headers=NOTION_HEADERS, json=query_payload)
    if resp.status_code == 200:
        results = resp.json().get("results", [])
        for r in results:
            page_id = r["id"]
            props = r.get("properties", {})
            title = props.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")
            subject = props.get("Subject", {}).get("select", {}).get("name", "Unknown")
            url = props.get("URL", {}).get("url", "No Link")
            
            # Due Date parsing
            due_date_rich_text = props.get("Due Date", {}).get("rich_text", [])
            if not due_date_rich_text:
                continue
            due_date_str = due_date_rich_text[0].get("text", {}).get("content")
            if not due_date_str:
                continue
                
            try:
                import re
                match = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4} \d{1,2}:\d{2} [AP]M)", due_date_str)
                if match:
                    due_date = datetime.datetime.strptime(match.group(1), "%b %d, %Y %I:%M %p")
                    due_date = IST.localize(due_date)
                else:
                    continue
            except ValueError:
                continue
                
            alert_level = props.get("Alert_Level", {}).get("number")
            if alert_level is None:
                alert_level = 0
            
            time_diff = due_date - now
            hours_left = time_diff.total_seconds() / 3600
            
            # Don't alert if deadline has passed
            if hours_left < 0:
                continue
                
            new_alert_level = alert_level
            payload = None
            
            if hours_left <= 6 and alert_level < 3:
                payload = f"🚨 *CRITICAL DEADLINE (6 HOURS)* 🚨\n\n*{subject}*: {title}\nDue: {due_date.strftime('%b %d, %Y %I:%M %p')}\n[Portal Link]({url})"
                new_alert_level = 3
            elif hours_left <= 24 and alert_level < 2:
                payload = f"⚠️ *24 HOUR WARNING* ⚠️\n\n*{subject}*: {title}\nDue: {due_date.strftime('%b %d, %Y %I:%M %p')}\n[Portal Link]({url})"
                new_alert_level = 2
            elif hours_left <= 48 and alert_level < 1:
                payload = f"⏳ *48 HOUR NOTICE* ⏳\n\n*{subject}*: {title}\nDue: {due_date.strftime('%b %d, %Y %I:%M %p')}\n[Portal Link]({url})"
                new_alert_level = 1
                
            if payload:
                send_telegram_message(payload)
                update_notion_alert_level(page_id, new_alert_level)
                logs.append(f"Sent alert level {new_alert_level} for {title}")
                
    else:
        logs.append(f"Notion query failed for assignments: {resp.text}")
        
    return jsonify({"status": "success", "logs": logs, "timestamp": now.isoformat()}), 200

if __name__ == '__main__':
    # This is for local testing. PythonAnywhere will use a WSGI file to load the `app`.
    app.run(host='0.0.0.0', port=5000)
