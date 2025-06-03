# -*- coding: utf-8 -*-
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, MATCH, ALL, ctx
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from collections import defaultdict

from GUI.Dash_Gui_Tabs.global_tab import global_layout, global_callbacks
from GUI.Dash_Gui_Tabs.milking_tab import milking_layout , register_callbacks as milking_callbacks
from GUI.Dash_Gui_Tabs.mounting_tab import mounting_layout , register_callbacks as mounting_callbacks
from GUI.Dash_Gui_Tabs.tasks_analysis_tab import task_layout , register_callbacks as task_callbacks
from GUI.graphing import GraphingManager
from DB.connection import MongoDBManager
from config_py import farm_connection_str, COWS_DB
graph_mgr = GraphingManager()

# Initialize app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "MongoDB Interactive Dashboard"

mongo_handler = MongoDBManager(farm_connection_str, COWS_DB)
mongo_handler.connect()
collections = mongo_handler.get_collections()

tabs = dbc.Tabs(
    [
        dbc.Tab(global_layout(mongo_handler ,app), label="Farm Data", tab_id="global-tab"),
        dbc.Tab(mounting_layout(mongo_handler ), label="Mounting Data", tab_id="mounting-tab"),
        dbc.Tab(milking_layout(mongo_handler), label="Milking Data", tab_id="milking-tab"),
        dbc.Tab(task_layout(mongo_handler), label="Tasks Data", tab_id="task-tab")
    ],
    id="data-tabs", active_tab="global-tab"  # set the first tab as active by default
)
app.layout = dbc.Container([html.H2("Farm Data Dashboard"), tabs], fluid=True)


mounting_callbacks(app, mongo_handler)
milking_callbacks(app, mongo_handler)
global_callbacks(app , mongo_handler)
task_callbacks(app , mongo_handler)
def main():
    app.run(debug=True)
