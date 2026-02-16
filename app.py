from dash import Dash, page_container
import dash_bootstrap_components as dbc
import os
import sys

# Import local modules
# Ensure imports work regardless of execution context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 1. Initialize App with Multi-Page Support
app = Dash(__name__, 
           use_pages=True, 
           external_stylesheets=[dbc.themes.LUX],
           external_scripts=['https://cdn.plot.ly/plotly-locale-fr-latest.js'],
           title="Observatoire Trafic Mercantour",
           suppress_callback_exceptions=True)

server = app.server

# 2. Setup Layout
# With pages, the layout is just the container
app.layout = dbc.Container([
    page_container
], fluid=True, className="p-0")

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True, port=8050)
