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
    logs = []
    
    # 1. 08:00 AM Daily Briefing
    if now.hour == 8:
        today_str = now.strftime("%Y-%m-%d")
        query_payload = {
            "filter": {
                "and": [
                    {
                        "property": "Type",
                        "select": {
                            "equals": "Lecture"
                        }
                    },
                    {
                        "property": "Scheduled Date",
                        "date": {
                            "equals": today_str
                        }
                    }
                ]
            }
        }
        resp = requests.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", headers=NOTION_HEADERS, json=query_payload)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            tasks_today = []
            for r in results:
                props = r.get("properties", {})
                title = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")
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
            title = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")
            subject = props.get("Subject", {}).get("select", {}).get("name", "Unknown")
            url = props.get("Link", {}).get("url", "No Link")
            
            # Due Date parsing
            date_prop = props.get("Due Date", {}).get("date")
            if not date_prop:
                continue
            due_date_str = date_prop.get("start")
            if not due_date_str:
                continue
                
            try:
                # Notion returns dates as ISO 8601 strings. 
                # Replace Z with +00:00 for python fromisoformat
                due_date = datetime.datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                if due_date.tzinfo is None:
                    # If naive (e.g. no time provided), assume 23:59:59 IST
                    due_date = IST.localize(due_date.replace(hour=23, minute=59, second=59))
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
