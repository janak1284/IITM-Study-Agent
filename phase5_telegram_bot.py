import os
import datetime
from dotenv import load_dotenv
import requests
from flask import Flask, jsonify, request
import pytz
from groq import Groq

load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NOTION_API_KEY, NOTION_DATABASE_ID]):
    print("Error: Missing credentials in .env")
    exit(1)

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

app = Flask(__name__)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

session = requests.Session()
session.headers.update(NOTION_HEADERS)

IST = pytz.timezone('Asia/Kolkata')

def send_telegram_message(message, chat_id=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id or TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            # If Markdown parsing fails due to special characters, send as plain text
            payload.pop("parse_mode", None)
            requests.post(url, json=payload, timeout=10)
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
    try:
        session.patch(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to update alert level for {page_id}: {e}")

@app.route('/trigger-check', methods=['GET'])
def trigger_check():
    import time
    import re
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
            
        try:
            resp = session.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", json=query_payload, timeout=15)
        except Exception as e:
            logs.append(f"Notion query exception for task fetching: {e}")
            break
            
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
        MAX_PATCHES_PER_RUN = 10 # Batch limit to ensure /trigger-check never exceeds web worker timeouts right at midnight (12:00 AM) when date boundaries shift
        
        while True:
            # Check if all subjects are empty or batch update cap reached
            if all(len(subjects_tasks[subj]) == 0 for subj in subject_keys) or reassigned_count >= MAX_PATCHES_PER_RUN:
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
                try:
                    time.sleep(0.3) # Rate limit protection for Notion API
                    patch_resp = session.patch(update_url, json=update_payload, timeout=10)
                    if patch_resp.status_code == 429:
                        time.sleep(2.0)
                        patch_resp = session.patch(update_url, json=update_payload, timeout=10)
                    if patch_resp.status_code == 200:
                        reassigned_count += 1
                    else:
                        logs.append(f"Failed to patch {task['title']}: {patch_resp.status_code}")
                except Exception as e:
                    logs.append(f"Exception patching {task['title']}: {e}")
                
        if reassigned_count > 0:
            logs.append(f"Smartly re-assigned {reassigned_count} incomplete tasks starting from {current_date}.")

    # 1. 08:00 AM Daily Briefing
    if now.hour == 8:
        query_payload = {
            "filter": {
                "and": [
                    {
                        "property": "Scheduled Date",
                        "date": {
                            "equals": today_str
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
        try:
            resp = session.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", json=query_payload, timeout=15)
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
        except Exception as e:
            logs.append(f"Exception querying briefing: {e}")

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
    try:
        resp = session.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", json=query_payload, timeout=15)
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
    except Exception as e:
        logs.append(f"Exception querying assignments: {e}")
        
    # 3. Adaptive Check-Ins & Proactive Burnout Protection
    if now.hour == 18 or now.hour == 22:
        query_payload = {
            "filter": {
                "property": "Scheduled Date",
                "date": {
                    "equals": today_str
                }
            }
        }
        try:
            resp = session.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", json=query_payload, timeout=15)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                total_today = len(results)
                completed_today = 0
                incomplete_titles = []
                for r in results:
                    props = r.get("properties", {})
                    status_str = props.get("Status", {}).get("status", {}).get("name", "")
                    title = props.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")
                    if status_str == "Completed":
                        completed_today += 1
                    else:
                        incomplete_titles.append(title)
                
                if now.hour == 18 and total_today > 0 and completed_today == 0:
                    msg = (f"⏳ *06:00 PM Check-In:*\n\nHey Janak! You have {len(incomplete_titles)} tasks scheduled for today and none marked completed yet.\n\n"
                           f"Want to knock out just 1 tonight?\n`{', '.join(incomplete_titles[:3])}`\n\n"
                           f"💡 *Tip:* If you're swamped today, reply `/snooze <keyword>` to shift a task to tomorrow!")
                    send_telegram_message(msg)
                    logs.append("6 PM adaptive check-in sent.")
                elif now.hour == 22 and total_today > 0:
                    if completed_today == total_today:
                        msg = f"🔥 *10:00 PM Daily Retrospective:*\n\nIncredible job! You completed all **{completed_today}/{total_today}** of your tasks today. You're 100% on track for this week's goals. Rest up well!"
                    else:
                        msg = (f"🌙 *10:00 PM Daily Retrospective:*\n\nYou completed **{completed_today}/{total_today}** of today's tasks.\n\n"
                               f"Any remaining items (`{', '.join(incomplete_titles[:3])}`) will be automatically rebalanced to upcoming slots at midnight by your Smart Rebalancer. Great effort today!")
                    send_telegram_message(msg)
                    logs.append("10 PM daily retrospective sent.")
        except Exception as e:
            logs.append(f"Exception querying check-in/retrospective: {e}")

    return jsonify({"status": "success", "logs": logs, "timestamp": now.isoformat()}), 200

def find_notion_tasks_by_keyword(keyword, only_pending=True):
    query_payload = {"page_size": 100}
    if only_pending:
        query_payload["filter"] = {
            "property": "Status",
            "status": {
                "does_not_equal": "Completed"
            }
        }
    try:
        has_more = True
        next_cursor = None
        results = []
        while has_more:
            if next_cursor:
                query_payload["start_cursor"] = next_cursor
            resp = session.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", json=query_payload, timeout=15)
            if resp.status_code != 200:
                break
            data = resp.json()
            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        matches = []
        kw_lower = keyword.lower().strip()
        kw_clean = kw_lower.replace(":", " ").replace("-", " ")
        
        for r in results:
            props = r.get("properties", {})
            title = props.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")
            subject = props.get("Subject", {}).get("select", {})
            subject_str = subject.get("name", "Unknown") if subject else "Unknown"
            url = props.get("URL", {}).get("url", "No Link")
            
            full_str = f"{subject_str}: {title}".lower()
            full_str_clean = f"{subject_str} {title}".lower().replace(":", " ").replace("-", " ")
            
            if (kw_lower == title.lower() or 
                kw_lower in title.lower() or 
                (kw_lower == subject_str.lower()) or 
                kw_lower in full_str or 
                all(token in full_str_clean.split() for token in kw_clean.split() if token)):
                matches.append({
                    "id": r["id"],
                    "title": title,
                    "subject": subject_str,
                    "url": url,
                    "full_name": f"{subject_str}: {title}"
                })
        return matches
    except Exception as e:
        print(f"Error finding tasks by keyword: {e}")
        return []

def get_today_pending_tasks():
    today_str = datetime.datetime.now(IST).strftime("%Y-%m-%d")
    query_payload = {
        "filter": {
            "and": [
                {
                    "property": "Scheduled Date",
                    "date": {
                        "equals": today_str
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
    try:
        resp = session.post(f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query", json=query_payload, timeout=15)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            tasks = []
            for r in results:
                props = r.get("properties", {})
                title = props.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")
                subject = props.get("Subject", {}).get("select", {})
                subject_str = subject.get("name", "Unknown") if subject else "Unknown"
                url = props.get("URL", {}).get("url", "")
                tasks.append({"title": title, "subject": subject_str, "url": url})
            return tasks
    except Exception as e:
        print(f"Error fetching today pending: {e}")
    return []

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"status": "ignored"}), 200
        
    message = data["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    
    if not text or not chat_id:
        return jsonify({"status": "ignored"}), 200

    # Command: /help or /start
    if text.startswith("/help") or text.startswith("/start"):
        help_msg = (
            "🎓 *IITM Study Agent Copilot Commands:*\n\n"
            "📋 `/today` - View pending tasks for today\n"
            "✅ `/done <keyword>` - Mark a task as completed (e.g. `/done L1.3`)\n"
            "💤 `/snooze <keyword>` - Shift a task to tomorrow (e.g. `/snooze L1.5`)\n"
            "📖 `/summary <keyword>` - Get a crisp 5-bullet executive summary of a lecture topic\n"
            "🎯 `/quiz <subject>` - Generate a 3-question practice MCQ quiz (e.g. `/quiz MLT`)\n"
            "🧠 `/ask <question>` - Ask any question to your 24/7 AI Tutor (or just type a question mark `?` or chat naturally!)"
        )
        send_telegram_message(help_msg, chat_id=chat_id)
        return jsonify({"status": "success"}), 200

    # Command: /today or /pending
    if text.startswith("/today") or text.startswith("/pending"):
        tasks = get_today_pending_tasks()
        if tasks:
            lines = []
            for t in tasks:
                link_part = f" [Portal Link]({t['url']})" if t['url'] and t['url'] != "Not Found" else ""
                lines.append(f"- **{t['subject']}**: {t['title']}{link_part}")
            send_telegram_message("📋 *Today's Pending Tasks:*\n\n" + "\n".join(lines), chat_id=chat_id)
        else:
            send_telegram_message("🎉 *All Clear!* No pending tasks scheduled for today. You're ahead of the schedule!", chat_id=chat_id)
        return jsonify({"status": "success"}), 200

    # Command: /done <keyword>
    if text.startswith("/done"):
        keyword = text[5:].strip()
        if not keyword:
            send_telegram_message("⚠️ Please provide a task keyword, e.g., `/done L1.3` or `/done Regression`.", chat_id=chat_id)
            return jsonify({"status": "success"}), 200
            
        matches = find_notion_tasks_by_keyword(keyword, only_pending=True)
        if not matches:
            send_telegram_message(f"❌ No pending task found matching `{keyword}`. Type `/today` to see your active tasks.", chat_id=chat_id)
        else:
            exact_matches = [m for m in matches if m["title"].lower().strip() == keyword.lower().strip() or m.get("full_name", "").lower().strip() == keyword.lower().strip()]
            if len(matches) > 1 and not exact_matches:
                match_titles = [f"- **{m['subject']}**: `{m['title']}`" for m in matches[:5]]
                send_telegram_message(f"⚠️ Multiple pending tasks matched `{keyword}`:\n\n" + "\n".join(match_titles) + "\n\nPlease be more specific (e.g. `/done L1.3`).", chat_id=chat_id)
            else:
                target = exact_matches[0] if exact_matches else matches[0]
                patch_url = f"https://api.notion.com/v1/pages/{target['id']}"
                patch_payload = {"properties": {"Status": {"status": {"name": "Completed"}}}}
                try:
                    resp = session.patch(patch_url, json=patch_payload, timeout=10)
                    if resp.status_code == 200:
                        send_telegram_message(f"✅ *Task Completed!*\n\nMarked **{target['title']}** ({target['subject']}) as Completed in Notion!", chat_id=chat_id)
                    else:
                        send_telegram_message(f"❌ Failed to update Notion: {resp.status_code}", chat_id=chat_id)
                except Exception as e:
                    send_telegram_message(f"❌ Error communicating with Notion API: {e}", chat_id=chat_id)
        return jsonify({"status": "success"}), 200

    # Command: /snooze <keyword> or /postpone <keyword>
    if text.startswith("/snooze") or text.startswith("/postpone"):
        keyword = text.split(" ", 1)[1].strip() if " " in text else ""
        if not keyword:
            send_telegram_message("⚠️ Please provide a task keyword, e.g., `/snooze L1.5`.", chat_id=chat_id)
            return jsonify({"status": "success"}), 200
            
        matches = find_notion_tasks_by_keyword(keyword, only_pending=True)
        if not matches:
            send_telegram_message(f"❌ No pending task found matching `{keyword}`.", chat_id=chat_id)
        else:
            exact_matches = [m for m in matches if m["title"].lower().strip() == keyword.lower().strip() or m.get("full_name", "").lower().strip() == keyword.lower().strip()]
            if len(matches) > 1 and not exact_matches:
                match_titles = [f"- **{m['subject']}**: `{m['title']}`" for m in matches[:5]]
                send_telegram_message(f"⚠️ Multiple pending tasks matched `{keyword}`:\n\n" + "\n".join(match_titles) + "\n\nPlease be more specific.", chat_id=chat_id)
            else:
                target = exact_matches[0] if exact_matches else matches[0]
                tomorrow_str = (datetime.datetime.now(IST).date() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                patch_url = f"https://api.notion.com/v1/pages/{target['id']}"
                patch_payload = {"properties": {"Scheduled Date": {"date": {"start": tomorrow_str}}}}
                try:
                    resp = session.patch(patch_url, json=patch_payload, timeout=10)
                    if resp.status_code == 200:
                        send_telegram_message(f"💤 *Task Snoozed!*\n\nMoved **{target['title']}** ({target['subject']}) to tomorrow (`{tomorrow_str}`).", chat_id=chat_id)
                    else:
                        send_telegram_message(f"❌ Failed to snooze task in Notion: {resp.status_code}", chat_id=chat_id)
                except Exception as e:
                    send_telegram_message(f"❌ Error communicating with Notion API: {e}", chat_id=chat_id)
        return jsonify({"status": "success"}), 200

    # Command: /summary <keyword>
    if text.startswith("/summary"):
        keyword = text.split(" ", 1)[1].strip() if " " in text else ""
        if not keyword:
            send_telegram_message("⚠️ Please provide a lecture/topic keyword, e.g., `/summary L1.3` or `/summary Regression`.", chat_id=chat_id)
            return jsonify({"status": "success"}), 200
            
        if not groq_client:
            send_telegram_message("❌ Groq API key not configured.", chat_id=chat_id)
            return jsonify({"status": "success"}), 200
            
        matches = find_notion_tasks_by_keyword(keyword, only_pending=False)
        topic_title = matches[0]["title"] if matches else keyword
        
        try:
            prompt = (f"Provide a crisp, rigorous, 5-bullet executive summary of the following IITM BS Data Science lecture/topic: '{topic_title}'. "
                      f"Focus on key mathematical/conceptual insights and practical takeaways. Format cleanly in Markdown.")
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            summary_text = completion.choices[0].message.content
            send_telegram_message(f"📖 *Executive Summary (`{topic_title}`):*\n\n{summary_text}", chat_id=chat_id)
        except Exception as e:
            send_telegram_message(f"❌ Error generating summary from Groq: {e}", chat_id=chat_id)
        return jsonify({"status": "success"}), 200

    # Command: /quiz <subject>
    if text.startswith("/quiz"):
        subject_kw = text.split(" ", 1)[1].strip() if " " in text else "Data Science / Machine Learning"
        if not groq_client:
            send_telegram_message("❌ Groq API key not configured.", chat_id=chat_id)
            return jsonify({"status": "success"}), 200
            
        try:
            prompt = (f"Generate a rigorous 3-question Multiple Choice conceptual practice quiz on '{subject_kw}' suitable for an IITM BS Data Science Diploma student. "
                      f"For each question, provide 4 options (A, B, C, D). At the very end of the response under the header '🔑 **Answers & Explanations**', provide the correct option and a brief explanation for each question.")
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )
            quiz_text = completion.choices[0].message.content
            send_telegram_message(f"🎯 *Active Recall Quiz (`{subject_kw}`):*\n\n{quiz_text}", chat_id=chat_id)
        except Exception as e:
            send_telegram_message(f"❌ Error generating quiz: {e}", chat_id=chat_id)
        return jsonify({"status": "success"}), 200

    # Command: /ask <question> or Natural Chat / Q&A
    if text.startswith("/ask") or "?" in text or not text.startswith("/"):
        question = text.replace("/ask", "", 1).strip() if text.startswith("/ask") else text
        if not question:
            send_telegram_message("⚠️ What question can I help you with? Try `/ask explain bias-variance tradeoff`.", chat_id=chat_id)
            return jsonify({"status": "success"}), 200
            
        if not groq_client:
            send_telegram_message("❌ Groq API key not configured.", chat_id=chat_id)
            return jsonify({"status": "success"}), 200
            
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert AI Study Tutor helping an IITM BS Data Science Diploma student. Be concise, mathematically rigorous, and clear. Use Markdown formatting effectively."},
                    {"role": "user", "content": question}
                ],
                temperature=0.3
            )
            answer = completion.choices[0].message.content
            send_telegram_message(f"🧠 *AI Tutor (`llama-3.3-70b`):*\n\n{answer}", chat_id=chat_id)
        except Exception as e:
            send_telegram_message(f"❌ Error getting AI answer: {e}", chat_id=chat_id)
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    # This is for local testing. PythonAnywhere will use a WSGI file to load the `app`.
    app.run(host='0.0.0.0', port=5000)
