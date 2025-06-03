# milking_tab.py
from dash import html, dcc, Input, Output, State, callback, dash_table, dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from bson import ObjectId

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# Available analysis types
MILKING_ANALYSIS_OPTIONS = [
    {'label': 'Flow Rate Over Time', 'value': 'flow_over_time'},
    {'label': 'Milk Quantity Distribution', 'value': 'quantity_distribution'},

]
def milking_layout(mongo_handler):
    return dbc.Container([
        html.H4("Milking Data Analysis", className="my-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Select Analysis"),
                dcc.Dropdown(
                    id="milking-analysis-type",
                    options=MILKING_ANALYSIS_OPTIONS,
                    placeholder="Choose analysis"
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Cow ID"),
                dcc.Input(id="milking-filter-cow-id", type="number", placeholder="Optional", className="form-control")
            ], width=2),
            dbc.Col([
                dbc.Label("Teat ID"),
                dcc.Input(id="milking-filter-teat-id", type="number", placeholder="Optional", className="form-control")
            ], width=2),
            dbc.Col([
                dbc.Label("Start Date"),
                dcc.DatePickerSingle(id="milking-filter-start-date", date=(datetime.now() - timedelta(days=7)).date())
            ], width=2),
            dbc.Col([
                dbc.Label("End Date"),
                dcc.DatePickerSingle(id="milking-filter-end-date", date=(datetime.now()+ timedelta(days=1)).date())
            ], width=2)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Rolling Average Window Size"),
                dcc.Input(id="rolling-window", type="number", min=1, value=120, className="form-control")
            ], width=2),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H6("Recent Task IDs:"),
                html.Div(id="milking-task-id-table"),
                dbc.Label("Select Task ID to View Flow Graph"),
                dcc.Dropdown(id="milking-task-id-dropdown", placeholder="Select Task ID")
            ])
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Plot", id="milking-plot-button", color="primary", className="me-2")
            ])
        ], className="mb-3"),
        dcc.Dropdown(
            id="teat-selector",
            options=[{"label": f"Teat {i}", "value": i} for i in range(1, 5)],
            multi=True,
            value=[1, 2, 3, 4],  # ✅ Default selection
            placeholder="Select Teats (default: all)"
        ),
        dcc.Loading(html.Div(id="milking-plot-container"), type="circle")
    ], fluid=True)

def register_callbacks(app, mongo_handler):
    @app.callback(
        Output("milking-task-id-table", "children"),
        Output("milking-task-id-dropdown", "options"),
        Input("milking-analysis-type", "value"),
        State("milking-filter-cow-id", "value"),
        State("milking-filter-teat-id", "value"),
        State("milking-filter-start-date", "date"),
        State("milking-filter-end-date", "date")
    )
    def update_task_table(analysis_type, cow_id, teat_id, start_date, end_date):
        if analysis_type != 'flow_over_time':
            return html.Div(), []

        query = {}
        if cow_id is not None:
            query["cow_id"] = cow_id
        if teat_id is not None:
            query["teat_id"] = teat_id
        if start_date and end_date:
            query["start"] = {"$gte": pd.to_datetime(start_date), "$lte": pd.to_datetime(end_date)}

        coll = mongo_handler.db["Milking_Data_Collection"]
        docs = list(coll.find(query))

        if not docs:
            return html.Div("No data found for the selected filters."), []

        for doc in docs:
            doc["_id"] = str(doc["_id"])
            doc["start"] = pd.to_datetime(doc["start"])
            doc["end"] = pd.to_datetime(doc["end"])

        df = pd.DataFrame(docs)
        print(df)
        df_sorted = df.sort_values("start", ascending=False)
        last_task_ids = df_sorted["task_id"].drop_duplicates().head(10)
        df_last = df[df["task_id"].isin(last_task_ids)].copy()
        df_last = df_last.drop(columns=["flow_rate_data", "milk_quantity_data"], errors="ignore")
        df_last = df_last.sort_values("start", ascending=False)

        table = dash_table.DataTable(
            id="milking-task-table",
            columns=[
                {"name": "Task ID", "id": "task_id"},
                {"name": "Cow ID", "id": "cow_id"},
                {"name": "Milk Quantity", "id": "milk_quantity"},
                {"name": "AVG Flow Rate", "id": "flow_rate"},
                {"name": "Teat ID", "id": "teat_id"},
                {"name": "Start", "id": "start"},
                {"name": "End", "id": "end"},
            ],
            data=df_last.to_dict("records"),
            page_size=10
        )

        dropdown_options = [{"label": str(task_id), "value": task_id} for task_id in last_task_ids]

        return table, dropdown_options

    @app.callback(
        Output("milking-plot-container", "children"),
        Input("milking-plot-button", "n_clicks"),
        State("milking-task-id-dropdown", "value"),
        State("rolling-window", "value"),
        Input("teat-selector", "value"),  # Add this input
        #
    # prevent_initial_call=True
    )
    def plot_flow_for_task(n_clicks ,task_id , rolling_window , selected_teats):
        import plotly.express as px
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go
        if not task_id:
            return html.Div("Please select a Task ID to plot.")

        coll = mongo_handler.db["Milking_Data_Collection"]
        docs = list(coll.find({"task_id": task_id}))
        if selected_teats:
            docs = [doc for doc in docs if doc["teat_id"] in selected_teats]
        from plotly.colors import DEFAULT_PLOTLY_COLORS

        teat_colors = {
            1: DEFAULT_PLOTLY_COLORS[0],
            2: DEFAULT_PLOTLY_COLORS[1],
            3: DEFAULT_PLOTLY_COLORS[2],
            4: DEFAULT_PLOTLY_COLORS[3],
        }

        fig = go.Figure()
        all_starts = [
            pd.to_datetime(doc["start"]["$date"] if isinstance(doc["start"], dict) else doc["start"])
            for doc in docs
        ]
        global_start = min(all_starts)

        for doc in docs:
            teat = doc["teat_id"]
            flow_data = pd.Series(doc.get("flow_rate_data", []))
            milk_data = pd.Series(doc.get("milk_quantity_data", []))
            if flow_data.empty:
                continue

            start = pd.to_datetime(doc["start"]["$date"] if isinstance(doc["start"], dict) else doc["start"])
            end = pd.to_datetime(doc["end"]["$date"] if isinstance(doc["end"], dict) else doc["end"])
            duration_sec = (end - start).total_seconds()

            # Align time to global start
            x_values = [
                (start - global_start).total_seconds() + i * duration_sec / (len(flow_data) - 1)
                for i in range(len(flow_data))
            ]

            smoothed_flow = flow_data.rolling(window=rolling_window or 12, min_periods=1).mean()
            smoothed_milk = milk_data.rolling(window=rolling_window or 12,
                                              min_periods=1).mean() if not milk_data.empty else None

            # FLOW trace (solid line)
            fig.add_trace(go.Scatter(
                x=x_values,
                y=smoothed_flow,
                mode="lines+markers",
                name=f"Teat {teat}",
                line=dict(color=teat_colors[teat], width=2, dash="solid"),
                marker=dict(size=4),
                hovertemplate=f"Teat {teat}<br>Time: %{{x:.1f}} sec<br>Flow: %{{y:.3f}}"
            ))

            # MILK trace (dotted line with same color)
            if smoothed_milk is not None:
                fig.add_trace(go.Scatter(
                    x=x_values,
                    y=smoothed_milk,
                    mode="lines+markers",
                    name=f"Teat {teat} - Milk",
                    line=dict(color=teat_colors[teat], width=2, dash="dot"),
                    marker=dict(size=4),
                    hovertemplate=f"Teat {teat} - Milk<br>Time: %{{x:.1f}} sec<br>Milk: %{{y:.3f}}"
                ))

        fig.update_layout(
            title=f"Flow Rate Over Duration (sec) for Task {task_id} COW: {doc['cow_id']}",
            xaxis_title="Milking Duration (seconds)",
            yaxis_title="Flow Rate / Milk Quantity",
            height=600,
            hovermode="x unified",
            template="plotly_white",
            legend_title="Teat ID"
        )

        return dcc.Graph(figure=fig)
