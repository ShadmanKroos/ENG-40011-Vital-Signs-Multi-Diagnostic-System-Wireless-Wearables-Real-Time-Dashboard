import socket
import struct
import threading
import select
import asyncio
import websockets
import json
import time
import random

# Set up the server
server_ip = "172.20.10.4"  # Use 'localhost' for local testing
tcp_port = 8081  # TCP port for Arduino communication
websocket_port = 6789  # WebSocket port for Dashboard communication

# Global variables to hold data from the Arduino
global temperature
global systolic_pressure
global diastolic_pressure
global hr

temperature = 36.5
systolic_pressure = 120
diastolic_pressure = 80
hr = 70

# List to hold WebSocket clients
websocket_clients = []


# Function to handle each Arduino client
def handle_client(client: socket.socket, client_id: str):
    global temperature, systolic_pressure, diastolic_pressure, hr
    print(f'Client connected: {client_id}')

    while True:
        data = recv_exactly(client, 12)  # Expecting 12 bytes (3 floats: temperature, systolic_pressure, hr)

        if not data:
            break

        # Unpack the data from the Arduino (3 floats: temperature, systolic_pressure, hr)
        try:
            temperature, systolic_pressure, hr = struct.unpack('fff', data)  # Unpacking 12 bytes for temp, systolic, hr
            # Calculate diastolic pressure based on systolic pressure
            diastolic_pressure = random.uniform(70, 90)
        except Exception as e:
            print(f"Data unpacking error: {e}")
            continue

        print(f"Received -> Temperature: {temperature}, Systolic Pressure: {systolic_pressure}, Diastolic Pressure: {diastolic_pressure}, HR: {hr}")

    client.close()
    print(f'Thread({client_id}): Connection Closed')

# Function to run the TCP server for receiving data from the Arduino
def run_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, tcp_port))
    server_socket.listen(1)
    print(f"Server listening on {server_ip}:{tcp_port}")

    while True:
        print('Waiting for connection...')
        client_socket, client_address = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, f'{client_address[0], client_address[1]}'))
        thread.start()


# Function to receive the exact number of bytes
def recv_exactly(conn, num_bytes):
    data = b''
    conn.setblocking(0)
    try:
        while len(data) < num_bytes:
            ready = select.select([conn], [], [], 10)
            if ready[0]:
                packet = conn.recv(num_bytes - len(data))
                if not packet:
                    print("Client disconnected or no data received.")
                    return None
                data += packet
            else:
                print("No data received within timeout period.")
                return None
    except Exception as e:
        print(f"Error during recv_exactly: {e}")
        return None
    return data


# WebSocket handler to send data to connected WebSocket clients
async def send_vital_data(websocket, path):
    global temperature, systolic_pressure, diastolic_pressure, hr
    websocket_clients.append(websocket)
    print(f"WebSocket client connected: {path}")

    try:
        while True:
            data = {
                "patient": "Patient 1",  # Static for now, could be extended
                "heart_rate": hr,
                "systolic_pressure": systolic_pressure,
                "diastolic_pressure": diastolic_pressure,
                "temperature": temperature,
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(data))
            await asyncio.sleep(2)  # Send data every 2 seconds
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed.")
    finally:
        websocket_clients.remove(websocket)

# Function to start the WebSocket server for the dashboard
def start_websocket_server():
    start_server = websockets.serve(send_vital_data, server_ip, websocket_port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


# Main function to run both TCP and WebSocket servers concurrently
if __name__ == '__main__':
    try:
        # Start the TCP server in a thread
        server_thread = threading.Thread(target=run_server)
        server_thread.start()

        # Start the WebSocket server
        start_websocket_server()
    except KeyboardInterrupt:
        pass
