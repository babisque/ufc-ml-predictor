import subprocess
import sys
import time

def run_script(script_path):
    """Execute a Python script and check for errors."""
    print(f"\nRunning: {script_path}...")
    
    resultado = subprocess.run([sys.executable, script_path])
    
    if resultado.returncode != 0:
        print(f"Error: Script {script_path} failed.")
        sys.exit(1)
        
    print(f"Completed: {script_path}")
    time.sleep(1)

def execute_complete_pipeline():
    print("Starting MLOps pipeline")
    
    print("\n--- Phase 1: Scraping New Data ---")
    run_script("src/scraper/events.py")
    run_script("src/scraper/fights.py")
    run_script("src/scraper/fighters.py")
    run_script("src/scraper/details.py")
    
    print("\n--- Phase 2: Cleaning Data ---")
    run_script("src/processing/clean_data.py")
    run_script("src/processing/clean_fighters.py")
    
    print("\n--- Phase 3: Preparing Features ---")
    run_script("src/processing/merge_data.py")
    run_script("src/processing/shuffle_data.py")
    
    print("\n--- Phase 4: Training AI Model ---")
    run_script("train.py")
    
    print("\nPipeline completed successfully. The Oracles' brain is updated! 🧠")

if __name__ == "__main__":
    execute_complete_pipeline()