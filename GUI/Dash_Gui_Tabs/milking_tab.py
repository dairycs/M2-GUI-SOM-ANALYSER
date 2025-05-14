# milking_tab.py
from dash import dash_table, html
import dash_bootstrap_components as dbc


def milking_layout(mongo_handler):
    """
    Returns a Dash layout for the Milking Data tab.
    Connects via mongo_handler to fetch sample data from Milking_Data_Collection and displays it in a DataTable.
    """
    # Fetch first 10 documents from the Milking_Data_Collection
    collection = mongo_handler.db["Milking_Data_Collection"]
    sample_docs = list(collection.find().limit(10))
    for doc in sample_docs:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])  # convert ObjectId to string if present

    # Define DataTable columns using the first document's keys
    columns = [{"name": str(key), "id": str(key)} for key in sample_docs[0].keys()] if sample_docs else []

    # Create the DataTable for Milking data
    data_table = dash_table.DataTable(
        data=sample_docs,
        columns=columns,
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left"}
    )

    # Assemble the layout with a Bootstrap container
    tab_content = dbc.Container(
        [
            html.H4("Milking Data Sample", className="my-3"),
            data_table
        ],
        fluid=True,
        className="pt-4"
    )
    return tab_content


def register_callbacks(app, mongo_handler):
    """
    (Optional) Register callbacks for the Milking Data tab.
    Currently not needed for static display.
    """
    # No interactive callbacks for this tab in the basic implementation.
    pass
