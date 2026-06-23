import os
import subprocess
import time
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

def run_pipeline():
    print(f"\n[{datetime.datetime.now()}] === Starting Weekly IITM Sync Pipeline ===")
    
    scripts = [
        "phase2_extractor.py",
        "phase3_transcripts.py",
        "phase4_schedule_builder.py",
        "phase4_notion_sync.py"
    ]
    
    for script in scripts:
        print(f"\n>>> Running {script}...")
        try:
            # We use the virtual environment's python if it exists, otherwise fallback to global
            python_exec = ".\\venv\\Scripts\\python.exe" if os.path.exists(".\\venv\\Scripts\\python.exe") else "python"
            
            result = subprocess.run([python_exec, script], check=True)
            print(f">>> Successfully completed {script}")
        except subprocess.CalledProcessError as e:
            print(f">>> ERROR: {script} failed with exit code {e.returncode}")
            print(">>> Aborting the rest of the pipeline.")
            return # Stop execution if one phase fails
        except Exception as e:
            print(f">>> FATAL ERROR running {script}: {e}")
            return
            
    print(f"\n[{datetime.datetime.now()}] === Pipeline Execution Complete ===")

if __name__ == "__main__":
    print("IITM Study Agent Orchestrator initialized.")
    run_pipeline()
    print("Initiating system sleep...")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
