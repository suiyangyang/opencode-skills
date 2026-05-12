#!/usr/bin/env python3
"""
OpenCode Orchestrator - CLI入口
用法: python main.py run
"""
import sys
import json
import os
from core import (
    run_once, setup_files, 
    reset_task, clear_tasks, 
    load_state, load_tasks
)

if __name__ == "__main__":
    # 确保必要文件存在
    setup_files()

    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"

    if cmd == "run":
        result = run_once()
        print(json.dumps(result, ensure_ascii=False))
    
    elif cmd == "status":
        state = load_state()
        tasks = load_tasks()
        print(json.dumps({"state": state, "tasks": tasks}, ensure_ascii=False))
    
    elif cmd == "reset-err":
        result = reset_task()
        print(json.dumps(result, ensure_ascii=False))
    
    elif cmd == "clear":
        result = clear_tasks()
        print(json.dumps(result, ensure_ascii=False))
    
    else:
        print(json.dumps({"status": "error", "msg": f"Unknown command: {cmd}"}))