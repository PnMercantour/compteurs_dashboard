from dash import Input, Output, html, State, ctx, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from report_generator import generate_html_report # Local Import

# --- Constants ---
# Professional Palette (Flat/Modern)
COLOR_MAP = {
    'VL': '#2980B9',       # Professional Blue
    'Motos': '#F39C12',    # Warning Orange
    'PL': '#C0392B',       # Alert Red
    'Vélos': '#16A085',    # Elegant Teal/Green
    'Motorisé': '#95A5A6', # Neutral Grey
    'Sens 1': '#8E44AD',   # Purple
    'Sens 2': '#2C3E50',   # Dark Blue
}

# Common Layout Style for consistency
COMMON_LAYOUT = dict(
    font=dict(family="Segoe UI, Roboto, Helvetica, Arial, sans-serif", size=12, color="#2c3e50"),
    title_font=dict(size=14, family="Segoe UI Semibold", color="#2c3e50"),
    plot_bgcolor="rgba(0,0,0,0)", # Transparent background
    paper_bgcolor="rgba(0,0,0,0)", # Transparent background
    margin=dict(l=40, r=40, t=60, b=40),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor="rgba(255,255,255,0.5)",
        bordercolor="#eee",
        borderwidth=1
    ),
    xaxis=dict(
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor='#eee',
        mirror=True
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='#f0f0f0',
        showline=True,
        linewidth=1,
        linecolor='#eee',
        mirror=True
    )
)

FRENCH_MONTHS_MAP = {
    1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin', 
    7: 'Juillet', 8: 'Août', 9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
}

DAYS_ORDER_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

def register_callbacks(app, df):
    
    # --- Headers / Filters Helper ---
    def _filter_by_date(df, start_date, end_date):
        if not start_date or not end_date:
            return df
        return df[(df['Datetime'] >= start_date) & (df['Datetime'] <= end_date)]

    # --- Map Modal Callback ---
    @app.callback(
        Output("map-modal", "is_open"),
        [Input("map-btn", "n_clicks"), Input("close-map-btn", "n_clicks")],
        [State("map-modal", "is_open")],
    )
    def toggle_map(n1, n2, is_open):
        if n1 or n2:
            return not is_open
        return is_open

    # --- Export Report Callback ---
    @app.callback(
        Output("download-report", "data"),
        Input("export-btn", "n_clicks"),
        [State('period-picker', 'start_date'),
         State('period-picker', 'end_date'),
         State('pie-active-share', 'figure'),
         State('pie-motorized-split', 'figure'),
         State('pie-all-mobilities', 'figure'),
         State('timeline-graph', 'figure'),
         State('heatmap-day-hour', 'figure'),
         State('annual-evolution-bar', 'figure'),
         State('annual-seasonality-line', 'figure')],
        prevent_initial_call=True
    )
    def export_report(n_clicks, start, end, f1, f2, f3, f4, f5, f6, f7):
        if not n_clicks:
            return None
            
        figures = {
            "Part Modale (Vélos)": f1,
            "Répartition Motorisée": f2,
            "Toutes Mobilités": f3,
            "Evolution Temporelle": f4,
            "Matrice Horaire": f5
        }
        
        # Filter None figures
        valid_figures = {k: v for k, v in figures.items() if v is not None}
        
        # Filter data for the table
        report_df = _filter_by_date(df, start, end)
        
        report_html = generate_html_report(report_df, valid_figures, start, end)
        
        return dict(content=report_html, filename=f"Rapport_Trafic_{start}_{end}.html")

    # -------------------------------------------------------------------------
    # Tab 1: Synthèse Globale
    # -------------------------------------------------------------------------
    @app.callback(
        [Output('synthesis-table-container', 'children'),
         Output('pie-active-share', 'figure'),
         Output('pie-motorized-split', 'figure'),
         Output('pie-all-mobilities', 'figure')],
        [Input('period-picker', 'start_date'),
         Input('period-picker', 'end_date')]
    )
    def update_synthesis(start_date, end_date):
        if df.empty:
            no_data = px.pie(title="Aucune donnée disponible")
            return html.Div("Pas de données."), no_data, no_data, no_data

        # 1. Filter Data
        period_df = _filter_by_date(df, start_date, end_date).copy()
            
        if period_df.empty:
            no_data = px.pie(title="Pas de données pour cette période")
            return html.Div("Pas de données sélectionnées."), no_data, no_data, no_data
            
        # 2. Build Metrics Table
        table = _build_synthesis_table(period_df, start_date, end_date, df.attrs.get('metadata'))

        # 3. Charts
        # Part Modale (Vélos vs Reste)
        period_df['ModalGroup'] = period_df['UnifiedCategory'].apply(lambda x: 'Vélos' if x == 'Vélos' else 'Motorisé')
        modal_counts = period_df['ModalGroup'].value_counts().reset_index()
        modal_counts.columns = ['Type', 'Count']
        
        fig_pie1 = px.pie(modal_counts, names='Type', values='Count', title=None,
                          color='Type', hole=0.4, color_discrete_map=COLOR_MAP)
        
        # Répartition Motorisée
        motorized_df = period_df[period_df['UnifiedCategory'].isin(['Motos', 'VL', 'PL'])]
        if not motorized_df.empty:
            mot_counts = motorized_df['UnifiedCategory'].value_counts().reset_index()
            mot_counts.columns = ['Cat', 'Count']
            fig_pie2 = px.pie(mot_counts, names='Cat', values='Count', title=None,
                              color='Cat', hole=0.4, color_discrete_map=COLOR_MAP)
        else:
            fig_pie2 = px.pie(title="Pas de trafic motorisé")
            
        # Toutes Mobilités
        all_counts = period_df['UnifiedCategory'].value_counts().reset_index()
        all_counts.columns = ['Cat', 'Count']
        fig_pie3 = px.pie(all_counts, names='Cat', values='Count', title=None,
                          color='Cat', hole=0.4, color_discrete_map=COLOR_MAP)
        
        # Apply Common Style
        for fig in [fig_pie1, fig_pie2, fig_pie3]:
            fig.update_layout(**COMMON_LAYOUT)
            fig.update_traces(textinfo='percent+label', textposition='outside', marker=dict(line=dict(color='#FFFFFF', width=2)))
            # Remove grid config from pie
            fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
            fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False)

        return table, fig_pie1, fig_pie2, fig_pie3

    # -------------------------------------------------------------------------
    # Tab 2: Analyse Temporelle
    # -------------------------------------------------------------------------
    @app.callback(
        [Output('timeline-graph', 'figure'),
         Output('heatmap-day-hour', 'figure')],
        [Input('period-picker', 'start_date'),
         Input('period-picker', 'end_date'),
         Input('chart-freq', 'value'),
         Input('chart-cats', 'value'),
         Input('chart-directions', 'value')],
        [State('timeline-graph', 'relayoutData')]
    )
    def update_timeline(start_date, end_date, freq, cats, directions, relayout_data):
        empty_figs = (px.line(title="Pas de données"), px.density_heatmap(title="Pas de données"))
        if df.empty: return empty_figs
            
        # 1. Broad Filter (Dates)
        period_df = _filter_by_date(df, start_date, end_date)
        if period_df.empty: return empty_figs

        # 2. Specific Filters
        cats = cats or []
        directions = directions or []
        
        filtered_df = period_df[period_df['UnifiedCategory'].isin(cats)]
        
        # Filter Direction
        def filter_dir(val):
            return any(d in str(val) for d in directions)
        
        filtered_df = filtered_df[filtered_df['Direction'].apply(filter_dir)]
        
        if filtered_df.empty: return empty_figs
             
        # Metadata
        meta = df.attrs.get('metadata', {})
        d1 = meta.get('direction_1', 'Sens 1')
        d2 = meta.get('direction_2', 'Sens 2')

        # 3. Timeline Graph
        filtered_df['SensLabel'] = filtered_df['Direction'].astype(str).apply(
            lambda x: d1 if '1' in x else (d2 if '2' in x else 'Inconnu')
        )
        filtered_df['Group'] = filtered_df['UnifiedCategory'] + " - " + filtered_df['SensLabel']
        
        freq_map = {'H': 'h', 'D': 'D', 'M': 'MS'}
        
        grouper = [pd.Grouper(key='Datetime', freq=freq_map.get(freq, 'D')), 'Group']
        grouped = filtered_df.groupby(grouper).size().reset_index(name='Count')
        
        # Color discrete map needs complex keys if we use Group, but Plotly handles it if we map base colors? 
        # Actually easier to let Plotly cycle or map manually if 'Group' matches COLOR_MAP key partially. 
        # For now, let's stick to default distinct colors for lines to avoid complexity with composite keys.
        
        if freq == 'M':
            # Bar chart with proper width (using Categorical axis to avoid thin lines on Date axis)
            # Create a label column sorted chronologically
            grouped = grouped.sort_values('Datetime')
            short_months = {
                1: 'Jan', 2: 'Fév', 3: 'Mars', 4: 'Avr', 5: 'Mai', 6: 'Juin', 
                7: 'Juil', 8: 'Août', 9: 'Sept', 10: 'Oct', 11: 'Nov', 12: 'Déc'
            }
            grouped['DateLabel'] = grouped['Datetime'].dt.month.map(short_months) + " " + grouped['Datetime'].dt.year.astype(str)
            
            fig_time = px.bar(grouped, x='DateLabel', y='Count', color='Group', barmode='group')
            fig_time.update_layout(**COMMON_LAYOUT)
            fig_time.update_xaxes(type='category', title=None)
        else:
            fig_time = px.line(grouped, x='Datetime', y='Count', color='Group', markers=True)
            fig_time.update_traces(line=dict(width=2.5))
            fig_time.update_layout(**COMMON_LAYOUT)
            fig_time.update_layout(hovermode="x unified")
            
        fig_time.update_layout(legend_title_text=None)
        fig_time.update_yaxes(title="Volume")
        fig_time.update_xaxes(title=None)
        
        # PERSIST ZOOM Logic
        # Apply previous zoom range if available and if we are not in incompatible mode (Monthly)
        # Also do NOT persist if the user explicitly changed the Date Period Picker (intent to reset view)
        trigger_id = ctx.triggered_id
        if relayout_data and freq != 'M' and (not trigger_id or 'period-picker' not in trigger_id):
             if 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
                 fig_time.update_layout(xaxis_range=[relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']])
             elif 'xaxis.range' in relayout_data:
                 fig_time.update_layout(xaxis_range=relayout_data['xaxis.range'])

        # 4. Heatmap
        if 'Weekday_FR' in filtered_df.columns and 'Hour' in filtered_df.columns:
            # 1. Calculate Total Volume
            heatmap_data = filtered_df.groupby(['Weekday_FR', 'Hour']).size().reset_index(name='TotalVolume')
            
            # 2. Normalize
            s_d = pd.to_datetime(start_date) if start_date else filtered_df['Datetime'].min()
            e_d = pd.to_datetime(end_date) if end_date else filtered_df['Datetime'].max()
            if hasattr(s_d, 'date'): s_d = s_d.date()
            if hasattr(e_d, 'date'): e_d = e_d.date()

            full_date_range = pd.date_range(start=s_d, end=e_d, freq='D')
            ref_days = pd.DataFrame({'Date': full_date_range})
            
            fr_map = {'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi', 
                      'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'}
            ref_days['Weekday_FR'] = ref_days['Date'].dt.day_name().map(fr_map)
            
            day_counts = ref_days['Weekday_FR'].value_counts().reset_index()
            day_counts.columns = ['Weekday_FR', 'NbDays']
            
            # Merge
            heatmap_data = pd.merge(heatmap_data, day_counts, on='Weekday_FR', how='left')
            heatmap_data['Flow'] = heatmap_data['TotalVolume'] / heatmap_data['NbDays']
            
            fig_hm = px.density_heatmap(heatmap_data, x='Hour', y='Weekday_FR', z='Flow',
                                        category_orders={'Weekday_FR': DAYS_ORDER_FR},
                                        color_continuous_scale='Viridis',
                                        nbinsx=24)
                                        
            fig_hm.update_yaxes(title="Jour")
            fig_hm.update_xaxes(title="Heure (0-23h)")
            fig_hm.update_coloraxes(colorbar_title="V/h")
            fig_hm.update_layout(**COMMON_LAYOUT)
            # Override grid for heatmap for cleaner look
            fig_hm.update_xaxes(showgrid=False) 
            fig_hm.update_yaxes(showgrid=False)
        else:
            fig_hm = px.density_heatmap(title="Données insuffisantes")
            fig_hm.update_layout(**COMMON_LAYOUT)
        
        return fig_time, fig_hm

    # -------------------------------------------------------------------------
    # Tab 3: Comparaison Pluriannuelle
    # -------------------------------------------------------------------------
    @app.callback(
        [Output('annual-evolution-bar', 'figure'),
         Output('annual-seasonality-line', 'figure')],
        [Input('comp-cats', 'value')]
    )
    def update_comparison(cats):
        empty_figs = (px.bar(title="Pas de données"), px.line(title="Pas de données"))
        if df.empty: return empty_figs
            
        cats = cats or []
        comp_df = df[df['UnifiedCategory'].isin(cats)].copy()
        
        if comp_df.empty: return empty_figs

        # 1. Bar Chart: TMJ Annuel
        annual_vols = comp_df.groupby(['Year', 'UnifiedCategory'], observed=True).size().reset_index(name='Volume')
        days_per_year = comp_df.groupby('Year', observed=True)['Date'].nunique().reset_index(name='NbDays')
        
        annual_group = pd.merge(annual_vols, days_per_year, on='Year')
        annual_group['TMJ'] = (annual_group['Volume'] / annual_group['NbDays']).round(0)
        
        fig_bar = px.bar(annual_group, x='Year', y='TMJ', color='UnifiedCategory', 
                         barmode='group',
                         color_discrete_map=COLOR_MAP, text='TMJ')
        
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(**COMMON_LAYOUT)
        fig_bar.update_yaxes(title="TMJ Moyen")
        fig_bar.update_xaxes(title=None, dtick=1)
        fig_bar.update_layout(legend_title_text=None)
        
        # 2. Line Chart: Seasonality
        monthly_vols = comp_df.groupby(['Year', 'Month'], observed=True).size().reset_index(name='Volume')
        days_per_month = comp_df.groupby(['Year', 'Month'], observed=True)['Date'].nunique().reset_index(name='NbDays')
        
        monthly_group = pd.merge(monthly_vols, days_per_month, on=['Year', 'Month'])
        monthly_group['TMJ_Month'] = (monthly_group['Volume'] / monthly_group['NbDays']).round(0)
        
        monthly_group['MonthName'] = monthly_group['Month'].map(FRENCH_MONTHS_MAP)
        
        fig_line = px.line(monthly_group, x='MonthName', y='TMJ_Month', color='Year', markers=True,
                           category_orders={'MonthName': list(FRENCH_MONTHS_MAP.values())})
        
        fig_line.update_layout(**COMMON_LAYOUT)
        fig_line.update_traces(line=dict(width=3))
        fig_line.update_yaxes(title="TMJ Mensuel")
        fig_line.update_xaxes(title=None)
        fig_line.update_layout(legend_title_text="Année")
        
        return fig_bar, fig_line


# --- Helpers ---

def _filter_by_date(df, start_date, end_date):
    """
    Robust date filtering using UTC comparison.
    """
    if not start_date: start_date = df['Datetime'].min()
    if not end_date: end_date = df['Datetime'].max()
    
    try:
        # Use simple string comparison or UTC conversion
        mask = (df['Datetime'] >= pd.to_datetime(start_date, utc=True)) & \
               (df['Datetime'] < (pd.to_datetime(end_date, utc=True) + pd.Timedelta(days=1)))
        return df[mask].copy()
    except:
        return pd.DataFrame()

def _build_synthesis_table(period_df, start_date, end_date, metadata=None):
    """
    Generates the HTML table with metrics.
    """
    if metadata is None: metadata = {}
    d1_label = metadata.get('direction_1', 'Sens 1')
    d2_label = metadata.get('direction_2', 'Sens 2')

    # Calculate reference days for the PERIOD
    s_date = pd.to_datetime(start_date or period_df['Datetime'].min()).date()
    e_date = pd.to_datetime(end_date or period_df['Datetime'].max()).date()
    
    date_range = pd.date_range(start=s_date, end=e_date, freq='D')
    dates_df = pd.DataFrame({'Date': date_range})
    dates_df['DayName'] = dates_df['Date'].dt.day_name()
    dates_df['IsWE'] = dates_df['DayName'].isin(['Saturday', 'Sunday'])
    
    nb_days_total = len(dates_df)
    nb_days_jo = len(dates_df[~dates_df['IsWE']])
    nb_days_we = len(dates_df[dates_df['IsWE']])
    
    # Rows
    rows = []
    categories = ['Vélos', 'Motos', 'VL', 'PL']
    
    def make_row_cells(label, filter_cat=None):
        cells = [html.Td(label, className="fw-bold")]
        # Sens 1 and 2
        for sens_code in ['1', '2']: # 1=Vers Bonette, 2=Vers Jausiers
            # Filter Data
            d_data = period_df[period_df['Direction'].astype(str).str.contains(sens_code)]
            if filter_cat:
                d_data = d_data[d_data['UnifiedCategory'] == filter_cat]
            
            # Compute
            m = _compute_metrics(d_data, nb_days_total, nb_days_jo, nb_days_we)
            
            # Format
            for val in m:
                formatted = val if isinstance(val, str) else f"{val:,}".replace(",", " ")
                cells.append(html.Td(formatted))
        return html.Tr(cells)

    for cat in categories:
        rows.append(make_row_cells(cat, cat))
    
    rows.append(make_row_cells("Toutes Mobilités", None))
    
    # Header
    table_header = html.Thead([
        html.Tr([
            html.Th(""),
            html.Th(f"{d1_label}", colSpan=5, className="text-center table-primary"),
            html.Th(f"{d2_label}", colSpan=5, className="text-center table-secondary")
        ]),
        html.Tr([
            html.Th("Catégorie"),
            html.Th("TOTAL"), html.Th("TMJ"), html.Th("TMJ JO"), html.Th("TMJ WE"), html.Th("VT"),
            html.Th("TOTAL"), html.Th("TMJ"), html.Th("TMJ JO"), html.Th("TMJ WE"), html.Th("VT")
        ], className="small text-center")
    ])
    
    return dbc.Table([table_header, html.Tbody(rows, className="text-end")], 
                     bordered=True, hover=True, responsive=True, striped=True)

def _compute_metrics(sub_df, days_total, days_jo, days_we):
    """
    Returns [Total, TMJ, TMJ_JO, TMJ_WE, SpeedStr]
    """
    if sub_df.empty:
        return [0, 0, 0, 0, "-"]
        
    total = len(sub_df)
    tmj = int(round(total / max(1, days_total)))
    
    # TMJ JO
    sub_jo = sub_df[sub_df['DayType'] == 'JO']
    tmj_jo = int(round(len(sub_jo) / max(1, days_jo))) if days_jo > 0 else 0
    
    # TMJ WE
    sub_we = sub_df[sub_df['DayType'] == 'WE']
    tmj_we = int(round(len(sub_we) / max(1, days_we))) if days_we > 0 else 0
    
    # Speed (VT)
    if 'Speed' in sub_df.columns:
         vt = sub_df['Speed'].mean()
         vt_str = "-" if pd.isna(vt) else f"{vt:.0f} km/h"
    else:
         vt_str = "-"
         
    return [total, tmj, tmj_jo, tmj_we, vt_str]
