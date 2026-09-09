from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode, HVACAction
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    manager = hass.data[DOMAIN]
    async_add_entities([HeatingMatClimate(manager)])

class HeatingMatClimate(ClimateEntity):
    def __init__(self, manager):
        self.manager = manager
        self._attr_name = "Heating Mat"
        self._attr_unique_id = f"{manager.mac_address}_climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_min_temp = 36
        self._attr_max_temp = 42
        self._attr_target_temperature_step = 1
        self.manager.register_callback(self.async_write_ha_state)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.manager.mac_address)},
            "name": "Smart Heating Mat",
            "manufacturer": "Custom BLE",
            "model": "Heating Mat",
        }

    @property
    def hvac_mode(self):
        return HVACMode.HEAT if self.manager.state["is_heating"] else HVACMode.OFF

    @property
    def hvac_action(self):
        return HVACAction.HEATING if self.manager.state["is_heating"] else HVACAction.OFF

    @property
    def current_temperature(self):
        return self.manager.state["current_temp"]

    @property
    def target_temperature(self):
        return self.manager.state["target_temp"]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        is_on = (hvac_mode == HVACMode.HEAT)
        await self.manager.set_power(is_on)

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get("temperature")
        if temp is not None:
            await self.manager.set_temperature(int(temp))