# RTL-SDR Gas Meter Monitor for Home Assistant

A Python script that reads gas meter data using RTL-SDR and rtlamr, then sends it to Home Assistant via MQTT with automatic sensor discovery and system health monitoring.

## Features

- **Automatic Home Assistant Discovery**: Sensors are automatically created in HA
- **Energy Dashboard Integration**: Gas consumption sensor works with HA Energy Dashboard
- **System Health Monitoring**: CPU, memory, disk usage, temperature, and uptime monitoring
- **Offline Detection**: All sensors show as "unavailable" when the device goes offline
- **Robust Error Handling**: Automatic restarts and comprehensive logging
- **Systemd Service**: Runs as a system service with auto-start on boot

## Hardware Requirements

- Raspberry Pi (tested on Pi 4)
- RTL-SDR dongle
- Compatible gas meter with AMR/AMI capability

## Software Dependencies

- Python 3.7+
- rtl-sdr tools
- rtlamr (Go binary)
- Home Assistant with MQTT integration

## Installation

### 1. Install System Dependencies

```bash
# Install RTL-SDR tools
sudo apt update
sudo apt install rtl-sdr

# Install Go (if not already installed)
wget https://golang.org/dl/go1.21.0.linux-armv6l.tar.gz
sudo tar -C /usr/local -xzf go1.21.0.linux-armv6l.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc

# Install rtlamr
go install github.com/bemasher/rtlamr@latest
```

### 2. Install Python Dependencies

```bash
sudo pip3 install paho-mqtt psutil
```

### 3. Configure the Script

Edit `gas_meter.py` and update these values:

```python
self.mqtt_host = "YOUR_MQTT_BROKER_IP"        # Your MQTT broker IP
self.mqtt_user = "YOUR_MQTT_USERNAME"         # Your MQTT username
self.mqtt_pass = "YOUR_MQTT_PASSWORD"         # Your MQTT password
self.meter_id = "YOUR_METER_ID"               # Your gas meter ID
```

### 4. Find Your Meter ID

Run rtlamr temporarily to find your meter ID:

```bash
rtl_tcp &
rtlamr -format=json -msgtype=scm
```

Look for JSON output with your meter's data and note the ID field.

### 5. Test the Script

```bash
sudo python3 gas_meter.py
```

You should see:
- MQTT discovery messages being sent
- Gas meter readings being captured and forwarded
- System health data being published

### 6. Install as Systemd Service

```bash
# Copy service file
sudo cp gas_meter.service /etc/systemd/system/

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable gas_meter.service
sudo systemctl start gas_meter.service
```

## Home Assistant Integration

### Automatic Sensor Creation

The script automatically creates these sensors in Home Assistant:

- `sensor.raspberry_pi_gas_meter_gas_consumption` - For Energy Dashboard
- `sensor.raspberry_pi_gas_meter_device_status` - Online/offline status
- `sensor.raspberry_pi_gas_meter_cpu_usage` - CPU usage percentage
- `sensor.raspberry_pi_gas_meter_memory_usage` - Memory usage percentage
- `sensor.raspberry_pi_gas_meter_disk_usage` - Disk usage percentage
- `sensor.raspberry_pi_gas_meter_cpu_temperature` - CPU temperature
- `sensor.raspberry_pi_gas_meter_uptime` - System uptime in hours

### Adding to Energy Dashboard

1. Go to **Settings → Dashboards → Energy**
2. Click **"Add Gas Source"**
3. Select `sensor.raspberry_pi_gas_meter_gas_consumption`
4. Configure any unit conversions if needed

### Offline Detection Automation

Create an automation to alert when the device goes offline:

```yaml
description: "Alert when gas meter monitoring goes offline"
mode: single
triggers:
  - trigger: state
    entity_id: sensor.raspberry_pi_gas_meter_device_status
    to: unavailable
    for:
      minutes: 5
  - trigger: state
    entity_id: sensor.raspberry_pi_gas_meter_device_status
    to: unknown
    for:
      minutes: 5
actions:
  - action: notify.persistent_notification
    data:
      title: "Gas Meter Monitor Offline"
      message: "The Raspberry Pi gas meter monitor has gone offline."
```

## Service Management

```bash
# Check service status
sudo systemctl status gas_meter

# View logs
sudo journalctl -u gas_meter -f
# or
sudo tail -f /var/log/gas_meter.log

# Restart service
sudo systemctl restart gas_meter

# Stop service
sudo systemctl stop gas_meter
```

## Troubleshooting

### Common Issues

1. **No gas readings**: Check that your RTL-SDR dongle is working and rtlamr can see your meter
2. **MQTT connection fails**: Verify MQTT broker settings and credentials
3. **Sensors not appearing in HA**: Check MQTT integration is configured and discovery is enabled
4. **Permission errors**: Ensure the script runs as root (required for RTL-SDR access)

### Logs

Check logs for detailed error information:
- System logs: `sudo journalctl -u gas_meter -f`
- Script logs: `sudo tail -f /var/log/gas_meter.log`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is open source and available under the MIT License.

## Acknowledgments

- [rtlamr](https://github.com/bemasher/rtlamr) for AMR/AMI decoding
- [RTL-SDR](https://www.rtl-sdr.com/) community
- Home Assistant community
