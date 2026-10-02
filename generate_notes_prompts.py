#!/usr/bin/env python3
"""
generate_notes_prompts.py

This script reads `curriculum_extracted.json` and generates specialized, high-context
prompts tailored for Gemini 3.1 Pro to create exhaustive, exam-ready review notes
for each course and week.

Key Features:
1. Skips tutorial videos automatically (identifies videos where 'tutorial' is in the title).
2. Generates exactly 1 detailed prompt per week per course containing all lecture video links.
3. Includes explicit instructions for Gemini 3.1 Pro to provide detailed step-by-step
   example questions and solutions for any mathematical or quantitative concepts, ensuring
   the student can implement the exact approach in exams.
4. Outputs each generated prompt to the console (`stdout`) and also saves them neatly into
   a local folder (`prompts_for_gemini/`) and a consolidated markdown file for easy access.

Usage (run locally when needed):
    python generate_notes_prompts.py
"""

import json
import os
import sys
from pathlib import Path

CURRICULUM_FILE = "curriculum_extracted.json"
OUTPUT_DIR = "prompts_for_gemini"

PROMPT_TEMPLATE = """You are an expert AI Professor and Academic Content Creator powered by Gemini 3.1 Pro.
I am a university student preparing for my exams in the course: **{course_name}**.
Below are the lecture video links and titles for **{week_name}** of this course.

### Lecture Videos for {course_name} - {week_name}:
{video_list_formatted}

### Your Task:
Please generate **highly detailed, comprehensive, and self-contained study notes** for **{course_name} ({week_name})** based on the topics, concepts, and materials covered in these lecture videos. My goal is to review **only these notes alone before my exams**, without having to re-watch any of the videos or refer to external textbooks. Therefore, your notes must be exhaustive, rigorous, and completely self-contained.

### Essential Requirements:
1. **Comprehensive & Exhaustive Coverage:**
   - Cover every single concept, theory, definition, framework, and discussion point introduced across all the listed lecture videos.
   - Do not summarize briefly or omit minor details; explain each topic in thorough depth so that all necessary intuition and formal definitions are captured.

2. **Mathematical & Quantitative Concepts (CRITICAL FOR EXAMS):**
   - Whenever a **mathematical concept, derivation, formula, statistical model, economic calculation, or algorithm** is covered:
     - Clearly state the exact formal definitions, equations, and notation, explaining what every variable and symbol represents.
     - **MANDATORY LATEX MATH FORMATTING:** You MUST format ALL mathematical expressions, variables, formulas, equations, norms, vectors, matrices, superscripts, and subscripts strictly inside LaTeX math blocks (use `$ ... $` for inline math such as `$c^*$` or `$||w||^2$`, and `$$ ... $$` for standalone equations). Never write multi-line ASCII math or unformatted Unicode fractions outside `$ ... $` syntax.
     - State all assumptions, boundary conditions, and intuitive reasoning behind the formula.
     - **Provide Example Questions with Detailed Step-by-Step Answers:** For every mathematical or numerical concept, formulate realistic, exam-style practice questions. Then, provide the **complete, detailed step-by-step solution** showing exact intermediate steps and calculations. This is critical so I can learn the exact problem-solving methodology and implement the same approach for similar quantitative questions when asked in my exam.


3. **Structured & Reader-Friendly Layout:**
   - Use clean Markdown hierarchy (`#`, `##`, `###`) to organize topics logically (either video-by-video or by cohesive conceptual themes across the week).
   - Use **bolding** for key definitions, terminology, and crucial rules.
   - Use structured bullet points, numbered lists, and comparison tables where appropriate to contrast concepts clearly.

4. **Exam Review Checklist & Key Pitfalls:**
   - At the end of the notes, include a **"Quick Exam Review Checklist & Key Takeaways"** summarizing the most important formulas, definitions, and core principles to memorize for this week.
   - Include a **"Common Exam Pitfalls & Mistakes to Avoid"** section highlighting frequent misconceptions or calculation errors students make regarding these specific topics.

Please proceed immediately with generating the complete, exhaustive review notes for **{course_name} - {week_name}**."""


def is_tutorial_video(title: str) -> bool:
    """Check if a video is a tutorial video based on its title."""
    return "tutorial" in title.lower()


def generate_prompts(curriculum_path: str = CURRICULUM_FILE, save_to_files: bool = True):
    """
    Reads the extracted curriculum JSON and generates review prompts per week per course.
    Outputs to console and optionally saves individual and consolidated markdown files.
    """
    if not os.path.exists(curriculum_path):
        print(f"[Error] Curriculum file '{curriculum_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(curriculum_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    subjects = data.get("subjects", [])
    if not subjects:
        print("[Warning] No subjects found in curriculum file.")
        return

    # Prepare output directory if saving to files
    if save_to_files:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        consolidated_file_path = os.path.join(OUTPUT_DIR, "all_week_prompts_consolidated.md")
        consolidated_f = open(consolidated_file_path, "w", encoding="utf-8")
        consolidated_f.write("# Gemini 3.1 Pro Exam Review Prompts\n\n")
        consolidated_f.write("This file contains all the weekly prompts generated from `curriculum_extracted.json`.\n\n")

    total_prompts_generated = 0

    print("=" * 80)
    print("GENERATING EXAM REVIEW PROMPTS FOR GEMINI 3.1 PRO (WEEK BY WEEK)")
    print("=" * 80)

    for subject in subjects:
        course_name = subject.get("subject_name", "Unknown Course")
        weeks = subject.get("weeks", [])

        for week in weeks:
            week_name = week.get("week_name", "Unknown Week")
            all_lectures = week.get("lectures", [])

            # Filter out tutorial videos
            lecture_videos = [
                lec for lec in all_lectures
                if not is_tutorial_video(lec.get("title", ""))
            ]
            skipped_tutorials = len(all_lectures) - len(lecture_videos)

            if not lecture_videos:
                print(f"\n[Skip] {course_name} - {week_name}: No lecture videos found (skipped {skipped_tutorials} tutorials).")
                continue

            # Format the video list
            video_lines = []
            for idx, lec in enumerate(lecture_videos, start=1):
                title = lec.get("title", f"Lecture {idx}")
                url = lec.get("url", "No URL provided")
                video_lines.append(f"{idx}. **{title}**\n   - Link: {url}")

            video_list_formatted = "\n".join(video_lines)

            # Fill the prompt template
            prompt_text = PROMPT_TEMPLATE.format(
                course_name=course_name,
                week_name=week_name,
                video_list_formatted=video_list_formatted
            )

            total_prompts_generated += 1

            # Output to stdout
            print(f"\n[{total_prompts_generated}] PROMPT FOR: {course_name} | {week_name}")
            print(f"    (Included {len(lecture_videos)} lecture videos, skipped {skipped_tutorials} tutorials)")
            print("-" * 80)
            print(prompt_text)
            print("=" * 80)

            # Save to individual files and consolidated file
            if save_to_files:
                # Sanitize folder/file names safely
                safe_course = "".join(c for c in course_name if c.isalnum() or c in (" ", "-", "_")).strip()
                safe_week = "".join(c for c in week_name if c.isalnum() or c in (" ", "-", "_")).strip()

                course_dir = os.path.join(OUTPUT_DIR, safe_course)
                os.makedirs(course_dir, exist_ok=True)

                indiv_file_path = os.path.join(course_dir, f"{safe_week}_prompt.md")
                with open(indiv_file_path, "w", encoding="utf-8") as out_f:
                    out_f.write(prompt_text)

                # Append to consolidated file
                consolidated_f.write(f"## {course_name} - {week_name}\n\n")
                consolidated_f.write(f"*Included {len(lecture_videos)} lecture videos (skipped {skipped_tutorials} tutorials)*\n\n")
                consolidated_f.write("```markdown\n")
                consolidated_f.write(prompt_text)
                consolidated_f.write("\n```\n\n---\n\n")

    if save_to_files:
        consolidated_f.close()
        print(f"\n[Success] Generated {total_prompts_generated} prompts across all courses.")
        print(f" -> Individual prompt files saved in: `{OUTPUT_DIR}/<Course Name>/<Week Name>_prompt.md`")
        print(f" -> Consolidated file saved at: `{OUTPUT_DIR}/all_week_prompts_consolidated.md`")


if __name__ == "__main__":
    generate_prompts()
