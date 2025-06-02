import subprocess
import json
import paho.mqtt.client as mqtt
import time
import psutil
import socket
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/gas_meter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HomeAssistantMQTT:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.device_id = "raspberrypi_gas_meter"
        self.device_name = "Raspberry Pi Gas Meter"
        
    def get_client(self):
        """Create and configure MQTT client."""
        client = mqtt.Client()
        client.username_pw_set(self.username, self.password)
        return client
    
    def publish_ha_discovery(self):
        """Publish Home Assistant auto-discovery configurations."""
        client = self.get_client()
        client.connect(self.host, self.port, 60)
        
        # Device info shared across all entities
        device_info = {
            "identifiers": [self.device_id],
            "name": self.device_name,
            "model": "Gas Meter Monitor",
            "manufacturer": "Custom",
            "sw_version": "1.0"
        }
        
        # Gas consumption sensor for Energy Dashboard with availability
        gas_config = {
            "name": "Gas Consumption",
            "unique_id": f"{self.device_id}_gas_consumption",
            "state_topic": "xcel_gas_usage_cubic_feet",
            "availability_topic": f"homeassistant/sensor/{self.device_id}/status",
            "availability_template": "{{ 'online' if value_json.status == 'online' else 'offline' }}",
            "value_template": "{{ value_json.Message.Consumption }}",
            "unit_of_measurement": "ft³",
            "device_class": "gas",
            "state_class": "total_increasing",
            "device": device_info,
            "json_attributes_topic": "xcel_gas_usage_cubic_feet",
            "json_attributes_template": "{{ {'last_reading_time': value_json.Time, 'meter_id': value_json.Message.ID, 'tamper_phy': value_json.Message.TamperPhy, 'tamper_enc': value_json.Message.TamperEnc} | tojson }}"
        }
        
        # Device status sensor (acts as availability indicator)
        status_config = {
            "name": "Device Status",
            "unique_id": f"{self.device_id}_status",
            "state_topic": f"homeassistant/sensor/{self.device_id}/status",
            "value_template": "{{ value_json.status }}",
            "json_attributes_topic": f"homeassistant/sensor/{self.device_id}/status",
            "json_attributes_template": "{{ {'last_seen': value_json.timestamp, 'gas_readings_count': value_json.gas_readings_count, 'script_version': value_json.script_version} | tojson }}",
            "device": device_info,
            "icon": "mdi:router-wireless"
        }

        # System health sensors with availability
        availability_topic = f"homeassistant/sensor/{self.device_id}/status"
        health_sensors = [
            {
                "name": "CPU Usage",
                "unique_id": f"{self.device_id}_cpu_usage",
                "state_topic": f"homeassistant/sensor/{self.device_id}/system_health",
                "availability_topic": availability_topic,
                "availability_template": "{{ 'online' if value_json.status == 'online' else 'offline' }}",
                "value_template": "{{ value_json.cpu_percent }}",
                "unit_of_measurement": "%",
                "device_class": "power_factor",
                "device": device_info
            },
            {
                "name": "Memory Usage",
                "unique_id": f"{self.device_id}_memory_usage",
                "state_topic": f"homeassistant/sensor/{self.device_id}/system_health",
                "availability_topic": availability_topic,
                "availability_template": "{{ 'online' if value_json.status == 'online' else 'offline' }}",
                "value_template": "{{ value_json.memory_percent }}",
                "unit_of_measurement": "%",
                "device_class": "power_factor",
                "device": device_info
            },
            {
                "name": "Disk Usage",
                "unique_id": f"{self.device_id}_disk_usage",
                "state_topic": f"homeassistant/sensor/{self.device_id}/system_health",
                "availability_topic": availability_topic,
                "availability_template": "{{ 'online' if value_json.status == 'online' else 'offline' }}",
                "value_template": "{{ value_json.disk_percent }}",
                "unit_of_measurement": "%",
                "device_class": "power_factor",
                "device": device_info
            },
            {
                "name": "CPU Temperature",
                "unique_id": f"{self.device_id}_cpu_temp",
                "state_topic": f"homeassistant/sensor/{self.device_id}/system_health",
                "availability_topic": availability_topic,
                "availability_template": "{{ 'online' if value_json.status == 'online' else 'offline' }}",
                "value_template": "{{ value_json.cpu_temp }}",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "device": device_info
            },
            {
                "name": "Uptime",
                "unique_id": f"{self.device_id}_uptime",
                "state_topic": f"homeassistant/sensor/{self.device_id}/system_health",
                "availability_topic": availability_topic,
                "availability_template": "{{ 'online' if value_json.status == 'online' else 'offline' }}",
                "value_template": "{{ value_json.uptime_hours }}",
                "unit_of_measurement": "h",
                "device": device_info
            }
        ]
        
        # Publish gas sensor discovery
        discovery_topic = f"homeassistant/sensor/{self.device_id}_gas/config"
        client.publish(discovery_topic, json.dumps(gas_config), retain=True)
        logger.info(f"Published HA discovery for gas sensor: {discovery_topic}")
        
        # Publish device status sensor discovery
        status_discovery_topic = f"homeassistant/sensor/{self.device_id}_status/config"
        client.publish(status_discovery_topic, json.dumps(status_config), retain=True)
        logger.info(f"Published HA discovery for status sensor: {status_discovery_topic}")
        
        # Publish health sensor discoveries
        for sensor in health_sensors:
            discovery_topic = f"homeassistant/sensor/{sensor['unique_id']}/config"
            client.publish(discovery_topic, json.dumps(sensor), retain=True)
            logger.info(f"Published HA discovery for {sensor['name']}: {discovery_topic}")
        
        client.disconnect()

class SystemHealthMonitor:
    @staticmethod
    def get_cpu_temperature():
        """Get CPU temperature for Raspberry Pi."""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
                return round(temp, 1)
        except Exception:
            return None
    
    @staticmethod
    def get_system_health():
        """Collect system health metrics."""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": round(psutil.cpu_percent(interval=1), 1),
            "memory_percent": round(psutil.virtual_memory().percent, 1),
            "disk_percent": round(psutil.disk_usage('/').percent, 1),
            "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1),
            "cpu_temp": SystemHealthMonitor.get_cpu_temperature()
        }
        return health_data

class GasMeterMonitor:
    def __init__(self):
        # CONFIGURATION - UPDATE THESE VALUES
        self.mqtt_host = "YOUR_MQTT_BROKER_IP"
        self.mqtt_port = 1883
        self.mqtt_user = "YOUR_MQTT_USERNAME"
        self.mqtt_pass = "YOUR_MQTT_PASSWORD"
        self.mqtt_topic = "xcel_gas_usage_cubic_feet"
        self.meter_id = "YOUR_METER_ID"  # Get this from your meter readings
        
        self.rtlamr_params = ["-format=json", "-msgtype=scm", f"-filterid={self.meter_id}"]
        
        self.ha_mqtt = HomeAssistantMQTT(
            self.mqtt_host, self.mqtt_port, 
            self.mqtt_user, self.mqtt_pass
        )
        self.health_monitor = SystemHealthMonitor()
        self.last_health_update = 0
        self.health_update_interval = 60  # Send health data every 60 seconds
        self.gas_readings_count = 0  # Track number of gas readings received
        
    def run_rtl_tcp(self):
        """Run rtl_tcp as a separate process."""
        try:
            logger.info("Starting rtl_tcp...")
            return subprocess.Popen(
                ["rtl_tcp"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        except Exception as e:
            logger.error(f"Error starting rtl_tcp: {e}")
            return None
    
    def capture_output(self, command):
        """Capture output from a given command."""
        logger.info("Starting rtlamr...")
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                yield output.strip()
    
    def send_to_mqtt(self, topic, data):
        """Send data to the MQTT server."""
        try:
            client = self.ha_mqtt.get_client()
            client.connect(self.mqtt_host, self.mqtt_port, 60)
            logger.info(f"Sending to topic {topic} -> {data}")
            client.publish(topic, data)
            client.disconnect()
        except Exception as e:
            logger.error(f"Error sending MQTT data: {e}")
    
    def send_health_data(self):
        """Send system health data to MQTT."""
        health_data = self.health_monitor.get_system_health()
        health_topic = f"homeassistant/sensor/{self.ha_mqtt.device_id}/system_health"
        self.send_to_mqtt(health_topic, json.dumps(health_data))
    
    def send_status_update(self):
        """Send device status update."""
        status_data = {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "gas_readings_count": self.gas_readings_count,
            "script_version": "1.0"
        }
        status_topic = f"homeassistant/sensor/{self.ha_mqtt.device_id}/status"
        self.send_to_mqtt(status_topic, json.dumps(status_data))
    
    def should_send_health_update(self):
        """Check if it's time to send health update."""
        current_time = time.time()
        if current_time - self.last_health_update >= self.health_update_interval:
            self.last_health_update = current_time
            return True
        return False
    
    def run(self):
        """Main function to capture, parse, and send data."""
        # Publish Home Assistant discovery configurations
        logger.info("Publishing Home Assistant auto-discovery configurations...")
        self.ha_mqtt.publish_ha_discovery()
        
        # Send initial health data and status
        self.send_health_data()
        self.send_status_update()
        
        rtl_tcp_process = self.run_rtl_tcp()
        if not rtl_tcp_process:
            logger.error("Failed to start rtl_tcp process")
            return
        
        time.sleep(5)  # Give rtl_tcp some time to start
        
        try:
            for data in self.capture_output(["/root/go/bin/rtlamr"] + self.rtlamr_params):
                # Send health data periodically
                if self.should_send_health_update():
                    self.send_health_data()
                    self.send_status_update()
                
                # Process gas meter data
                if data.startswith('{'):
                    try:
                        parsed_data = json.loads(data)
                        json_data = json.dumps(parsed_data)
                        self.send_to_mqtt(self.mqtt_topic, json_data)
                        self.gas_readings_count += 1  # Increment counter
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding JSON: {e}")
                    except Exception as e:
                        logger.error(f"An error occurred: {e}")
                else:
                    logger.debug(f"Ignoring non-JSON data: {data}")
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            if rtl_tcp_process:
                rtl_tcp_process.terminate()
                logger.info("Terminated rtl_tcp process")

def main():
    monitor = GasMeterMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
