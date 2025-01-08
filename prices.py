import appdaemon.plugins.hass.hassapi as hass
import adbase as ad
import mqttapi as mqtt
from datetime import datetime,timezone,timedelta
from urllib.request import urlopen
import json

class Prices(ad.ADBase):

    def initialize(self):
        self.adapi = self.get_ad_api()
        self.mqtt = self.get_plugin_api("MQTT")
        self.mqtt_topic_state = "testpris/state"
        self.mqtt_topic_att = "testpris/att"
        self.mqtt_topic_state2 = "totalpris/state"
        self.mqtt_topic_att2 = "totalpris/att"
        self.next_day_sensor = "binary_sensor.morgendagenspriserklar"
        self.price_sensor = "sensor.nordpool_kwh_no1_nok_3_10_025"
        self.adapi.listen_state(self.update_sensor_daily,entity_id=self.next_day_sensor,new="on")
        self.adapi.listen_state(self.update_sensor_hourly,entity_id=self.price_sensor)

        #self.adapi.run_every(self.test, datetime.now(timezone.utc) + timedelta(seconds=5) , 1000)
        #self.adapi.run_every(self.update_sensor_daily, datetime.now(timezone.utc) + timedelta(seconds=5) , 1000)
    

    def update_sensor_daily(self,kwargs,entity=None,attribute=None,old=None,new=None):
        state = self.adapi.get_state(self.price_sensor,attribute="all")
        keys=["unit","currency","country","region","today","tomorrow","raw_today","raw_tomorrow","icon"]
        info= {x:state["attributes"][x] for x in keys}
        for i in info["raw_tomorrow"]:
            i["value"]=self.calculate_price(i["value"])
        for i in info["raw_today"]:
            i["value"]=self.calculate_price(i["value"])
        info["today"]= [self.calculate_price(i) for i in info["today"]]
        info["tomorrow"]= [self.calculate_price(i) for i in info["tomorrow"]]
        info2=info
        info=json.dumps(info)
        self.mqtt.mqtt_publish(topic=self.mqtt_topic_att, payload=info, retain=True)
        info2=self.calc_nettleie(info2)
        info2=json.dumps(info2)
        self.mqtt.mqtt_publish(topic=self.mqtt_topic_att2, payload=info2, retain=True)
        self.adapi.log("Oppdatert test_pris")

    def update_sensor_hourly(self,entity,attribute,old,new,kwargs):
        state = self.calculate_price(float(new))
        self.mqtt.mqtt_publish(topic=self.mqtt_topic_state, payload=state, retain=True)
        state2 = float(state) + self.get_nettleie()
        self.mqtt.mqtt_publish(topic=self.mqtt_topic_state2, payload=state2, retain=True)
        self.adapi.log("Oppdatert state for test_pris")
        if self.adapi.get_now().hour == 0:
            state = self.adapi.get_state(self.price_sensor,attribute="all")
            keys=["unit","currency","country","region","today","tomorrow","raw_today","raw_tomorrow","icon"]
            info= {x:state["attributes"][x] for x in keys}
            for i in info["raw_tomorrow"]:
                i["value"]=self.calculate_price(i["value"])
            for i in info["raw_today"]:
                i["value"]=self.calculate_price(i["value"])
            info["today"]= [self.calculate_price(i) for i in info["today"]]
            info["tomorrow"]= [self.calculate_price(i) for i in info["tomorrow"]]
            info2=info
            info=json.dumps(info)
            self.mqtt.mqtt_publish(topic=self.mqtt_topic_att, payload=info, retain=True)
            info2=self.calc_nettleie(info2)
            info2=json.dumps(info2)
            self.mqtt.mqtt_publish(topic=self.mqtt_topic_att2, payload=info2, retain=True)
            self.adapi.log("Oppdatert test_pris attributter")
        
    def calculate_price(self,spot):
        threshold = 0.75 * 1.25
        if spot <= threshold:
            return round(spot,3)
        else:
            return round(spot - (0.9 * (spot-threshold)),3)

    def calc_nettleie(self,attributesdict):
        for i in attributesdict["raw_today"]:
            time=datetime.strptime(i["start"],"%Y-%m-%dT%H:%M:%S%z").hour
            if (time >= 6 and time < 23):
                i["nettleie"]=0.4469
                i["value"]=i["nettleie"]+i["value"]
            else:
                i["nettleie"]=0.3269
                i["value"]=i["nettleie"]+i["value"]
        for i in attributesdict["raw_tomorrow"]:
            time=datetime.strptime(i["start"],"%Y-%m-%dT%H:%M:%S%z").hour
            if (time >= 6 and time < 23):
                i["nettleie"]=0.4469
                i["value"]=i["nettleie"]+i["value"]
            else:
                i["nettleie"]=0.3269
                i["value"]=i["nettleie"]+i["value"]
        return attributesdict

    def get_nettleie(self):
        time=self.adapi.get_now().hour
        if (time >= 6 and time < 23):
            return 0.53
        else:
            return 0.41
