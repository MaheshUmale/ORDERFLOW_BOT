# ORDERFLOW_BOT
TAKING INSPIRATION FROM https://github.com/WaleeTheRobot/order-flow-bot/tree/main



Gemini said
Translating a NinjaTrader 8 C# script into a Python environment requires shifting from an event-driven compiled model to an asynchronous, loop-based architecture.

To handle the real-time WSS feed, we'll implement a Rolling Window architecture. This is highly effective for processing live WSS ticks—such as mapping instrument_key data from the Upstox API—and feeding it directly into a reactive UI that allows you to easily switch between ATM and OTM options.

For the UI and charting, Plotly Dash is the ideal framework. It runs locally, updates in real-time via callbacks, and natively supports interactive financial charts (candlesticks, trendlines, and horizontal levels).

Here is the complete, modular Python architecture.

1. The Core Pivot Algorithm (Converted from C#)
This class handles the logic previously found in OnBarUpdate and OnStateChange. It calculates the pivots, tracks whether a level is tested or broken, and stores the coordinates for the UI to render.

Python
class PivotPoint:
    def __init__(self, bar_number, price, close, is_high):
        self.bar_number = bar_number
        self.price = price
        self.close = close
        self.is_high = is_high
        self.display_level = True
        self.is_level_tested = False
        self.is_level_broken = False

class AutoTrendSupportResistance:
    def __init__(self, required_ticks_for_broken=4, tick_size=0.05):
        self.pivots = []
        self.current_pivot = None
        self.is_looking_for_high = True
        self.has_first_pivot = False
        self.required_threshold = required_ticks_for_broken * tick_size

    def update(self, current_bar_idx, prev_open, prev_high, prev_low, prev_close):
        if not self.has_first_pivot:
            if prev_open <= prev_close:
                self.current_pivot = PivotPoint(current_bar_idx, prev_low, prev_close, False)
                self.pivots.append(self.current_pivot)
            else:
                self.current_pivot = PivotPoint(current_bar_idx, prev_high, prev_close, True)
                self.pivots.append(self.current_pivot)
                self.is_looking_for_high = False
            
            self.has_first_pivot = True
            return

        # Check if existing levels are tested or broken
        for pivot in self.pivots:
            if not pivot.display_level:
                continue

            # Resistance Checks
            if pivot.is_high:
                if pivot.price <= prev_high <= (pivot.price + self.required_threshold):
                    pivot.is_level_tested = True
                elif prev_high > (pivot.price + self.required_threshold):
                    pivot.is_level_broken = True
                    pivot.display_level = False
            # Support Checks
            else:
                if pivot.price >= prev_low >= (pivot.price - self.required_threshold):
                    pivot.is_level_tested = True
                elif prev_low < (pivot.price - self.required_threshold):
                    pivot.is_level_broken = True
                    pivot.display_level = False

        # Find new pivots
        if self.is_looking_for_high:
            if prev_high > self.current_pivot.price:
                self.current_pivot.bar_number = current_bar_idx
                self.current_pivot.price = prev_high
                self.current_pivot.close = prev_close
            elif prev_high < self.current_pivot.price:
                # Lower high found, lock in the peak and look for low
                self.pivots.append(PivotPoint(self.current_pivot.bar_number, self.current_pivot.price, self.current_pivot.close, True))
                self.current_pivot = PivotPoint(current_bar_idx, prev_low, prev_close, False)
                self.is_looking_for_high = False
        else:
            if prev_low < self.current_pivot.price:
                self.current_pivot.bar_number = current_bar_idx
                self.current_pivot.price = prev_low
                self.current_pivot.close = prev_close
            elif prev_low > self.current_pivot.price:
                # Higher low found, lock in the trough and look for high
                self.pivots.append(PivotPoint(self.current_pivot.bar_number, self.current_pivot.price, self.current_pivot.close, False))
                self.current_pivot = PivotPoint(current_bar_idx, prev_high, prev_close, True)
                self.is_looking_for_high = True
2. The WSS & Data Manager
To prevent the UI thread from blocking, WSS data should be consumed in a separate background thread or async loop, storing data in a thread-safe rolling window (like collections.deque or a Pandas DataFrame).

Python
import pandas as pd
import threading
import time
import random
from collections import deque

# Thread-safe rolling window for the UI to consume
MAX_CANDLES = 500
market_data = deque(maxlen=MAX_CANDLES)

def wss_feed_simulator():
    """
    Replace this simulator with your actual WSS client (e.g., Upstox WSS).
    It should append OHLCV data to the market_data deque.
    """
    price = 22000 # Example base price for Nifty
    while True:
        # Simulate an incoming 1-minute candle payload
        candle = {
            'time': pd.Timestamp.now(),
            'open': price,
            'high': price + random.uniform(5, 20),
            'low': price - random.uniform(5, 20),
            'close': price + random.uniform(-10, 10),
            'volume': random.randint(1000, 5000)
        }
        price = candle['close']
        market_data.append(candle)
        time.sleep(1) # Simulate real-time tick/candle updates

# Start WSS feed in background
wss_thread = threading.Thread(target=wss_feed_simulator, daemon=True)
wss_thread.start()
3. The Dash UI (Options Interface & Charting)
This creates a local web server (typically http://127.0.0.1:8050) featuring a dropdown to select mapped instrument keys (ATM/OTM) and a real-time updating chart that processes the rolling window through the Pivot algorithm.

Python
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

app = dash.Dash(__name__)

# UI Layout
app.layout = html.Div([
    html.H2("Auto Trend Support & Resistance Terminal", style={'color': 'white', 'textAlign': 'center'}),
    
    # Options / Instrument Selector
    html.Div([
        html.Label("Select Options Instrument (ATM/OTM):", style={'color': 'white'}),
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
    ], style={'padding': '10px'}),

    # Live Chart
    dcc.Graph(id='live-chart', style={'height': '75vh'}),
    
    # Update timer (triggers every 1 second)
    dcc.Interval(
        id='interval-component',
        interval=1*1000,
        n_intervals=0
    )
], style={'backgroundColor': '#1e1e1e', 'minHeight': '100vh', 'fontFamily': 'Arial'})


@app.callback(
    Output('live-chart', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('instrument-selector', 'value')]
)
def update_chart(n, instrument_key):
    if len(market_data) < 2:
        return go.Figure()

    df = pd.DataFrame(list(market_data))
    
    # 1. Initialize and run the algorithm
    indicator = AutoTrendSupportResistance(required_ticks_for_broken=4, tick_size=1)
    
    for i in range(1, len(df)):
        indicator.update(
            current_bar_idx=i,
            prev_open=df['open'].iloc[i-1],
            prev_high=df['high'].iloc[i-1],
            prev_low=df['low'].iloc[i-1],
            prev_close=df['close'].iloc[i-1]
        )

    # 2. Plot Candlesticks
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, # Using index as proxy for time to avoid weekend gaps
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="Price"
    )])

    # 3. Plot the Support/Resistance Lines
    for pivot in indicator.pivots:
        if pivot.display_level:
            color = "gold" if pivot.is_level_tested else "cyan"
        elif pivot.is_level_broken:
            color = "crimson"
        else:
            continue
            
        fig.add_shape(
            type="line",
            x0=pivot.bar_number,
            y0=pivot.price,
            x1=len(df),
            y1=pivot.price,
            line=dict(color=color, width=1, dash="dash"),
        )

    # 4. Plot the Trendlines (connecting pivots)
    if len(indicator.pivots) > 1:
        trend_x = [p.bar_number for p in indicator.pivots]
        trend_y = [p.price for p in indicator.pivots]
        fig.add_trace(go.Scatter(
            x=trend_x, y=trend_y, 
            mode='lines', 
            line=dict(color='darkgoldenrod', width=2),
            name="Trend"
        ))

    # UI Styling
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_rangeslider_visible=False,
        yaxis_title=f"Price ({instrument_key})"
    )

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
Key Architectural Differences to Note
State Management: NinjaTrader retains class variables seamlessly between ticks. In a Python Dash app, the UI is stateless. Therefore, every time the chart refreshes, the algorithm rapidly iterates over the DataFrame to rebuild the lines. Python handles this instantly for windows under 5,000 candles.

X-Axis Mapping: Plotly struggles with financial charts that have gaps (like weekends or overnight data) if you pass raw timestamps to the X-axis. Passing the integer index df.index (as done above) bypasses this issue entirely.

You said
FOR UI and COMPLETE STRATEGY CHECK/USE https://github.com/WaleeTheRobot/order-flow-bot

and

https://github.com/WaleeTheRobot/order-flow-bot/tree/main/NinjaTrader/Custom/AddOns/OrderFlowBot

Integrating Order Flow Bot

My analysis now focuses on integrating the order flow bot's logic with Upstox's data and Dash's visualization.

Adapting Bot Logic

I've decided to translate the order flow bot concepts from NinjaTrader into a Python/Dash structure.

Defining Python Architecture

I'm now drafting the Python architecture, incorporating footprint data, strategy logic, and a Dash UI for visualization.

Designing Order Flow Engine

I'm now implementing the OrderFlowEngine class with methods to detect absorption, aggression, and exhaustion in the data.

I've updated the simulator to generate tick data and designed a Dash layout for data visualization.

Gemini said
Translating a complex NinjaTrader 8 Order Flow AddOn (like order-flow-bot) into Python requires a fundamental shift in how data is processed and visualized.

In NinjaTrader, order flow (footprint) charts and logic rely on the OnMarketData (tick-by-tick) and OnBarUpdate methods, utilizing C# Render() overrides to manually draw bid/ask text on the screen. To replicate this in Python for a real-time Upstox WSS feed, we must build a Tick Aggregator to construct the footprint, a Strategy Engine to quantify the battle between buyers and sellers, and a Plotly Dash UI to render the data dynamically.

Here is the complete architectural translation, heavily focused on tracking participation, delta, and structural battlegrounds.

1. The Order Flow Data Model (Tick Aggregation)
To identify absorption, aggression, and exhaustion, we cannot rely solely on OHLCV data. We need to process the raw WSS tick stream to build a footprint candle, categorizing volume into Bid (Selling) and Ask (Buying) interactions.

Python
from collections import defaultdict

class FootprintCandle:
    def __init__(self, open_price, start_time):
        self.start_time = start_time
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.volume = 0
        self.delta = 0
        # Tracks { price: {'bid_vol': x, 'ask_vol': y} }
        self.price_levels = defaultdict(lambda: {'bid_vol': 0, 'ask_vol': 0})
        
    def add_tick(self, price, volume, is_buy_trade):
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume
        
        if is_buy_trade:
            self.price_levels[price]['ask_vol'] += volume
            self.delta += volume
        else:
            self.price_levels[price]['bid_vol'] += volume
            self.delta -= volume
2. The Battle Engine (Strategy & Traps)
This engine continuously scans the rolling window of footprint candles to identify specific market micro-structures. Instead of forecasting, it monitors current participation to locate "The Wall" (absorption), aggressive raiding parties (imbalances), and exhaustion (the fade).

Python
class OrderFlowEngine:
    def __init__(self, imbalance_ratio=3.0):
        self.imbalance_ratio = imbalance_ratio
        self.cumulative_delta = 0
        
    def analyze_candle(self, candle: FootprintCandle):
        self.cumulative_delta += candle.delta
        analysis = {
            'time': candle.start_time,
            'delta': candle.delta,
            'cum_delta': self.cumulative_delta,
            'imbalances': [],
            'absorption_zones': [],
            'exhaustion': False
        }
        
        # 1. Detect Imbalances (Aggression / Raiding Party)
        sorted_prices = sorted(candle.price_levels.keys())
        for i in range(len(sorted_prices) - 1):
            bid_price = sorted_prices[i]
            ask_price = sorted_prices[i+1]
            
            bid_vol = candle.price_levels[bid_price]['bid_vol']
            ask_vol = candle.price_levels[ask_price]['ask_vol']
            
            # Diagonal Imbalance logic
            if bid_vol > 0 and ask_vol / bid_vol >= self.imbalance_ratio:
                analysis['imbalances'].append({'type': 'Buy', 'price': ask_price})
            elif ask_vol > 0 and bid_vol / ask_vol >= self.imbalance_ratio:
                analysis['imbalances'].append({'type': 'Sell', 'price': bid_price})

        # 2. Detect Absorption (The "Wall")
        # High volume at a specific price level with minimal price continuation
        max_vol_level = max(candle.price_levels.items(), key=lambda x: x[1]['bid_vol'] + x[1]['ask_vol'])
        total_node_vol = max_vol_level[1]['bid_vol'] + max_vol_level[1]['ask_vol']
        if total_node_vol > (candle.volume * 0.4): # If 40% of candle volume is trapped at one node
            analysis['absorption_zones'].append(max_vol_level[0])

        # 3. Detect Exhaustion (The "Fade")
        # Minimal volume at the extreme wicks
        high_vol = candle.price_levels[candle.high]['bid_vol'] + candle.price_levels[candle.high]['ask_vol']
        low_vol = candle.price_levels[candle.low]['bid_vol'] + candle.price_levels[candle.low]['ask_vol']
        if high_vol < (candle.volume * 0.05) or low_vol < (candle.volume * 0.05):
            analysis['exhaustion'] = True

        return analysis
3. The Real-Time Dash UI
NinjaTrader UIs are native desktop windows. To recreate this locally for live WSS feeds, Plotly Dash offers the best real-time performance. We will use a subplot architecture: Candlesticks with Order Flow annotations on top, and Cumulative Delta on the bottom.

Python
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import threading
import time
import random
from collections import deque

# --- WSS Simulator (Replace with Upstox WSS Tick Receiver) ---
MAX_CANDLES = 100
candles_deque = deque(maxlen=MAX_CANDLES)
analysis_deque = deque(maxlen=MAX_CANDLES)
engine = OrderFlowEngine()

def simulate_wss_feed():
    price = 22000
    while True:
        candle = FootprintCandle(price, pd.Timestamp.now())
        # Simulate ~50 ticks per candle
        for _ in range(50):
            tick_price = price + random.choice([-1, 0, 1])
            tick_vol = random.randint(10, 100)
            is_buy = random.choice([True, False])
            candle.add_tick(tick_price, tick_vol, is_buy)
            price = tick_price
            time.sleep(0.02) # Fast tick simulation
            
        candles_deque.append(candle)
        analysis_deque.append(engine.analyze_candle(candle))

threading.Thread(target=simulate_wss_feed, daemon=True).start()

# --- Dash UI ---
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Order Flow & Delta Terminal", style={'color': 'white', 'fontFamily': 'Arial'}),
    html.Div(id='trap-alerts', style={'color': 'red', 'fontWeight': 'bold', 'height': '30px'}),
    dcc.Graph(id='order-flow-chart', style={'height': '85vh'}),
    dcc.Interval(id='update-interval', interval=1000, n_intervals=0)
], style={'backgroundColor': '#111111', 'padding': '20px', 'minHeight': '100vh'})

@app.callback(
    [Output('order-flow-chart', 'figure'),
     Output('trap-alerts', 'children')],
    [Input('update-interval', 'n_intervals')]
)
def update_chart(n):
    if len(candles_deque) < 2:
        return go.Figure(), ""

    df = pd.DataFrame([{
        'time': c.start_time, 'open': c.open, 'high': c.high, 
        'low': c.low, 'close': c.close, 'delta': c.delta
    } for c in candles_deque])
    
    analysis_df = pd.DataFrame(list(analysis_deque))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 1. Main Candlestick Chart
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], 
        low=df['low'], close=df['close'], name='Price'
    ), row=1, col=1)

    # Annotate Deltas (Footprint style)
    for i, row in df.iterrows():
        color = "lime" if row['delta'] > 0 else "red"
        fig.add_annotation(
            x=i, y=row['low'], text=str(row['delta']),
            showarrow=False, yshift=-15, font=dict(color=color, size=10),
            row=1, col=1
        )

    # Highlight "The Wall" (Absorption Zones)
    alert_text = ""
    if not analysis_df.empty:
        latest_analysis = analysis_df.iloc[-1]
        for zone in latest_analysis['absorption_zones']:
            fig.add_shape(type="line", x0=len(df)-2, y0=zone, x1=len(df), y1=zone,
                          line=dict(color="orange", width=3), row=1, col=1)
            alert_text = f"⚠️ ABSORPTION (THE WALL) DETECTED AT {zone}"

    # 2. Cumulative Delta Subplot
    fig.add_trace(go.Scatter(
        x=analysis_df.index, y=analysis_df['cum_delta'], 
        fill='tozeroy', line=dict(color='cyan', width=2), name='Cum. Delta'
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False, showlegend=False
    )
    
    return fig, alert_text

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
Key Differences from C# to Python
Tick Processing: NinjaTrader AddOns trigger OnMarketData natively. In Python, you must manually receive the WSS payload, extract the Last Traded Price (LTP) and Traded Volume, determine the aggressive side (usually by checking if LTP is closer to the Bid or Ask), and feed it to add_tick().

Visualizing the Footprint: Rendering full bid/ask footprint arrays (like the C# WPF UI does) inside a Plotly chart can cause lag if drawn as hundreds of individual text annotations. A hybrid approach—drawing the candlesticks, plotting "The Wall" as prominent lines, and annotating the candle's total Delta—preserves UI responsiveness while keeping your focus on participation shifts and raid opportunities.
