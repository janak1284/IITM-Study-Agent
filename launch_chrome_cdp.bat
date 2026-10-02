@echo off
echo Launching Google Chrome for Gemini on Port 9223...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9223 --user-data-dir="C:\chrome-gemini-profile" "https://gemini.google.com/app"
echo Chrome launched on port 9223! Please make sure you are logged into Gemini in this window.
