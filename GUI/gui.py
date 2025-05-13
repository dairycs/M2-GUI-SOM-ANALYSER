import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from gui_elements import create_filter_frame, create_plot_frame
from DB import get_collections, get_collection_data

class MongoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MongoDB Data Explorer")
        self.root.geometry("1200x700")

        # Variables
        self.selected_collection = tk.StringVar()

        # Layout
        self.create_widgets()

    def create_widgets(self):
        # Collection selection
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill='x', pady=10, padx=10)

        ttk.Label(top_frame, text="Select Collection:").pack(side='left')
        collections = get_collections()
        self.collection_combo = ttk.Combobox(top_frame, values=collections, textvariable=self.selected_collection)
        self.collection_combo.pack(side='left', padx=5)
        self.collection_combo.bind("<<ComboboxSelected>>", self.on_collection_selected)

        # Main area: filters + plot
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True)

        self.filter_frame = ttk.LabelFrame(self.main_frame, text="Filters")
        self.filter_frame.pack(side='left', fill='y', padx=10, pady=10)

        self.plot_frame = ttk.LabelFrame(self.main_frame, text="Plot")
        self.plot_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)

    def on_collection_selected(self, event):
        selected = self.selected_collection.get()
        if not selected:
            return

        data = get_collection_data(selected)
        if not data:
            return

        # Clear previous frames
        for widget in self.filter_frame.winfo_children():
            widget.destroy()
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Create new filter and plot interface
        create_filter_frame(self.filter_frame, data, self.update_plot)
        create_plot_frame(self.plot_frame)

    def update_plot(self, filtered_data, x_field, y_field, plot_type):
        from graphing import plot_graph
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        plot_graph(self.plot_frame, filtered_data, x_field, y_field, plot_type)


def run_gui():
    root = tk.Tk()
    app = MongoGUI(root)
    root.mainloop()
