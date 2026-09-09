import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from .const import DOMAIN, CONF_MAC_ADDRESS, CONF_INIT_PACKET
from .ble_manager import HeatingMatBLEManager

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_MAC_ADDRESS): cv.string,
        vol.Optional(CONF_INIT_PACKET, default="a55affff"): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: dict):
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    mac_address = conf[CONF_MAC_ADDRESS]
    init_packet = conf[CONF_INIT_PACKET]

    manager = HeatingMatBLEManager(hass, mac_address, init_packet)
    hass.data.setdefault(DOMAIN, manager)

    # 플랫폼 로드
    for platform in ["switch", "climate", "number"]:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True