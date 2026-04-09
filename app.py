import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from collections import deque
from data_manager import candles_deque, analysis_deque, start_simulation
from pivot_algorithm import AutoTrendSupportResistance

# Start simulation
start_simulation()

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Order Flow & Pivot Terminal", style={'color': 'white', 'textAlign': 'center', 'fontFamily': 'Arial'}),

    html.Div([
        html.Div(id='trap-alerts', style={'color': 'red', 'fontWeight': 'bold', 'height': '30px'}),
        html.Div([
            html.Label("Select Instrument:", style={'color': 'white'}),
            dcc.Dropdown(
                id='instrument-selector',
                options=[
                    {'label': 'NIFTY 22000 CE (ATM)', 'value': 'NIFTY_22000_CE'},
                    {'label': 'NIFTY 22100 CE (OTM)', 'value': 'NIFTY_22100_CE'},
                    {'label': 'NIFTY 21900 PE (OTM)', 'value': 'NIFTY_21900_PE'}
                ],
                value='NIFTY_22000_CE',
                style={'width': '300px', 'color': 'black'}
            )
        ], style={'padding': '10px'})
    ]),

    dcc.Graph(id='main-chart', style={'height': '80vh'}),
    dcc.Interval(id='update-interval', interval=1000, n_intervals=0)
], style={'backgroundColor': '#111111', 'padding': '20px', 'minHeight': '100vh'})

@app.callback(
    [Output('main-chart', 'figure'),
     Output('trap-alerts', 'children')],
    [Input('update-interval', 'n_intervals'),
     Input('instrument-selector', 'value')]
)
def update_chart(n, instrument_key):
    if len(candles_deque) < 2:
        return go.Figure(), "Waiting for data..."

    # 1. Prepare Data
    df = pd.DataFrame([{
        'time': c.start_time, 'open': c.open, 'high': c.high,
        'low': c.low, 'close': c.close, 'delta': c.delta, 'volume': c.volume
    } for c in candles_deque])

    analysis_df = pd.DataFrame(list(analysis_deque))

    # 2. Run Pivot Algorithm
    indicator = AutoTrendSupportResistance(required_ticks_for_broken=4, tick_size=1)
    for i in range(1, len(df)):
        indicator.update(
            current_bar_idx=i,
            prev_open=df['open'].iloc[i-1],
            prev_high=df['high'].iloc[i-1],
            prev_low=df['low'].iloc[i-1],
            prev_close=df['close'].iloc[i-1]
        )

    # 3. Create Figure with subplots
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 4. Main Candlestick Chart (Row 1)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name='Price'
    ), row=1, col=1)

    # 5. Support/Resistance Lines & Trendlines
    for pivot in indicator.pivots:
        if pivot.display_level:
            color = "gold" if pivot.is_level_tested else "cyan"
        elif pivot.is_level_broken:
            color = "crimson"
        else:
            continue

        fig.add_shape(
            type="line",
            x0=pivot.bar_number, y0=pivot.price,
            x1=len(df), y1=pivot.price,
            line=dict(color=color, width=1, dash="dash"),
            row=1, col=1
        )

    if len(indicator.pivots) > 1:
        trend_x = [p.bar_number for p in indicator.pivots]
        trend_y = [p.price for p in indicator.pivots]
        fig.add_trace(go.Scatter(
            x=trend_x, y=trend_y,
            mode='lines',
            line=dict(color='darkgoldenrod', width=2),
            name="Trend"
        ), row=1, col=1)

    # 6. Order Flow Annotations (Deltas)
    for i, row in df.iterrows():
        color = "lime" if row['delta'] > 0 else "red"
        fig.add_annotation(
            x=i, y=row['low'], text=str(row['delta']),
            showarrow=False, yshift=-15, font=dict(color=color, size=10),
            row=1, col=1
        )

    # 7. Highlight Absorption Zones
    alert_text = ""
    if not analysis_df.empty:
        latest_analysis = analysis_df.iloc[-1]
        for zone in latest_analysis['absorption_zones']:
            fig.add_shape(type="line", x0=len(df)-2, y0=zone, x1=len(df), y1=zone,
                          line=dict(color="orange", width=3), row=1, col=1)
            alert_text = f"⚠️ ABSORPTION (THE WALL) DETECTED AT {zone}"

        if latest_analysis['exhaustion']:
            alert_text += " | 💨 EXHAUSTION DETECTED"

    # 8. Cumulative Delta Subplot (Row 2)
    fig.add_trace(go.Scatter(
        x=analysis_df.index, y=analysis_df['cum_delta'],
        fill='tozeroy', line=dict(color='cyan', width=2), name='Cum. Delta'
    ), row=2, col=1)

    # UI Styling
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False,
        showlegend=False,
        yaxis_title=f"Price ({instrument_key})"
    )

    return fig, alert_text

if __name__ == '__main__':
    app.run(debug=True, port=8050)
