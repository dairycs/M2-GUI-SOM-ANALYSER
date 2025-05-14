import ast
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
from datetime import datetime
import pandas
import openpyxl

# Remove ANSI escape sequences from a line
def clean_ansi_codes(line):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    return ansi_escape.sub('', line)

def parse_log_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    tasks = {}
    current_task = None

    task_start_re = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*START_RUN manual task.*'task': '([^']+)',.*'task_id': (\d+)")
    task_end_success_re = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*END_RUN Task (\w+) completed successfully")
    task_end_error_re = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*END_RUN task .* failed with error .* task_id (\d+)")
    alarm_from_host = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*receive alarm from HOST: (.*)")
    err_handling_re = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*Handle(.*)")
    step_start_re = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*START (.*)")
    step_end_re = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*END (.*)")

    for line in lines:
        if "ANALYSE -" not in line:
            continue
        else:
            pass
            # print(line)
        if match := task_start_re.search(line):
            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
            task_name = match.group(2)
            task_id = int(match.group(3))
            params =line.split("'params': {")[1].split('}, \'task_id')[0]
            current_task = {
                "id": task_id,
                "name": task_name,
                "params": params,
                "start_time": timestamp,
                "steps": [],
                "end_time": None,
                "status": "unknown"
            }
            tasks[task_id] = current_task

        elif match := task_end_success_re.search(line):
            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
            task_name = match.group(2)
            for task in tasks.values():
                if task["name"] == task_name and task["end_time"] is None:
                    task["end_time"] = timestamp
                    task["status"] = "success"
                    break

        elif match := task_end_error_re.search(line):
            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
            task_id = int(match.group(2))
            # print(line)
            error_desc = line.split("failed with error")[1].split('task_id')[0]

            if task_id in tasks:
                tasks[task_id]["end_time"] = timestamp
                tasks[task_id]["status"] = f"ERROR {error_desc}"

        elif match := step_start_re.search(line):
            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
            step_desc = match.group(2).split(" (")[0].strip()
            if "maestro" in line:
                worker = "maestro"
                match = re.search(r"\(([^()]+)\)", line)
                if match:
                    param_str = match.group(1)  # e.g., "1200, 2500, 90"
                    params = [int(x.strip()) for x in param_str.split(',') if x.strip().isdigit()]
                    step_desc += " " + str(params)
            elif "mtc" in line:
                worker = "mtc"
            else:
                worker = "som"
            # print(line)
            if current_task:
                current_task["steps"].append({
                    "type": "start",
                    "line": line,
                    "desc": step_desc,
                    "worker": worker,
                    "time": timestamp
                })

        elif match := step_end_re.search(line):
            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
            step_desc = match.group(2).split(" (")[0].strip()
            if current_task:
                current_task["steps"].append({
                    "type": "end",
                    "line": line,
                    "desc": step_desc,
                    "time": timestamp
                })
        elif match := alarm_from_host.search(line):
            # print(line)
            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
            step_desc = match.group(2).split(" (")[0].strip()
            worker = "som"

            if current_task:
                current_task["steps"].append({
                    "type": "start",
                    "line": line,
                    "worker": worker,
                    "desc": f"ALARM FROM HOST: {step_desc}",
                    "time": timestamp
                })
        elif match := err_handling_re.search(line):
            # print(line)
            # print(match)
            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
            step_desc = match.group(2).split(" (")[0].strip()
            worker = "som"
            if "SUCCESS" in line:
                type = "end"
            else:
                type = "start"
            if current_task:
                current_task["steps"].append({
                    "type": type,
                    "line": line,
                    "worker": worker,
                    "desc": f"ERROR HANDLING {step_desc}",
                    "time": timestamp
                })
        else:
            # print(line)
            pass

    return tasks


class TaskViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Log Task Viewer")

        self.tasks = {}

        self.load_btn = tk.Button(root, text="Choose Log File", command=self.load_log_file)
        self.load_btn.pack(pady=5)

        self.tree = ttk.Treeview(root, columns=("Task ID", "Task Name", "Status","Start Time","End Time", "Duration (s)"), show="headings")
        self.tree.heading("Task ID", text="Task ID")
        self.tree.heading("Task Name", text="Task Name")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Start Time", text="Start Time")
        self.tree.heading("End Time", text="End Time")
        self.tree.heading("Duration (s)", text="Duration (s)")
        self.tree.pack(expand=True, fill=tk.BOTH)
        self.tree.bind("<<TreeviewSelect>>", self.show_task_details)

        # self.detail_text = tk.Text(root, height=20, wrap=tk.WORD)
        # self.detail_text.pack(expand=True, fill=tk.BOTH)
        # self.detail_text.tag_configure("error", foreground="red")

        # Create frame for steps table
        self.steps_frame = ttk.Frame(root)
        self.steps_frame.pack(fill=tk.BOTH, expand=True)

        # Steps table
        self.steps_table = ttk.Treeview(self.steps_frame, columns=("desc", "start", "end", "duration"), show="headings")
        self.steps_table.heading("desc", text="Step Description")
        self.steps_table.heading("start", text="Start Time")
        self.steps_table.heading("end", text="End Time")
        self.steps_table.heading("duration", text="Duration (sec)")

        # Optional: column widths
        self.steps_table.column("desc", width=300)
        self.steps_table.column("start", width=180)
        self.steps_table.column("end", width=180)
        self.steps_table.column("duration", width=120)

        self.steps_table.pack(fill=tk.BOTH, expand=True)

        # Style error rows (optional)
        self.steps_table.tag_configure("error", foreground="red")

        self.export_button = tk.Button(self.steps_frame, text="Export to Excel", command=self.export_steps_to_excel)
        self.export_button.pack(pady=5)

    def load_log_file(self):
        path = filedialog.askopenfilename(filetypes=[("Log Files", "*.log*")])
        if not path:
            return

        self.tasks = parse_log_file(path)
        # print(self.tasks)
        self.tree.delete(*self.tree.get_children())

        for task in self.tasks.values():
            duration = ""
            # print(task["start_time"])
            # print(task["end_time"])
            start = task["start_time"].strftime("%Y-%m-%d %H:%M:%S") if task["start_time"] else ""
            end = task["end_time"].strftime("%Y-%m-%d %H:%M:%S") if task["end_time"] else ""
            if task["end_time"] and task["start_time"]:
                duration = round((task["end_time"] - task["start_time"]).total_seconds(), 2)
            # print(task["status"])
            if task["status"].lower() == "success":
                self.tree.insert("", tk.END, iid=str(task["id"]),
                                 values=(task["id"], task["name"], task["status"],start,end, duration),
                                 tags=('success',))
            else:
                self.tree.insert("", tk.END, iid=str(task["id"]),
                                 values=(task["id"], task["name"], task["status"],start,end, duration),
                                 tags=('error',))

    def normalize_step_desc(self, desc):
        # Handle common patterns for both start and end
        # print(desc)
        if "wait for maestro to complete" in desc:
            desc = desc.split("[")[0]
            return desc.replace("wait for maestro to complete", "").strip()
        elif "wait for mtc" in desc:
            desc = desc.split("task")[1]
            return desc.replace("start the task", "").strip()
        elif "maestro task - " in desc and "completed successfully" in desc:
            return desc.replace("maestro task - ", "").replace("completed successfully", "").strip()
        elif "mtc" in desc and "retry" in desc:
            desc = desc.split("task")[1]
            desc = desc.split("completed")[0]
            return desc.replace("task", "").strip()
        elif "ERROR: maestro failed to completed task" in desc:
            desc = desc.split("with")[0]
            desc = desc.replace("ERROR: maestro failed to completed task", "").strip()
            desc = desc.split(" ")
            result = ""
            for i in range(len(desc)):
                result += desc[i]
                if i < len(desc) -1:
                    result +="_"
            return  result
        elif "SUCCESS" in desc:
            return desc.split("SUCCESS")[0].strip()
        else:
            print(desc)
            return desc.strip()

    # def show_task_details(self, event):
    #     self.detail_text.delete("1.0", tk.END)
    #     selected = self.tree.selection()
    #     if not selected:
    #         return
    #     task_id = int(selected[0])
    #     task = self.tasks.get(task_id)
    #     print(task)
    #     if not task:
    #         return
    #
    #     self.detail_text.insert(tk.END, f"Task ID: {task['id']}\n")
    #     self.detail_text.insert(tk.END, f"Task Name: {task['name']}\n")
    #     self.detail_text.insert(tk.END, f"Params: {task['params']}\n")
    #     self.detail_text.insert(tk.END, f"Start: {task['start_time']}\n")
    #     self.detail_text.insert(tk.END, f"End: {task['end_time']}\n")
    #     self.detail_text.insert(tk.END, f"Status: {task['status']}\n")
    #
    #     if task["start_time"] and task["end_time"]:
    #         total = round((task["end_time"] - task["start_time"]).total_seconds(), 2)
    #         self.detail_text.insert(tk.END, f"Duration: {total} seconds\n")
    #
    #     self.detail_text.insert(tk.END, "Steps:\n")
    #
    #     step_pairs = {}
    #     for step in task["steps"]:
    #         print(step["line"])
    #         normalized = self.normalize_step_desc(step["desc"])
    #         print(normalized)
    #         if normalized not in step_pairs:
    #             step_pairs[normalized] = {}
    #         step_pairs[normalized][step["type"]] = step["time"]
    #
    #     for desc, times in step_pairs.items():
    #         if "start" in times and "end" in times:
    #             duration = round((times["end"] - times["start"]).total_seconds(), 2)
    #             self.detail_text.insert(tk.END, f"  - {desc}: {duration} seconds\n")
    #         else:
    #             self.detail_text.insert(tk.END, f"  - {desc}: (incomplete)\n")
    def show_task_details(self, event):
        # self.detail_text.delete("1.0", tk.END)
        selected = self.tree.selection()
        if not selected:
            return
        task_id = int(selected[0])
        task = self.tasks.get(task_id)
        if not task:
            return

        # self.detail_text.insert(tk.END, f"Task ID: {task['id']}\n")
        # self.detail_text.insert(tk.END, f"Task Name: {task['name']}\n")
        # self.detail_text.insert(tk.END, f"Params: {task['params']}\n")
        # self.detail_text.insert(tk.END, f"Start: {task['start_time']}\n")
        # self.detail_text.insert(tk.END, f"End: {task['end_time']}\n")
        # self.detail_text.insert(tk.END, f"Status: {task['status']}\n")
        #
        # if task["start_time"] and task["end_time"]:
        #     total = round((task["end_time"] - task["start_time"]).total_seconds(), 2)
        #     self.detail_text.insert(tk.END, f"Duration: {total} seconds\n")
        #
        # self.detail_text.insert(tk.END, "Steps:\n")

        # === Sequential pairing logic ===
        start_stack = []
        steps = task["steps"]
        paired_steps = []

        for step in steps:
            normalized = self.normalize_step_desc(step["desc"])
            # print(f"normalized {normalized}")
            # print(step["line"])
            if step["type"] == "start":
                step["desc_normalized"] = normalized
                start_stack.append(step)
            elif step["type"] == "end":
                for i, s in enumerate(start_stack):
                    if normalized in self.normalize_step_desc(s["desc"]):
                        # print(s["desc"])
                        # print(step["desc"])
                        # print(s["worker"])
                        description = self.set_desc(s,step)
                        paired_steps.append({
                            "desc": description ,
                            "start": s["time"],
                            "end": step["time"],
                            "duration": round((step["time"] - s["time"]).total_seconds(), 2)
                        })
                        del start_stack[i]
                        break
                else:
                    # unmatched end
                    paired_steps.append({
                        "desc": step["desc"],
                        "start": None,
                        "end": step["time"],
                        "duration": None
                    })

        for leftover in start_stack:
            paired_steps.append({
                "desc": leftover["desc"],
                "start": leftover["time"],
                "end": None,
                "duration": None
            })

        # Sort by start or end time
        paired_steps.sort(key=lambda x: x["start"] or x["end"])

        # for step in paired_steps:
        #     if step["start"] and step["end"]:
        #         if "error" in step["desc"].lower():
        #             self.detail_text.insert(tk.END, f"  - {step['desc']}: {step['duration']} seconds\n", "error")
        #         else:
        #             self.detail_text.insert(tk.END, f"  - {step['desc']}: {step['duration']} seconds\n")
        #     elif step["start"]:
        #         self.detail_text.insert(tk.END, f"  - {step['desc']}: started at {step['start']}, but no end\n")
        #     elif step["end"]:
        #         self.detail_text.insert(tk.END, f"  - {step['desc']}: ended at {step['end']}, but no start\n")
        # Clear previous rows
        for row in self.steps_table.get_children():
            self.steps_table.delete(row)

        for step in paired_steps:
            desc = step["desc"]
            start = step["start"].strftime("%Y-%m-%d %H:%M:%S") if step["start"] else ""
            end = step["end"].strftime("%Y-%m-%d %H:%M:%S") if step["end"] else ""
            duration = f"{step['duration']:.2f}" if step.get("duration") else ""

            tag = "error" if "error" in desc.lower() else ""

            self.steps_table.insert("", tk.END, values=(desc, start, end, duration), tags=(tag,))

    def set_desc(self,start_desc,end_desc):
        # print(start_desc)
        # print(end_desc)
        if start_desc["worker"] == "maestro":
            if "completed successfully" in end_desc["desc"]:
                desc = "maestro end " + start_desc["desc"].split("complete")[1] + " task successfully"
            elif "with error"  in end_desc["desc"]:
                match = re.search(r"\(([^()]+)\)", start_desc["line"])
                if match:
                    param_str = match.group(1)  # e.g., "1200, 2500, 90"
                    params = [int(x.strip()) for x in param_str.split(',') if x.strip().isdigit()]
                desc = end_desc["desc"].split("with error")
                desc = desc[0] + " " + str(params) + " " + desc[1]

        elif start_desc["worker"] == "mtc":
            desc = end_desc["desc"]

        else:
            desc = end_desc["desc"]
            print(start_desc)
            print(end_desc)
        # print(f"result {desc}")
        return desc

    def export_steps_to_excel(self):
        import pandas as pd
        from tkinter import filedialog, messagebox

        # Extract data from the table
        rows = []
        for row_id in self.steps_table.get_children():
            values = self.steps_table.item(row_id)["values"]
            rows.append({
                "Description": values[0],
                "Start Time": values[1],
                "End Time": values[2],
                "Duration (sec)": values[3],
            })

        if not rows:
            messagebox.showwarning("No Data", "There are no steps to export.")
            return

        df = pd.DataFrame(rows)

        # Ask user where to save the file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Save as"
        )

        if file_path:
            try:
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Export Successful", f"Steps exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Error: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskViewerApp(root)
    root.mainloop()
