import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data_manager import (get_all_opt_candles, get_synced_df, get_opt_df_with_indicators, get_volume_profile,
                          start_live_feed, change_instrument, rs_strategy, engine, trade_manager)
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
                html.Label("TF:", style={'color': 'white'}),
                dcc.Dropdown(id='timeframe-selector',
                             options=[{'label': '1m', 'value': '1min'},
                                      {'label': '5m', 'value': '5min'},
                                      {'label': '15m', 'value': '15min'}],
                             value='1min', style={'width': '80px', 'color': 'black'})
            ], style={'display': 'inline-block', 'padding': '10px'}),

            html.Div([
                html.Label("Live Trading:", style={'color': 'white'}),
                dcc.Checklist(id='live-trading-toggle',
                              options=[{'label': ' Enabled', 'value': 'LIVE'}],
                              value=[], style={'color': 'white', 'marginTop': '5px'})
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
                    html.Div("PnL", style={'fontSize': '10px', 'color': '#aaa'}),
                    html.Div(id='stat-pnl', children="0.00", style={'fontSize': '18px', 'color': '#00ff00', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block', 'marginRight': '20px', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Win Rate", style={'fontSize': '10px', 'color': '#aaa'}),
                    html.Div(id='stat-winrate', children="0%", style={'fontSize': '18px', 'color': 'white'})
                ], style={'display': 'inline-block', 'marginRight': '20px', 'textAlign': 'center'}),
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
            html.H3("Live Monitor", style={'color': 'white', 'textAlign': 'center'}),
            dcc.Tabs(id='monitor-tabs', value='signals', children=[
                dcc.Tab(label='Signals', value='signals', style={'backgroundColor': '#222', 'color': 'white'}, selected_style={'backgroundColor': '#444', 'color': 'lime'}),
                dcc.Tab(label='Trades', value='trades', style={'backgroundColor': '#222', 'color': 'white'}, selected_style={'backgroundColor': '#444', 'color': 'cyan'}),
            ]),
            html.Div(id='monitor-content', style={'height': '60vh', 'overflowY': 'scroll', 'backgroundColor': '#000', 'padding': '5px', 'fontFamily': 'Courier New', 'fontSize': '12px', 'border':'1px solid #444'})
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
     State('signal-history', 'data'),
     State('live-trading-toggle', 'value')],
    prevent_initial_call=True
)
def handle_connect(n_clicks, instrument_key, options, index, history, live_toggle):
    if n_clicks > 0 and instrument_key:
        label = "Unknown"
        if options:
            for opt in options:
                if opt['value'] == instrument_key:
                    label = opt['label']
                    break

        # Start backend processes
        trade_manager.live_mode = ('LIVE' in live_toggle)
        change_instrument(instrument_key, index)
        start_live_feed()

        status = f"CONNECTED: {label} [{'LIVE' if trade_manager.live_mode else 'VIRTUAL'}]"
        # Reset history on new connection to avoid confusion between instruments
        return [], {'key': instrument_key, 'label': label}, status

    # On initialization or if no key, keep current state
    if not instrument_key and n_clicks == 0:
        return dash.no_update, dash.no_update, dash.no_update
    return history, {'key': None, 'label': 'No Instrument Selected'}, "STATUS: READY"

@app.callback(
    [Output('main-chart', 'figure'),
     Output('trap-alerts', 'children'),
     Output('monitor-content', 'children'),
     Output('signal-alert', 'children'),
     Output('signal-history', 'data', allow_duplicate=True),
     Output('stat-ltp', 'children'),
     Output('stat-candles', 'children'),
     Output('stat-tick-time', 'children'),
     Output('stat-refresh-count', 'children'),
     Output('stat-heartbeat', 'style'),
     Output('stat-pnl', 'children'),
     Output('stat-winrate', 'children')],
    [Input('update-interval', 'n_intervals'),
     Input('active-instrument-store', 'data'),
     Input('timeframe-selector', 'value')],
    [State('terminal-mode', 'value'),
     State('signal-history', 'data'),
     State('monitor-tabs', 'value')],
    prevent_initial_call=True
)
def update_chart(n, active_instrument, timeframe, mode, history, tab):
    # Common stats
    refresh_count = str(n)
    heartbeat_style = {'color': 'red' if n % 2 == 0 else 'lime'}

    print(f"DEBUG: update_chart called. n={n}, active_instrument={active_instrument}", flush=True)

    if not active_instrument or not isinstance(active_instrument, dict):
        return go.Figure().update_layout(template="plotly_dark"), "STATUS: INITIALIZING", [], "", history, "0.00", "0", "--:--:--", refresh_count, heartbeat_style, "0.00", "0%"

    instrument_label = active_instrument.get('label', 'Unknown')
    instrument_key = active_instrument.get('key')

    if not instrument_key:
        monitor_content = [html.Div(e) for e in reversed(history)] if tab == 'signals' else "No Trades"
        return go.Figure().update_layout(title="Please select an instrument and click Connect.", template="plotly_dark"), "STATUS: READY", monitor_content, "", history, "0.00", "0", "--:--:--", refresh_count, heartbeat_style, "0.00", "0%"

    # 1. Prepare Data
    df_opt = get_opt_df_with_indicators(instrument_key, timeframe)
    print(f"DEBUG: update_chart called. n={n}, instrument={instrument_key}, tf={timeframe}, candles={len(df_opt)}", flush=True)

    if df_opt.empty:
        msg = f"Waiting for ticks for {instrument_label}..."
        monitor_content = [html.Div(e) for e in reversed(history)] if tab == 'signals' else "No Trades"
        return go.Figure().update_layout(title=msg, template="plotly_dark"), msg, monitor_content, "", history, "0.00", "0", "--:--:--", refresh_count, heartbeat_style, "0.00", "0%"

    # Utilize pre-calculated analysis from storage, appending current incomplete candle analysis
    from data_manager import analysis_storage, engines
    inst_analysis = list(analysis_storage.get((instrument_key, timeframe), []))
    inst_engine = engines.get(instrument_key, engine)

    all_opt_candles = get_all_opt_candles(instrument_key, timeframe)
    if not df_opt.empty and all_opt_candles:
        last_c = all_opt_candles[-1]
        # Ensure we have some base analysis to start from
        prev_cum_delta = inst_analysis[-1].get('cum_delta', 0) if inst_analysis else 0
        current_c_analysis = inst_engine.analyze_candle(last_c, prev_cum_delta)
        # Deep copy to avoid modifying the analysis_storage
        display_analysis = inst_analysis + [current_c_analysis]
    else:
        display_analysis = inst_analysis

    analysis_df = pd.DataFrame(display_analysis).drop_duplicates(subset='time', keep='last')

    # Merge data to ensure perfect alignment and avoid index errors
    # Indicators df_opt has 'time' from get_opt_df_with_indicators
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

    # VWAP & Bands
    if 'vwap' in df_merged.columns:
        fig.add_trace(go.Scatter(x=df_merged['time'], y=df_merged['vwap'], name='VWAP', line=dict(color='yellow', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_merged['time'], y=df_merged['vwap_upper1'], name='VWAP U1', line=dict(color='rgba(255,255,0,0.3)', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_merged['time'], y=df_merged['vwap_lower1'], name='VWAP L1', line=dict(color='rgba(255,255,0,0.3)', width=1, dash='dash')), row=1, col=1)

    # Volume Profile (Horizontal Bars)
    vp = get_volume_profile(instrument_key, timeframe)
    if vp:
        prices = list(vp.keys())
        vols = list(vp.values())
        max_v = max(vols) if vols else 1
        # Normalize for display on time axis (hacky but works for overlay)
        last_time = df_merged['time'].iloc[-1]
        norm_vols = [(v / max_v) * pd.Timedelta(minutes=5) for v in vols]
        fig.add_trace(go.Bar(y=prices, x=norm_vols, orientation='h', name='VPVR', marker_color='rgba(100,100,100,0.2)', base=last_time - pd.Timedelta(minutes=5)), row=1, col=1)

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
            ev = trade_manager.get_ev(row['confidence'])
            fig.add_trace(go.Scatter(x=[row['time']], y=[row['low'] if row['signal'] == 'BUY' else row['high']],
                                     mode="markers+text", marker=dict(symbol="triangle-up" if row['signal'] == 'BUY' else "triangle-down", size=15, color=color),
                                     text=[f"{row['signal']} (EV:{ev:.1f})"], textposition="bottom center", name="OF SIGNAL"), row=1, col=1)

            sig_msg = f"{row['time'].strftime('%H:%M:%S')} - OF {row['signal']} (EV:{ev:.1f}) detected"
            if sig_msg not in history:
                history.append(sig_msg)
                if i == len(df_merged) - 1:
                    signal_alert_div = html.Div(f"🚀 {row['signal']} SIGNAL (EV: {ev:.1f}) DETECTED!",
                                               style={'backgroundColor': 'green' if row['signal']=='BUY' else 'red', 'color': 'white', 'padding': '15px', 'borderRadius':'5px', 'fontSize':'20px', 'textAlign':'center'})

    if mode == 'RS' and not df_sync.empty:
        rs_sigs = df_sync[df_sync['rs_bullish_signal']]
        for ts, row in rs_sigs.iterrows():
            fig.add_trace(go.Scatter(x=[ts], y=[row['opt_low'] - 2], mode="markers", marker=dict(symbol="star", size=15, color='cyan'), name="RS BUY"), row=1, col=1)
            sig_msg = f"{ts.strftime('%H:%M:%S')} - RS BULLISH Divergence"
            if sig_msg not in history:
                history.append(sig_msg)
                signal_alert_div = html.Div("🌟 RS BULLISH SIGNAL DETECTED!", style={'backgroundColor': 'cyan', 'color': 'black', 'padding': '15px', 'borderRadius':'5px', 'fontSize':'20px', 'textAlign':'center'})

    # 6. Footprint & Delta (Limit to last 10 candles for performance)
    start_idx = max(0, len(df_merged) - 10)
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

    # Auto-scale Y-axis and set X-axis range to last 30 units for better visibility if data is dense
    if not df_opt.empty:
        last_time = df_opt['time'].iloc[-1]
        lookback = 30
        if timeframe == '5min': lookback = 30 * 5
        elif timeframe == '15min': lookback = 30 * 15
        start_view = last_time - pd.Timedelta(minutes=lookback)
        # Add a 2-minute buffer on the right so the live candle isn't cut off
        fig.update_xaxes(range=[start_view, last_time + pd.Timedelta(minutes=2)])

    import data_manager
    import time
    last_tick = data_manager.last_wss_tick_time
    time_since_tick = time.time() - last_tick if last_tick > 0 else 0
    last_tick_str = datetime.datetime.fromtimestamp(last_tick).strftime("%H:%M:%S") if last_tick > 0 else "--:--:--"

    alert_text = "STATUS: MONITORING"
    if last_tick == 0:
        alert_text = "STATUS: WAITING FOR FIRST TICK..."
    elif time_since_tick > 10:
        alert_text = f"⚠️ NO DATA ({int(time_since_tick)}s)"
    elif not analysis_df.empty:
        if analysis_df.iloc[-1]['absorption_zones']: alert_text = "⚠️ ABSORPTION ZONE"
        if analysis_df.iloc[-1]['exhaustion']: alert_text += " | 💨 EXHAUSTION"

    current_ltp = f"{df_opt['close'].iloc[-1]:.2f}"
    candles_count = str(len(df_opt))
    pnl_str = f"{trade_manager.stats['realized_pnl']:.2f}"
    winrate_str = f"{trade_manager.stats['win_rate']:.1f}%"

    if tab == 'signals':
        monitor_content = [html.Div(e) for e in reversed(history)]
    else:
        # Trades tab
        trade_items = []
        for t in reversed(trade_manager.trades):
            color = 'cyan' if t.status == 'OPEN' else ('lime' if t.pnl > 0 else 'red')
            text = f"[{t.status}] {t.side} @ {t.entry_price:.2f}"
            if t.status == 'CLOSED':
                text += f" | Exit: {t.exit_price:.2f} PnL: {t.pnl:.2f}"
            trade_items.append(html.Div(text, style={'color': color, 'marginBottom': '5px', 'borderBottom': '1px solid #333'}))
        monitor_content = trade_items if trade_items else "No Trades"

    return fig, alert_text, monitor_content, signal_alert_div, history, current_ltp, candles_count, last_tick_str, refresh_count, heartbeat_style, pnl_str, winrate_str

if __name__ == '__main__':
    # Initialize with no active instrument as requested (no simulation by default)
    app.run(debug=True, port=8050)
