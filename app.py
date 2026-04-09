import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

# Initialize the Dash app
app = dash.Dash(__name__)

# Sample data for order flow analysis
order_data = {
    'time': ['2026-04-08 09:00:00', '2026-04-08 09:01:00', '2026-04-08 09:02:00'],
    'orders': [120, 150, 110],
    'price': [100, 101, 102]
}

# Layout of the Dash app
app.layout = html.Div(children=[
    html.H1(children='Order Flow Analysis'),
    dcc.Graph(id='order-flow-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1*1000,  # in milliseconds
        n_intervals=0
    )
])

# Callback to update the graph based on order data
@app.callback(
    Output('order-flow-graph', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_graph(n):
    figure = {
        'data': [
            go.Scatter(
                x=order_data['time'],
                y=order_data['orders'],
                mode='lines+markers',
                name='Orders'
            ),
            go.Scatter(
                x=order_data['time'],
                y=order_data['price'],
                mode='lines+markers',
                name='Price'
            )
        ],
        'layout': go.Layout(
            title='Real-Time Order Flow Visualization',
            xaxis={'title': 'Time'},
            yaxis={'title': 'Orders and Price'},
            hovermode='closest'
        )
    }
    return figure

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)