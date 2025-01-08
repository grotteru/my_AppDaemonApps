import appdaemon.plugins.hass.hassapi as hass
from datetime import time

class LuxToggle(hass.Hass):
    def initialize(self):
        # Get configuration parameters from apps.yaml
        self.entities = self.args["entities"]
        self.lux_sensor = self.args["lux_sensor"]
        self.lux_threshold = float(self.args["lux_threshold"])
        self.morning_lux_threshold = float(self.args["morning_lux_threshold"])
        self.interval_minutes = int(self.args["interval_minutes"])

        self.log(f"Initialized LuxToggle with lux sensor '{self.lux_sensor}', threshold {self.lux_threshold}, morning threshold {self.morning_lux_threshold}, interval {self.interval_minutes} minutes, controlling entities: {self.entities}")

        # Schedule a recurring check every interval_minutes
        self.run_every(self.check_lux, self.datetime(), self.interval_minutes * 60)
        
    def check_lux(self, kwargs):
        # Get the current lux value from the sensor
        lux_value = self.get_state(self.lux_sensor, attribute="state")
        
        try:
            lux_value = float(lux_value)
            self.log(f"Lux value is {lux_value}. Threshold is {self.lux_threshold}. Morning threshold is {self.morning_lux_threshold}.", level="DEBUG")

            # Determine the appropriate threshold based on the time of day
            current_time = self.time()
            if time(4, 0) <= current_time <= time(10, 0):
                threshold = self.morning_lux_threshold
            else:
                threshold = self.lux_threshold
            
            if lux_value < threshold:
                # Lux is below the threshold, turn on all specified entities if not already on
                for entity in self.entities:
                    if self.get_state(entity) != "on":
                        self.turn_on(entity)
                        self.log(f"Lux {lux_value} is below threshold {threshold}. Turning on '{entity}'.")
            else:
                # Lux is above the threshold, turn off all specified entities if not already off
                for entity in self.entities:
                    if self.get_state(entity) != "off":
                        self.turn_off(entity)
                        self.log(f"Lux {lux_value} is above threshold {threshold}. Turning off '{entity}'.")
        except (TypeError, ValueError):
            self.log(f"Invalid lux value received from '{self.lux_sensor}': {lux_value}", level="ERROR")