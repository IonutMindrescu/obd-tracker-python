import time
import random
import threading
import asyncio
import websockets
from rpi_ws281x import PixelStrip, Color

# === LED Configuration ===
LED_COUNT = 30
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255 #255 max value
LED_INVERT = False
LED_CHANNEL = 0

# Initialize LED strip
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# === Global Mode Variable ===
current_mode = "chase"

# === Color Functions ===
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

# === LED Modes ===
def update_strip_acceleration(strip, ratio):
    speed_leds = int(ratio * strip.numPixels())
    color = get_color(ratio)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color if i < speed_leds else Color(0, 0, 0))
    strip.show()

def simulate_acceleration(strip):
    speed_ratio = 1.0
    direction = 1
    while current_mode == "acceleration":
        target_ratio = random.uniform(0.3, 1.0) if direction == 1 else random.uniform(0.0, 0.7)
        duration = random.uniform(1.5, 2.0)
        steps = int(duration / 0.05)
        delta = (target_ratio - speed_ratio) / steps
        for _ in range(steps):
            if current_mode != "acceleration":
                return
            speed_ratio = max(0.0, min(1.0, speed_ratio + delta))
            update_strip_acceleration(strip, speed_ratio)
            time.sleep(0.05)
        if random.random() < 0.4:
            direction *= -1
        time.sleep(random.uniform(0.2, 0.5))

def police_lights(strip):
    """Realistic police lights: red flashes left side, blue flashes right side."""
    half = strip.numPixels() // 2
    flash_count = 5        # Number of strobe flashes before switching sides
    flash_delay = 0.03      # Flash timing (seconds)

    while current_mode == "police":
        # Flash red on left, right off
        for _ in range(flash_count):
            for i in range(half):
                strip.setPixelColor(i, Color(255, 0, 0))  # Red
            for i in range(half, strip.numPixels()):
                strip.setPixelColor(i, Color(0, 0, 0))    # Off
            strip.show()
            time.sleep(flash_delay)

            # Turn all off between flashes
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, Color(0, 0, 0))
            strip.show()
            time.sleep(flash_delay)

        # Flash blue on right, left off
        for _ in range(flash_count):
            for i in range(half):
                strip.setPixelColor(i, Color(0, 0, 0))    # Off
            for i in range(half, strip.numPixels()):
                strip.setPixelColor(i, Color(0, 0, 255))  # Blue
            strip.show()
            time.sleep(flash_delay)

            # Turn all off between flashes
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, Color(0, 0, 0))
            strip.show()
            time.sleep(flash_delay)

def hazard_lights(strip):
    """Amber hazard lights: all LEDs flash on/off in sync."""
    amber = Color(255, 120, 0)  # Bright orange/amber
    flash_delay = 0.3           # Half-second on/off cycle

    while current_mode == "hazard":
        # Turn all LEDs on (amber)
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, amber)
        strip.show()
        time.sleep(flash_delay)

        # Turn all LEDs off
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        time.sleep(flash_delay)

def pit_crew_mode(strip):
    """Alternating red/white stripes or yellow/black caution pattern."""
    color1 = Color(255, 0, 0)     # Red
    color2 = Color(255, 255, 255) # White

    block_size = 3  # Number of LEDs per color block
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

def chase_mode(strip):
    """Single or grouped pixel chases along the strip."""
    tail_length = 4
    base_color = Color(0, 0, 255)  # Blue chase dot
    off_color = Color(0, 0, 0)

    while current_mode == "chase":
        for i in range(strip.numPixels() + tail_length):
            for j in range(strip.numPixels()):
                # Set a tail effect
                distance = i - j
                if 0 <= distance < tail_length:
                    brightness = int(255 * (1 - (distance / tail_length)))
                    strip.setPixelColor(j, Color(0, 0, brightness))
                else:
                    strip.setPixelColor(j, off_color)
            strip.show()
            time.sleep(0.05)

def off_mode(strip):
    """Turn off all LEDs."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    # Remain idle while in 'off' mode
    while current_mode == "off":
        time.sleep(0.5)

def clear_strip():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

# === WebSocket Client ===
async def listen_to_server():
    global current_mode
    uri = "wss://ws.sonny.ro"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Connected to WebSocket server.")
                async for message in websocket:
                    message = message.decode('utf-8')

                    print(f"Received: {message}")
                    if message in ["off", "acceleration", "police", "pit", "chase", "hazard"]:
                        current_mode = message
                        clear_strip()
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            await asyncio.sleep(5)

def start_websocket_client():
    asyncio.run(listen_to_server())

# === Mode Manager Thread ===
def mode_manager():
    while True:
        if current_mode == "acceleration":
            simulate_acceleration(strip)
        elif current_mode == "police":
            police_lights(strip)
        elif current_mode == "chase":
            chase_mode(strip)
        elif current_mode == "pit":
            pit_crew_mode(strip)
        elif current_mode == "hazard":
            hazard_lights(strip)
        elif current_mode == "off":
            off_mode(strip)
        else:
            time.sleep(0.1)

# === Main Entry Point ===
if __name__ == "__main__":
    try:
        # Start WebSocket client thread
        threading.Thread(target=start_websocket_client, daemon=True).start()
        # Start mode execution loop
        mode_manager()
    except KeyboardInterrupt:
        print("Exiting...")
        clear_strip()
