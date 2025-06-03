from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, timedelta

# Analysis options
TASK_ANALYSIS_OPTIONS = [
    {'label': 'Task Steps Table', 'value': 'task_steps_table'},
    {'label': 'Success Rate by Process', 'value': 'success_rate'}
]

def task_layout(mongo_handler):
    # Fetch latest 300 tasks
    latest_docs = list(mongo_handler.db["Tasks_collection"]
                       .find({}, {"worker": 1, "process": 1,"state":1,"task_id":1,"error":1})
                       .sort("start_time", -1)
                       .limit(3000))

    # Extract unique workers and processes
    workers = sorted(set(doc.get("worker", "") for doc in latest_docs if "worker" in doc))
    processes = sorted(set(doc.get("process", "") for doc in latest_docs if "process" in doc))
    states = sorted(set(doc.get("state", "") for doc in latest_docs if "state" in doc))
    errors = sorted(set(doc.get("error", "") for doc in latest_docs if "error" in doc))
    tasks = sorted(set(doc.get("task_id", "") for doc in latest_docs if "task_id" in doc))
    # print(errors)
    # print(states)
    # Create dropdown options
    worker_options = [{"label": w, "value": w} for w in workers]
    process_options = [{"label": p, "value": p} for p in processes]
    state_options = [{"label": s, "value": s} for s in states]
    error_options = [{"label": e, "value": e} for e in errors]
    tasks_options = [{"label": t, "value": t} for t in tasks]

    return dbc.Container([
        html.H4("Task Data Analysis", className="my-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Select Analysis"),
                dcc.Dropdown(
                    id="task-analysis-type",
                    options=TASK_ANALYSIS_OPTIONS,
                    placeholder="Choose analysis"
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Worker"),
                dcc.Dropdown(
                    id="tasks-filter-worker",
                    options=worker_options,
                    placeholder="Select Worker",
                    multi=True
                )
            ], width=2),
            dbc.Col([
                dbc.Label("Process"),
                dcc.Dropdown(
                    id="tasks-filter-process",
                    options=process_options,
                    placeholder="Select Process",
                    multi=True
                )
            ], width=2),
            dbc.Col([
                dbc.Label("Start Date"),
                dcc.DatePickerSingle(id="tasks-filter-start-date", date=(datetime.now() - timedelta(days=7)).date())
            ], width=2),
            dbc.Col([
                dbc.Label("End Date"),
                dcc.DatePickerSingle(id="tasks-filter-end-date", date=(datetime.now() + timedelta(days=1)).date())
            ], width=2)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("State"),
                dcc.Dropdown(
                    id="tasks-filter-state",
                    options=state_options,
                    placeholder="Select State",
                    multi=True
                )
            ], width=2),
            dbc.Col([
                dbc.Label("Error"),
                dcc.Dropdown(
                    id="tasks-filter-error",
                    options=error_options,
                    placeholder="Select Error",
                    multi=True
                )
            ], width=2),
            dbc.Col([
                dbc.Label("Tasks"),
                dcc.Dropdown(
                    id="tasks-filter-task_id",
                    options=tasks_options,
                    placeholder="Select Task_ID",
                    multi=True
                )
            ], width=2),
            dbc.Col([
                dbc.Button("Plot", id="task-plot-button", color="primary", className="me-2")
            ])
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.H6("Recent Tasks:"),
                html.Div(id="task-recent-table")
            ]),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Div(id="task-step-table-container")
            ])
        ]),
        dcc.Loading(html.Div(id="task-plot-container"), type="circle")
    ], fluid=True)


def register_callbacks(app, mongo_handler):
    @app.callback(
        Output("task-recent-table", "children"),
        Output("task-step-table-container", "children"),
        Input("tasks-filter-worker", "value"),
        Input("tasks-filter-process", "value"),
        Input("tasks-filter-state", "value"),
        Input("tasks-filter-error", "value"),
        Input("tasks-filter-task_id", "value"),
        Input("tasks-filter-start-date", "date"),
        Input("tasks-filter-end-date", "date"),
        prevent_initial_call=True
    )
    def update_task_table(worker_filter, process_filter, state_filter, error_filter,taskid_filter, start_date, end_date):
        query = {}
        if worker_filter:
            query["worker"] = {"$in": worker_filter}
        if process_filter:
            query["process"] = {"$in": process_filter}
        if state_filter:
            query["state"] = {"$in": state_filter}
        if error_filter:
            query["error"] = {"$in": error_filter}
        if taskid_filter:
            query["task_id"] = {"$in": taskid_filter}
        if start_date and end_date:
            query["start_time"] = {"$gte": pd.to_datetime(start_date), "$lte": pd.to_datetime(end_date)}

        docs = list(mongo_handler.db["Tasks_collection"].find(query).sort("start_time", -1).limit(100))
        if not docs:
            return html.Div("No data found.")

        for doc in docs:
            doc["_id"] = str(doc["_id"])
            doc["start_time"] = pd.to_datetime(doc["start_time"])
            doc["end_time"] = pd.to_datetime(doc["end_time"])

        df = pd.DataFrame(docs)
        recent_df = df[["task_id", "worker", "process", "state", "error", "start_time", "end_time"]].sort_values(
            "start_time", ascending=False)

        return dash_table.DataTable(
            columns=[{"name": i.replace("_", " ").title(), "id": i} for i in recent_df.columns],
            data=recent_df.to_dict("records"),
            page_size=10,
            style_table={"overflowX": "auto"}
        )
    @app.callback(
        Output("task-plot-container", "children"),
        Input("task-plot-button", "n_clicks"),
        State("task-analysis-type", "value"),
        State("tasks-filter-worker", "value"),
        State("tasks-filter-process", "value"),
        State("tasks-filter-state", "value"),
        State("tasks-filter-error", "value"),
        State("tasks-filter-start-date", "date"),
        State("tasks-filter-end-date", "date"),
        prevent_initial_call=True
    )
    def generate_task_plot(n_clicks, analysis_type, worker_filter, process_filter, state_filter, error_filter, start_date, end_date):
        query = {}
        if worker_filter:
            query["worker"] = {"$in": worker_filter}
        if process_filter:
            query["process"] = {"$in": process_filter}
        if state_filter:
            query["state"] = {"$in": state_filter}
        if error_filter:
            query["error"] = {"$in": error_filter}
        if start_date and end_date:
            query["start_time"] = {"$gte": pd.to_datetime(start_date), "$lte": pd.to_datetime(end_date)}

        docs = list(mongo_handler.db["Tasks_collection"].find(query).sort("start_time", -1))
        if not docs:
            return html.Div("No data found for plotting.")

        for doc in docs:
            doc["start_time"] = pd.to_datetime(doc["start_time"])
            doc["end_time"] = pd.to_datetime(doc["end_time"])

        df = pd.DataFrame(docs)

        if analysis_type == "success_rate":
            summary = df.groupby(["worker", "process", "state"]).size().unstack(fill_value=0)
            success_df = summary.reset_index()
            bar_fig = {
                "data": [
                    dict(
                        x=success_df["process"],
                        y=success_df.get("completed", success_df.get("completed_successfully", 0)),
                        type="bar",
                        name="Completed"
                    )
                ],
                "layout": dict(
                    title="Success Rate by Process",
                    xaxis={"title": "Process"},
                    yaxis={"title": "Count"},
                    barmode="group"
                )
            }
            return dcc.Graph(figure=bar_fig)
        elif analysis_type == "task_steps_table":
            task_table = dash_table.DataTable(
                columns=[{"name": i.replace("_", " ").title(), "id": i} for i in df.columns],
                data=df.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto"}
            )
            all_rows = []
            for doc in docs:
                task_id = doc["task_id"]
                state = doc.get("state", "unknown")

                for step in doc.get("task_steps", []):
                    try:
                        start = pd.to_datetime(step["start"])
                        end = pd.to_datetime(step["end"])
                        duration = (end - start).total_seconds() if end else None
                        all_rows.append({
                            "task_id": task_id,
                            "task_state": state,
                            "step_name": step["step_name"],
                            "step_status": step["step_status"],
                            "start": start,
                            "end": end,
                            "duration": duration
                        })
                    except Exception as err:
                        print(err, step)
            df_steps = pd.DataFrame(all_rows)
            steps_table = dash_table.DataTable(
                columns=[{"name": col.replace("_", " ").title(), "id": col} for col in df_steps.columns],
                data=df_steps.to_dict("records"),
                page_size=20,
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{step_status} != "completed_successfully"'},
                        'backgroundColor': '#FFCCCC',
                        'color': 'red'
                    }
            ],
                style_table={"overflowX": "auto"}
            )
            return  steps_table

        return html.Div("Analysis type not implemented.")
