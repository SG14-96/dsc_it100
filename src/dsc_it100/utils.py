import logging
from typing import Callable, Optional

from .constants import (
    ARM_MODES, BAUD_RATES, ERROR_CODES,
    CMD_ZONE_OPEN, CMD_ZONE_RESTORED, CMD_ZONE_FAULT, CMD_ZONE_FAULT_RESTORE,
    CMD_ZONE_ALARM, CMD_ZONE_ALARM_RESTORE, CMD_ZONE_TAMPER, CMD_ZONE_TAMPER_RESTORE,
    CMD_PARTITION_READY, CMD_PARTITION_NOT_READY, CMD_PARTITION_READY_FORCE,
    CMD_PARTITION_IN_ALARM, CMD_PARTITION_DISARMED, CMD_EXIT_DELAY, CMD_ENTRY_DELAY,
    CMD_KEYPAD_LOCKOUT, CMD_KEYPAD_BLANKING, CMD_COMMAND_OUTPUT_PROGRESS,
    CMD_INVALID_ACCESS_CODE, CMD_FUNCTION_NOT_AVAILABLE, CMD_FAIL_TO_ARM,
    CMD_PARTITION_BUSY, CMD_SPECIAL_CLOSING, CMD_PARTIAL_CLOSING, CMD_SPECIAL_OPENING,
    CMD_TROUBLE_LED_ON, CMD_TROUBLE_LED_OFF,
    CMD_PARTITION_ARMED, CMD_USER_CLOSING, CMD_USER_OPENING,
    CMD_CODE_REQUIRED, CMD_SYSTEM_ERROR, CMD_COMMAND_ACK, CMD_SOFTWARE_VERSION,
    CMD_LED_STATUS, CMD_LCD_UPDATE, CMD_BROADCAST_LABELS, CMD_BAUD_RATE_SET,
    CMD_INDOOR_TEMP, CMD_OUTDOOR_TEMP, CMD_THERMOSTAT_SET_POINTS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Checksum helpers
# ---------------------------------------------------------------------------

def calculate_checksum(command: str, data: str = '') -> str:
    """
    Sum the ASCII (hex) values of every character in command+data,
    truncate to 8 bits, return as two uppercase hex characters.
    """
    total = sum(ord(c) for c in (command + data)) & 0xFF
    return f'{total:02X}'


def build_packet(command: str, data: str = '') -> bytes:
    """Return a fully-formed IT-100 packet ready to write to the serial port."""
    checksum = calculate_checksum(command, data)
    packet = f'{command}{data}{checksum}\r\n'
    return packet.encode('ascii')


def verify_checksum(raw: str) -> bool:
    """Verify the checksum of a raw packet string (CR/LF is stripped if present)."""
    raw = raw.rstrip('\r\n')
    if len(raw) < 5:   # 3 cmd + 2 checksum minimum
        return False
    body     = raw[:-2]
    received = raw[-2:].upper()
    expected = calculate_checksum(body)
    return received == expected


# ---------------------------------------------------------------------------
# Packet parser
# ---------------------------------------------------------------------------

def parse_packet(raw: str) -> Optional[dict]:
    """
    Parse a raw IT-100 response string into a dict:
        {
            'command': '650',
            'data':    '1',
            'checksum':'CC',
            'valid':   True,
            'parsed':  { ... command-specific fields ... }
        }
    Returns None if the packet is too short to parse.
    """
    raw = raw.strip()
    if len(raw) < 5:
        return None

    command  = raw[:3]
    checksum = raw[-2:]
    data     = raw[3:-2]

    return {
        'command':  command,
        'data':     data,
        'checksum': checksum,
        'valid':    verify_checksum(raw),
        'parsed':   _parse_data(command, data),
    }


def _parse_data(command: str, data: str) -> dict:
    """Return command-specific parsed fields."""
    LED_NAMES  = {
        '1': 'ready', '2': 'armed',      '3': 'memory',
        '4': 'bypass', '5': 'trouble',   '6': 'program',
        '7': 'fire',   '8': 'backlight', '9': 'ac',
    }
    STATE_NAMES     = {'0': 'off', '1': 'on', '2': 'flashing'}
    BAUD_RATE_CODES = {'0': 9600, '1': 19200, '2': 38400, '3': 57600, '4': 115200}

    ZONE_ONLY_CMDS = (CMD_ZONE_OPEN, CMD_ZONE_RESTORED,
                      CMD_ZONE_FAULT, CMD_ZONE_FAULT_RESTORE)
    ZONE_PARTITION_CMDS = (CMD_ZONE_ALARM, CMD_ZONE_ALARM_RESTORE,
                           CMD_ZONE_TAMPER, CMD_ZONE_TAMPER_RESTORE)
    PARTITION_ONLY_CMDS = (
        CMD_PARTITION_READY, CMD_PARTITION_NOT_READY, CMD_PARTITION_READY_FORCE,
        CMD_PARTITION_IN_ALARM, CMD_PARTITION_DISARMED, CMD_EXIT_DELAY,
        CMD_ENTRY_DELAY, CMD_KEYPAD_LOCKOUT, CMD_KEYPAD_BLANKING,
        CMD_COMMAND_OUTPUT_PROGRESS, CMD_INVALID_ACCESS_CODE,
        CMD_FUNCTION_NOT_AVAILABLE, CMD_FAIL_TO_ARM, CMD_PARTITION_BUSY,
        CMD_SPECIAL_CLOSING, CMD_PARTIAL_CLOSING, CMD_SPECIAL_OPENING,
        CMD_TROUBLE_LED_ON, CMD_TROUBLE_LED_OFF,
    )
    USER_CMDS = (CMD_USER_CLOSING, CMD_USER_OPENING)
    TEMP_CMDS = (CMD_INDOOR_TEMP, CMD_OUTDOOR_TEMP)

    def _zone_only(d):        return {'zone': int(d) if d.isdigit() else d}
    def _partition_zone(d):   return {'partition': int(d[0]), 'zone': int(d[1:])} if len(d) >= 4 else {}
    def _partition_only(d):   return {'partition': int(d[0]) if d else None}
    def _partition_armed(d):  return {'partition': int(d[0]), 'mode': ARM_MODES.get(d[1], d[1])} if len(d) >= 2 else {}
    def _user_cmd(d):         return {'partition': int(d[0]), 'user': int(d[1:])} if len(d) >= 5 else {}
    def _code_required(d):    return {'partition': int(d[0]), 'code_length': int(d[1])} if len(d) >= 2 else {}
    def _system_error(d):     return {'error_code': d, 'error_description': ERROR_CODES.get(d, 'Unknown error')}
    def _command_ack(d):      return {'acknowledged_command': d}
    def _software_ver(d):     return {'version': d[0:2], 'sub_version': d[2:4]} if len(d) >= 4 else {}
    def _led_status(d):       return {'led': LED_NAMES.get(d[0], d[0]), 'state': STATE_NAMES.get(d[1], d[1])} if len(d) >= 2 else {}
    def _lcd_update(d):       return {'line': int(d[0]), 'column': int(d[1:3]), 'char_count': int(d[3:5]), 'text': d[5:]} if len(d) >= 6 else {}
    # Per spec: 3 ASCII digit label number (001-151) + 32 bytes label text (space-padded).
    def _broadcast_labels(d): return {'label_number': int(d[0:3]) if d[0:3].isdigit() else None, 'label': d[3:].strip('\x00 \t')} if len(d) >= 3 else {}
    def _baud_rate_set(d):    return {'baud_rate': BAUD_RATE_CODES.get(d, d)}
    def _temperature(d):      return {'thermostat': int(d[0:2]), 'temperature': int(d[2:])} if len(d) >= 4 else {}
    def _thermostat_sp(d):    return {'thermostat': int(d[0:2]), 'cool_set': int(d[2:5]), 'heat_set': int(d[5:8])} if len(d) >= 8 else {}

    dispatch: dict[str, Callable[[str], dict]] = {
        **{cmd: _zone_only      for cmd in ZONE_ONLY_CMDS},
        **{cmd: _partition_zone for cmd in ZONE_PARTITION_CMDS},
        **{cmd: _partition_only for cmd in PARTITION_ONLY_CMDS},
        CMD_PARTITION_ARMED:       _partition_armed,
        **{cmd: _user_cmd       for cmd in USER_CMDS},
        CMD_CODE_REQUIRED:         _code_required,
        CMD_SYSTEM_ERROR:          _system_error,
        CMD_COMMAND_ACK:           _command_ack,
        CMD_SOFTWARE_VERSION:      _software_ver,
        CMD_LED_STATUS:            _led_status,
        CMD_LCD_UPDATE:            _lcd_update,
        CMD_BROADCAST_LABELS:      _broadcast_labels,
        CMD_BAUD_RATE_SET:         _baud_rate_set,
        **{cmd: _temperature    for cmd in TEMP_CMDS},
        CMD_THERMOSTAT_SET_POINTS: _thermostat_sp,
    }

    return dispatch.get(command, lambda _: {})(data)


# ---------------------------------------------------------------------------
# Callback dispatch helpers
# ---------------------------------------------------------------------------

async def _safe_coro(cb: Callable, packet: dict, code: str):
    try:
        await cb(packet)
    except Exception as exc:
        logger.error('Listener error for %s: %s', code, exc)


def _safe_call(cb: Callable, packet: dict, code: str):
    try:
        cb(packet)
    except Exception as exc:
        logger.error('Listener error for %s: %s', code, exc)


# ---------------------------------------------------------------------------
# Code padding
# ---------------------------------------------------------------------------

def _pad_code(code: str) -> str:
    """Pad a 4-digit code to 6 digits as required by the protocol."""
    code = code.strip()
    if len(code) == 4:
        return code + '00'
    if len(code) == 6:
        return code
    raise ValueError(f'Access code must be 4 or 6 digits, got {len(code)}: {code!r}')
