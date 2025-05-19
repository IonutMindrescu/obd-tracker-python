import time
import random
from rpi_ws281x import PixelStrip, Color

# LED configuration
LED_COUNT = 30
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 30
LED_INVERT = False
LED_CHANNEL = 0

# Initialize LED strip
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def get_color(speed_ratio):
    """Return a color that transitions from green to red, with full red at 0.8+."""
    if speed_ratio < 0.4:
        # Green to Yellow
        r = int(speed_ratio / 0.4 * 255)
        g = 255
    elif speed_ratio < 0.8:
        # Yellow to Red
        r = 255
        g = int((0.8 - speed_ratio) / 0.4 * 255)
    else:
        # Full Red
        r = 255
        g = 0
    return Color(r, g, 0)

def update_strip(strip, ratio):
    """Update LED strip with current speed ratio."""
    speed_leds = int(ratio * strip.numPixels())
    color = get_color(ratio)

    for i in range(strip.numPixels()):
        if i < speed_leds:
            strip.setPixelColor(i, color)
        else:
            strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

def simulate_drive(strip):
    """Run a continuous race-style simulation with random acceleration patterns."""
    speed_ratio = 1.0  # current speed level (0.0 to 1.0)
    direction = 1      # 1 for accelerating, -1 for braking

    try:
        while True:
            # Random acceleration or deceleration phase
            target_ratio = random.uniform(0.3, 1.0) if direction == 1 else random.uniform(0.0, 0.7)
            duration = random.uniform(1.5, 2.0)  # seconds for this phase
            steps = int(duration / 0.05)
            delta = (target_ratio - speed_ratio) / steps

            for _ in range(steps):
                speed_ratio += delta
                speed_ratio = max(0.0, min(1.0, speed_ratio))
                update_strip(strip, speed_ratio)
                time.sleep(0.05)

            # Randomly decide whether to change direction
            if random.random() < 0.4:
                direction *= -1  # switch between accelerate/decelerate

            # Small pause at end of phase
            time.sleep(random.uniform(0.2, 0.5))

    except KeyboardInterrupt:
        print("Stopping simulation...")
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()

# Start the simulation
simulate_drive(strip)
