import asyncio
import logging
from bleak import BleakClient, BleakScanner

from .const import TEMP_LEVEL_MAP, LEVEL_TEMP_MAP

_LOGGER = logging.getLogger(__name__)

class HeatingMatBLEManager:
    def __init__(self, hass, config_data):
        self.hass = hass
        self.mac_address = config_data["mac_address"].upper()
        self.init_packet = bytes.fromhex(config_data["init_packet"])
        
        self.uuids = {
            "service": config_data["service_uuid"],
            "set": config_data["char_set"],
            "temp": config_data["char_temp"],
            "timer": config_data["char_timer"],
        }
        
        self.client = None
        self.is_connected = False
        self.is_tracking = False
        
        self._main_task = None
        self._ping_task = None
        
        self.state = {
            "current_temp": 38,
            "target_temp": 38,
            "last_heat_temp": 38,
            "is_heating": False,
            "timer_hours": 0
        }
        self.callbacks = []

    def register_callback(self, callback):
        self.callbacks.append(callback)

    def _notify_update(self):
        for cb in self.callbacks:
            cb()

    def create_control_packet(self, value: int) -> bytes:
        data_byte = value & 0xFF
        check_sum = (0xFF - data_byte) & 0xFF
        return bytes([data_byte, check_sum, data_byte, check_sum])

    def parse_packet(self, data: bytes):
        if len(data) < 4:
            return None
        b2, b3 = data[2], data[3]
        if ((b2 + b3) & 0xFF) == 0xFF:
            return (0xFF - b2) & 0xFF
        return None

    async def start_tracking(self):
        if self.is_tracking:
            return
        self.is_tracking = True
        self._notify_update()
        self._main_task = self.hass.loop.create_task(self._run_tracking_loop())

    async def stop_tracking(self):
        self.is_tracking = False
        self._notify_update()
        if self._ping_task:
            self._ping_task.cancel()
        if self._main_task:
            self._main_task.cancel()
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            self.is_connected = False

    async def _run_tracking_loop(self):
        while self.is_tracking:
            if not self.is_connected:
                try:
                    device = await BleakScanner.find_device_by_address(
                        self.mac_address, timeout=5.0
                    )
                    if device:
                        await self._connect_device(device)
                except Exception:
                    pass
            await asyncio.sleep(20.0)

    async def _connect_device(self, device):
        self.client = BleakClient(device, disconnected_callback=self._on_disconnect)
        try:
            await self.client.connect(timeout=7.0)
            self.is_connected = True

            # 인증
            await self.client.write_gatt_char(self.uuids['set'], self.init_packet, response=True)
            await asyncio.sleep(1.0)
            
            # Notify
            await self.client.start_notify(self.uuids['temp'], self._on_temp_notify)
            await asyncio.sleep(0.5)
            await self.client.start_notify(self.uuids['timer'], self._on_timer_notify)
            await asyncio.sleep(1.0)

            # 상태 요청 및 핑
            await self._write_raw(self.uuids['temp'], self.create_control_packet(0x12))
            self._ping_task = self.hass.loop.create_task(self._run_ping_loop())

        except Exception:
            await self.client.disconnect()

    def _on_disconnect(self, client):
        self.is_connected = False
        if self._ping_task:
            self._ping_task.cancel()

    async def _run_ping_loop(self):
        while self.is_connected and self.is_tracking:
            await asyncio.sleep(30.0)
            await self._write_raw(self.uuids['temp'], self.create_control_packet(0x12))

    async def set_power(self, is_on: bool):
        level = TEMP_LEVEL_MAP.get(self.state["last_heat_temp"], 3) if is_on else 0
        if await self._write_raw(self.uuids['temp'], self.create_control_packet(level)):
            self.state["is_heating"] = is_on
            if not is_on:
                self.state["timer_hours"] = 0
                await asyncio.sleep(0.5)
                await self.set_timer(1)
            self._notify_update()

    async def set_temperature(self, temp: int):
        level = TEMP_LEVEL_MAP.get(temp, 0)
        if await self._write_raw(self.uuids['temp'], self.create_control_packet(level)):
            self.state["target_temp"] = temp
            self.state["is_heating"] = (level > 0)
            if level > 0:
                self.state["last_heat_temp"] = temp
            self._notify_update()

    async def set_timer(self, hours: int):
        packet = bytes([0x00, 0xFF, 0x00, 0xFF]) if hours == 0 else self.create_control_packet(hours)
        if await self._write_raw(self.uuids['timer'], packet):
            self.state["timer_hours"] = hours
            self._notify_update()

    async def _write_raw(self, uuid, data, retry=3):
        if not self.is_connected:
            return False
        for _ in range(retry):
            try:
                await self.client.write_gatt_char(uuid, data)
                return True
            except Exception:
                await asyncio.sleep(0.5)
        return False

    def _on_temp_notify(self, sender, data):
        val = self.parse_packet(data)
        if val is not None and val in LEVEL_TEMP_MAP:
            temp = LEVEL_TEMP_MAP[val]
            self.state["current_temp"] = temp
            self.state["target_temp"] = temp
            self.state["is_heating"] = (val > 0)
            if val > 0:
                self.state["last_heat_temp"] = temp
            self._notify_update()

    def _on_timer_notify(self, sender, data):
        val = self.parse_packet(data)
        if val is not None:
            self.state["timer_hours"] = val
            self._notify_update()