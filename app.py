import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data_manager import (get_all_opt_candles, get_synced_df,
                          start_live_feed, change_instrument, rs_strategy, engine)
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
                               labelStyle={'display': 'inline-block', 'marginRight': '10px'})
            ], style={'display': 'inline-block', 'padding': '10px'}),

            html.Button('Connect & Start', id='connect-button', n_clicks=0,
                        style={'marginTop': '30px', 'backgroundColor': '#00ff00', 'fontWeight': 'bold', 'padding':'5px 15px', 'borderRadius':'5px'}),

            # Live Stats Panel
            html.Div([
                html.Div([
                    html.Div("Backend LTP", style={'fontSize': '10px', 'color': '#aaa'}),
                    html.Div(id='stat-ltp', children="0.00", style={'fontSize': '18px', 'color': '#00ff00', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block', 'marginRight': '20px', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Candles", style={'fontSize': '10px', 'color': '#aaa'}),
                    html.Div(id='stat-candles', children="0", style={'fontSize': '18px', 'color': 'white'})
                ], style={'display': 'inline-block', 'marginRight': '20px', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Last Tick", style={'fontSize': '10px', 'color': '#aaa'}),
                    html.Div(id='stat-tick-time', children="--:--:--", style={'fontSize': '18px', 'color': 'white'})
                ], style={'display': 'inline-block', 'marginRight': '20px', 'textAlign': 'center'}),
                html.Div([
                    html.Div("UI Refresh", style={'fontSize': '10px', 'color': '#aaa'}),
                    html.Div(id='stat-refresh-count', children="0", style={'fontSize': '18px', 'color': 'cyan'})
                ], style={'display': 'inline-block', 'marginRight': '20px', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Heartbeat", style={'fontSize': '10px', 'color': '#aaa'}),
                    html.Div(id='stat-heartbeat', children="●", style={'fontSize': '18px', 'color': 'red'})
                ], style={'display': 'inline-block', 'textAlign': 'center'})
            ], style={'display': 'inline-block', 'float': 'right', 'backgroundColor': '#333', 'padding': '10px', 'borderRadius': '5px', 'marginTop': '5px'})

        ], style={'backgroundColor': '#222', 'borderRadius': '5px', 'marginBottom': '10px', 'padding':'10px'}),

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

app.clientside_callback(
    """
    function(n) {
        return [
            n,
            {color: n % 2 === 0 ? 'red' : 'lime'}
        ];
    }
    """,
    [Output('stat-refresh-count', 'children'),
     Output('stat-heartbeat', 'style')],
    [Input('update-interval', 'n_intervals')]
)

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
        print(f"Error loading options: {e}", flush=True)
        return []

@app.callback(
    [Output('signal-history', 'data'),
     Output('active-instrument-store', 'data'),
     Output('status-line', 'children')],
    [Input('connect-button', 'n_clicks')],
    [State('instrument-selector', 'value'),
     State('instrument-selector', 'options'),
     State('base-index', 'value'),
     State('signal-history', 'data')],
    prevent_initial_call=True
)
def handle_connect(n_clicks, instrument_key, options, index, history):
    if n_clicks > 0 and instrument_key:
        label = "Unknown"
        if options:
            for opt in options:
                if opt['value'] == instrument_key:
                    label = opt['label']
                    break

        # Start backend processes
        change_instrument(instrument_key, index)
        start_live_feed()

        status = f"CONNECTED: {label}"
        # Reset history on new connection to avoid confusion between instruments
        return [], {'key': instrument_key, 'label': label}, status

    # On initialization or if no key, keep current state
    if not instrument_key and n_clicks == 0:
        return dash.no_update, dash.no_update, dash.no_update
    return history, {'key': None, 'label': 'No Instrument Selected'}, "STATUS: READY"

@app.callback(
    [Output('main-chart', 'figure'),
     Output('trap-alerts', 'children'),
     Output('signal-log', 'children'),
     Output('signal-alert', 'children'),
     Output('signal-history', 'data', allow_duplicate=True),
     Output('stat-ltp', 'children'),
     Output('stat-candles', 'children'),
     Output('stat-tick-time', 'children')],
    [Input('update-interval', 'n_intervals'),
     Input('active-instrument-store', 'data')],
    [State('terminal-mode', 'value'),
     State('signal-history', 'data')],
    prevent_initial_call=True
)
def update_chart(n, active_instrument, mode, history):
    print(f"DEBUG: update_chart called. n={n}, instrument={active_instrument.get('key') if isinstance(active_instrument, dict) else None}", flush=True)

    if not active_instrument or not isinstance(active_instrument, dict):
        return go.Figure().update_layout(template="plotly_dark"), "STATUS: INITIALIZING", [], "", history, "0.00", "0", "--:--:--"

    instrument_label = active_instrument.get('label', 'Unknown')
    instrument_key = active_instrument.get('key')

    if not instrument_key:
        return go.Figure().update_layout(title="Please select an instrument and click Connect.", template="plotly_dark"), "STATUS: READY", [html.Div(e) for e in reversed(history)], "", history, "0.00", "0", "--:--:--"

    # 1. Prepare Data
    all_opt_candles = get_all_opt_candles(instrument_key)

    if not all_opt_candles:
        msg = f"Waiting for ticks for {instrument_label}..."
        return go.Figure().update_layout(title=msg, template="plotly_dark"), msg, [html.Div(e) for e in reversed(history)], "", history, "0.00", "0", "--:--:--"

    df_opt = pd.DataFrame([{
        'time': c.start_time, 'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close, 'delta': c.delta
    } for c in all_opt_candles]).drop_duplicates(subset='time', keep='last')

    # Utilize pre-calculated analysis from storage, appending current incomplete candle analysis
    from data_manager import analysis_storage, engines
    inst_analysis = list(analysis_storage.get(instrument_key, []))
    inst_engine = engines.get(instrument_key, engine)

    if not df_opt.empty:
        last_c = all_opt_candles[-1]
        prev_cum_delta = inst_analysis[-1]['cum_delta'] if inst_analysis else 0
        current_c_analysis = inst_engine.analyze_candle(last_c, prev_cum_delta)
        inst_analysis.append(current_c_analysis)

    analysis_df = pd.DataFrame(inst_analysis).drop_duplicates(subset='time', keep='last')

    # Merge data to ensure perfect alignment and avoid index errors
    df_merged = pd.merge(df_opt, analysis_df, on='time', how='inner', suffixes=('', '_an'))

    df_sync = get_synced_df(instrument_key)
    if not df_sync.empty:
        df_sync = rs_strategy.detect_signals(df_sync)

    # 2. Figure Setup
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        row_heights=[0.7, 0.3],
                        specs=[[{"secondary_y": True}], [{"secondary_y": False}]])

    # 3. Main Plot
    fig.add_trace(go.Candlestick(x=df_merged['time'], open=df_merged['open'], high=df_merged['high'], low=df_merged['low'], close=df_merged['close'], name=instrument_label), row=1, col=1, secondary_y=False)

    # Current Price Line (Confirmation of real-time update)
    last_price = df_merged['close'].iloc[-1]
    fig.add_shape(type="line", x0=df_merged['time'].iloc[0], y0=last_price, x1=df_merged['time'].iloc[-1] + pd.Timedelta(minutes=2), y1=last_price,
                  line=dict(color="white", width=1, dash="dot"), row=1, col=1)
    fig.add_annotation(x=df_merged['time'].iloc[-1] + pd.Timedelta(minutes=1), y=last_price, text=f"LTP: {last_price}", showarrow=False, bgcolor="rgba(0,0,0,0.5)", font=dict(color="white"), row=1, col=1)

    if mode == 'RS' and not df_sync.empty:
        # Overlay Index on secondary Y-axis
        fig.add_trace(go.Scatter(x=df_sync.index, y=df_sync['idx_close'], name='NIFTY Index', line=dict(color='orange', width=1, dash='dot')), row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="Index Price", secondary_y=True, row=1, col=1)

    # 4. Technical Levels
    indicator = AutoTrendSupportResistance(required_ticks_for_broken=4, tick_size=1)
    for i in range(1, len(df_merged)):
        indicator.update(i, df_merged['open'].iloc[i-1], df_merged['high'].iloc[i-1], df_merged['low'].iloc[i-1], df_merged['close'].iloc[i-1])

    for pivot in indicator.pivots:
        if not pivot.display_level: continue
        color = "gold" if pivot.is_level_tested else "cyan"
        fig.add_shape(type="line", x0=df_merged['time'].iloc[pivot.bar_number], y0=pivot.price, x1=df_merged['time'].iloc[-1], y1=pivot.price,
                      line=dict(color=color, width=1, dash="dash"), row=1, col=1)

    # 5. Signal Detection & Display
    signal_alert_div = None

    for i, row in df_merged.iterrows():
        if row['signal'] and pd.notna(row['signal']):
            color = 'lime' if row['signal'] == 'BUY' else 'red'
            fig.add_trace(go.Scatter(x=[row['time']], y=[row['low'] if row['signal'] == 'BUY' else row['high']],
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

    # 6. Footprint & Delta (Limit to last 5 candles for maximum performance)
    start_idx = max(0, len(df_merged) - 5)
    for i in range(start_idx, len(df_merged)):
        row = df_merged.iloc[i]
        delta_val = row['delta']
        if pd.isna(delta_val): continue
        color = "lime" if delta_val > 0 else "red"
        fig.add_annotation(x=row['time'], y=row['low'], text=str(int(delta_val)), showarrow=False, yshift=-15, font=dict(color=color, size=10), row=1, col=1)

    if not df_merged.empty:
        fig.add_trace(go.Scatter(x=df_merged['time'], y=df_merged['cum_delta'], fill='tozeroy', name='Cumulative Delta', line=dict(color='cyan', width=2)), row=2, col=1)

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    fig.update_layout(title=f"LIVE: {instrument_label} | UI Last Update: {now_str}", template="plotly_dark",
                      margin=dict(l=10, r=10, t=50, b=10), xaxis_rangeslider_visible=False, showlegend=False)

    # Auto-scale Y-axis and set X-axis range to last 30 mins for better visibility if data is dense
    if not df_opt.empty:
        last_time = df_opt['time'].iloc[-1]
        start_view = last_time - pd.Timedelta(minutes=30)
        # Add a 2-minute buffer on the right so the live candle isn't cut off
        fig.update_xaxes(range=[start_view, last_time + pd.Timedelta(minutes=2)])

    from data_manager import last_wss_tick_time
    import time
    time_since_tick = time.time() - last_wss_tick_time
    last_tick_str = datetime.datetime.fromtimestamp(last_wss_tick_time).strftime("%H:%M:%S") if last_wss_tick_time > 0 else "--:--:--"

    alert_text = "STATUS: MONITORING"
    if time_since_tick > 10:
        alert_text = f"⚠️ NO DATA ({int(time_since_tick)}s)"
    elif not analysis_df.empty:
        if analysis_df.iloc[-1]['absorption_zones']: alert_text = "⚠️ ABSORPTION ZONE"
        if analysis_df.iloc[-1]['exhaustion']: alert_text += " | 💨 EXHAUSTION"

    current_ltp = f"{df_opt['close'].iloc[-1]:.2f}"
    candles_count = str(len(df_opt))

    return fig, alert_text, [html.Div(e) for e in reversed(history)], signal_alert_div, history, current_ltp, candles_count, last_tick_str

if __name__ == '__main__':
    # Initialize with no active instrument as requested (no simulation by default)
    # Enable threaded mode to handle multiple concurrent callbacks from different tabs
    app.run(debug=False, port=8050, threaded=True)
