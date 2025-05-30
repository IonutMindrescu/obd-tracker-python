import time
import random
import threading
import asyncio
import websockets
import json
import obd
import subprocess
import serial
from rpi_ws281x import PixelStrip, Color

# === Application Configuration ===
LED_COUNT = 30
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0
RECONNECT_OBD = 30
WEBSOCKET_URL = "wss://ws.sonny.ro"

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# === Globals ===
current_mode = "chase"
websocket = None
throttle_ratio = 0.0  # Global variable to store the latest throttle position

# === OBD-II Handler ===
async def obd_handler():
    loop = asyncio.get_running_loop()

    while True:  # Keep trying to connect forever
        try:
            print("Connecting to OBD-II...")
            connection = obd.Async('/dev/rfcomm0', delay_cmds=0.25)
            await asyncio.sleep(1)

            if not connection.is_connected():
                print(f"OBD-II connection failed. Retrying in {RECONNECT_OBD} seconds...")
                await asyncio.sleep(RECONNECT_OBD)
                continue

            print("Connected to OBD-II.")

            def create_callback(cmd):
                def callback_func(response):
                    if not response.is_null():
                        value = response.value
                        val = getattr(value, "magnitude", 0.0)
                        if cmd == obd.commands.THROTTLE_POS:
                            global throttle_ratio
                            throttle_ratio = float(val) / 100.0  # Normalize to 0.0 - 1.0 

                        data = {
                            "command": cmd.name,
                            "value": getattr(value, "magnitude", str(value))
                        }
                        message = json.dumps(data)
                        asyncio.run_coroutine_threadsafe(send_data(message), loop)
                return callback_func

            commands = [
                obd.commands.RPM, obd.commands.SPEED, obd.commands.COOLANT_TEMP,
                obd.commands.THROTTLE_POS, obd.commands.ENGINE_LOAD, obd.commands.MAF,
                obd.commands.INTAKE_TEMP, obd.commands.ELM_VOLTAGE, obd.commands.GET_CURRENT_DTC
            ]

            for cmd in commands:
                connection.watch(cmd, callback=create_callback(cmd))

            connection.start()

            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                connection.stop()
                break

        except serial.serialutil.SerialException as e:
            print(f"SerialException: {e}. Retrying in {RECONNECT_OBD} seconds...")
            await asyncio.sleep(RECONNECT_OBD)

        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in {RECONNECT_OBD} seconds...")
            await asyncio.sleep(RECONNECT_OBD)

def bind_rfcomm():
    try:
        # Check if rfcomm0 is already bound
        result = subprocess.run(["rfcomm"], capture_output=True, text=True)
        if "/dev/rfcomm0" in result.stdout:
            print("rfcomm0 already bound.")
            return

        # Bind the device
        subprocess.run(
            ["sudo", "rfcomm", "bind", "/dev/rfcomm0", "DD:0D:30:48:A4:9C"],
            check=True
        )
        print("rfcomm0 bound successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to bind rfcomm: {e}")

# === LED Functions ===
def get_color(speed_ratio):
    if speed_ratio < 0.4:
        r = int(speed_ratio / 0.4 * 255)
        g = 255
    elif speed_ratio < 0.8:
        r = 255
        g = int((0.8 - speed_ratio) / 0.4 * 255)
    else:
        r = 255
        g = 0
    return Color(r, g, 0)

def update_strip_acceleration(ratio):
    speed_leds = int(ratio * strip.numPixels())
    color = get_color(ratio)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color if i < speed_leds else Color(0, 0, 0))
    strip.show()

def realtime_acceleration():
    while current_mode == "acceleration":
        update_strip_acceleration(throttle_ratio)
        time.sleep(0.05)

# def simulate_acceleration():
#     speed_ratio = 1.0
#     direction = 1
#     while current_mode == "acceleration":
#         target_ratio = random.uniform(0.3, 1.0) if direction == 1 else random.uniform(0.0, 0.7)
#         duration = random.uniform(1.5, 2.0)
#         steps = int(duration / 0.05)
#         delta = (target_ratio - speed_ratio) / steps
#         for _ in range(steps):
#             if current_mode != "acceleration":
#                 return
#             speed_ratio = max(0.0, min(1.0, speed_ratio + delta))
#             update_strip_acceleration(speed_ratio)
#             time.sleep(0.05)
#         if random.random() < 0.4:
#             direction *= -1
#         time.sleep(random.uniform(0.2, 0.5))

def police_lights():
    half = strip.numPixels() // 2
    flash_count = 5
    flash_delay = 0.03
    while current_mode == "police":
        for _ in range(flash_count):
            for i in range(half):
                strip.setPixelColor(i, Color(255, 0, 0))
            for i in range(half, strip.numPixels()):
                strip.setPixelColor(i, Color(0, 0, 0))
            strip.show()
            time.sleep(flash_delay)
            clear_strip()
            time.sleep(flash_delay)
        for _ in range(flash_count):
            for i in range(half):
                strip.setPixelColor(i, Color(0, 0, 0))
            for i in range(half, strip.numPixels()):
                strip.setPixelColor(i, Color(0, 0, 255))
            strip.show()
            time.sleep(flash_delay)
            clear_strip()
            time.sleep(flash_delay)

def hazard_lights():
    amber = Color(255, 120, 0)
    flash_delay = 0.3
    while current_mode == "hazard":
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, amber)
        strip.show()
        time.sleep(flash_delay)
        clear_strip()
        time.sleep(flash_delay)

def pit_crew_mode():
    color1 = Color(255, 0, 0)
    color2 = Color(255, 255, 255)
    block_size = 3
    blink_state = True
    while current_mode == "pit":
        for i in range(strip.numPixels()):
            if ((i // block_size) % 2 == 0) == blink_state:
                strip.setPixelColor(i, color1)
            else:
                strip.setPixelColor(i, color2)
        strip.show()
        blink_state = not blink_state
        time.sleep(0.5)

def chase_mode():
    tail_length = 4
    base_color = Color(0, 0, 255)
    off_color = Color(0, 0, 0)
    while current_mode == "chase":
        for i in range(strip.numPixels() + tail_length):
            for j in range(strip.numPixels()):
                distance = i - j
                if 0 <= distance < tail_length:
                    brightness = int(255 * (1 - (distance / tail_length)))
                    strip.setPixelColor(j, Color(0, 0, brightness))
                else:
                    strip.setPixelColor(j, off_color)
            strip.show()
            time.sleep(0.05)

def off_mode():
    clear_strip()
    while current_mode == "off":
        time.sleep(0.5)

def clear_strip():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

def run_mode():
    while True:
        if current_mode == "acceleration":
            realtime_acceleration()
        elif current_mode == "police":
            police_lights()
        elif current_mode == "chase":
            chase_mode()
        elif current_mode == "pit":
            pit_crew_mode()
        elif current_mode == "hazard":
            hazard_lights()
        elif current_mode == "off":
            off_mode()
        else:
            time.sleep(0.1)

# === WebSocket Handler ===
async def websocket_handler():
    global websocket, current_mode
    while True:
        try:
            async with websockets.connect(WEBSOCKET_URL) as ws:
                websocket = ws
                print("Connected to WebSocket.")
                async for message in websocket:
                    message = message.decode("utf-8")
                    #print(f"Received: {message}")
                    if message in ["off", "acceleration", "police", "pit", "chase", "hazard"]:
                        current_mode = message
                        clear_strip()
        except Exception as e:
            print(f"WebSocket error: {e}")
            await asyncio.sleep(5)

async def send_data(message):
    if websocket:
        try:
            await websocket.send(message)
            #print(f"Sent: {message}")
        except Exception as e:
            print(f"Error sending data: {e}")

# === Main Async Runner ===
async def main():
    led_thread = threading.Thread(target=run_mode, daemon=True)
    led_thread.start()

    await asyncio.gather(
        websocket_handler(),
        obd_handler()
    )

if __name__ == "__main__":
    try:
        bind_rfcomm()
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
        clear_strip()
