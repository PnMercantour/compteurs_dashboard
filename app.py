from dash import Dash
import dash_bootstrap_components as dbc
import os
import sys

# Import local modules
# Ensure imports work regardless of execution context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_data, process_data
from layout import create_layout
from callbacks import register_callbacks

# --- Global Initialization (Standard Pattern) ---

# 1. Initialize App
# Using LUX theme for a cleaner, high-end look
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX], title="Traffic Dashboard")
server = app.server  # Expose server for WSGI deployment (Gunicorn, etc.)

# 2. Load Data Globally
# Note: With debug=True, this will print twice (Watcher process + Worker process)
print("--- Initialisation des données ---")
BASE_DATA_PATH = os.path.join(os.path.dirname(__file__))

try:
    raw_data = load_data(BASE_DATA_PATH)
    df = process_data(raw_data)
    print(f"succès : {len(df)} enregistrements prêts.")
except Exception as e:
    print(f"Erreur lors du chargement des données : {e}")
    # Initialize empty DF to avoid crash on startup
    import pandas as pd
    df = pd.DataFrame()

# 3. Setup Layout
app.layout = create_layout(df)

# 4. Register Callbacks
register_callbacks(app, df)

# --- Main Execution ---
if __name__ == '__main__':
    # Debug mode enables hot-reloading (runs script twice on startup)
    app.run(debug=True, port=8050)
