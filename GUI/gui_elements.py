from dash import html, dcc

def create_label(text: str):
    return html.Label(text)

def create_entry(id: str, default_text: str = "", width: str = "100%"):
    return dcc.Input(
        id=id,
        type="text",
        value=default_text,
        style={"width": width, "margin": "5px"}
    )

def create_combobox(id: str, options: list, default_value=None):
    return dcc.Dropdown(
        id=id,
        options=[{"label": val, "value": val} for val in options],
        value=default_value or (options[0] if options else None),
        style={"width": "100%", "margin": "5px"}
    )

def create_button(id: str, text: str):
    return html.Button(text, id=id, style={"margin": "5px"})

def create_checkbox(id: str, text: str, default_checked: bool = False):
    return dcc.Checklist(
        id=id,
        options=[{"label": text, "value": "checked"}],
        value=["checked"] if default_checked else [],
        labelStyle={"display": "inline-block"},
        style={"margin": "5px"}
    )
