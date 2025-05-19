import asyncio
import obd
import websockets
import json

# WebSocket server details
WS_SERVER_URI = "wss://ws.sonny.ro"

# Global variable for WebSocket
websocket = None

async def send_data(message):
    if websocket is not None:
        try:
            await websocket.send(message)
            print(f"Sent: {message}")
        except Exception as e:
            print(f"Error sending data: {e}")

# Main async function
async def main():
    global websocket

    # Capture the main event loop
    loop = asyncio.get_running_loop()

    # Connect to WebSocket
    try:
        websocket = await websockets.connect(WS_SERVER_URI)
        print("Connected to WebSocket server.")
    except Exception as e:
        print(f"Failed to connect to WebSocket: {e}")
        return

    # Connect to OBD-II using Async with 0.25s delay
    print("Connecting to OBD-II...")
    connection = obd.Async('/dev/rfcomm0', delay_cmds=0.25)

    # Wait briefly to allow connection to initialize
    await asyncio.sleep(1)

    if not connection.is_connected():
        print("OBD-II connection failed. Is the device on and paired?")
        return
    else:
        print("Connected to OBD-II device.")

    # Define callback with captured loop
    def create_callback(cmd):
        def callback_func(response):
            if not response.is_null():
                value = response.value
                data = {
                    "command": cmd.name,
                    "value": getattr(value, "magnitude", str(value))
                }
                message = json.dumps(data)
                asyncio.run_coroutine_threadsafe(send_data(message), loop)
        return callback_func

    # List of commands to monitor
    commands = [
        obd.commands.RPM, obd.commands.SPEED, obd.commands.COOLANT_TEMP,
        obd.commands.THROTTLE_POS, obd.commands.ENGINE_LOAD, obd.commands.MAF,
        obd.commands.INTAKE_TEMP, obd.commands.ELM_VOLTAGE, obd.commands.GET_CURRENT_DTC
    ]

    # Register each command with a callback
    for cmd in commands:
        print(f"Watching command: {cmd.name}")
        connection.watch(cmd, callback=create_callback(cmd))

    print("Starting OBD async polling...")
    connection.start()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        connection.stop()
        await websocket.close()
        print("Closed connection.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
