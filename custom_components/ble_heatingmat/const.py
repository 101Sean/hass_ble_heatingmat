DOMAIN = "ble_heatingmat"

CONF_MAC_ADDRESS = "mac_address"
CONF_INIT_PACKET = "init_packet_hex"
CONF_SERVICE_UUID = "service_uuid"
CONF_CHAR_SET = "char_set_uuid"
CONF_CHAR_TEMP = "char_temp_uuid"
CONF_CHAR_TIMER = "char_timer_uuid"

TEMP_LEVEL_MAP = {0: 0, 36: 1, 37: 2, 38: 3, 39: 4, 40: 5, 41: 6, 42: 7}
LEVEL_TEMP_MAP = {0: 0, 1: 36, 2: 37, 3: 38, 4: 39, 5: 40, 6: 41, 7: 42}