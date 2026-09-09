import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from .const import (
    DOMAIN, CONF_MAC_ADDRESS, CONF_INIT_PACKET,
    CONF_SERVICE_UUID, CONF_CHAR_SET, CONF_CHAR_TEMP, CONF_CHAR_TIMER
)
from .ble_manager import HeatingMatBLEManager

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_MAC_ADDRESS): cv.string,
        vol.Required(CONF_INIT_PACKET): cv.string,
        vol.Required(CONF_SERVICE_UUID): cv.string,
        vol.Required(CONF_CHAR_SET): cv.string,
        vol.Required(CONF_CHAR_TEMP): cv.string,
        vol.Required(CONF_CHAR_TIMER): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: dict):
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    
    # 설정값 추출
    config_data = {
        "mac_address": conf[CONF_MAC_ADDRESS],
        "init_packet": conf[CONF_INIT_PACKET],
        "service_uuid": conf[CONF_SERVICE_UUID],
        "char_set": conf[CONF_CHAR_SET],
        "char_temp": conf[CONF_CHAR_TEMP],
        "char_timer": conf[CONF_CHAR_TIMER],
    }

    manager = HeatingMatBLEManager(hass, config_data)
    hass.data.setdefault(DOMAIN, manager)

    for platform in ["switch", "climate", "number"]:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True