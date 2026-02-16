import dash
from dash import Input, Output, html, State, ctx, dcc, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from data_loader import DataManager
from layout import create_dashboard_layout, create_breadcrumb
from utils import (
    COLOR_MAP, 
    filter_by_date,
    filter_by_season,
    compute_metrics
)

dash.register_page(__name__, path_template='/dashboard/pedestre/<site_id>', title='Tableau de Bord Piéton')

# --- Helpers ---

def _compute_pedestrian_metrics(df, nb_days_total, nb_days_jo, nb_days_we):
    """
    Computes: [Total, Avg Daily, Avg Workday, Avg Weekend, Peak Day, Peak Count, Max Day of Week]
    """
    if df.empty:
        return ["-"] * 8
        
    # Aggregate by day first to get daily stats
    daily_df = df.groupby('Date')['Count'].sum().reset_index()
    
    total = daily_df['Count'].sum()
    avg_daily = total / max(1, nb_days_total)
    
    # Filter for JO/WE
    # We need to join with Weekday info or re-derive
    daily_df['Datetime'] = pd.to_datetime(daily_df['Date'])
    daily_df['Weekday'] = daily_df['Datetime'].dt.day_name()
    daily_df['IsWE'] = daily_df['Weekday'].isin(['Saturday', 'Sunday'])
    
    # JO
    jo_data = daily_df[~daily_df['IsWE']]
    total_jo = jo_data['Count'].sum()
    avg_jo = total_jo / max(1, nb_days_jo) if nb_days_jo > 0 else 0
    
    # WE
    we_data = daily_df[daily_df['IsWE']]
    total_we = we_data['Count'].sum()
    avg_we = total_we / max(1, nb_days_we) if nb_days_we > 0 else 0
    
    # Peak
    if not daily_df.empty:
        peak_idx = daily_df['Count'].idxmax()
        peak_row = daily_df.loc[peak_idx]
        peak_day = peak_row['Date'].strftime('%d/%m/%Y') if pd.notnull(peak_row['Date']) else "-"
        peak_count = peak_row['Count']
    else:
        peak_day = "-"
        peak_count = 0
        
    # Busiest Day of Week
    # Average by Weekday
    if not daily_df.empty:
        weekday_avg = daily_df.groupby('Weekday')['Count'].mean()
        # Translate to French for display
        french_days = {'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
                       'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'}
        # Sort by standard week to find max? Or just idxmax
        max_day_en = weekday_avg.idxmax()
        max_day = french_days.get(max_day_en, max_day_en)
    else:
        max_day = "-"

    return [
        f"{int(total):,}".replace(",", " "),
        f"{int(round(avg_daily)):,}".replace(",", " "),
        f"{int(round(avg_jo)):,}".replace(",", " "),
        f"{int(round(avg_we)):,}".replace(",", " "),
        peak_day,
        f"{int(peak_count):,}".replace(",", " "),
        max_day
    ]

def _build_synthesis_table(period_df, start_date, end_date, is_seasonal=False):
    if period_df.empty:
        return html.Div("Pas de données sur la période.")
        
    # Calculate days based on range, not just data presence, to get correct averages?
    # Usually averages are over the selected period.
    if is_seasonal:
        dates_df = pd.DataFrame({'Date': period_df['Date'].unique()})
    else:
        s_date = pd.to_datetime(start_date or period_df['Datetime'].min()).date()
        e_date = pd.to_datetime(end_date or period_df['Datetime'].max()).date()
        date_range = pd.date_range(start=s_date, end=e_date, freq='D')
        dates_df = pd.DataFrame({'Date': date_range})
        
    dates_df['Date'] = pd.to_datetime(dates_df['Date']) # Ensure datetime
    dates_df['DayName'] = dates_df['Date'].dt.day_name()
    dates_df['IsWE'] = dates_df['DayName'].isin(['Saturday', 'Sunday'])
    
    nb_days_total = len(dates_df)
    nb_days_jo = len(dates_df[~dates_df['IsWE']])
    nb_days_we = len(dates_df[dates_df['IsWE']])
    
    metrics = _compute_pedestrian_metrics(period_df, nb_days_total, nb_days_jo, nb_days_we)
    
    labels = [
        "Fréquentation totale",
        "Moyenne journalière (FMJ)",
        "Moyenne jours ouvrés (JO)",
        "Moyenne week-end (WE)",
        "Jour du pic de fréquentation",
        "Pic de fréquentation",
        "Jour de la semaine le plus fréquenté"
    ]
    
    rows = []
    for lbl, val in zip(labels, metrics):
        rows.append(html.Tr([
            html.Td(lbl, className="fw-bold"),
            html.Td(str(val), className="text-end")
        ]))
        
    return dbc.Table([html.Tbody(rows)], bordered=True, hover=True, striped=True, className="w-100")

def layout(site_id=None):
    if not site_id:
        return dbc.Container(html.Div("Site non spécifié", className="alert alert-danger mt-5"))
        
    dm = DataManager()
    df = dm.get_data(site_id)
    
    if df.empty:
         return dbc.Container(html.Div(f"Pas de données trouvées pour le site: {site_id}", className="alert alert-warning mt-5"))
    
    # Store site_id
    store = dcc.Store(id='ped-site-id', data=site_id)
    
    # Unified layout
    ped_layout = create_dashboard_layout(df, dashboard_type="PIÉTON")
    
    ped_layout.children.insert(0, store)
    
    # Add navigation breadcrumb
    breadcrumb = create_breadcrumb(df.attrs.get('metadata', {}).get('site_name', site_id))
    ped_layout.children.insert(0, breadcrumb)

    return ped_layout


# --- Callbacks ---

@callback(
    Output("ped-season-collapse", "is_open"),
    Input("ped-season-switch", "value")
)
def toggle_ped_season(val):
    return val

@callback(
    [Output("ped-content-synthese", "children"),
     Output("ped-timeline-graph", "figure"),
     Output("ped-heatmap-day-hour", "figure"),
     Output("ped-content-annual", "children")],
    [Input("ped-tabs", "value"),
     Input("ped-date-picker", "start_date"),
     Input("ped-date-picker", "end_date"),
     Input("ped-season-switch", "value"),
     Input("ped-season-start-month", "value"),
     Input("ped-season-start-day", "value"),
     Input("ped-season-end-month", "value"),
     Input("ped-season-end-day", "value"),
     Input('ped-timeline-graph', 'relayoutData')],
    [State("ped-site-id", "data")]
)
def update_content(active_tab, start_date, end_date, season_mode, sm, sd, em, ed, relayout_data, site_id):
    dm = DataManager()
    df = dm.get_data(site_id)
    
    # Filter Data
    # 1. Date Range
    filtered_df = filter_by_date(df, start_date, end_date)
    s_date = pd.to_datetime(start_date)
    e_date = pd.to_datetime(end_date)
    
    # 2. Season Intersection
    if season_mode:
        filtered_df = filter_by_season(filtered_df, sm, sd, em, ed, False) # For seasonal filtering, we don't need the theoretical days count as we're only looking at actual data presence
    
    synthese_content = html.Div()
    annual_content = html.Div()
    timeline_fig = {}
    heatmap_fig = {}
    
    if active_tab == "tab-synthese":
        label_period = f"Période: {start_date} au {end_date}"
        if season_mode:
             label_period += f" (Filtré: {sd}/{sm} - {ed}/{em})"
             
        synthese_content = dbc.Card([
            dbc.CardHeader(f"INDICATEURS CLÉS", className="bg-white fw-bold"),
            dbc.CardBody(_build_synthesis_table(filtered_df, start_date, end_date, is_seasonal=season_mode), className="p-0")
        ], className="shadow-sm border-0")
        return synthese_content, dash.no_update, dash.no_update, dash.no_update

    elif active_tab == "tab-temporal":
        if filtered_df.empty:
            return dash.no_update, {}, {}, dash.no_update

        # --- Dynamic Granularity Logic ---
        current_visible_start = s_date
        current_visible_end = e_date
        
        if relayout_data:
            if 'xaxis.range[0]' in relayout_data:
                try:
                    current_visible_start = pd.to_datetime(relayout_data['xaxis.range[0]'])
                    current_visible_end = pd.to_datetime(relayout_data['xaxis.range[1]'])
                except:
                    pass
            elif 'xaxis.range' in relayout_data: # sometimes array
                 try:
                    current_visible_start = pd.to_datetime(relayout_data['xaxis.range'][0])
                    current_visible_end = pd.to_datetime(relayout_data['xaxis.range'][1])
                 except:
                    pass

        duration = current_visible_end - current_visible_start
        days = duration.days
        
        # Decision Thresholds
        freq = 'D'
        title_suffix = "Journalier"
        chart_type = 'line' # Default requested
        
        if days > 400: # Broad view -> Monthly
             freq = 'MS' # Monthly
             title_suffix = "Mensuelle"
             chart_type = 'bar'
        elif days < 14: # Very close -> Hourly
             freq = 'h'
             title_suffix = "Horaire"
             chart_type = 'line'
        else: # Default -> Daily
             freq = 'D'
             title_suffix = "Journalière"
             chart_type = 'line'

        target_df = filtered_df.copy()
        resampled = target_df .groupby(pd.Grouper(key='Datetime', freq=freq))['Count'].sum(min_count=1).reset_index()
        
        if chart_type == 'bar':
             fig_timeline = px.bar(resampled, x='Datetime', y='Count', 
                                  title=f"Évolution ({title_suffix})",
                                  labels={'Datetime': 'Date', 'Count': 'Passages'},
                                  template='plotly_white', color_discrete_sequence=[COLOR_MAP.get('Piétons', '#27AE60')])
             fig_timeline.update_layout(bargap=0.1)
             fig_timeline.update_traces(hovertemplate="%{x|%b %Y} : %{y} passages<extra></extra>")
             fig_timeline.update_xaxes(dtick="M2", tickformat="%b\n%Y")
        else:
             fig_timeline = px.line(resampled, x='Datetime', y='Count', 
                                   title=f"Évolution ({title_suffix})",
                                   labels={'Datetime': 'Date', 'Count': 'Passages'},
                                   template='plotly_white', color_discrete_sequence=[COLOR_MAP.get('Piétons', '#27AE60')])  
             fig_timeline.update_traces(fill='tozeroy')

        # Prevent un-zooming: If we detected a zoom, re-apply it.
        # But only if the zoom is smaller than the date-picker range?
        # Actually, simpler: if relayout triggered this update, keep the range.
        if ctx.triggered_id == 'ped-timeline-graph' and relayout_data and ('xaxis.range[0]' in relayout_data or 'xaxis.range' in relayout_data):
             fig_timeline.update_layout(xaxis_range=[current_visible_start, current_visible_end])

        timeline_fig = fig_timeline

        # --- Heatmap ---
        grp = filtered_df.groupby(['Weekday', 'Hour'])['Count'].mean().reset_index()
        grp['Weekday'] = pd.Categorical(grp['Weekday'], categories=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ordered=True)
        grp = grp.sort_values('Weekday')
        grp['Weekday_FR'] = grp['Weekday'].map({
            'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
        })
        
        fig_heatmap = px.density_heatmap(grp, x='Hour', y='Weekday_FR', z='Count', 
                                         title="Intensité Moyenne (Semaine Type)",
                                         labels={'Hour': 'Heure', 'Weekday_FR': 'Jour', 'Count': 'Passages (Moy)'},
                                         nbinsx=24, nbinsy=7, color_continuous_scale="Viridis",
                                         category_orders={"Weekday_FR": ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']},)
        fig_heatmap.update_layout(template='plotly_white')
        fig_heatmap.update_traces( hovertemplate="Jour: %{y}<br>Heure: %{x}:00<br>Passages (Moy): %{z:.2f}<extra></extra>")
        fig_heatmap.update_coloraxes(colorbar_title="Moyenne des passages")
        heatmap_fig = fig_heatmap

        return dash.no_update, timeline_fig, heatmap_fig, dash.no_update

    elif active_tab == "tab-annual":
        df_annual = df.copy()
        df_annual['DOY'] = df_annual['Datetime'].dt.dayofyear
        
        # Force Integer Year
        df_annual['Year'] = pd.to_numeric(df_annual['Year'], errors='coerce').fillna(0).astype(int)
        df_annual['YearStr'] = df_annual['Year'].astype(str)
        
        daily_annual = df_annual.groupby(['YearStr', 'DOY'])['Count'].sum().reset_index()
        
        # --- Smoothing for nicer "Ridgeline" visual ---
        # Rolling average 7 days to smooth out the jagged daily peaks
        daily_annual['Count_Smooth'] = daily_annual.groupby('YearStr')['Count'].transform(lambda x: x.rolling(7, min_periods=1, center=True).mean())
        
        daily_annual['FakeDate'] = pd.to_datetime(daily_annual['DOY'] - 1, unit='D', origin='2000-01-01')
        
        # Ridgeline Logic
        years = sorted(daily_annual['YearStr'].unique(), reverse=True) # Top to bottom
        if not years:
             return dash.no_update, dash.no_update, dash.no_update, html.Div("Pas de données")

        # Dynamic offset based on max smoothed value to ensure consistent look
        max_val = daily_annual['Count_Smooth'].max()
        # Increased spacing to reduce overlap (was 0.35)
        offset_step = max_val * 0.75 
        
        fig = go.Figure()
        
        fill_color = COLOR_MAP.get('Piétons', '#27AE60')
        
        for i, year in enumerate(years):
            d_year = daily_annual[daily_annual['YearStr'] == year].sort_values('DOY')
            if d_year.empty:
                continue
            
            # Use specific scale factor to control height relative to spacing if needed
            # Here we just use the raw values, but spaced out more
            base_y = i * offset_step
            
            x_vals = d_year['FakeDate'].tolist()
            y_vals = (d_year['Count_Smooth'] + base_y).tolist()
            
            # Close polygon for fill (down to baseline)
            x_poly = x_vals + x_vals[::-1]
            y_poly = y_vals + [base_y] * len(y_vals)
            
            fig.add_trace(go.Scatter(
                x=x_poly,
                y=y_poly,
                fill='toself',
                mode='lines',
                line=dict(color='white', width=1.5), # White outline for separation
                fillcolor=fill_color,
                opacity=0.9, # Higher opacity to hide the lines behind, creating a cleaner "stack"
                name=year,
                # customdata=np.stack((d_year['Count'], d_year['YearStr']), axis=-1),
                # hovertemplate=f"<b>%{{customdata[1]}}</b><br>Date: %{{x|%d %B}}<br>Fréquentation: %{{customdata[0]}}<extra></extra>",
                showlegend=False
            ))

            # Add Label on the left
            fig.add_annotation(
                x=pd.to_datetime('2000-01-01'),
                y=base_y,
                text=f"<b>{year}</b>",
                showarrow=False,
                xanchor='right',
                xshift=-10,
                yshift=10, 
                font=dict(size=12, color="#444")
            )

        fig.update_layout(
            title="Comparaison Annuelle (Profil journalier lissé)",
            template='plotly_white',
            yaxis=dict(showticklabels=False, title=None, showgrid=False, zeroline=False),
            xaxis=dict(
                title=None,
                tickmode='array',
                tickvals=pd.date_range('2000-01-01', periods=12, freq='MS'),
                ticktext=['Janv', 'Févr', 'Mars', 'Avri', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc']
            ),
            height=600,
            margin=dict(l=80, r=20, t=60, b=40),
            hovermode="x unified" 
        )
        
        annual_content = dbc.Card(dbc.CardBody([dcc.Graph(id='ped-annual-graph', figure=fig, config={'locale': 'fr'})]), className="shadow-sm border-0")
        return dash.no_update, dash.no_update, dash.no_update, annual_content

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update
