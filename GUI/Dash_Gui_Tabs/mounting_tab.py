# mounting_tab.py
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from datetime import datetime
from bson import ObjectId

# Available analysis types
ANALYSIS_OPTIONS = [
    {"label": "Mounting duration by cow and teat", "value": "duration"},
    {"label": "Mounting success by cow and teat", "value": "success"},
    {"label": "Error distribution by cow and teat", "value": "errors"},
    {"label": "Retries until success by cow and teat", "value": "retries"},
    {"label": "Mounting results over time", "value": "over_time"}
]

def mounting_layout(mongo_handler):
    return dbc.Container([
        html.H4("Mounting Data Analysis", className="my-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Select Analysis"),
                dcc.Dropdown(
                    id="mounting-analysis-type",
                    options=ANALYSIS_OPTIONS,
                    placeholder="Choose analysis"
                )
            ], width=4),
            dbc.Col([
                dbc.Label("Cow ID"),
                dcc.Input(id="filter-cow-id", type="number", placeholder="Optional", className="form-control")
            ], width=2),
            dbc.Col([
                dbc.Label("Teat ID"),
                dcc.Input(id="filter-teat-id", type="number", placeholder="Optional", className="form-control")
            ], width=2),
            dbc.Col([
                dbc.Label("Start Date"),
                dcc.DatePickerSingle(id="filter-start-date")
            ], width=2),
            dbc.Col([
                dbc.Label("End Date"),
                dcc.DatePickerSingle(id="filter-end-date")
            ], width=2)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Plot", id="mounting-plot-button", color="primary", className="me-2")
            ])
        ], className="mb-3"),
        dcc.Loading(html.Div(id="mounting-plot-container"), type="circle")
    ], fluid=True)

def register_callbacks(app, mongo_handler):

    @app.callback(
        Output("mounting-plot-container", "children"),
        Input("mounting-plot-button", "n_clicks"),
        State("mounting-analysis-type", "value"),
        State("filter-cow-id", "value"),
        State("filter-teat-id", "value"),
        State("filter-start-date", "date"),
        State("filter-end-date", "date")
    )
    def analyze_mounting_data(n_clicks, analysis_type, cow_id, teat_id, start_date, end_date):
        if not n_clicks or not analysis_type:
            return html.Div("Select analysis type and click Plot.")

        # === Build MongoDB query ===
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

        # === Fetch Data ===
        coll = mongo_handler.db["Mounting_Data_Collection"]
        docs = list(coll.find(query))

        if not docs:
            return html.Div("No data found for the selected filters.")

        # === Convert to DataFrame ===
        for doc in docs:
            doc["_id"] = str(doc["_id"])  # make _id serializable
            doc["start"] = pd.to_datetime(doc["start"]["$date"]) if isinstance(doc["start"], dict) else pd.to_datetime(doc["start"])
            doc["end"] = pd.to_datetime(doc["end"]["$date"]) if isinstance(doc["end"], dict) else pd.to_datetime(doc["end"])
            doc["duration_sec"] = (doc["end"] - doc["start"]).total_seconds()

        df = pd.DataFrame(docs)

        if analysis_type == "duration":
            # Group by cow and teat
            grouped = df.groupby(["cow_id", "teat_id"])["duration_sec"].mean().reset_index()
            grouped["cow_id"] = grouped["cow_id"].astype(str)  # make cow_id categorical
            grouped["teat_id"] = grouped["teat_id"].astype(str)  # 🆕 Force teat_id to be categorical

            fig = px.bar(
                grouped,
                x="cow_id",
                y="duration_sec",
                color="teat_id",
                barmode="group",  # show side-by-side bars
                labels={"duration_sec": "Average Mounting Duration (sec)", "cow_id": "Cow ID", "teat_id": "Teat"},
                title="Average Mounting Duration by Cow and Teat"
            )

            return dcc.Graph(figure=fig)
        # Mounting Success
        elif analysis_type == "success":
            # Determine success per document
            def is_success(mounting_data):
                if not isinstance(mounting_data, dict):
                    return False
                numeric_keys = [int(k) for k in mounting_data.keys() if k.isdigit()]
                if not numeric_keys:
                    return False
                last_key = str(max(numeric_keys))
                return str(mounting_data.get(last_key, [None])[0]) == "Mounted_successfully"

            df["success"] = df["Mounting_data"].apply(is_success)
            df["cow_id"] = df["cow_id"].astype(str)
            df["teat_id"] = df["teat_id"].astype(str)

            grouped = df.groupby(["cow_id", "teat_id"]).agg(
                success_rate=("success", "mean"),
                trial_count=("success", "count")
            ).reset_index()

            grouped["success_percent"] = grouped["success_rate"] * 100
            grouped["label"] = grouped["success_percent"].round(1).astype(str) + "% (" + grouped["trial_count"].astype(
                str) + " trials)"

            fig = px.bar(
                grouped,
                x="cow_id",
                y="success_percent",
                color="teat_id",
                barmode="group",
                text=grouped["label"],
                labels={
                    "success_percent": "Mounting Success Rate (%)",
                    "cow_id": "Cow ID",
                    "teat_id": "Teat ID"
                },
                title="Mounting Success Rate by Cow and Teat"
            )
            fig.update_traces(textposition="auto")
            fig.update_yaxes(range=[0, 100])

            return dcc.Graph(figure=fig)
        # Placeholder for other analysis types
        return html.Div("This analysis is not implemented yet.")
