import re
from datetime import datetime
from collections import defaultdict

LOG_FILE = "C:\\Users\\Yvtsan.l\\Downloads\\mmu1_logs.log.2025-05-08_08"  # Change this if needed

def parse_timestamp(line):
    match = re.match(r"\x1b\[38;20m(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", line)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
    return None

def extract_task_info(line):
    match = re.search(r"START_RUN manual task ({.*})", line)
    if match:
        return eval(match.group(1))  # Use json.loads if structure is JSON-safe
    return None

def extract_step_info(line):
    start_match = re.search(r"ANALYSE - START (.+)", line)
    end_match = re.search(r"ANALYSE - END (.+)", line)
    return ("start", start_match.group(1)) if start_match else \
           ("end", end_match.group(1)) if end_match else (None, None)

def extract_end_status(line):
    if "END_RUN Task" in line:
        return "success"
    elif "END_RUN task" in line and "error" in line:
        print(line)
        return "error"
    return None

def analyze_log_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        # print(lines)

    tasks = {}
    current_task_id = None
    for line in lines:
        # print(line)
        timestamp = parse_timestamp(line)
        if not timestamp:
            continue

        # Task start
        if "ANALYSE - START_RUN manual task" in line:
            task_info = extract_task_info(line)
            current_task_id = task_info["task_id"]
            tasks[current_task_id] = {
                "task": task_info["task"],
                "params": task_info.get("params", {}),
                "start_time": timestamp,
                "steps": [],
                "end_time": None,
                "success": None
            }

        # Steps within a task
        elif current_task_id is not None:
            step_type, step_detail = extract_step_info(line)
            if step_type and step_detail:
                tasks[current_task_id]["steps"].append({
                    "type": step_type,
                    "detail": step_detail,
                    "time": timestamp
                })

        # Task end
        if "ANALYSE - END_RUN" in line and current_task_id is not None:
            status = extract_end_status(line)
            if status:
                tasks[current_task_id]["end_time"] = timestamp
                tasks[current_task_id]["success"] = status
                current_task_id = None

    return tasks

def print_summary(tasks):
    for task_id, task in tasks.items():
        duration = (task["end_time"] - task["start_time"]).total_seconds() if task["end_time"] else None
        print(f"\nTask ID: {task_id}")
        print(f"Task Name: {task['task']}")
        print(f"Params: {task['params']}")
        print(f"Start: {task['start_time']}")
        print(f"End: {task['end_time']}")
        print(f"Status: {task['success']}")
        print(f"Duration: {duration:.2f} seconds" if duration else "Duration: N/A")
        print("Steps:")
        for step in task["steps"]:
            print(f"  - [{step['type']}] {step['detail']} at {step['time']}")

if __name__ == "__main__":
    tasks_data = analyze_log_file(LOG_FILE)
    print_summary(tasks_data)
