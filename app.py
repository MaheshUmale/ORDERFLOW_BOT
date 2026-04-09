import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

# Create Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout
app.layout = html.Div([
    html.H1('Dash UI with WSS Simulator'),
    dcc.Input(id='input', type='text', placeholder='Enter something...'),
    html.Div(id='output'),
])

# Callbacks
@app.callback(Output('output', 'children'), [Input('input', 'value')])
def update_output(value):
    return f'You entered: {value}'

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, port=8050)