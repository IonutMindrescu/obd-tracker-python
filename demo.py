import asyncio
import websockets
import json
import random

# Vehicle simulation class
class VehicleSimulator:
    def __init__(self):
        self.rpm = 800
        self.speed = 0
        self.coolant_temp = 75
        self.engine_load = 10
        self.throttle_pos = 0
        self.intake_temp = 25
        self.elm_voltage = 12.5
        self.maf = 2.0

    def generate_data(self):
        # Simulate throttle changes
        self.throttle_pos += random.uniform(-5, 5)
        self.throttle_pos = max(0, min(100, self.throttle_pos))

        # Simulate speed change based on throttle
        accel_factor = self.throttle_pos / 100
        self.speed += random.uniform(-2, 3) * accel_factor
        self.speed = max(0, min(180, self.speed))

        # RPM depends on speed and throttle
        self.rpm = 700 + (self.speed * 30) + (self.throttle_pos * 10)
        self.rpm += random.uniform(-200, 200)
        self.rpm = max(700, min(6000, self.rpm))

        # Engine load correlates with throttle and RPM
        self.engine_load = (self.throttle_pos * 0.6) + (self.rpm / 10000 * 40)
        self.engine_load = min(100, self.engine_load + random.uniform(-2, 2))

        # Coolant temperature rises slowly, then stabilizes
        if self.coolant_temp < 90:
            self.coolant_temp += random.uniform(0.1, 0.5)
        else:
            self.coolant_temp += random.uniform(-0.2, 0.2)
        self.coolant_temp = max(70, min(120, self.coolant_temp))

        # Intake temp varies slightly around ambient with engine heat
        self.intake_temp += random.uniform(-1, 1)
        self.intake_temp = max(10, min(50, self.intake_temp))

        # Simulate ELM voltage fluctuation
        self.elm_voltage += random.uniform(-0.05, 0.05)
        self.elm_voltage = max(11.5, min(14.5, self.elm_voltage))

        # Simulate Mass Air Flow (MAF) in grams/sec
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

async def connect_to_obd():
    uri = "wss://ws.sonny.ro"
    simulator = VehicleSimulator()

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        while True:
            data = simulator.generate_data()
            for key, value in data.items():
                message = json.dumps({"command": key, "value": value})
                await websocket.send(message)
                print(f"Sent: {message}")
            await asyncio.sleep(0.5)

asyncio.run(connect_to_obd())
