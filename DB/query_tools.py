import pandas as pd

def explode_array_field(df: pd.DataFrame, array_field: str, index_field: str = "array_index", keep_fields=None):
    """
    Explodes a DataFrame where one column contains arrays (e.g., flow_rate_data), keeping other identifiers.

    Parameters:
        df (pd.DataFrame): The original DataFrame with array column.
        array_field (str): The column to explode (e.g., 'flow_rate_data').
        index_field (str): Name for the new index column created after exploding.
        keep_fields (list): List of fields to keep (like cow_id, teat_id, etc.)

    Returns:
        pd.DataFrame: Exploded DataFrame.
    """
    if keep_fields is None:
        keep_fields = []

    df = df.copy()
    # Ensure the array field exists
    if array_field not in df.columns:
        raise ValueError(f"Field {array_field} not found in DataFrame")

    # Create a temporary index to preserve row order
    df['_temp_index'] = df.index
    df_exploded = df.explode(array_field)
    df_exploded[index_field] = df_exploded.groupby('_temp_index').cumcount()

    # Only keep necessary columns
    columns_to_keep = keep_fields + [array_field, index_field]
    df_exploded = df_exploded[columns_to_keep]

    df_exploded = df_exploded.dropna(subset=[array_field])  # Clean if needed
    return df_exploded
