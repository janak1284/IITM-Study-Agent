import os
import subprocess
import time
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

def run_pipeline():
    print(f"\n[{datetime.datetime.now()}] === Starting Weekly IITM Sync Pipeline ===")
    
    print("\n>>> Ensuring dependencies are installed (using ultra-fast uv)...")
    try:
        if not os.path.exists(".venv"):
            subprocess.run(["uv", "venv"], check=True)
        subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"], check=True)
    except Exception as e:
        print(f">>> Failed to setup environment with uv: {e}")
        return False
        
    scripts = [
        "phase2_extractor.py",
        "phase3_transcripts.py",
        "phase4_schedule_builder.py",
        "phase4_notion_sync.py"
    ]
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--user_id", type=str, help="The ID of the user executing the task")
    args, unknown = parser.parse_known_args()
    
    for script in scripts:
        print(f"\n>>> Running {script}...")
        try:
            # Run the script using the uv environment
            cmd = ["uv", "run", script]
            if args.user_id:
                cmd.extend(["--user_id", args.user_id])
                
            result = subprocess.run(cmd, check=True)
            print(f">>> Successfully completed {script}")
        except subprocess.CalledProcessError as e:
            print(f">>> ERROR: {script} failed with exit code {e.returncode}")
            print(">>> Aborting the rest of the pipeline.")
            return False # Stop execution if one phase fails
        except Exception as e:
            print(f">>> FATAL ERROR running {script}: {e}")
            return False
            
    print(f"\n[{datetime.datetime.now()}] === Pipeline Execution Complete ===")
    return True

if __name__ == "__main__":
    print("IITM Study Agent Orchestrator initialized.")
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_pipeline()
    
    if not success:
        print("\n[ALERT] >>> Pipeline encountered errors or was aborted prematurely.")
        print("[ALERT] >>> System sleep/hibernation is ABORTED so errors can be inspected/debugged.")
        sys.exit(1)
        
    # Check if auto-sleep is requested via command line (--sleep / -s) or .env (AUTO_SLEEP=true)
    auto_sleep_env = os.environ.get("AUTO_SLEEP", "").lower() in ("true", "1", "yes")
    auto_sleep_arg = any(arg in sys.argv for arg in ("--sleep", "-s", "--auto-sleep"))
    
    if auto_sleep_env or auto_sleep_arg:
        print("\n>>> Pipeline completed successfully. Initiating system sleep/hibernation in 10 seconds...")
        print(">>> Press Ctrl+C within 10 seconds to CANCEL system sleep.")
        try:
            for i in range(10, 0, -1):
                print(f"Sleeping in {i} seconds...", end="\r", flush=True)
                time.sleep(1)
            print("\nInitiating system sleep/hibernation...")
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        except KeyboardInterrupt:
            print("\n>>> System sleep CANCELLED by user.")
    else:
        print("\n>>> Pipeline completed successfully.")
        print(">>> Note: Automatic system sleep was NOT triggered. To enable automatic sleep/hibernation after pipeline runs, pass '--sleep' flag or set AUTO_SLEEP=true in .env.")
