import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox
from tkcalendar import DateEntry

import pandas as pd

from GUI.gui_elements import GUIElements
from GUI.graphing import GraphingManager
from DB.connection import MongoDBManager
from config_py import farm_connection_str, COWS_DB


class MilkingDataGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MongoDB Interactive GUI")
        self.root.geometry("1200x800")

        # Split into top and bottom sections
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # GUI controls go to top
        self.gui = GUIElements(self.top_frame)

        # Graph will render in bottom
        self.graphing = GraphingManager(self.bottom_frame)

        self.db = None
        self.current_df = None
        self.filter_entries = {}
        self.date_field_dropdown = None
        self.start_date_entry = None
        self.end_date_entry = None

        self.setup_initial_ui()

    def setup_initial_ui(self):
        self.gui.create_label("Mongo URI:", 0, 0)
        self.mongo_uri_entry = self.gui.create_entry(0, 1, default_text=farm_connection_str)

        self.gui.create_label("Database Name:", 1, 0)
        self.db_name_entry = self.gui.create_entry(1, 1 , default_text=COWS_DB)

        self.connect_button = self.gui.create_button("Connect", self.connect_to_db, 2, 0)

    def connect_to_db(self):
        uri = self.mongo_uri_entry.get()
        db_name = self.db_name_entry.get()
        try:
            self.db = MongoDBManager(uri, db_name)
            self.db.connect()
            self.show_collection_selector()
        except Exception as e:
            print(f"Connection error: {e}")

    def show_collection_selector(self):
        self.gui.create_label("Select Collection:", row=0, column=2)
        self.collection_dropdown = self.gui.create_combobox(
            self.db.get_collections(), row=0, column=3
        )
        self.gui.create_button("Load Collection", self.preview_collection_data, row=1, column=2)

    def preview_collection_data(self):
        collection_name = self.collection_dropdown.get()
        docs = self.db.get_documents(collection_name,limit=100)
        if not docs:
            messagebox.showerror("Error", "No data found in selected collection.")
            return

        # Clear previous widgets except the initial connection ones (rows 0 and 1)
        for widget in self.top_frame.grid_slaves():
            if int(widget.grid_info()["row"]) > 1:
                widget.grid_forget()

        self.current_df = pd.DataFrame(docs)
        self.filter_entries.clear()

        self.gui.create_label("Filter Fields:", 2, 0)
        for col_index, column in enumerate(self.current_df.columns):
            self.gui.create_label(column, 3, col_index)
            entry = self.gui.create_entry(4, col_index)
            self.filter_entries[column] = entry

        self.gui.create_label("X Axis:", 5, 0)
        self.x_dropdown = self.gui.create_combobox(list(self.current_df.columns), 5, 1)
        self.categorical_var = self.gui.create_checkbox("Categorical X-Axis", row=5, column=2)

        self.gui.create_label("Y Axis:", 6, 0)
        y_fields = list(self.current_df.columns) + ["Frequency"]
        self.y_dropdown = self.gui.create_combobox(y_fields, 6, 1)

        self.gui.create_label("Graph Type:", 7, 0)
        self.graph_type_dropdown = self.gui.create_combobox(["Line", "Bar", "Scatter", "Pie"], 7, 1)

        self.gui.create_label("Y Aggregation:", row=7, column=2)
        self.y_agg_dropdown = self.gui.create_combobox(
            values=["None", "SUM", "AVG", "MAX", "MIN", "COUNT"],
            row=7,
            column=3,
            default_index=0
        )

        self.gui.create_label("Date Field:", 8, 0)
        date_candidates = [col for col in self.current_df.columns if
                           'date' in col.lower() or 'time' in col.lower() or 'start' in col.lower() or 'end' in col.lower()]
        self.date_field_dropdown = self.gui.create_combobox(date_candidates, 8, 1)

        default_start = datetime.now() - timedelta(days=7)
        default_end = datetime.now()

        self.start_date_picker = DateEntry(self.top_frame, width=12, year=default_start.year, month=default_start.month,
                                           day=default_start.day)
        self.start_date_picker.grid(row=8, column=2)

        self.end_date_picker = DateEntry(self.top_frame, width=12, year=default_end.year, month=default_end.month,
                                         day=default_end.day)
        self.end_date_picker.grid(row=8, column=3)

        self.gui.create_button("Plot", self.plot_filtered_data, 10, 0)

    def plot_filtered_data(self):
        query = {}

        # Apply field filters
        for col, entry in self.filter_entries.items():
            value = entry.get().strip()
            if value:
                try:
                    # Convert numeric fields properly
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass  # Keep as string if it's not a number
                query[col] = value

        # Apply date range filter
        date_col = self.date_field_dropdown.get()
        start_date = pd.to_datetime(self.start_date_picker.get_date(), errors='coerce')
        end_date = pd.to_datetime(self.end_date_picker.get_date(), errors='coerce')

        if date_col and pd.notnull(start_date) and pd.notnull(end_date):
            query[date_col] = {
                "$gte": start_date,
                "$lte": end_date
            }

        # --- Fetch from Mongo with filters ---
        collection_name = self.collection_dropdown.get()
        docs = self.db.get_documents(collection_name, query=query)
        df = pd.DataFrame(docs)
        self.current_df = df
        if df.empty:
            messagebox.showinfo("No Data", "No data matches the selected filters.")
            return

        x_col = self.x_dropdown.get()
        y_col = self.y_dropdown.get()
        # Handle Frequency
        if y_col == "Frequency":
            df = df[x_col].value_counts().reset_index()
            df.columns = [x_col, "Frequency"]
            y_col = "Frequency"

        agg_func = self.y_agg_dropdown.get()

        # --- Apply aggregation if selected ---
        if agg_func != "None" and x_col in df.columns and y_col in df.columns:
            try:
                if agg_func == "SUM":
                    df = df.groupby(x_col)[y_col].sum().reset_index()
                elif agg_func == "AVG":
                    df = df.groupby(x_col)[y_col].mean().reset_index()
                elif agg_func == "MAX":
                    df = df.groupby(x_col)[y_col].max().reset_index()
                elif agg_func == "MIN":
                    df = df.groupby(x_col)[y_col].min().reset_index()
                elif agg_func == "COUNT":
                    df = df.groupby(x_col)[y_col].count().reset_index()
            except Exception as e:
                messagebox.showerror("Aggregation Error", f"Failed to apply aggregation: {e}")
                return

        graph_type = self.graph_type_dropdown.get()
        categorical_x = self.categorical_var.get()
        print(categorical_x)
        # --- Call appropriate graph function ---
        if graph_type == "Line":
            self.graphing.create_line_chart(df, x_col, y_col, f"{y_col} over {x_col}", categorical_x=categorical_x)
        elif graph_type == "Bar":
            self.graphing.create_bar_chart(df, x_col, y_col, title=f"{y_col} by {x_col}", categorical_x=categorical_x)
        elif graph_type == "Scatter":
            self.graphing.create_scatter_plot(df, x_col, y_col, title=f"{y_col} vs {x_col}", categorical_x=categorical_x)
        elif graph_type == "Pie":
            self.graphing.create_pie_chart(df, x_col, y_col, title=f"{y_col} per {x_col}")
        else:
            messagebox.showwarning("Graph Error", "Please select a valid graph type.")


def main():
    root = tk.Tk()
    app = MilkingDataGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
