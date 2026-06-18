import json
import os
import time
import re
from pathlib import Path
from dotenv import load_dotenv
import pymupdf4llm
from groq import Groq
from thefuzz import fuzz
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import builtins

def print(*args, **kwargs):
    kwargs['flush'] = True
    builtins.print(*args, **kwargs)

# Load environment variables
load_dotenv()
groq_api_key = os.environ.get("GROQ_API_KEY")
drive_api_key = os.environ.get("GOOGLE_DRIVE_API_KEY")

if not groq_api_key:
    print("Error: GROQ_API_KEY not found in .env file.")
    exit(1)

client = Groq(api_key=groq_api_key)
drive_service = build('drive', 'v3', developerKey=drive_api_key) if drive_api_key else None

def download_folder_files(folder_id, download_dir, depth=0):
    if not drive_service: return
    prefix = "  " * depth
    print(f"{prefix}[Drive API] Scanning folder ID: {folder_id} into {download_dir}")
    try:
        page_token = None
        while True:
            response = drive_service.files().list(
                q=f"'{folder_id}' in parents",
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token
            ).execute()
            
            for file in response.get('files', []):
                file_id = file.get('id')
                file_name = file.get('name')
                mime_type = file.get('mimeType')
                
                # Clean filename
                safe_name = "".join([c for c in file_name if c.isalpha() or c.isdigit() or c in ' ._-']).rstrip()
                
                if mime_type == 'application/vnd.google-apps.folder':
                    print(f"{prefix}[Drive API] Found sub-folder: {file_name}")
                    sub_dir = os.path.join(download_dir, safe_name)
                    os.makedirs(sub_dir, exist_ok=True)
                    download_folder_files(file_id, sub_dir, depth + 1)
                elif mime_type == 'application/pdf':
                    file_path = os.path.join(download_dir, safe_name)
                    
                    if os.path.exists(file_path):
                        print(f"{prefix}[Drive API] Skipping already downloaded: {file_name}")
                        continue
                        
                    print(f"{prefix}[Drive API] Downloading PDF: {file_name}...")
                    try:
                        request = drive_service.files().get_media(fileId=file_id)
                        with open(file_path, 'wb') as fh:
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while done is False:
                                status, done = downloader.next_chunk()
                    except Exception as e:
                        print(f"{prefix}[Error] Failed to download {file_name}: {e}")
                        
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                print(f"{prefix}[Drive API] Finished scanning folder: {folder_id}")
                break
    except Exception as e:
        print(f"{prefix}[Error] Drive API download failed for folder {folder_id}: {e}")

def clean_title(title):
    cleaned = re.sub(r'^(?:L\d+\.\d+|\d+\.\d+|Week \d+:?)\s*:?\s*', '', title, flags=re.IGNORECASE)
    cleaned = cleaned.replace('.pdf', '').replace('.docx', '').replace('.txt', '')
    cleaned = re.sub(r'[^\w\s]', '', cleaned).lower().strip()
    return cleaned

def summarize_text(text, filename, subject_name, week_name, is_youtube=False):
    print(f"    Summarizing {filename} with Groq...")
    
    system_prompt = """
You are an expert Data Science tutor. Summarize this specific portion of a lecture transcript.
Extract the core concepts, definitions, and any Python code or mathematical formulas. 
Output clean text. Do NOT invent or generate any homework assignments or practice questions.
"""
    if is_youtube:
        system_prompt += "\nNOTE: This text is an auto-generated speech-to-text transcript from a video. It lacks punctuation and may have phonetic transcription errors for technical terms or math. Please infer the correct technical terms and structure it logically."

    chunk_size = 10000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    chunk_summaries = []
    
    # 1. The MAP Phase
    for idx, chunk in enumerate(chunks):
        if idx > 0:
            print(f"    [Chunking] Processing part {idx+1}/{len(chunks)} of {filename}...")
            print("    [Rate Limit Protection] Sleeping for 65 seconds before next chunk...")
            time.sleep(65)
            
        max_retries = 5
        for attempt in range(max_retries):
            try:
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": chunk}
                    ],
                    temperature=0.3,
                    max_tokens=1500
                )
                chunk_summaries.append(completion.choices[0].message.content)
                break
            except Exception as e:
                err_str = str(e)
                if "Rate limit" in err_str or "429" in err_str or "413" in err_str:
                    wait_time = (attempt + 1) * 25
                    print(f"    [Rate Limit] Hit rate limit. Waiting {wait_time}s before retry {attempt+1}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    print(f"    [Error] Groq API failed for {filename}: {e}")
                    return None
        else:
            print(f"    [Error] Max retries reached for {filename} chunk {idx+1}")
            return None

    # 2. The REDUCE Phase
    print(f"    [Map-Reduce] Merging {len(chunk_summaries)} summaries into a cohesive document...")
    combined_raw_summaries = "\n\n".join(chunk_summaries)
    
    reduce_prompt = """
You are an expert technical editor. I am providing you with sequential summaries of a single lecture. 
Merge them into ONE cohesive, master study guide. 
Use a single set of Markdown headers (e.g., ## Core Concepts, ## Definitions, ## Code Snippets). 
Remove any redundant or repeating headers. Do NOT invent new information or homework assignments.
"""
    
    if len(chunk_summaries) > 1:
        time.sleep(65) # Rate limit protection before the big reduce
        
    for attempt in range(5):
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": reduce_prompt},
                    {"role": "user", "content": combined_raw_summaries}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            final_cohesive_summary = completion.choices[0].message.content
            return final_cohesive_summary
        except Exception as e:
            err_str = str(e)
            if "Rate limit" in err_str or "429" in err_str or "413" in err_str:
                wait_time = (attempt + 1) * 25
                print(f"    [Rate Limit] Hit rate limit on reduce. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    [Error] Groq API reduce failed for {filename}: {e}")
                return None
                
    return None

def extract_yt_id(url):
    match = re.search(r'(?:v=|youtu\.be/)([^&]+)', url)
    return match.group(1) if match else None

def main():
    if not os.path.exists("curriculum_extracted.json"):
        print("curriculum_extracted.json not found!")
        return
        
    with open("curriculum_extracted.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    subjects = data.get("subjects", [])
    
    for subject in subjects:
        subject_name = subject["subject_name"]
        drive_url = subject.get("drive_folder_url")
        
        print(f"\n=== Processing Subject: {subject_name} ===")
        transcripts_dir = os.path.join("transcripts", subject_name.replace(":", ""))
        summaries_dir = os.path.join("summaries", subject_name.replace(":", ""))
        
        os.makedirs(transcripts_dir, exist_ok=True)
        os.makedirs(summaries_dir, exist_ok=True)
        
        # 1. Download PDFs using Google Drive API
        pdf_files = []
        if drive_url and drive_url != "Not Found" and drive_service:
            print(f"  Downloading transcripts from Drive using Google API...")
            folder_id = ""
            try:
                folder_id = drive_url.split("folders/")[1].split("?")[0]
            except Exception:
                pass
            
            if folder_id:
                download_folder_files(folder_id, transcripts_dir)
                
            pdf_files = list(Path(transcripts_dir).rglob("*.pdf"))
            print(f"  Found {len(pdf_files)} PDFs downloaded.")

        # 2. Iterate through curriculum and map/fallback
        for week in subject.get("weeks", []):
            week_name = week["week_name"]
            week_dir = os.path.join(summaries_dir, week_name)
            os.makedirs(week_dir, exist_ok=True)
            
            for lecture in week.get("lectures", []):
                title = lecture["title"]
                url = lecture["url"]
                cleaned_title = clean_title(title)
                
                safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in ' ._-']).rstrip()
                summary_filepath = os.path.join(week_dir, f"{safe_title}.md")
                
                if os.path.exists(summary_filepath):
                    print(f"  [Skipping] Summary exists for: {title}")
                    continue
                    
                best_match_pdf = None
                best_score = 0
                for pdf_path in pdf_files:
                    score = fuzz.token_set_ratio(cleaned_title, clean_title(pdf_path.name))
                    if score > best_score:
                        best_score = score
                        best_match_pdf = pdf_path
                
                md_text = None
                is_youtube = False
                source_name = ""
                
                if best_match_pdf and best_score > 80:
                    print(f"  [Match {best_score}%] '{title}' -> PDF: {best_match_pdf.name}")
                    source_name = best_match_pdf.name
                    try:
                        print(f"    [PyMuPDF] Converting {best_match_pdf.name} to Markdown...")
                        md_text = pymupdf4llm.to_markdown(str(best_match_pdf))
                    except Exception as e:
                        print(f"    [Error] PDF parsing failed for {best_match_pdf.name}: {e}")
                else:
                    print(f"  [Fallback to YouTube] No PDF found for: '{title}'. Fetching captions...")
                    yt_id = extract_yt_id(url)
                    is_youtube = True
                    source_name = f"YouTube ({yt_id})"
                    if yt_id:
                        try:
                            print(f"    [YouTube API] Fetching transcript for video ID: {yt_id}")
                            ytt_api = YouTubeTranscriptApi()
                            transcript_list = ytt_api.list(yt_id)
                            transcript = transcript_list.find_transcript(['en', 'en-IN', 'en-GB', 'hi'])
                            md_text = " ".join([t.text for t in transcript.fetch()])
                        except Exception as e:
                            print(f"    [Error] YouTube Transcript failed for {yt_id}: {e}")
                            
                if md_text:
                    print(f"    [Groq AI] Sending text to Llama 3 for Map-Reduce summarization...")
                    summary = summarize_text(md_text, source_name, subject_name, week_name, is_youtube=is_youtube)
                    if summary:
                        # 3. The Assembly Phase (Python handles the structure)
                        file_content = f"""---
course: {subject_name}
week: {week_name}
status: AI_Generated
---

{summary}

---
[[{week_name} Graded Assignments]]
"""
                        with open(summary_filepath, "w", encoding="utf-8") as sf:
                            sf.write(file_content)
                        print(f"    Saved structured summary to {summary_filepath}")
                        print("    [Rate Limit Protection] Sleeping for 65 seconds to reset Groq 6000 TPM limit...")
                        time.sleep(65)

if __name__ == "__main__":
    main()
