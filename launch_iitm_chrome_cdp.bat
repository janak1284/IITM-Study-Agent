@echo off
echo Launching Google Chrome for IITM Portal on Port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-iitm-profile" "https://app.onlinedegree.iitm.ac.in/student_dashboard/current_courses"
echo Chrome launched on port 9222! Please make sure you are logged into the IITM portal in this window before running the orchestrator.
