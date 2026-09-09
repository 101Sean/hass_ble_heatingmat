from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    manager = hass.data[DOMAIN]
    async_add_entities([HeatingMatTrackingSwitch(manager)])

class HeatingMatTrackingSwitch(SwitchEntity):
    def __init__(self, manager):
        self.manager = manager
        self._attr_name = "BLE Tracking"
        self._attr_unique_id = f"{manager.mac_address}_tracking"
        self._attr_icon = "mdi:bluetooth-connect"
        self.manager.register_callback(self.async_write_ha_state)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.manager.mac_address)},
        }

    @property
    def is_on(self):
        return self.manager.is_tracking

    async def async_turn_on(self, **kwargs):
        await self.manager.start_tracking()

    async def async_turn_off(self, **kwargs):
        await self.manager.stop_tracking()