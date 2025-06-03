# mounting_tab.py
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from bson import ObjectId
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)


# Available analysis types
ANALYSIS_OPTIONS = [
    {"label": "Mounting duration by cow and teat", "value": "duration"},
    {"label": "Mounting success by cow and teat", "value": "success"},
    {"label": "Retries until success by cow and teat", "value": "retries"},
    {"label": "Success over time", "value": "success_over_time"},
    {"label": "Retries over time", "value": "retries_over_time"},
    {"label": "Error distribution by cow and teat", "value": "errors"},
    {"label": "Error distribution over time", "value": "errors_over_time"},

]


def is_success(mounting_data):
    if not isinstance(mounting_data, dict):
        return 0

    numeric_keys = [int(k) for k in mounting_data.keys() if k.isdigit()]
    if not numeric_keys:
        return 0

    last_key = str(max(numeric_keys))
    if isinstance(mounting_data[last_key], list):
        return 1 if mounting_data[last_key][0] == "Mounted_successfully" else 0
    return 0


def mounting_retry(mounting_data):
    if not isinstance(mounting_data, dict):
        return 1

    numeric_keys = [int(k) for k in mounting_data.keys() if k.isdigit()]
    if not numeric_keys:
        return 1
    print(max(numeric_keys))
    return max(numeric_keys)

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
                dcc.DatePickerSingle(id="filter-start-date" ,date=(datetime.now() - timedelta(days=7)).date() )
            ], width=2),
            dbc.Col([
                dbc.Label("End Date"),
                dcc.DatePickerSingle(id="filter-end-date", date=(datetime.now()+ timedelta(days=1)).date())
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
        import plotly.express as px
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go
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
        # print(df["duration_sec"])

        if analysis_type == "duration":
            # Group by cow and teat

            df["cow_id"] = df["cow_id"].astype(str)
            df["teat_id"] = df["teat_id"].astype(str)
            df["duration_sec"] = df["duration_sec"].round(1)
            df = df[df["duration_sec"] < 7200]  # filter out corrupted rows
            df = df[df["duration_sec"] > 0]  # optional: remove zero/negative

            grouped = df.groupby(["cow_id", "teat_id"])["duration_sec"].mean().reset_index()

            print(grouped)
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


            # Apply function to each row
            df["success"] = df["Mounting_data"].apply(is_success)

            df["cow_id"] = df["cow_id"].astype(str)
            df["teat_id"] = df["teat_id"].astype(str)
            # print(df[df["cow_id"] == "60"])
            # print(df[df["teat_id"] == "2"])
            # print(df[(df["cow_id"] == "60") & (df["teat_id"] == "2")])
            grouped = df.groupby(["cow_id", "teat_id"]).agg(
                success_rate=("success", "mean"),
                trial_count=("success", "count")
            ).reset_index()

            grouped["success_percent"] = grouped["success_rate"] * 100
            grouped["label"] = grouped["success_percent"].round(1).astype(str) + "% (" + grouped["trial_count"].astype(
                str) + " trials)"
            print(grouped)

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

        elif analysis_type == "retries":


            # Apply function to each row
            df["success"] = df["Mounting_data"].apply(is_success)
            df["mounting_retry"] = df["Mounting_data"].apply(mounting_retry)

            df["cow_id"] = df["cow_id"].astype(str)
            df["teat_id"] = df["teat_id"].astype(str)
            grouped = df.groupby(["cow_id", "teat_id"]).agg(
                mounting_retry=("mounting_retry", "sum"),
                trial_count=("success", "sum")
            ).reset_index()

            grouped["retry_to_success"] = grouped["mounting_retry"] / grouped["trial_count"]
            grouped["label"] = grouped["retry_to_success"].round(1).astype(str) + " (" + grouped["mounting_retry"].astype(
                str) + " Mounting trials)"
            print(grouped)

            fig = px.bar(
                grouped,
                x="cow_id",
                y="retry_to_success",
                color="teat_id",
                barmode="group",
                text=grouped["label"],
                labels={
                    "retry_to_success": "Mounting retry to Success AVG ",
                    "cow_id": "Cow ID",
                    "teat_id": "Teat ID"
                },
                title="Mounting Retry to Success  by Cow and Teat"
            )
            fig.update_traces(textposition="auto")
            return dcc.Graph(figure=fig)
        elif analysis_type == "success_over_time":
            df["success"] = df["Mounting_data"].apply(is_success)
            df["cow_id"] = df["cow_id"].astype(str)
            df["teat_id"] = df["teat_id"].astype(str)
            df["date"] = df["start"].dt.date.astype(str)

            grouped = df.groupby(["date", "cow_id", "teat_id"]).agg(
                success_rate=("success", "mean"),
                trial_count=("success", "count")
            ).reset_index()
            grouped["annotation"] = grouped["trial_count"].astype(str) + " trials"

            fig = px.line(
                grouped,
                x="date",
                y="success_rate",
                color="teat_id",
                line_group="cow_id",
                markers=True,
                labels={
                    "success_rate": "Success Rate",
                    "date": "Date",
                    "teat_id": "Teat ID"
                },
                title="Mounting Success Rate Over Time by Cow and Teat",
                text="annotation"  # 👈 this adds text annotations
            )

            fig.update_yaxes(range=[0, 1])
            fig.update_layout(
                title={
                    "text": "Mounting Success Rate Over Time by Cow and Teat",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": dict(size=20)
                },
                xaxis_title="Date",
                yaxis_title="Success Rate",
                legend_title="Teat, Cow",
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.3,
                    xanchor="center",
                    x=0.5
                ),
                hovermode="x unified",
                template="simple_white",
                margin=dict(l=40, r=20, t=60, b=60),
            )
            fig.update_traces(
                mode="lines+markers",
                marker=dict(size=6),
                line=dict(width=2),
            )
            fig.update_traces(textposition="top center", textfont_size=12)

            fig.update_xaxes(
                tickformat="%b %d",  # Format as "May 01"
                tickangle=45,
                dtick="D1"  # Force daily ticks if many days
            )

            return dcc.Graph(figure=fig)

        elif analysis_type == "retries_over_time":
            df["success"] = df["Mounting_data"].apply(is_success)
            df["mounting_retry"] = df["Mounting_data"].apply(mounting_retry)
            df["cow_id"] = df["cow_id"].astype(str)
            df["teat_id"] = df["teat_id"].astype(str)
            df["date"] = df["start"].dt.date.astype(str)

            grouped = df.groupby(["date", "cow_id", "teat_id"]).agg(
                total_retries=("mounting_retry", "sum"),
                total_successes=("success", "sum")
            ).reset_index()

            # Avoid division by zero
            grouped = grouped[grouped["total_successes"] > 0]

            # Calculate retries per success
            grouped["retries_per_success"] = grouped["total_retries"] / grouped["total_successes"]

            # Format annotation
            # grouped["annotation"] = grouped["retries_per_success"].round(1).astype(str) + \
            #                         "× (" + grouped["total_retries"].astype(str) + " retries)"

            fig = px.line(
                grouped,
                x="date",
                y="retries_per_success",
                color="teat_id",
                line_group="cow_id",
                markers=True,
                # text="annotation",
                hover_data={
                    "date": False,
                    "cow_id": False,
                    "teat_id": True,
                    "total_retries": True,
                    "total_successes": True,
                    "retries_per_success": ':.2f'
                },
                labels={
                    "retries_per_success": "Retries per Success",
                    "date": "Date",
                    "teat_id": "Teat ID"
                },
                title="📈 Daily Retries Needed per Successful Mounting (by Cow and Teat)"
            )

            fig.update_layout(
                title_font_size=18,
                title_x=0.5,
                legend_title_text="Teat ID",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                xaxis=dict(
                    tickangle=-45,
                    tickformat="%b %d"
                ),
                yaxis=dict(
                    title="Retries per Success",
                    rangemode="tozero"
                ),
                plot_bgcolor="rgba(248, 248, 255, 1)",
                paper_bgcolor="white",
                hovermode="x unified"
            )

            fig.update_traces(
                textposition="top center",
                textfont_size=12,
                line=dict(width=2),
                marker=dict(size=8)
            )

            return dcc.Graph(figure=fig)
        elif analysis_type == "errors":
            from collections import defaultdict

            # Create a list of all error occurrences
            error_records = []

            for _, row in df.iterrows():
                cow = row["cow_id"]
                teat = row["teat_id"]
                mounting_data = row.get("Mounting_data", {})

                if isinstance(mounting_data, dict):
                    for attempt, entry in mounting_data.items():
                        if isinstance(entry, list) and isinstance(entry[0], int):  # Error code
                            error_code = entry[0]
                            error_records.append({
                                "cow_id": str(cow),
                                "teat_id": str(teat),
                                "error_code": str(error_code)
                            })

            # Convert to DataFrame
            error_df = pd.DataFrame(error_records)

            # Group by cow, teat, and error
            grouped = error_df.groupby(["cow_id", "teat_id", "error_code"]).size().reset_index(name="count")

            # Optional: Pivot for heatmap-style plot
            pivot = grouped.pivot_table(index=["cow_id", "teat_id"], columns="error_code", values="count",
                                        fill_value=0).reset_index()

            # Or use bar chart
            import plotly.express as px
            grouped["label"] = grouped["error_code"].astype(str)
            fig = px.bar(
                grouped,
                x="cow_id",
                y="count",
                color="label",
                barmode="stack",
                facet_col="teat_id",
                labels={"count": "Error Count", "cow_id": "Cow ID", "label": "Error Code"},
                title="🚨 Error Distribution by Cow and Teat"
            )
            return dcc.Graph(figure=fig)

        elif analysis_type == "errors_over_time":
            # Extract error entries with date
            error_records = []

            for _, row in df.iterrows():
                cow = row["cow_id"]
                teat = row["teat_id"]
                start = row["start"].date()
                mounting_data = row.get("Mounting_data", {})

                if isinstance(mounting_data, dict):
                    for key, entry in mounting_data.items():
                        if isinstance(entry, list) and isinstance(entry[0], int):  # Error code
                            error_code = entry[0]
                            error_records.append({
                                "cow_id": str(cow),
                                "teat_id": str(teat),
                                "date": start,
                                "error_code": str(error_code)
                            })

            if not error_records:
                return html.Div("No errors found for selected filters.")

            error_df = pd.DataFrame(error_records)

            # Group by date, cow, teat, and error
            grouped = error_df.groupby(["date", "cow_id", "teat_id", "error_code"]).size().reset_index(name="count")
            grouped["label"] = grouped["error_code"] + " (" + grouped["count"].astype(str) + ")"
            grouped["teat_label"] = "Cow " + grouped["cow_id"].astype(str) + " - Teat " + grouped["teat_id"].astype(str)
            grouped["text"] = grouped["label"]

            teat_ids = sorted(grouped["teat_id"].unique())
            fig = make_subplots(
                rows=len(teat_ids),
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=[f"Teat ID = {teat}" for teat in teat_ids]
            )

            # Add one subplot per teat ID
            for i, teat in enumerate(teat_ids):
                sub_df = grouped[grouped["teat_id"] == teat]
                for error in sub_df["error_code"].unique():
                    error_data = sub_df[sub_df["error_code"] == error]
                    fig.add_trace(
                        go.Scatter(
                            x=error_data["date"],
                            y=error_data["count"],
                            mode="lines+markers",
                            name=f"{error}",
                            text=error_data["label"],
                            hovertemplate=(
                                    "Date: %{x|%Y-%m-%d}<br>" +
                                    "Error: %{text}<br>" +
                                    "Count: %{y}<extra></extra>"
                            ),
                            legendgroup=str(error),
                            showlegend=(i == 0)
                        ),
                        row=i + 1,
                        col=1
                    )

            # Layout tweaks
            fig.update_layout(
                hovermode="x unified",
                height=400 * len(teat_ids),
                title="Error Distribution Over Time by Cow and Teat",
                xaxis_title="Date",
                yaxis_title="Error Count",
                margin=dict(t=100)
            )

            fig.update_yaxes(title_text="Error Count")
            fig.update_xaxes(title_text="Date")
            fig.for_each_xaxis(lambda ax: ax.update(showticklabels=True))

            return dcc.Graph(figure=fig)

        # Placeholder for other analysis types
        return html.Div("This analysis is not implemented yet.")
