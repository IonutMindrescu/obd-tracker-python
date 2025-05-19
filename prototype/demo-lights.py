import asyncio
import websockets
import json
import random
import time
import math
from rpi_ws281x import PixelStrip, Color

# --- LED Strip Setup ---
LED_COUNT = 30             # Two strips of 30 LEDs each
LED_PIN = 18               # GPIO18 (pin 12)
LED_FREQ_HZ = 800000       # LED signal frequency
LED_DMA = 10               # DMA channel
LED_BRIGHTNESS = 10       # Brightness (0–255)
LED_INVERT = False
LED_CHANNEL = 0

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# --- LED Helpers ---
def get_color(speed_ratio):
    """Green → Yellow → Red, fully red from 0.8–1.0."""
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

def update_strip(strip, ratio):
    """Update LEDs to reflect current speed ratio."""
    lit_leds = int(ratio * strip.numPixels())
    color = get_color(ratio)

    for i in range(strip.numPixels()):
        if i < lit_leds:
            strip.setPixelColor(i, color)
        else:
            strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

def animate_rpm_change(strip, old_rpm, new_rpm, duration=0.5):
    """Smoothly animate the RPM change on the LED strip."""
    steps = 30  # More steps for smoother transition
    delay = duration / steps
    for i in range(steps + 1):
        interp_rpm = old_rpm + (new_rpm - old_rpm) * (i / steps)
        rpm_ratio = (interp_rpm - 700) / (6000 - 700)  # Normalize RPM
        rpm_ratio = max(0.0, min(1.0, rpm_ratio))
        update_strip(strip, rpm_ratio)
        time.sleep(delay)

# --- Vehicle Simulator ---
class VehicleSimulator:
    def __init__(self):
        self.start_time = time.time()
        self.speed = 0
        self.coolant_temp = 75
        self.engine_load = 10
        self.throttle_pos = 0
        self.intake_temp = 25
        self.elm_voltage = 12.5
        self.maf = 2.0
        self.last_rpm = 500  # Initialize last RPM

    def generate_data(self):
        now = time.time()
        cycle_time = 4.0  # 2s accel + 2s decel
        elapsed = (now - self.start_time) % cycle_time

        # Create a smooth acceleration-deceleration curve (ease-in-out)
        t = elapsed / cycle_time  # 0 to 1

        # Use a cubic ease-in-out curve: 3t² - 2t³
        if t < 0.5:
            ratio = 4 * t**3
        else:
            ratio = 1 - pow(-2 * t + 2, 3) / 2

        # Map ratio to RPM
        self.rpm = 500 + ratio * (7000 - 500)

        # Realistic mappings
        self.throttle_pos = ratio * 100
        self.speed = ratio * 150

        self.engine_load = (self.throttle_pos * 0.6) + (self.rpm / 10000 * 40)
        self.engine_load = min(100, self.engine_load + random.uniform(-2, 2))

        if self.coolant_temp < 90:
            self.coolant_temp += random.uniform(0.1, 0.5)
        else:
            self.coolant_temp += random.uniform(-0.2, 0.2)
        self.coolant_temp = max(70, min(120, self.coolant_temp))

        self.intake_temp += random.uniform(-1, 1)
        self.intake_temp = max(10, min(50, self.intake_temp))

        self.elm_voltage += random.uniform(-0.05, 0.05)
        self.elm_voltage = max(11.5, min(14.5, self.elm_voltage))

        self.maf = (self.rpm * self.engine_load) / 12000 + random.uniform(-1, 1)
        self.maf = max(0, min(100, self.maf))

        return {
            "RPM": round(self.rpm, 1),
            "SPEED": round(self.speed, 1),
            "COOLANT_TEMP": round(self.coolant_temp),
            "ENGINE_LOAD": round(self.engine_load, 2),
            "THROTTLE_POS": round(self.throttle_pos, 2),
            "INTAKE_TEMP": round(self.intake_temp),
            "ELM_VOLTAGE": round(self.elm_voltage, 2),
            "MAF": round(self.maf, 2)
        }

# --- Main Async Loop ---
async def connect_to_obd():
    uri = "wss://ws.sonny.ro"
    simulator = VehicleSimulator()

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        while True:
            data = simulator.generate_data()

            # Extract RPM and animate the LED strip based on RPM
            new_rpm = data["RPM"]
            animate_rpm_change(strip, simulator.last_rpm, new_rpm)

            # Update the simulator's last RPM for the next animation
            simulator.last_rpm = new_rpm

            # Send data to WebSocket
            for key, value in data.items():
                message = json.dumps({"command": key, "value": value})
                await websocket.send(message)
                print(f"Sent: {message}")

            await asyncio.sleep(0.5)

try:
    asyncio.run(connect_to_obd())
except KeyboardInterrupt:
    print("Stopping...")
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
