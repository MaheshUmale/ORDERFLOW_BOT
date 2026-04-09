import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data_manager import (get_all_opt_candles, analysis_deque, get_synced_df,
                          start_simulation, start_live_feed, change_instrument, rs_strategy, engine)
from pivot_algorithm import AutoTrendSupportResistance
from upstox_helper import UpstoxHelper
import datetime

helper = UpstoxHelper()
app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div([
    dcc.Store(id='signal-history', data=[]),
    dcc.Store(id='active-instrument-store', data={'key': None, 'label': 'No Instrument Selected'}),

    html.H2("Order Flow & RS Trading Terminal (Upstox Live)",
            style={'color': 'white', 'textAlign': 'center', 'fontFamily': 'Arial'}),

    html.Div([
        # Control Bar
        html.Div([
            html.Div([
                html.Label("Base Index:", style={'color': 'white'}),
                dcc.Dropdown(id='base-index',
                             options=[{'label': 'NIFTY', 'value': 'NIFTY'},
                                      {'label': 'BANKNIFTY', 'value': 'BANKNIFTY'}],
                             value='NIFTY', style={'width': '120px', 'color': 'black'})
            ], style={'display': 'inline-block', 'padding': '10px'}),

            html.Div([
                html.Label("Option Instrument:", style={'color': 'white'}),
                dcc.Dropdown(id='instrument-selector',
                             placeholder="Example: NIFTY 23800 CE",
                             searchable=True,
                             style={'width': '450px', 'color': 'black'})
            ], style={'display': 'inline-block', 'padding': '10px'}),

            html.Div([
                html.Label("Terminal Mode:", style={'color': 'white'}),
                dcc.RadioItems(id='terminal-mode',
                               options=[{'label': 'Order Flow', 'value': 'OF'},
                                        {'label': 'Rel. Strength', 'value': 'RS'}],
                               value='OF', style={'color': 'white'},
                               labelStyle={'display': 'inline-block', 'margin-right': '10px'})
            ], style={'display': 'inline-block', 'padding': '10px'}),

            html.Button('Connect & Start', id='connect-button', n_clicks=0,
                        style={'margin-top': '30px', 'backgroundColor': '#00ff00', 'fontWeight': 'bold', 'padding':'5px 15px', 'borderRadius':'5px'})
        ], style={'backgroundColor': '#222', 'borderRadius': '5px', 'margin-bottom': '10px', 'padding':'10px'}),

        html.Div(id='status-line', style={'color': '#00ff00', 'padding': '5px', 'fontWeight': 'bold'}),
        html.Div(id='trap-alerts', style={'color': '#ffcc00', 'fontWeight': 'bold', 'height': '30px'}),
        html.Div(id='signal-alert', style={'padding': '5px'})
    ]),

    html.Div([
        dcc.Graph(id='main-chart', style={'height': '75vh', 'width': '78%', 'display': 'inline-block'}),
        html.Div([
            html.H3("Signal Log", style={'color': 'white', 'textAlign': 'center'}),
            html.Div(id='signal-log', style={'height': '65vh', 'overflowY': 'scroll', 'color': '#00ff00', 'backgroundColor': '#000', 'padding': '5px', 'fontFamily': 'Courier New', 'fontSize': '12px', 'border':'1px solid #444'})
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
    ]),

    dcc.Interval(id='update-interval', interval=1000, n_intervals=0),
    dcc.Interval(id='slow-update-interval', interval=30000, n_intervals=0)
], style={'backgroundColor': '#111111', 'padding': '10px', 'minHeight': '100vh'})

@app.callback(
    Output('instrument-selector', 'options'),
    [Input('base-index', 'value')]
)
def update_instrument_options(index):
    try:
        chain = helper.get_option_chain(symbol=index)
        if chain.empty: return []
        options = []
        for _, row in chain.iterrows():
            options.append({'label': row['label'], 'value': row['instrument_key']})
        return options
    except Exception as e:
        print(f"Error loading options: {e}")
        return []

@app.callback(
    [Output('signal-history', 'data'),
     Output('active-instrument-store', 'data'),
     Output('status-line', 'children')],
    [Input('connect-button', 'n_clicks')],
    [State('instrument-selector', 'value'),
     State('instrument-selector', 'options'),
     State('base-index', 'value'),
     State('signal-history', 'data')]
)
def handle_connect(n_clicks, instrument_key, options, index, history):
    if n_clicks > 0 and instrument_key:
        label = "Unknown"
        if options:
            for opt in options:
                if opt['value'] == instrument_key:
                    label = opt['label']
                    break
        change_instrument(instrument_key, index)
        start_live_feed()
        status = f"CONNECTED: {label}"
        return [], {'key': instrument_key, 'label': label}, status
    return history, {'key': None, 'label': 'No Instrument Selected'}, "STATUS: READY"

@app.callback(
    [Output('main-chart', 'figure'),
     Output('trap-alerts', 'children'),
     Output('signal-log', 'children'),
     Output('signal-alert', 'children'),
     Output('signal-history', 'data', allow_duplicate=True)],
    [Input('update-interval', 'n_intervals')],
    [State('terminal-mode', 'value'),
     State('signal-history', 'data'),
     State('active-instrument-store', 'data')],
    prevent_initial_call=True
)
def update_chart(n, mode, history, active_instrument):
    instrument_label = active_instrument['label']

    # 1. Prepare Data
    all_opt_candles = get_all_opt_candles()
    if not all_opt_candles:
        return go.Figure().update_layout(title="Waiting for Data...", template="plotly_dark"), "Waiting for ticks...", "", "", history

    df_opt = pd.DataFrame([{
        'time': c.start_time, 'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close, 'delta': c.delta
    } for c in all_opt_candles])

    # Re-calculate analysis for all candles including current one for real-time signals
    current_analysis = []
    temp_cum_delta = engine.cumulative_delta
    for i, c in enumerate(all_opt_candles):
        # For historical candles in the deque, we use their stored/calculated cum_delta
        # Actually it's easier to just re-run from the start of the current session view
        if i == 0:
            analysis = engine.analyze_candle(c, 0)
        else:
            analysis = engine.analyze_candle(c, current_analysis[-1]['cum_delta'])
        current_analysis.append(analysis)

    analysis_df = pd.DataFrame(current_analysis)

    df_sync = get_synced_df()
    if not df_sync.empty:
        df_sync = rs_strategy.detect_signals(df_sync)

    # 2. Figure Setup
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 3. Main Plot
    fig.add_trace(go.Candlestick(x=df_opt['time'], open=df_opt['open'], high=df_opt['high'], low=df_opt['low'], close=df_opt['close'], name=instrument_label), row=1, col=1)

    if mode == 'RS' and not df_sync.empty:
        # Overlay Index (Normalized or secondary axis recommended, but overlay for now)
        fig.add_trace(go.Scatter(x=df_sync.index, y=df_sync['idx_close'], name='NIFTY Index', line=dict(color='orange', width=1, dash='dot')), row=1, col=1)

    # 4. Technical Levels
    indicator = AutoTrendSupportResistance(required_ticks_for_broken=4, tick_size=1)
    for i in range(1, len(df_opt)):
        indicator.update(i, df_opt['open'].iloc[i-1], df_opt['high'].iloc[i-1], df_opt['low'].iloc[i-1], df_opt['close'].iloc[i-1])

    for pivot in indicator.pivots:
        if not pivot.display_level: continue
        color = "gold" if pivot.is_level_tested else "cyan"
        fig.add_shape(type="line", x0=df_opt['time'].iloc[pivot.bar_number], y0=pivot.price, x1=df_opt['time'].iloc[-1], y1=pivot.price,
                      line=dict(color=color, width=1, dash="dash"), row=1, col=1)

    # 5. Signal Detection & Display
    signal_alert_div = None

    for i, row in analysis_df.iterrows():
        if row['signal'] and pd.notna(row['signal']):
            color = 'lime' if row['signal'] == 'BUY' else 'red'
            fig.add_trace(go.Scatter(x=[row['time']], y=[df_opt.iloc[i]['low'] if row['signal'] == 'BUY' else df_opt.iloc[i]['high']],
                                     mode="markers+text", marker=dict(symbol="triangle-up" if row['signal'] == 'BUY' else "triangle-down", size=15, color=color),
                                     text=[row['signal']], textposition="bottom center", name="OF SIGNAL"), row=1, col=1)

            sig_msg = f"{row['time'].strftime('%H:%M:%S')} - OF {row['signal']} detected"
            if sig_msg not in history:
                history.append(sig_msg)
                if i == len(analysis_df) - 1:
                    signal_alert_div = html.Div(f"🚀 {row['signal']} SIGNAL DETECTED!",
                                               style={'backgroundColor': 'green' if row['signal']=='BUY' else 'red', 'color': 'white', 'padding': '15px', 'borderRadius':'5px', 'fontSize':'20px', 'textAlign':'center'})

    if mode == 'RS' and not df_sync.empty:
        rs_sigs = df_sync[df_sync['rs_bullish_signal']]
        for ts, row in rs_sigs.iterrows():
            fig.add_trace(go.Scatter(x=[ts], y=[row['opt_low'] - 2], mode="markers", marker=dict(symbol="star", size=15, color='cyan'), name="RS BUY"), row=1, col=1)
            sig_msg = f"{ts.strftime('%H:%M:%S')} - RS BULLISH Divergence"
            if sig_msg not in history:
                history.append(sig_msg)
                signal_alert_div = html.Div("🌟 RS BULLISH SIGNAL DETECTED!", style={'backgroundColor': 'cyan', 'color': 'black', 'padding': '15px', 'borderRadius':'5px', 'fontSize':'20px', 'textAlign':'center'})

    # 6. Footprint & Delta
    for i, row in df_opt.iterrows():
        color = "lime" if row['delta'] > 0 else "red"
        fig.add_annotation(x=row['time'], y=row['low'], text=str(int(row['delta'])), showarrow=False, yshift=-15, font=dict(color=color, size=10), row=1, col=1)

    fig.add_trace(go.Scatter(x=analysis_df['time'], y=analysis_df['cum_delta'], fill='tozeroy', name='Cumulative Delta', line=dict(color='cyan', width=2)), row=2, col=1)

    fig.update_layout(title=f"LIVE: {instrument_label}", template="plotly_dark", margin=dict(l=10, r=10, t=50, b=10), xaxis_rangeslider_visible=False, showlegend=False)

    alert_text = "STATUS: MONITORING"
    if not analysis_df.empty:
        if analysis_df.iloc[-1]['absorption_zones']: alert_text = "⚠️ ABSORPTION ZONE"
        if analysis_df.iloc[-1]['exhaustion']: alert_text += " | 💨 EXHAUSTION"

    return fig, alert_text, [html.Div(e) for e in reversed(history)], signal_alert_div, history

if __name__ == '__main__':
    # Default to simulation mode if no credentials provided or specifically requested
    # For live usage, the 'Connect & Start' button will initialize the Upstox WSS feed.
    start_simulation()
    app.run(debug=True, port=8050)
