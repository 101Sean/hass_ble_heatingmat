import asyncio
import logging
from bleak import BleakClient, BleakScanner
from .const import TEMP_LEVEL_MAP, LEVEL_TEMP_MAP, DEFAULT_HEAT_TEMP

_LOGGER = logging.getLogger(__name__)

class HeatingMatBLEManager:
    def __init__(self, hass, config_data):
        self.hass = hass
        self.mac_address = config_data["mac_address"].upper()
        self.init_packet = bytes.fromhex(config_data["init_packet"])
        
        self.uuids = {
            "service": config_data["service_uuid"].lower(),
            "set": config_data["char_set"].lower(),
            "temp": config_data["char_temp"].lower(),
            "timer": config_data["char_timer"].lower(),
        }
        
        self.client = None
        self.is_connected = False
        self.is_tracking = False # 기본 OFF 상태
        
        self._main_task = None
        self._ping_task = None
        
        self.state = {
            "target_temp": DEFAULT_HEAT_TEMP,
            "current_temp": DEFAULT_HEAT_TEMP,
            "is_heating": False,
            "timer_hours": 0,
            "last_heat_temp": DEFAULT_HEAT_TEMP
        }
        self.callbacks = []

    def register_callback(self, callback):
        self.callbacks.append(callback)

    def _notify_update(self):
        for cb in self.callbacks:
            try:
                cb()
            except Exception:
                pass

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
        if self.is_tracking: return
        self.is_tracking = True
        self._notify_update()
        self._main_task = self.hass.loop.create_task(self._run_tracking_loop())

    async def stop_tracking(self):
        self.is_tracking = False
        self._notify_update()
        if self._ping_task: self._ping_task.cancel()
        if self._main_task: self._main_task.cancel()
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False

    async def _run_tracking_loop(self):
        while self.is_tracking:
            if not self.is_connected:
                try:
                    _LOGGER.info("[BLE] 주변 기기 검색 중...")
                    device = await BleakScanner.find_device_by_address(self.mac_address, timeout=4.0)
                    if device:
                        await self._connect_device(device)
                except Exception as e:
                    _LOGGER.error(f"[BLE] 스캔 루프 에러: {e}")
            await asyncio.sleep(20.0) # RECONNECT_DELAY_MS

    async def _connect_device(self, device):
        self.client = BleakClient(device, disconnected_callback=self._on_disconnect)
        try:
            await self.client.connect(timeout=7.0)
            self.is_connected = True
            _LOGGER.info("[BLE] 연결 성공.")

            # GATT_WAIT_MS
            await asyncio.sleep(3.0)

            # 인증 패킷
            await self.client.write_gatt_char(self.uuids['set'], self.init_packet, response=True)
            await asyncio.sleep(1.0) # AUTH_WAIT_MS
            
            # 알림 등록 (Notify)
            await self.client.start_notify(self.uuids['temp'], self._on_temp_notify)
            await asyncio.sleep(0.5) # NOTIFY_STEP_MS
            
            await self.client.start_notify(self.uuids['timer'], self._on_timer_notify)
            await asyncio.sleep(1.0) # NOTIFY_READY_MS

            # 상태 요청 (0x12)
            await self._write_raw(self.uuids['temp'], self.create_control_packet(0x12))
            await asyncio.sleep(1.0) # POST_INIT_WAIT_MS

            # Ping 루프 시작
            self._ping_task = self.hass.loop.create_task(self._run_ping_loop())

        except Exception as e:
            _LOGGER.error(f"[BLE] 연결 오류: {e}")
            await self.client.disconnect()
            self.is_connected = False

    def _on_disconnect(self, client):
        _LOGGER.warning("[BLE] 연결 유실 감지.")
        self.is_connected = False
        if self._ping_task:
            self._ping_task.cancel()

    async def _run_ping_loop(self):
        while self.is_connected and self.is_tracking:
            await asyncio.sleep(30.0) # PING_INTERVAL_MS
            await self._write_raw(self.uuids['temp'], self.create_control_packet(0x12))

    async def set_power(self, is_on: bool):
        level = TEMP_LEVEL_MAP.get(self.state["last_heat_temp"], 3) if is_on else 0
        success = await self._write_raw(self.uuids['temp'], self.create_control_packet(level))
        
        if success:
            self.state["is_heating"] = is_on
            if not is_on:
                # 전원 끌 때 타이머를 1시간으로 설정
                self.state["timer_hours"] = 1
                await asyncio.sleep(0.5) # WRITE_DELAY_MS
                await self._write_raw(self.uuids['timer'], self.create_control_packet(1))
            self._notify_update()

    async def set_temperature(self, temp: int):
        level = TEMP_LEVEL_MAP.get(temp, 0)
        success = await self._write_raw(self.uuids['temp'], self.create_control_packet(level))
        if success:
            self.state["target_temp"] = temp
            self.state["is_heating"] = (level > 0)
            if level > 0:
                self.state["last_heat_temp"] = temp
            self._notify_update()

    async def set_timer(self, hours: int):
        # 0일 때 [0x00, 0xff, 0x00, 0xff] 전송
        packet = bytes([0x00, 0xFF, 0x00, 0xFF]) if hours == 0 else self.create_control_packet(hours)
        success = await self._write_raw(self.uuids['timer'], packet)
        if success:
            self.state["timer_hours"] = hours
            self._notify_update()

    async def _write_raw(self, uuid, data, retry=3):
        if not self.is_connected: return False
        for i in range(retry):
            try:
                await self.client.write_gatt_char(uuid, data)
                return True
            except Exception:
                await asyncio.sleep(0.5) # WRITE_DELAY_MS
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