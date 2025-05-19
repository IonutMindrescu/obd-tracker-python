# GTA Bucovina - OBD Tracker Device `#3399ff`

## Configuration
```python
# === Application Configuration ===
LED_COUNT = 30
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0
RECONNECT_OBD = 30
```

### Binding rfcomm serial port to OBD
`sudo rfcomm bind /dev/rfcomm0 DD:0D:30:48:A4:9C`

### Activate Python env
`source myenv/bin/activate`

### Run Application
`sudo nohup /home/pi/obd-tracker/myenv/bin/python /home/pi/obd-tracker/application.py > /dev/null 2>&1 &`

`sudo nohup /home/pi/obd-tracker/myenv/bin/python /home/pi/obd-tracker/application.py > /home/pi/obd-tracker/logs/app.log 2>&1 &`

### Run Application & Log Exceptions
`LOGFILE="/home/pi/obd-tracker/logs/app_$(date +%Y%m%d_%H%M%S).log"
sudo nohup /home/pi/obd-tracker/myenv/bin/python /home/pi/obd-tracker/application.py > "$LOGFILE" 2>&1 &`
