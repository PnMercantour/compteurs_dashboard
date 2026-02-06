import dash
from dash import Input, Output, html, State, ctx, dcc, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
import re
from data_loader import DataManager
from report_generator import generate_html_report
from utils import (
    COLOR_MAP, 
    COMMON_LAYOUT, 
    FRENCH_MONTHS_MAP, 
    DAYS_ORDER_FR, 
    compute_metrics,
    filter_by_date
)
from layout import create_layout as create_base_layout

dash.register_page(__name__, path_template='/dashboard/<site_id>', title='Tableau de Bord')

# --- Helpers ---

def _build_synthesis_table(period_df, start_date, end_date, metadata=None):
    if metadata is None: metadata = {}
    d1_label = metadata.get('direction_1', 'Sens 1')
    d2_label = metadata.get('direction_2', 'Sens 2')

    s_date = pd.to_datetime(start_date or period_df['Datetime'].min()).date()
    e_date = pd.to_datetime(end_date or period_df['Datetime'].max()).date()
    
    date_range = pd.date_range(start=s_date, end=e_date, freq='D')
    dates_df = pd.DataFrame({'Date': date_range})
    dates_df['DayName'] = dates_df['Date'].dt.day_name()
    dates_df['IsWE'] = dates_df['DayName'].isin(['Saturday', 'Sunday'])
    
    nb_days_total = len(dates_df)
    nb_days_jo = len(dates_df[~dates_df['IsWE']])
    nb_days_we = len(dates_df[dates_df['IsWE']])
    
    rows = []
    categories = ['Vélos', 'Motos', 'VL', 'PL']
    
    def make_row_cells(label, filter_cat=None):
        cells = [html.Td(label, className="fw-bold")]
        for sens_code in ['1', '2']:
            d_data = period_df[period_df['Direction'].astype(str).str.contains(sens_code)]
            if filter_cat:
                d_data = d_data[d_data['UnifiedCategory'] == filter_cat]
            m = compute_metrics(d_data, nb_days_total, nb_days_jo, nb_days_we)
            for val in m:
                formatted = val if isinstance(val, str) else f"{val:,}".replace(",", " ")
                cells.append(html.Td(formatted))
        return html.Tr(cells)

    for cat in categories:
        rows.append(make_row_cells(cat, cat))
    rows.append(make_row_cells("Toutes Mobilités", None))
    
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

# --- Layout ---

def layout(site_id=None):
    if not site_id:
        return dbc.Container(html.Div("Site non spécifié", className="alert alert-danger mt-5"))
        
    dm = DataManager()
    df = dm.get_data(site_id)
    
    if df.empty:
         return dbc.Container(html.Div(f"Pas de données trouvées pour le site: {site_id}", className="alert alert-warning mt-5"))
    
    layout_content = create_base_layout(df)
    
    # Inject Store and Header
    layout_content.children.insert(0, dcc.Store(id='current-site-id', data=site_id))
    
    # Add navigation breadcrumb
    breadcrumb = dbc.Row(dbc.Col(
        html.Div([
            dcc.Link("Accueil", href="/", className="text-decoration-none text-secondary"),
            html.Span(" / ", className="mx-2 text-muted"),
            html.Span(df.attrs.get('metadata', {}).get('site_name', site_id), className="fw-bold")
        ], className="my-3 small")
    ))
    layout_content.children.insert(0, breadcrumb)
    
    return layout_content


# --- Callbacks ---

@callback(
    Output("map-modal", "is_open"),
    [Input("map-btn", "n_clicks"), Input("close-map-btn", "n_clicks")],
    [State("map-modal", "is_open")],
)
def toggle_map(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@callback(
    Output("download-report", "data"),
    Input("export-btn", "n_clicks"),
    [State('period-picker', 'start_date'),
     State('period-picker', 'end_date'),
     State('pie-active-share', 'figure'),
     State('pie-motorized-split', 'figure'),
     State('pie-all-mobilities', 'figure'),
     State('timeline-graph', 'figure'),
     State('heatmap-day-hour', 'figure'),
     State('current-site-id', 'data')],
    prevent_initial_call=True
)
def export_report(n_clicks, start, end, f1, f2, f3, f4, f5, site_id):
    if not n_clicks or not site_id:
        return None
    
    df = DataManager().get_data(site_id)
    figures = {"Part Modale (Vélos)": f1, "Répartition Motorisée": f2, "Toutes Mobilités": f3, "Evolution Temporelle": f4, "Matrice Horaire": f5}
    valid_figures = {k: v for k, v in figures.items() if v is not None}
    report_df = filter_by_date(df, start, end)
    report_html = generate_html_report(report_df, valid_figures, start, end)
    return dict(content=report_html, filename=f"Rapport_{site_id}_{start}_{end}.html")

@callback(
    [Output('synthesis-table-container', 'children'),
     Output('pie-active-share', 'figure'),
     Output('pie-motorized-split', 'figure'),
     Output('pie-all-mobilities', 'figure')],
    [Input('period-picker', 'start_date'),
     Input('period-picker', 'end_date'),
     Input('current-site-id', 'data')]
)
def update_synthesis(start_date, end_date, site_id):
    if not site_id:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    df = DataManager().get_data(site_id)
    
    if df.empty:
        no_data = px.pie(title="Aucune donnée disponible")
        return html.Div("Pas de données."), no_data, no_data, no_data

    period_df = filter_by_date(df, start_date, end_date).copy()
        
    if period_df.empty:
        no_data = px.pie(title="Pas de données pour cette période")
        return html.Div("Pas de données sélectionnées."), no_data, no_data, no_data
        
    table = _build_synthesis_table(period_df, start_date, end_date, df.attrs.get('metadata'))

    # Optimized ModalGroup creation
    period_df['ModalGroup'] = np.where(period_df['UnifiedCategory'] == 'Vélos', 'Vélos', 'Motorisé')
    modal_counts = period_df['ModalGroup'].value_counts().reset_index()
    modal_counts.columns = ['Type', 'Count']
    
    fig_pie1 = px.pie(modal_counts, names='Type', values='Count', title=None, color='Type', hole=0.4, color_discrete_map=COLOR_MAP)
    
    motorized_df = period_df[period_df['UnifiedCategory'].isin(['Motos', 'VL', 'PL'])]
    if not motorized_df.empty:
        mot_counts = motorized_df['UnifiedCategory'].value_counts().reset_index()
        mot_counts.columns = ['Cat', 'Count']
        fig_pie2 = px.pie(mot_counts, names='Cat', values='Count', title=None, color='Cat', hole=0.4, color_discrete_map=COLOR_MAP)
    else:
        fig_pie2 = px.pie(title="Pas de trafic motorisé")
        
    all_counts = period_df['UnifiedCategory'].value_counts().reset_index()
    all_counts.columns = ['Cat', 'Count']
    fig_pie3 = px.pie(all_counts, names='Cat', values='Count', title=None, color='Cat', hole=0.4, color_discrete_map=COLOR_MAP)
    
    for fig in [fig_pie1, fig_pie2, fig_pie3]:
        fig.update_layout(**COMMON_LAYOUT)
        fig.update_traces(textinfo='percent+label', textposition='outside', marker=dict(line=dict(color='#FFFFFF', width=2)))
        fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
        fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False)

    return table, fig_pie1, fig_pie2, fig_pie3

@callback(
    [Output('timeline-graph', 'figure'),
     Output('heatmap-day-hour', 'figure')],
    [Input('period-picker', 'start_date'),
     Input('period-picker', 'end_date'),
     Input('chart-freq', 'value'),
     Input('chart-cats', 'value'),
     Input('chart-directions', 'value'),
     Input('current-site-id', 'data')],
    [State('timeline-graph', 'relayoutData')]
)
def update_timeline(start_date, end_date, freq, cats, directions, site_id, relayout_data):
    if not site_id: return dash.no_update, dash.no_update
    
    df = DataManager().get_data(site_id)
    empty_figs = (px.line(title="Pas de données"), px.density_heatmap(title="Pas de données"))
    
    if df.empty: return empty_figs
        
    period_df = filter_by_date(df, start_date, end_date)
    if period_df.empty: return empty_figs

    cats = cats or []
    directions = directions or []
    
    # Fast filtering with isin for categories
    filtered_df = period_df[period_df['UnifiedCategory'].isin(cats)]
    
    # Optimized Direction Filtering
    # Convert to string once for vectorization
    if 'Direction' in filtered_df.columns:
        dir_series = filtered_df['Direction'].astype(str)
        # Create a boolean mask for all selected directions
        if directions:
             # Fast regex-style OR matching or simple isin if values are exact
             # Given '1' and '2' are substrings in complex strings sometimes, we check containment
             # But here values are likely "1" or "2" or "Voie 1" etc.
             # Using list comp with reduce is safer for arbitrary substrings but 'str.contains' with regex is faster
             pattern = '|'.join([re.escape(d) for d in directions])
             if pattern:
                filtered_df = filtered_df[dir_series.str.contains(pattern, regex=True)]
    
    if filtered_df.empty: return empty_figs
            
    meta = df.attrs.get('metadata', {})
    d1 = meta.get('direction_1', 'Sens 1')
    d2 = meta.get('direction_2', 'Sens 2')

    # Optimized SensLabel with numpy select
    # Re-eval series on filtered data
    d_series = filtered_df['Direction'].astype(str)
    cond1 = d_series.str.contains('1')
    cond2 = d_series.str.contains('2')
    
    filtered_df['SensLabel'] = np.select(
        [cond1, cond2],
        [d1, d2],
        default='Inconnu'
    )
    filtered_df['Group'] = filtered_df['UnifiedCategory'] + " - " + filtered_df['SensLabel']
    
    freq_map = {'H': 'h', 'D': 'D', 'M': 'MS'}
    grouper = [pd.Grouper(key='Datetime', freq=freq_map.get(freq, 'D')), 'Group']
    
    grouped_raw = filtered_df.groupby(grouper).size()

    if freq != 'M': # if not monthly fill missing periods with 0 counts if there is data for the day
            grouped_unstacked = grouped_raw.unstack(level='Group', fill_value=0)
            grouped_resampled = grouped_unstacked.resample(freq_map.get(freq, 'D')).asfreq()

            if freq == 'H':
                active_days = grouped_unstacked.index.floor('D').unique()
                current_days = grouped_resampled.index.floor('D')
                mask_active_days = current_days.isin(active_days)
                grouped_resampled.loc[mask_active_days] = grouped_resampled.loc[mask_active_days].fillna(0)
            
            grouped = grouped_resampled.stack(future_stack=True).reset_index(name='Count')
            fig_time = px.line(grouped, x='Datetime', y='Count', color='Group', markers=True)
            fig_time.update_traces(line=dict(width=2.5))
            fig_time.update_layout(hovermode="x unified")
    else:
            grouped = grouped_raw.reset_index(name='Count')
            grouped = grouped.sort_values('Datetime')
            short_months = {1: 'Jan', 2: 'Fév', 3: 'Mars', 4: 'Avr', 5: 'Mai', 6: 'Juin', 7: 'Juil', 8: 'Août', 9: 'Sept', 10: 'Oct', 11: 'Nov', 12: 'Déc'}
            grouped['DateLabel'] = grouped['Datetime'].dt.month.map(short_months) + " " + grouped['Datetime'].dt.year.astype(str)
            fig_time = px.bar(grouped, x='DateLabel', y='Count', color='Group', barmode='group')
            fig_time.update_xaxes(type='category', title=None)
        
    fig_time.update_layout(**COMMON_LAYOUT)
    fig_time.update_layout(legend_title_text=None)
    fig_time.update_yaxes(title="Volume")
    fig_time.update_xaxes(title=None)
    
    trigger_id = ctx.triggered_id
    if relayout_data and freq != 'M' and (not trigger_id or 'period-picker' not in trigger_id):
            if 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
                fig_time.update_layout(xaxis_range=[relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']])
            elif 'xaxis.range' in relayout_data:
                fig_time.update_layout(xaxis_range=relayout_data['xaxis.range'])

    # Heatmap
    if 'Weekday_FR' in filtered_df.columns and 'Hour' in filtered_df.columns:
        heatmap_data = filtered_df.groupby(['Weekday_FR', 'Hour']).size().reset_index(name='TotalVolume')
        s_d = pd.to_datetime(start_date) if start_date else filtered_df['Datetime'].min()
        e_d = pd.to_datetime(end_date) if end_date else filtered_df['Datetime'].max()
        if hasattr(s_d, 'date'): s_d = s_d.date()
        if hasattr(e_d, 'date'): e_d = e_d.date()

        full_date_range = pd.date_range(start=s_d, end=e_d, freq='D')
        ref_days = pd.DataFrame({'Date': full_date_range})
        fr_map = {'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi', 'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'}
        ref_days['Weekday_FR'] = ref_days['Date'].dt.day_name().map(fr_map)
        day_counts = ref_days['Weekday_FR'].value_counts().reset_index()
        day_counts.columns = ['Weekday_FR', 'NbDays']
        
        heatmap_data = pd.merge(heatmap_data, day_counts, on='Weekday_FR', how='left')
        heatmap_data['Flow'] = heatmap_data['TotalVolume'] / heatmap_data['NbDays']
        
        fig_hm = px.density_heatmap(heatmap_data, x='Hour', y='Weekday_FR', z='Flow', category_orders={'Weekday_FR': DAYS_ORDER_FR}, color_continuous_scale='Viridis', nbinsx=24)
        fig_hm.update_yaxes(title="Jour")
        fig_hm.update_xaxes(title="Heure (0-23h)")
        fig_hm.update_coloraxes(colorbar_title="V/h")
        fig_hm.update_layout(**COMMON_LAYOUT)
        fig_hm.update_xaxes(showgrid=False) 
        fig_hm.update_yaxes(showgrid=False)
    else:
        fig_hm = px.density_heatmap(title="Données insuffisantes")
        fig_hm.update_layout(**COMMON_LAYOUT)
    
    return fig_time, fig_hm

@callback(
    [Output('annual-evolution-bar', 'figure'),
     Output('annual-seasonality-line', 'figure')],
    [Input('comp-cats', 'value'),
     Input('current-site-id', 'data')]
)
def update_comparison(cats, site_id):
    if not site_id: return dash.no_update, dash.no_update
    df = DataManager().get_data(site_id)
    empty_figs = (px.bar(title="Pas de données"), px.line(title="Pas de données"))
    if df.empty: return empty_figs
        
    cats = cats or []
    comp_df = df[df['UnifiedCategory'].isin(cats)].copy()
    
    if comp_df.empty: return empty_figs

    annual_vols = comp_df.groupby(['Year', 'UnifiedCategory'], observed=True).size().reset_index(name='Volume')
    days_per_year = comp_df.groupby('Year', observed=True)['Date'].nunique().reset_index(name='NbDays')
    
    annual_group = pd.merge(annual_vols, days_per_year, on='Year')
    annual_group['TMJ'] = (annual_group['Volume'] / annual_group['NbDays']).round(0)
    
    fig_bar = px.bar(annual_group, x='Year', y='TMJ', color='UnifiedCategory', barmode='group', color_discrete_map=COLOR_MAP, text='TMJ')
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(**COMMON_LAYOUT)
    fig_bar.update_yaxes(title="TMJ Moyen")
    fig_bar.update_xaxes(title=None, dtick=1)
    fig_bar.update_layout(legend_title_text=None)
    
    monthly_vols = comp_df.groupby(['Year', 'Month'], observed=True).size().reset_index(name='Volume')
    days_per_month = comp_df.groupby(['Year', 'Month'], observed=True)['Date'].nunique().reset_index(name='NbDays')
    
    monthly_group = pd.merge(monthly_vols, days_per_month, on=['Year', 'Month'])
    monthly_group['TMJ_Month'] = (monthly_group['Volume'] / monthly_group['NbDays']).round(0)
    monthly_group['MonthName'] = monthly_group['Month'].map(FRENCH_MONTHS_MAP)
    
    fig_line = px.line(monthly_group, x='MonthName', y='TMJ_Month', color='Year', markers=True, category_orders={'MonthName': list(FRENCH_MONTHS_MAP.values())})
    fig_line.update_layout(**COMMON_LAYOUT)
    fig_line.update_traces(line=dict(width=3))
    fig_line.update_yaxes(title="TMJ Mensuel")
    fig_line.update_xaxes(title=None)
    fig_line.update_layout(legend_title_text="Année")
    
    return fig_bar, fig_line
