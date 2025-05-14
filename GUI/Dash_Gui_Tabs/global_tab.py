# mounting_tab.py
from dash import dash_table, html, dash  # Import Dash HTML and DataTable components
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, MATCH, ALL, ctx
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from collections import defaultdict
from GUI.graphing import GraphingManager
from DB.connection import MongoDBManager
from config_py import farm_connection_str, COWS_DB
graph_mgr = GraphingManager()

# Layout function for the Mounting Data tab
def global_layout(mongo_handler , app):
    collections = mongo_handler.get_collections()

    layout = dbc.Container([
        html.H2("MongoDB Data Visualizer", className="my-4 text-primary"),

        dbc.Row([
            dbc.Col([
                dbc.Label("Mongo URI:"),
                dcc.Input(id="mongo-uri", type="text", value=farm_connection_str, style={"width": "100%"})
            ]),
            dbc.Col([
                dbc.Label("Database Name:"),
                dcc.Input(id="db-name", type="text", value=COWS_DB, style={"width": "100%"})
            ]),
            dbc.Col([
                dbc.Label("Select Collection:"),
                dcc.Dropdown(id="collection-dropdown", options=[{"label": c, "value": c} for c in collections])
            ]),
            dbc.Col([
                dbc.Button("Load Collection", id="load-button", color="primary", className="mt-4")
            ])
        ], className="mb-4"),

        dcc.Loading(html.Div(id="filter-ui"), type="default"),
        html.Hr(),
        dcc.Store(id="filters-store", data=[]),
        dcc.Loading(
            id="loading-plot",
            type="circle",
            color="#0d6efd",  # Bootstrap primary color
            children=html.Div(id="plot-container"),
            style={"marginTop": "20px"}
        ),

    ], fluid=True)

    return layout

def global_callbacks(app , mongo_handler):
    @app.callback(
        Output("filter-ui", "children"),
        Input("load-button", "n_clicks"),
        State("collection-dropdown", "value")
    )
    def build_filter_ui(n_clicks, collection_name):
        if not collection_name:
            return html.Div("No collection selected.")

        print("Loading collection metadata...")
        docs = mongo_handler.get_documents(collection_name, limit=5)
        if not docs:
            return html.Div("No data found in this collection.")

        df = pd.DataFrame(docs)
        df.drop(columns=[col for col in df.columns if isinstance(df[col].iloc[0], dict)], inplace=True, errors='ignore')
        columns = df.columns.tolist()
        date_fields = [col for col in columns if any(k in col.lower() for k in ["date", "time", "start", "end"])]

        return html.Div([
            html.H5("Filters & Options", className="text-secondary mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Add Filter Field"),
                    dcc.Dropdown(id="new-filter-field", options=[{"label": c, "value": c} for c in columns],
                                 placeholder="Select field")
                ], width=2),
                dbc.Col([
                    dbc.Label("Value"),
                    dcc.Input(id="new-filter-value", type="text", placeholder="Enter value", className="form-control")
                ], width=2),
                dbc.Col([
                    dbc.Label("Type"),
                    dcc.Dropdown(
                        id="new-filter-type",
                        options=[
                            {"label": "String", "value": "string"},
                            {"label": "Number", "value": "number"},
                            {"label": "Boolean", "value": "boolean"}
                        ],
                        placeholder="Select type"
                    )
                ], width=2),

                dbc.Col([
                    dbc.Button("Add Filter", id="add-filter", color="secondary", className="mt-4 me-2"),
                    dbc.Button("Reset Filters", id="reset-filter", color="danger", className="mt-4")
                ], width=2)
            ]),

            html.Hr(),
            html.Div(id="dynamic-filters"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("X Axis"),
                    dcc.Dropdown(id="x-axis", options=[{"label": c, "value": c} for c in columns])
                ], width=2),
                dbc.Col([
                    dbc.Checklist(
                        id="categorical-x",
                        options=[{"label": "Treat X axis as categorical", "value": "categorical"}],
                        value=["categorical"],
                        inline=True
                    )
                ], width=2),
                dbc.Col([
                    dbc.Label("Y Axis"),
                    dcc.Dropdown(id="y-axis", options=[{"label": c, "value": c} for c in columns] + [
                        {"label": "Frequency", "value": "Frequency"}])
                ], width=2),
                dbc.Col([
                    dbc.Label("Group By"),
                    dcc.Dropdown(
                        id="group-column",
                        options=[{"label": c, "value": c} for c in df.columns],
                        placeholder="Optional grouping field"
                    )
                ], width=2),

                dbc.Col([
                    dbc.Label("Graph Type"),
                    dcc.Dropdown(id="graph-type", value="Line", options=[
                        {"label": "Line", "value": "Line"},
                        {"label": "Bar", "value": "Bar"},
                        {"label": "Scatter", "value": "Scatter"},
                        {"label": "Pie", "value": "Pie"}
                    ])
                ], width=2)
                ,
                dbc.Col([
                    dbc.Label("Y Aggregation"),
                    dcc.Dropdown(id="agg-func", value="None",
                                 options=[{"label": x, "value": x} for x in
                                          ["None", "SUM", "AVG", "MAX", "MIN", "COUNT"]])
                ], width=2)
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Date Field"),
                    dcc.Dropdown(id="date-field", options=[{"label": d, "value": d} for d in date_fields])
                ], width=2),
                dbc.Col([
                    dbc.Label("Start Date"),
                    dcc.DatePickerSingle(id="start-date", date=(datetime.now() - timedelta(days=7)).date())
                ], width=2),
                dbc.Col([
                    dbc.Label("End Date"),
                    dcc.DatePickerSingle(id="end-date", date=datetime.now().date())
                ], width=2),
                dbc.Col([
                    dbc.Button("Plot", id="plot-button", color="success", className="mt-4")
                ], width=2)
            ])
        ], className="p-3 border rounded bg-light")

    @app.callback(
        Output("filters-store", "data"),
        Output("dynamic-filters", "children"),
        Input("add-filter", "n_clicks"),
        Input("reset-filter", "n_clicks"),
        State("new-filter-field", "value"),
        State("new-filter-value", "value"),
        State("new-filter-type", "value"),
        State("filters-store", "data")
    )
    def update_filter_list(add_clicks, reset_clicks, new_field, new_value, new_type, current_filters):
        triggered = ctx.triggered_id
        if triggered == "reset-filter":
            print("Filters reset.")
            return [], []

        if triggered == "add-filter" and new_field and new_value and new_type:
            current_filters.append({"field": new_field, "value": new_value, "type": new_type})
            print("Added filter:", new_field, new_value, new_type)

        children = [html.Div(f"{f['field']} = {f['value']}") for f in current_filters]
        return current_filters, children

    @app.callback(
        Output("plot-container", "children"),
        Input("plot-button", "n_clicks"),
        State("collection-dropdown", "value"),
        State("x-axis", "value"),
        State("y-axis", "value"),
        State("graph-type", "value"),
        State("agg-func", "value"),
        State("date-field", "value"),
        State("start-date", "date"),
        State("end-date", "date"),
        State("filters-store", "data"),
        State("categorical-x", "value"),
        State("group-column", "value"),
    )
    def generate_graph(n_clicks, collection, x_col, y_col, graph_type, agg_func, date_field, start_date, end_date,
                       current_filters, categorical_flag, group_column):
        if not n_clicks or not collection or not x_col or not y_col:
            raise dash.exceptions.PreventUpdate

        query = {}
        for f in current_filters:
            field = f['field']
            val = f['value']
            typ = f.get('type', 'string')
            if typ == 'number':
                try:
                    val = float(val)
                except ValueError:
                    continue
            elif typ == 'boolean':
                val = str(val).lower() == 'true'
            query[str(field)] = val

        # Date filter
        if date_field and start_date and end_date:
            query[date_field] = {
                "$gte": pd.to_datetime(start_date),
                "$lte": pd.to_datetime(end_date)
            }

        agg_map = {
            "SUM": "$sum",
            "AVG": "$avg",
            "MAX": "$max",
            "MIN": "$min",
            "COUNT": "$count"
        }

        pipeline = [{"$match": query}]
        df = pd.DataFrame()

        if y_col == "Frequency":
            pipeline.extend([
                {"$group": {
                    "_id": f"${x_col}",
                    "Frequency": {"$sum": 1}
                }},
                {"$project": {
                    x_col: "$_id",
                    "Frequency": 1,
                    "_id": 0
                }}
            ])
            docs = mongo_handler.get_aggregated_documents(collection, pipeline)
            df = pd.DataFrame(docs)
            y_col = "Frequency"

        elif agg_func != "None" and y_col != "Frequency":
            group_id = {x_col: f"${x_col}"}
            if group_column:
                group_id[group_column] = f"${group_column}"

            pipeline.append({
                "$group": {
                    "_id": group_id,
                    y_col: {agg_map[agg_func]: f"${y_col}"}
                }
            })

            # Project output to flat format
            project_fields = {y_col: 1}
            for key in group_id:
                project_fields[key] = f"$_id.{key}"
            project_fields["_id"] = 0

            pipeline.append({"$project": project_fields})

            docs = mongo_handler.get_aggregated_documents(collection, pipeline)
            df = pd.DataFrame(docs)

        else:
            docs = mongo_handler.get_documents(collection, query=query, limit=10000)
            df = pd.DataFrame(docs)

        if df.empty:
            return html.Div("No data found.")

        categorical_x = 'categorical' in (categorical_flag or [])
        title = f"{y_col} by {x_col}"

        if graph_type == "Bar":
            fig = graph_mgr.create_bar_chart(df, x_col, y_col, title, categorical_x=categorical_x,
                                             group_column=group_column)
        elif graph_type == "Line":
            fig = graph_mgr.create_line_chart(df, x_col, y_col, title, categorical_x=categorical_x,
                                              group_column=group_column)
        elif graph_type == "Scatter":
            fig = graph_mgr.create_scatter_plot(df, x_col, y_col, title, categorical_x=categorical_x,
                                                group_column=group_column)
        elif graph_type == "Pie":
            fig = graph_mgr.create_pie_chart(df, x_col, y_col, title)
        else:
            return html.Div("Unknown graph type.")

        return dcc.Graph(figure=fig)
