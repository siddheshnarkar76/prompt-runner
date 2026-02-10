#!/usr/bin/env python
"""
Report Consolidator - Merge all logs into unified reports structure
"""
import json
import os
import shutil
from datetime import datetime

# Directories
REPORTS_DIR = "reports"
LOGS_DIR = "logs"
PROMPT_LOG = "prompt_logs.json"
ACTION_LOG = "action_logs.json"
RL_LOG = "rl_training_logs.json"


def consolidate_reports():
    """Consolidate all logs into unified reports/run_logs.json"""
    
    # Create reports directory
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Load all logs
    prompt_logs = []
    action_logs = []
    rl_logs = []
    
    # Load prompt logs
    if os.path.exists(PROMPT_LOG):
        with open(PROMPT_LOG, 'r', encoding='utf-8') as f:
            prompt_logs = json.load(f)
    elif os.path.exists(os.path.join(LOGS_DIR, PROMPT_LOG)):
        with open(os.path.join(LOGS_DIR, PROMPT_LOG), 'r', encoding='utf-8') as f:
            prompt_logs = json.load(f)
    
    # Load action logs
    if os.path.exists(ACTION_LOG):
        with open(ACTION_LOG, 'r', encoding='utf-8') as f:
            action_logs = json.load(f)
    elif os.path.exists(os.path.join(LOGS_DIR, ACTION_LOG)):
        with open(os.path.join(LOGS_DIR, ACTION_LOG), 'r', encoding='utf-8') as f:
            action_logs = json.load(f)
    
    # Load RL logs
    if os.path.exists(RL_LOG):
        with open(RL_LOG, 'r', encoding='utf-8') as f:
            rl_logs = json.load(f)
    
    # Create unified run logs
    run_logs = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "version": "2.0",
            "system": "DCR Compliance Platform"
        },
        "statistics": {
            "total_prompts": len(prompt_logs),
            "total_actions": len(action_logs),
            "total_rl_feedback": len(rl_logs)
        },
        "logs": {
            "prompts": prompt_logs,
            "actions": action_logs,
            "rl_training": rl_logs
        }
    }
    
    # Save consolidated report
    output_file = os.path.join(REPORTS_DIR, "run_logs.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(run_logs, f, indent=2)
    
    print(f"✅ Consolidated report saved to: {output_file}")
    print(f"   - Prompts: {len(prompt_logs)}")
    print(f"   - Actions: {len(action_logs)}")
    print(f"   - RL Feedback: {len(rl_logs)}")
    
    return output_file


def backup_original_logs():
    """Backup original log files"""
    backup_dir = os.path.join(REPORTS_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    files_to_backup = [
        PROMPT_LOG,
        ACTION_LOG,
        RL_LOG,
        os.path.join(LOGS_DIR, PROMPT_LOG),
        os.path.join(LOGS_DIR, ACTION_LOG)
    ]
    
    backed_up = 0
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            backup_path = os.path.join(backup_dir, f"{timestamp}_{filename}")
            shutil.copy2(file_path, backup_path)
            print(f"✅ Backed up: {file_path} → {backup_path}")
            backed_up += 1
    
    print(f"\n✅ Backed up {backed_up} files")


if __name__ == "__main__":
    print("🔄 Consolidating reports...\n")
    backup_original_logs()
    print()
    consolidate_reports()
    print("\n✨ Consolidation complete!")

