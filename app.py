import asyncio
import obd
import websockets
import json

# WebSocket server details
WS_SERVER_URI = "wss://ws.sonny.ro"  # Replace with your WebSocket server URL

# Connect to OBD-II over Bluetooth
def connect_obd():
    connection = None
    try:
        # Use `obd.OBD()` for automatic port detection
        # or specify Bluetooth port directly, e.g., "/dev/rfcomm0" or COM port in Windows
        connection = obd.OBD('/dev/rfcomm0')  
        if connection.is_connected():
            print("Connected to OBD-II device!")
        else:
            print("Failed to connect to OBD-II device.")
    except Exception as e:
        print(f"Error connecting to OBD-II: {e}")
    return connection

# Read OBD-II data
async def read_obd_data(connection, websocket):
    while True:
        if not connection.is_connected():
            print("Lost connection to OBD-II device.")
            break
        
        # Example commands: RPM, Speed, Coolant Temperature
        data = {}
        for cmd in [obd.commands.RPM, obd.commands.SPEED, obd.commands.COOLANT_TEMP,
        obd.commands.THROTTLE_POS, obd.commands.ENGINE_LOAD, obd.commands.MAF,
        obd.commands.INTAKE_TEMP, obd.commands.ELM_VOLTAGE, obd.commands.GET_CURRENT_DTC]:
            response = connection.query(cmd)
            if not response.is_null():
                if cmd == obd.commands.GET_CURRENT_DTC:
                    # Save the list of DTCs as-is or as a string
                    data[cmd.name] = response.value  # or str(response.value)
                else:
                    # Try to extract magnitude or fallback to raw value
                    value = response.value
                    data[cmd.name] = getattr(value, 'magnitude', value)
        
        if data:
            # Send data as JSON to WebSocket server
            message = json.dumps(data)
            await websocket.send(message)
            print(f"Sent: {message}")

        await asyncio.sleep(0.5)  # wait 1 second before next reading

# Main async function
async def main():
    connection = connect_obd()
    if connection is None or not connection.is_connected():
        print("Unable to connect to OBD-II device. Exiting...")
        return

    async with websockets.connect(WS_SERVER_URI) as websocket:
        print("Connected to WebSocket server.")
        await read_obd_data(connection, websocket)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting program.")
