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
    """
    Returns a Dash layout for the Milking Data tab.
    Connects via mongo_handler to fetch sample data from Milking_Data_Collection and displays it in a DataTable.
    """
    # pass
    # Fetch first 10 documents from the Milking_Data_Collection
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
                dcc.DatePickerSingle(id="milking-filter-end-date", date=datetime.now().date())
            ], width=2)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Plot", id="milking-plot-button", color="primary", className="me-2")
            ])
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.H6("Recent Task IDs:"),
                html.Div(id="milking-task-id-table"),
                dbc.Label("Select Task ID to View Flow Graph"),
                dcc.Dropdown(id="milking-task-id-dropdown", placeholder="Select Task ID")
            ])
        ], className="mb-3"),

        dcc.Loading(html.Div(id="milking-plot-container"), type="circle")
    ], fluid=True)


def register_callbacks(app, mongo_handler):
    from dash import callback_context

    @app.callback(
        Output("milking-task-id-table", "children"),
        Output("milking-task-id-dropdown", "options"),
        Output("milking-task-id-dropdown", "value"),
        Output("milking-plot-container", "children"),
        Input("milking-plot-button", "n_clicks"),
        Input("milking-task-id-dropdown", "value"),
        State("milking-analysis-type", "value"),
        State("milking-filter-cow-id", "value"),
        State("milking-filter-teat-id", "value"),
        State("milking-filter-start-date", "date"),
        State("milking-filter-end-date", "date"),
        prevent_initial_call=True
    )
    def handle_milking_analysis(n_clicks, selected_task_id, analysis_type, cow_id, teat_id, start_date, end_date):
        import plotly.express as px
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go
        triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]

        coll = mongo_handler.db["Milking_Data_Collection"]

        if triggered_id == "milking-plot-button":
            query = {}
            if cow_id is not None:
                query["cow_id"] = cow_id
            if teat_id is not None:
                query["teat_id"] = teat_id
            if start_date and end_date:
                query["start"] = {
                    "$gte": pd.to_datetime(start_date),
                    "$lte": pd.to_datetime(end_date)
                }

            docs = list(coll.find(query))
            if not docs:
                return html.Div("No data found."), [], None, None

            for doc in docs:
                doc["_id"] = str(doc["_id"])
                doc["start"] = pd.to_datetime(doc["start"]["$date"] if isinstance(doc["start"], dict) else doc["start"])
                doc["end"] = pd.to_datetime(doc["end"]["$date"] if isinstance(doc["end"], dict) else doc["end"])
                doc["duration_sec"] = (doc["end"] - doc["start"]).total_seconds()

            df = pd.DataFrame(docs)

            if analysis_type == "flow_over_time":
                latest = df.sort_values("start", ascending=False).drop_duplicates("task_id").head(10)
                table = dbc.Table.from_dataframe(latest[["task_id", "cow_id", "teat_id", "start"]], striped=True,
                                                 bordered=True, hover=True)
                dropdown_options = [
                    {"label": f"Task {row.task_id} (Cow {row.cow_id}, Teat {row.teat_id})", "value": row.task_id} for
                    row in latest.itertuples()]
                return table, dropdown_options, None, None

            return None, [], None, html.Div("Analysis not implemented.")

        elif triggered_id == "milking-task-id-dropdown" and selected_task_id:
            doc = coll.find_one({"task_id": selected_task_id})
            if not doc:
                return dash.no_update, dash.no_update, dash.no_update, html.Div("Task ID not found.")

            flow_data = doc.get("flow_rate_data", [])
            if not flow_data:
                return dash.no_update, dash.no_update, dash.no_update, html.Div("No flow data available.")

            fig = go.Figure()
            fig.add_trace(go.Scatter(y=flow_data, mode="lines+markers", name="Flow Rate"))
            fig.update_layout(
                title=f"Flow Rate Data for Task {selected_task_id}",
                xaxis_title="Sample Index",
                yaxis_title="Flow Rate",
                height=500
            )
            return dash.no_update, dash.no_update, selected_task_id, dcc.Graph(figure=fig)

        return dash.no_update, dash.no_update, dash.no_update, None
