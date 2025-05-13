import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

class GraphingManager:
    def __init__(self):
        pass

    def create_bar_chart(self, df, x_column, y_column, title="", categorical_x=False, group_column=None):
        if categorical_x:
            df[x_column] = df[x_column].astype(str)

        if group_column and group_column in df.columns:
            df[group_column] = df[group_column].astype(str)
            fig = px.bar(df, x=x_column, y=y_column, color=group_column, title=title)
            fig.update_layout(barmode="group")
        else:
            fig = px.bar(df, x=x_column, y=y_column, title=title)

        return fig

    def create_line_chart(self, df: pd.DataFrame, x_column: str, y_column: str, title: str = "",
                          categorical_x: bool = False, group_column: str = None):

        if categorical_x:
            df[x_column] = df[x_column].astype(str)

        if group_column and group_column in df.columns:
            fig = px.line(df, x=x_column, y=y_column, color=group_column, markers=True, title=title)
        else:
            fig = px.line(df, x=x_column, y=y_column, markers=True, title=title)
        fig.update_traces(connectgaps=False)

        return fig

    def create_pie_chart(self, df: pd.DataFrame, names_column: str, values_column: str, title: str = ""):
        fig = px.pie(df, names=names_column, values=values_column, title=title)
        return fig

    def create_scatter_plot(self, df, x_column: str, y_column: str, title: str = "",
                            categorical_x: bool = False, group_column: str = None):
        if categorical_x:
            df[x_column] = df[x_column].astype(str)

        if group_column and group_column in df.columns:
            df[group_column] = df[group_column].astype(str)
            fig = px.scatter(df, x=x_column, y=y_column, color=group_column, title=title)
        else:
            fig = px.scatter(df, x=x_column, y=y_column, title=title)

        return fig

    def plot_grouped_lines(self, df, x_column, y_column, group_column, title=""):
        fig = px.line(df, x=x_column, y=y_column, color=group_column, title=title)
        return fig
