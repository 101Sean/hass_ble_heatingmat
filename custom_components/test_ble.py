import asyncio
import logging
from custom_components.ble_heatingmat.ble_manager import HeatingMatBLEManager

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

class MockHass:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

def on_state_update():
    print(f"\n[매트 상태 업데이트] {manager.state}\n")

async def main():
    mac_address = "EF:E1:70:4D:03:87" 
    init_packet_hex = "a55affff"

    mock_hass = MockHass()
    
    global manager
    manager = HeatingMatBLEManager(mock_hass, mac_address, init_packet_hex)
    manager.register_callback(on_state_update)

    print("\n블루투스 추적 및 스캔 시작")
    await manager.start_tracking()

    print("\n기기 연결 대기 중")
    while not manager.is_connected:
        await asyncio.sleep(1)
        
    print("\n연결 성공! 5초 후 전원을 켜고 40도로 설정합니다")
    await asyncio.sleep(5)
    
    await manager.set_power(True)
    await asyncio.sleep(1)
    await manager.set_temperature(40)

    print("\n30초 동안 매트의 온도 변화를 수신합니다")
    await asyncio.sleep(30)

    print("\n추적 종료 및 연결 해제")
    await manager.stop_tracking()
    print("테스트 완료!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n사용자에 의해 강제 종료되었습니다.")