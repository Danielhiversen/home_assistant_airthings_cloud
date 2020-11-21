"""Support for Airthings."""
import asyncio
import datetime
import json
import logging

import aiohttp
import async_timeout
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    DEVICE_CLASS_TEMPERATURE,
    PRESSURE_MBAR,
    DEVICE_CLASS_PRESSURE,
    PERCENTAGE,
    DEVICE_CLASS_HUMIDITY,
    CONCENTRATION_PARTS_PER_MILLION,
    CONCENTRATION_PARTS_PER_BILLION,
    DEVICE_CLASS_BATTERY,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "airthings_cloud"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
)

SENSOR_TYPES = {
    "radonshorttermavg": ["Bq/m³", None],
    "radonshorttermavg_pci": ["pCi/L", None],
    "temp": [TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE],
    "temp_f": [TEMP_FAHRENHEIT, DEVICE_CLASS_TEMPERATURE],
    "humidity": [PERCENTAGE, DEVICE_CLASS_HUMIDITY],
    "pressure": [PRESSURE_MBAR, DEVICE_CLASS_PRESSURE],
    "co2": [CONCENTRATION_PARTS_PER_MILLION, None],
    "voc": [CONCENTRATION_PARTS_PER_BILLION, None],
    "battery": [PERCENTAGE, DEVICE_CLASS_BATTERY],
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Airthings."""
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    airthings_data = AirthingsData(username, password, async_get_clientsession(hass))

    if not await airthings_data.get_user_credentials():
        _LOGGER.error("Failed to connect to Airthings")
    if not await airthings_data.update_data():
        _LOGGER.error("Failed to get data from Airthings")

    dev = []
    for sensor_id, sensor in airthings_data.sensors.items():
        if sensor[1] in SENSOR_TYPES:
            dev.append(Airthings(sensor_id, sensor, airthings_data))

    async_add_entities(dev)


class Airthings(Entity):
    """Representation of an weather sensor."""

    def __init__(self, sensor_id, sensor, airthings_data):
        """Initialize the sensor."""
        self._sensor_id = sensor_id
        self._sensor = sensor
        self._airthings_data = airthings_data
        self._unit_of_measurement = SENSOR_TYPES[sensor[1]][0]
        self._device_class = SENSOR_TYPES[sensor[1]][1]

    @property
    def name(self):
        """Return the name of the sensor."""
        return f'Airthings {self._sensor[2].get("roomName", "")} {self._sensor[1]}'

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._sensor_id

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "timestamp": datetime.datetime.fromisoformat(
                self._sensor[2].get("latestSample", "")
            )
        }

    @property
    def state(self):
        """Return the state of the device."""
        return self._sensor[0]

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    async def async_update(self):
        """Get the latest data."""
        await self._airthings_data.update()
        self._sensor = self._airthings_data.sensors.get(self._sensor_id)

    @property
    def device_class(self):
        """Return the device class of this entity, if any."""
        return self._device_class


class AirthingsData:
    def __init__(self, username, password, session):
        self._username = username
        self._password = password
        self._session = session

        self.access_token = None

        self._timeout = 10
        self._updated_at = datetime.datetime.utcnow()

        self.sensors = {}

    async def update(self, _=None, force_update=False):
        now = datetime.datetime.utcnow()
        elapsed = now - self._updated_at
        if elapsed < datetime.timedelta(minutes=20) and not force_update:
            return
        self._updated_at = now
        if self.access_token is None:
            await self.get_user_credentials()
        await self.update_data()

    async def get_user_credentials(self):
        headers = {
            "content-type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
        }

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self._session.post(
                    "https://accounts-api.airthings.com/v1/token",
                    data=json.dumps(
                        {
                            "username": self._username,
                            "password": self._password,
                            "grant_type": "password",
                            "client_id": "accounts",
                        }
                    ),
                    headers=headers,
                )
            if resp.status != 200:
                _LOGGER.error(
                    "Error connecting to Airthings, resp code:  %s %s",
                    resp.status,
                    resp.reason,
                )
                return False
            result = await resp.json()

            with async_timeout.timeout(self._timeout):
                headers["authorization"] = result["access_token"]
                resp = await self._session.post(
                    "https://accounts-api.airthings.com/v1/authorize?"
                    "client_id=dashboard&redirect_uri=https%3A%2F%2Fdashboard.airthings.com",
                    data=json.dumps({"scope": ["dashboard"]}),
                    headers=headers,
                )
            if resp.status != 200:
                _LOGGER.error(
                    "Error connecting to Airthings, resp code:  %s %s",
                    resp.status,
                    resp.reason,
                )
                return False
            result = await resp.json()
            code = str(result["redirect_uri"].split("=")[1])

            headers = {
                "accept": "application/json",
                "content-type": "application/json",
            }
            data = (
                '{"grant_type":"authorization_code","client_id":"dashboard",'
                '"client_secret":"e333140d-4a85-4e3e-8cf2-bd0a6c710aaa","code":"'
                + code
                + '","redirect_uri":"https://dashboard.airthings.com"}'
            )
            with async_timeout.timeout(self._timeout):
                resp = await self._session.post(
                    "https://accounts-api.airthings.com/v1/token",
                    data=data,
                    headers=headers,
                )
            if resp.status != 200:
                _LOGGER.error(
                    "Error connecting to Airthings, resp code:  %s %s",
                    resp.status,
                    resp.reason,
                )
                return False
            result = await resp.json()
            self.access_token = result["access_token"]

        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Airthings: %s ", err, exc_info=True)
            raise
        except asyncio.TimeoutError:
            return False
        return True

    async def update_data(self):
        if self.access_token is None:
            await self.get_user_credentials()

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": self.access_token,
        }

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self._session.get(
                    "https://web-api.airthin.gs/v1/dashboard",
                    headers=headers,
                )
            if resp.status != 200:
                _LOGGER.error(
                    "Error connecting to Airthings, resp code: %s %s",
                    resp.status,
                    resp.reason,
                )
                return False
            result = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Airthings: %s ", err, exc_info=True)
            raise
        except asyncio.TimeoutError:
            return False

        for device in result.get("tiles", []):
            device_id = device.get("content", {}).get("serialNumber")
            sensors = device.get("content", {}).get("currentSensorValues", [])
            if not sensors:
                continue
            for sensor in sensors:
                sensor_type = sensor["type"].lower()
                if sensor_type == "temp" and sensor.get("providedUnit") != "c":
                    sensor_type = "temp_f"
                if sensor_type == "radonshorttermavg" and sensor.get("providedUnit") == "pci":
                    sensor_type = "radonshorttermavg_pci"
                self.sensors[f'{device_id}_{sensor["type"].lower()}'] = (
                    sensor.get("value"),
                    sensor_type,
                    device.get("content", {}),
                )
            self.sensors[f"{device_id}_battery"] = (
                device.get("content", {}).get("batteryPercentage"),
                "battery",
                device.get("content", {}),
            )
        return True
