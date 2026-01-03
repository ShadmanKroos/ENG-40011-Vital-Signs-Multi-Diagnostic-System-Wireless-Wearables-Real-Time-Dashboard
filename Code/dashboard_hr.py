import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import asyncio
import websockets
import json
import threading
import plotly.graph_objs as go
from datetime import datetime

# Initialize Dash app
app = dash.Dash(__name__)

# Global dictionary to store incoming data and history for each patient
patient_data = {
    "Patient 1": {"timestamps": [], "heart_rate": [], "systolic_pressure": [], "diastolic_pressure": [], "temperature": []},
    "Patient 2": {"timestamps": [], "heart_rate": [], "systolic_pressure": [], "diastolic_pressure": [], "temperature": []},
    "Patient 3": {"timestamps": [], "heart_rate": [], "systolic_pressure": [], "diastolic_pressure": [], "temperature": []}
}

# WebSocket listener to simulate data reception
async def listen_to_data():
    global patient_data
    uri = "ws://172.20.10.4:6789"  # WebSocket URI
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                patient_name = data['patient']

                # Append the received data to the patient's history
                patient_data[patient_name]['timestamps'].append(datetime.now().strftime('%H:%M:%S'))
                patient_data[patient_name]['heart_rate'].append(data['heart_rate'])
                patient_data[patient_name]['systolic_pressure'].append(data['systolic_pressure'])
                patient_data[patient_name]['diastolic_pressure'].append(data['diastolic_pressure'])
                patient_data[patient_name]['temperature'].append(data['temperature'])

                # Limit the data points to the last 10
                for key in ['timestamps', 'heart_rate', 'systolic_pressure', 'diastolic_pressure', 'temperature']:
                    if len(patient_data[patient_name][key]) > 10:
                        patient_data[patient_name][key].pop(0)

            except Exception as e:
                print("Error receiving data:", e)

# Start WebSocket listener in a background thread
def run_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen_to_data())

thread = threading.Thread(target=run_listener)
thread.start()

# Helper function to compute line angle based on value and specific thresholds
def compute_angle(value, low, high):
    if value < low:
        return -45  # Tilt left for low
    elif value > high:
        return 45  # Tilt right for high
    else:
        return 0  # Horizontal for normal values

# Function to dynamically assign color based on value range (low, medium, high)
def get_value_color(value, low, high):
    if value < low:
        return 'blue'  # Low value
    elif value > high:
        return 'red'   # High value
    else:
        return 'green'  # Normal value

# Create an SVG triangle with a much thicker rotating line and ensure proper alignment
def get_triangle_with_rotating_line(angle, color):
    return html.Div([
        html.Div(
            style={
                'width': '0',
                'height': '0',
                'border-left': '35px solid transparent',  # Increased triangle size for better visual impact
                'border-right': '35px solid transparent',
                'border-bottom': f'60px solid {color}',  # Height of the triangle
                'margin': '0 auto',
            }
        ),
        html.Div(
            style={
                'width': '120px',  # Increased line length
                'height': '6px',  # Increased line thickness
                'background-color': color,
                'transform': f'rotate({angle}deg)',
                'transform-origin': 'center bottom',
                'margin': '0 auto',
                'position': 'relative',
                'bottom': '60px',  # Keep the line positioned right above the triangle
            }
        )
    ], style={'position': 'relative', 'height': '80px', 'textAlign': 'center'})

# Updated layout with patient dropdown, title adjustment, and centered readings
app.layout = html.Div(style={'backgroundColor': '#f9f9f9', 'padding': '20px'}, children=[

    # Patient dropdown moved to the top left corner
    html.Div(
        dcc.Dropdown(id='patient-dropdown', options=[
            {'label': 'Patient 1', 'value': 'Patient 1'},
            {'label': 'Patient 2', 'value': 'Patient 2'},
            {'label': 'Patient 3', 'value': 'Patient 3'},
        ], value='Patient 1'),
        style={'position': 'absolute', 'top': '20px', 'left': '20px', 'width': '20%'}
    ),

    # Title moved upwards with reduced padding for better positioning
    html.H1('Real-Time Patient Monitoring',
            style={'textAlign': 'center', 'fontFamily': 'Arial, sans-serif', 'color': '#333',
                   'paddingTop': '10px', 'marginBottom': '40px'}),

    # Alert indicators (beams) and graphs laid out in a row
    html.Div([

        html.Div([  # Heart Rate section
            html.Div(id='heart-rate-indicator'),
            html.Div(dcc.Graph(id='heart-rate-graph'), style={'width': '100%'}),
            html.Div(id='heart-rate-reading', style={'textAlign': 'center', 'fontSize': '18px', 'paddingTop': '10px'})
        ], style={'display': 'inline-block', 'width': '32%', 'verticalAlign': 'top', 'textAlign': 'center'}),

        html.Div([  # Blood Pressure section updated with two graphs (systolic and diastolic)
            html.Div(id='blood-pressure-indicator'),
            html.Div(dcc.Graph(id='systolic-pressure-graph'), style={'width': '100%'}),
            html.Div(dcc.Graph(id='diastolic-pressure-graph'), style={'width': '100%'}),
            html.Div(id='blood-pressure-reading', style={'textAlign': 'center', 'fontSize': '18px', 'paddingTop': '10px'})
        ], style={'display': 'inline-block', 'width': '32%', 'verticalAlign': 'top', 'textAlign': 'center'}),

        html.Div([  # Temperature section
            html.Div(id='temperature-indicator'),
            html.Div(dcc.Graph(id='temperature-graph'), style={'width': '100%'}),
            html.Div(id='temperature-reading', style={'textAlign': 'center', 'fontSize': '18px', 'paddingTop': '10px'})
        ], style={'display': 'inline-block', 'width': '32%', 'verticalAlign': 'top', 'textAlign': 'center'}),
    ], style={'display': 'flex', 'justifyContent': 'space-between'}),

    # Interval component to update the graphs periodically
    dcc.Interval(id='graph-update', interval=2000, n_intervals=0)
])

# Callback to update graphs and dynamic indicators
@app.callback(
    [Output('heart-rate-graph', 'figure'),
     Output('systolic-pressure-graph', 'figure'),
     Output('diastolic-pressure-graph', 'figure'),
     Output('temperature-graph', 'figure'),
     Output('heart-rate-reading', 'children'),
     Output('blood-pressure-reading', 'children'),
     Output('temperature-reading', 'children'),
     Output('heart-rate-indicator', 'children'),
     Output('blood-pressure-indicator', 'children'),
     Output('temperature-indicator', 'children')],
    [Input('graph-update', 'n_intervals'), Input('patient-dropdown', 'value')]
)
def update_graph(n, selected_patient):
    global patient_data

    # Check if we have data for the selected patient
    if selected_patient not in patient_data or not patient_data[selected_patient]['timestamps']:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, "No data available", dash.no_update, dash.no_update, dash.no_update

    # Get the patient's data
    timestamps = patient_data[selected_patient]['timestamps']
    heart_rate = patient_data[selected_patient]['heart_rate']
    systolic_pressure = patient_data[selected_patient]['systolic_pressure']
    diastolic_pressure = patient_data[selected_patient]['diastolic_pressure']
    temperature = patient_data[selected_patient]['temperature']

    # Update Heart Rate indicator (60-100 BPM)
    heart_rate_angle = compute_angle(heart_rate[-1], 60, 100)
    heart_rate_color = get_value_color(heart_rate[-1], 60, 100)
    heart_rate_indicator = get_triangle_with_rotating_line(heart_rate_angle, heart_rate_color)

    # Update Blood Pressure indicator using systolic pressure (110-130 systolic pressure)
    bp_angle = compute_angle(systolic_pressure[-1], 110, 130)
    bp_color = get_value_color(systolic_pressure[-1], 110, 130)
    bp_indicator = get_triangle_with_rotating_line(bp_angle, bp_color)

    # Update Temperature indicator (36.1°C - 37.2°C)
    temp_angle = compute_angle(temperature[-1], 36.1, 37.2)
    temp_color = get_value_color(temperature[-1], 36.1, 37.2)
    temp_indicator = get_triangle_with_rotating_line(temp_angle, temp_color)

    # Graph for heart rate
    heart_rate_trace = go.Scatter(
        x=timestamps, y=heart_rate, mode='lines+markers', name='Heart Rate',
        line=dict(color='blue')
    )
    heart_rate_fig = {
        'data': [heart_rate_trace],
        'layout': go.Layout(title='Heart Rate Over Time', xaxis={'title': 'Time'}, yaxis={'title': 'BPM'})
    }

    # Graph for systolic pressure
    systolic_trace = go.Scatter(
        x=timestamps, y=systolic_pressure, mode='lines+markers', name='Systolic Pressure',
        line=dict(color='red')
    )
    systolic_fig = {
        'data': [systolic_trace],
        'layout': go.Layout(title='Systolic Pressure Over Time', xaxis={'title': 'Time'}, yaxis={'title': 'mmHg'})
    }

    # Graph for diastolic pressure
    diastolic_trace = go.Scatter(
        x=timestamps, y=diastolic_pressure, mode='lines+markers', name='Diastolic Pressure',
        line=dict(color='purple')
    )
    diastolic_fig = {
        'data': [diastolic_trace],
        'layout': go.Layout(title='Diastolic Pressure Over Time', xaxis={'title': 'Time'}, yaxis={'title': 'mmHg'})
    }

    # Graph for temperature
    temp_trace = go.Scatter(
        x=timestamps, y=temperature, mode='lines+markers', name='Temperature',
        line=dict(color='orange')
    )
    temp_fig = {
        'data': [temp_trace],
        'layout': go.Layout(title='Temperature Over Time', xaxis={'title': 'Time'}, yaxis={'title': '°C'})
    }

    # Display actual values
    heart_rate_reading = f"{heart_rate[-1]} BPM"
    bp_reading = f"{systolic_pressure[-1]}/{diastolic_pressure[-1]} mmHg"
    temperature_reading = f"{temperature[-1]}°C"

    return heart_rate_fig, systolic_fig, diastolic_fig, temp_fig, heart_rate_reading, bp_reading, temperature_reading, heart_rate_indicator, bp_indicator, temp_indicator


if __name__ == '__main__':
    app.run_server(debug=True)
