"""
Earthquake Data Analysis Dashboard
===================================
Interactive dashboard for visualizing earthquake patterns in Mexico

This dashboard uses ONLY the transformed analytics layer (analytics_earthquakes table),
demonstrating the separation between raw and analytics data in the ELT pattern.
"""

import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import os
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DW_HOST', 'postgres'),
    'port': os.getenv('DW_PORT', '5432'),
    'database': os.getenv('DW_DB', 'earthquake_dw'),
    'user': os.getenv('DW_USER', 'dwuser'),
    'password': os.getenv('DW_PASSWORD', 'dwpassword')
}

# Create SQLAlchemy engine
engine = create_engine(
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Color scheme
COLORS = {
    'background': '#0f172a',
    'surface': '#1e293b',
    'primary': '#3b82f6',
    'secondary': '#8b5cf6',
    'accent': '#f59e0b',
    'danger': '#ef4444',
    'success': '#10b981',
    'text': '#f1f5f9',
    'text_secondary': '#94a3b8'
}

def fetch_analytics_data():
    """Fetch data from ANALYTICS layer only (not raw)"""
    query = """
    SELECT 
        earthquake_date,
        earthquake_datetime,
        magnitude,
        latitude,
        longitude,
        depth_km,
        location_reference,
        status,
        year,
        month,
        day_of_week,
        hour_of_day,
        magnitude_category,
        depth_category,
        region,
        is_significant
    FROM analytics_earthquakes
    ORDER BY earthquake_datetime DESC
    LIMIT 10000
    """
    return pd.read_sql(query, engine)

def fetch_statistics():
    """Fetch aggregated statistics"""
    query = """
    SELECT * FROM earthquake_statistics
    ORDER BY calculation_date DESC
    LIMIT 1
    """
    return pd.read_sql(query, engine)

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="Earthquake Analysis Dashboard"
)
app.config.suppress_callback_exceptions = True

# Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("🌍 Earthquake Data Analysis Dashboard", 
                   className="text-center mb-2 mt-4",
                   style={'color': COLORS['text'], 'fontWeight': 'bold'}),
            html.P("Real-time seismic activity analysis for disaster preparedness and policy-making",
                  className="text-center mb-4",
                  style={'color': COLORS['text_secondary'], 'fontSize': '1.1rem'})
        ])
    ]),
    
    # KPI Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("📊 Total Earthquakes", className="card-title",
                           style={'color': COLORS['text_secondary']}),
                    html.H2(id='kpi-total', className="text-center",
                           style={'color': COLORS['primary'], 'fontWeight': 'bold'})
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("📈 Avg Magnitude", className="card-title",
                           style={'color': COLORS['text_secondary']}),
                    html.H2(id='kpi-avg-magnitude', className="text-center",
                           style={'color': COLORS['accent'], 'fontWeight': 'bold'})
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("⚠️ Significant Events", className="card-title",
                           style={'color': COLORS['text_secondary']}),
                    html.H2(id='kpi-significant', className="text-center",
                           style={'color': COLORS['danger'], 'fontWeight': 'bold'})
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("🔥 Max Magnitude", className="card-title",
                           style={'color': COLORS['text_secondary']}),
                    html.H2(id='kpi-max-magnitude', className="text-center",
                           style={'color': COLORS['success'], 'fontWeight': 'bold'})
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=3),
    ], className="mb-4"),
    
    # Filters
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Magnitude Range", style={'color': COLORS['text']}),
                    dcc.RangeSlider(
                        id='magnitude-slider',
                        min=0,
                        max=8,
                        step=0.5,
                        value=[0, 8],
                        marks={i: str(i) for i in range(0, 9)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Label("Region Filter", style={'color': COLORS['text']}),
                    dcc.Dropdown(
                        id='region-dropdown',
                        multi=True,
                        placeholder="Select regions...",
                        style={'color': '#000'}
                    )
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=6),
    ], className="mb-4"),
    
    # Main Charts Row 1
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Magnitude Distribution by Category", 
                           style={'color': COLORS['text']}),
                    dcc.Graph(id='magnitude-distribution')
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Earthquakes by Region", 
                           style={'color': COLORS['text']}),
                    dcc.Graph(id='region-chart')
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=6),
    ], className="mb-4"),
    
    # Main Charts Row 2
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Temporal Pattern: Earthquakes Over Time", 
                           style={'color': COLORS['text']}),
                    dcc.Graph(id='temporal-chart')
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=12),
    ], className="mb-4"),
    
    # Map and Depth Analysis
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Geographic Distribution Map", 
                           style={'color': COLORS['text']}),
                    dcc.Graph(id='earthquake-map')
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=8),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Depth Analysis", 
                           style={'color': COLORS['text']}),
                    dcc.Graph(id='depth-chart')
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ], width=4),
    ], className="mb-4"),
    
    # Insights Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("📋 Key Insights", style={'color': COLORS['text']}),
                    html.Div(id='insights-text')
                ])
            ], style={'backgroundColor': COLORS['surface'], 'border': 'none'})
        ])
    ], className="mb-4"),
    
    # Refresh interval
    dcc.Interval(
        id='interval-component',
        interval=60*1000,  # Update every minute
        n_intervals=0
    ),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(style={'borderColor': COLORS['text_secondary']}),
            html.P("Data Source: Analytics Layer (analytics_earthquakes) | ELT Pipeline Project",
                  className="text-center",
                  style={'color': COLORS['text_secondary'], 'fontSize': '0.9rem'})
        ])
    ])
    
], fluid=True, style={'backgroundColor': COLORS['background'], 'minHeight': '100vh'})

# Callbacks
@app.callback(
    [Output('kpi-total', 'children'),
     Output('kpi-avg-magnitude', 'children'),
     Output('kpi-significant', 'children'),
     Output('kpi-max-magnitude', 'children'),
     Output('region-dropdown', 'options'),
     Output('magnitude-distribution', 'figure'),
     Output('region-chart', 'figure'),
     Output('temporal-chart', 'figure'),
     Output('earthquake-map', 'figure'),
     Output('depth-chart', 'figure'),
     Output('insights-text', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('magnitude-slider', 'value'),
     Input('region-dropdown', 'value')]
)
def update_dashboard(n, magnitude_range, selected_regions):
    # Fetch data
    df = fetch_analytics_data()
    
    # Apply filters
    df_filtered = df[
        (df['magnitude'] >= magnitude_range[0]) & 
        (df['magnitude'] <= magnitude_range[1])
    ]
    
    if selected_regions:
        df_filtered = df_filtered[df_filtered['region'].isin(selected_regions)]
    
    # KPIs
    total_earthquakes = len(df_filtered)
    avg_magnitude = round(df_filtered['magnitude'].mean(), 2)
    significant_count = df_filtered['is_significant'].sum()
    max_magnitude = round(df_filtered['magnitude'].max(), 1)
    
    # Region options
    region_options = [{'label': r, 'value': r} for r in sorted(df['region'].unique())]
    
    # Chart 1: Magnitude Distribution
    mag_counts = df_filtered['magnitude_category'].value_counts().reset_index()
    mag_counts.columns = ['category', 'count']
    fig1 = px.bar(mag_counts, x='category', y='count',
                  title='',
                  color='count',
                  color_continuous_scale='Viridis')
    fig1.update_layout(
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['surface'],
        font_color=COLORS['text'],
        showlegend=False
    )
    
    # Chart 2: Earthquakes by Region
    region_counts = df_filtered['region'].value_counts().head(10).reset_index()
    region_counts.columns = ['region', 'count']
    fig2 = px.bar(region_counts, x='count', y='region',
                  orientation='h',
                  title='',
                  color='count',
                  color_continuous_scale='Plasma')
    fig2.update_layout(
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['surface'],
        font_color=COLORS['text'],
        showlegend=False
    )
    
    # Chart 3: Temporal Pattern
    temporal = df_filtered.groupby('year').size().reset_index()
    temporal.columns = ['year', 'count']
    fig3 = px.line(temporal, x='year', y='count',
                   title='',
                   markers=True)
    fig3.update_traces(line_color=COLORS['primary'], line_width=3)
    fig3.update_layout(
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['surface'],
        font_color=COLORS['text']
    )
    
    # Chart 4: Map
    fig4 = px.scatter_mapbox(
        df_filtered.head(500),
        lat='latitude',
        lon='longitude',
        color='magnitude',
        size='magnitude',
        hover_name='location_reference',
        hover_data=['magnitude', 'depth_km', 'earthquake_date'],
        color_continuous_scale='YlOrRd',
        zoom=4,
        height=500
    )
    fig4.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_center={"lat": 23.6345, "lon": -102.5528},
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['surface'],
        font_color=COLORS['text']
    )
    
    # Chart 5: Depth Analysis
    depth_counts = df_filtered['depth_category'].value_counts().reset_index()
    depth_counts.columns = ['category', 'count']
    fig5 = px.pie(depth_counts, values='count', names='category',
                  title='',
                  color_discrete_sequence=px.colors.sequential.RdBu)
    fig5.update_layout(
        plot_bgcolor=COLORS['surface'],
        paper_bgcolor=COLORS['surface'],
        font_color=COLORS['text']
    )
    
    # Insights
    most_active_region = df_filtered['region'].value_counts().index[0]
    most_active_count = df_filtered['region'].value_counts().values[0]
    avg_depth = round(df_filtered['depth_km'].mean(), 1)
    
    insights = html.Div([
        html.P(f"🎯 Most Active Region: {most_active_region} with {most_active_count} earthquakes", 
               style={'color': COLORS['text'], 'fontSize': '1.1rem'}),
        html.P(f"📊 Average Depth: {avg_depth} km (helps determine potential surface impact)", 
               style={'color': COLORS['text'], 'fontSize': '1.1rem'}),
        html.P(f"⚠️ {significant_count} significant events detected (magnitude ≥5.0 or shallow depth <50km)", 
               style={'color': COLORS['text'], 'fontSize': '1.1rem'}),
        html.P(f"🔍 Data shows patterns useful for: building code updates, emergency response planning, and public awareness campaigns", 
               style={'color': COLORS['text_secondary'], 'fontSize': '1rem', 'marginTop': '15px'})
    ])
    
    return (f"{total_earthquakes:,}", 
            f"{avg_magnitude}", 
            f"{significant_count}",
            f"{max_magnitude}",
            region_options,
            fig1, fig2, fig3, fig4, fig5,
            insights)

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=True)