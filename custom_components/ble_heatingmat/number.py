from homeassistant.components.number import NumberEntity
from .const import DOMAIN

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    manager = hass.data[DOMAIN]
    async_add_entities([HeatingMatTimer(manager)])

class HeatingMatTimer(NumberEntity):
    def __init__(self, manager):
        self.manager = manager
        self._attr_name = "Heating Mat Timer"
        self._attr_unique_id = f"{manager.mac_address}_timer"
        self._attr_icon = "mdi:timer-outline"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 15
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "h"
        self.manager.register_callback(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.manager.state["timer_hours"]

    async def async_set_native_value(self, value: float):
        await self.manager.set_timer(int(value))