import dash
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data_manager import (candles_deque, analysis_deque, get_synced_df,
                          start_simulation, change_instrument, rs_strategy)
from pivot_algorithm import AutoTrendSupportResistance
from upstox_helper import UpstoxHelper

helper = UpstoxHelper()
app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div([
    dcc.Store(id='signal-history', data=[]),

    html.H2("Enhanced Order Flow & RS Trading Terminal",
            style={'color': 'white', 'textAlign': 'center', 'fontFamily': 'Arial'}),

    html.Div([
        # Control Bar
        html.Div([
            html.Div([
                html.Label("Base Index:", style={'color': 'white'}),
                dcc.Dropdown(id='base-index', options=[{'label': 'NIFTY', 'value': 'NIFTY'}, {'label': 'BANKNIFTY', 'value': 'BANKNIFTY'}], value='NIFTY', style={'width': '120px', 'color': 'black'})
            ], style={'display': 'inline-block', 'padding': '10px'}),

            html.Div([
                html.Label("Option Instrument:", style={'color': 'white'}),
                dcc.Dropdown(id='instrument-selector', placeholder="Search Option...", style={'width': '350px', 'color': 'black'})
            ], style={'display': 'inline-block', 'padding': '10px'}),

            html.Div([
                html.Label("Terminal Mode:", style={'color': 'white'}),
                dcc.RadioItems(id='terminal-mode', options=[{'label': 'Order Flow', 'value': 'OF'}, {'label': 'Rel. Strength', 'value': 'RS'}], value='OF', style={'color': 'white'}, labelStyle={'display': 'inline-block', 'margin-right': '10px'})
            ], style={'display': 'inline-block', 'padding': '10px'}),

            html.Button('Connect WSS', id='connect-button', n_clicks=0, style={'margin-top': '30px'})
        ], style={'backgroundColor': '#222', 'borderRadius': '5px', 'margin-bottom': '10px'}),

        html.Div(id='trap-alerts', style={'color': '#ffcc00', 'fontWeight': 'bold', 'height': '30px'}),
        html.Div(id='signal-alert', style={'padding': '5px'})
    ]),

    html.Div([
        dcc.Graph(id='main-chart', style={'height': '75vh', 'width': '78%', 'display': 'inline-block'}),
        html.Div([
            html.H3("Signal Log", style={'color': 'white', 'textAlign': 'center'}),
            html.Div(id='signal-log', style={'height': '65vh', 'overflowY': 'scroll', 'color': '#00ff00', 'backgroundColor': '#000', 'padding': '5px', 'fontFamily': 'Courier New', 'fontSize': '12px'})
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
    ]),

    dcc.Interval(id='update-interval', interval=1000, n_intervals=0),
    dcc.Interval(id='slow-update-interval', interval=10000, n_intervals=0)
], style={'backgroundColor': '#111111', 'padding': '10px', 'minHeight': '100vh'})

@app.callback(
    Output('instrument-selector', 'options'),
    [Input('base-index', 'value'), Input('slow-update-interval', 'n_intervals')]
)
def update_instrument_options(index, n):
    try:
        chain = helper.get_option_chain(symbol=index)
        options = []
        for _, row in chain.iterrows():
            label = f"{row['underlying_symbol']} {row['expiry']} {row['strike']} {row['instrument_type']}"
            options.append({'label': label, 'value': row['instrument_key']})
        return options
    except: return []

@app.callback(
    Output('signal-history', 'data'),
    [Input('connect-button', 'n_clicks')],
    [State('instrument-selector', 'value'), State('base-index', 'value'), State('signal-history', 'data')]
)
def handle_connect(n_clicks, instrument_key, index, history):
    if n_clicks > 0 and instrument_key:
        change_instrument(instrument_key, index)
        return []
    return history

@app.callback(
    [Output('main-chart', 'figure'),
     Output('trap-alerts', 'children'),
     Output('signal-log', 'children'),
     Output('signal-alert', 'children'),
     Output('signal-history', 'data', allow_duplicate=True)],
    [Input('update-interval', 'n_intervals')],
    [State('terminal-mode', 'value'), State('signal-history', 'data')],
    prevent_initial_call=True
)
def update_chart(n, mode, history):
    # 1. Get Synchronized Data for RS logic
    df_sync = get_synced_df()
    if not df_sync.empty:
        df_sync = rs_strategy.detect_signals(df_sync)

    if len(candles_deque) < 2:
        return go.Figure(), "Waiting for feed...", "", "", history

    # 2. Main Option Data (for Candlesticks)
    df_opt = pd.DataFrame([{
        'time': c.start_time, 'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close, 'delta': c.delta
    } for c in candles_deque])

    analysis_df = pd.DataFrame(list(analysis_deque))

    # 3. Figure Setup
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 4. Mode-based Charting
    if mode == 'RS' and not df_sync.empty:
        # Show Index + Option Divergence
        fig.add_trace(go.Scatter(x=df_sync.index, y=df_sync['idx_close'], name='Index', line=dict(color='gray', width=1)), row=1, col=1)
        # Note: Index and Option have different price scales. In a real app we'd use secondary_y.
        # For simplicity, we just plot them together.

    fig.add_trace(go.Candlestick(x=df_opt.index, open=df_opt['open'], high=df_opt['high'], low=df_opt['low'], close=df_opt['close'], name='Option'), row=1, col=1)

    # 5. Support/Resistance (Pivots)
    indicator = AutoTrendSupportResistance(required_ticks_for_broken=4, tick_size=1)
    for i in range(1, len(df_opt)):
        indicator.update(i, df_opt['open'].iloc[i-1], df_opt['high'].iloc[i-1], df_opt['low'].iloc[i-1], df_opt['close'].iloc[i-1])

    for pivot in indicator.pivots:
        if not pivot.display_level: continue
        color = "gold" if pivot.is_level_tested else "cyan"
        fig.add_shape(type="line", x0=pivot.bar_number, y0=pivot.price, x1=len(df_opt), y1=pivot.price, line=dict(color=color, width=1, dash="dash"), row=1, col=1)

    # 6. Signal Markers
    signal_alert_div = None

    # Check OF Signals
    for i, row in analysis_df.iterrows():
        if row['signal']:
            fig.add_trace(go.Scatter(x=[i], y=[df_opt.iloc[i]['low']], mode="markers", marker=dict(symbol="triangle-up", size=12, color='lime'), name="OF BUY"), row=1, col=1)
            sig_msg = f"{row['time'].strftime('%H:%M:%S')} - OF {row['signal']} detected"
            if sig_msg not in history:
                history.append(sig_msg)
                if i == len(analysis_df) - 1:
                    signal_alert_div = html.Div(f"OF SIGNAL: {row['signal']}", style={'backgroundColor': 'green', 'color': 'white', 'padding': '10px'})

    # Check RS Signals
    if mode == 'RS' and not df_sync.empty:
        rs_sigs = df_sync[df_sync['rs_bullish_signal']]
        for ts, row in rs_sigs.iterrows():
            # Find index in opt_df
            idx_list = df_opt[df_opt['time'] == ts].index
            if not idx_list.empty:
                i = idx_list[0]
                fig.add_trace(go.Scatter(x=[i], y=[df_opt.iloc[i]['low'] - 2], mode="markers", marker=dict(symbol="star", size=15, color='cyan'), name="RS BUY"), row=1, col=1)
                sig_msg = f"{ts.strftime('%H:%M:%S')} - RS BULLISH setup"
                if sig_msg not in history:
                    history.append(sig_msg)
                    signal_alert_div = html.Div("RS BULLISH SIGNAL DETECTED!", style={'backgroundColor': 'cyan', 'color': 'black', 'padding': '10px'})

    # 7. Bottom Chart: Delta
    fig.add_trace(go.Scatter(x=analysis_df.index, y=analysis_df['cum_delta'], fill='tozeroy', name='Cum. Delta'), row=2, col=1)

    fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, showlegend=False)

    alert_text = "NORMAL"
    if not analysis_df.empty and analysis_df.iloc[-1]['absorption_zones']:
        alert_text = "⚠️ ABSORPTION ZONE"

    return fig, alert_text, [html.Div(e) for e in reversed(history)], signal_alert_div, history

if __name__ == '__main__':
    start_simulation()
    app.run(debug=True, port=8050)
