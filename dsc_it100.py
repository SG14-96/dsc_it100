"""
dsc_it100.py
============
Python interface for the DSC IT-100 Data Interface Module.

Usage example:
    panel = IT100('/dev/ttyUSB0', baud=9600)
    panel.connect()
    panel.poll()                        # verify comms
    panel.request_status()              # get full zone/partition snapshot
    panel.arm_away(partition=1)
    panel.disarm(partition=1, code='1234')
    panel.disconnect()

Event callbacks:
    panel.on('zone_open', lambda data: print(f"Zone {data['zone']} opened"))
    panel.on('partition_alarm', lambda data: print(f"ALARM on partition {data['partition']}"))
"""

import serial
import threading
import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Command constants
# ---------------------------------------------------------------------------

# Application → IT-100
CMD_POLL                    = '000'
CMD_STATUS_REQUEST          = '001'
CMD_LABELS_REQUEST          = '002'
CMD_SET_TIME_DATE           = '010'
CMD_COMMAND_OUTPUT          = '020'
CMD_ARM_AWAY                = '030'
CMD_ARM_STAY                = '031'
CMD_ARM_NO_ENTRY_DELAY      = '032'
CMD_ARM_WITH_CODE           = '033'
CMD_DISARM                  = '040'
CMD_TIME_STAMP_CONTROL      = '055'
CMD_TIME_BROADCAST_CONTROL  = '056'
CMD_TEMP_BROADCAST_CONTROL  = '057'
CMD_VIRTUAL_KEYPAD_CONTROL  = '058'
CMD_TRIGGER_PANIC           = '060'
CMD_KEY_PRESSED             = '070'
CMD_BAUD_RATE_CHANGE        = '080'
CMD_GET_TEMP_SET_POINT      = '095'
CMD_TEMPERATURE_CHANGE      = '096'
CMD_SAVE_TEMP_SETTING       = '097'
CMD_CODE_SEND               = '200'

# IT-100 → Application
CMD_COMMAND_ACK             = '500'
CMD_COMMAND_ERROR           = '501'
CMD_SYSTEM_ERROR            = '502'
CMD_TIME_DATE_BROADCAST     = '550'
CMD_RING_DETECTED           = '560'
CMD_INDOOR_TEMP             = '561'
CMD_OUTDOOR_TEMP            = '562'
CMD_THERMOSTAT_SET_POINTS   = '563'
CMD_BROADCAST_LABELS        = '570'
CMD_BAUD_RATE_SET           = '580'
CMD_ZONE_ALARM              = '601'
CMD_ZONE_ALARM_RESTORE      = '602'
CMD_ZONE_TAMPER             = '603'
CMD_ZONE_TAMPER_RESTORE     = '604'
CMD_ZONE_FAULT              = '605'
CMD_ZONE_FAULT_RESTORE      = '606'
CMD_ZONE_OPEN               = '609'
CMD_ZONE_RESTORED           = '610'
CMD_DURESS_ALARM            = '620'
CMD_F_KEY_ALARM             = '621'
CMD_F_KEY_RESTORAL          = '622'
CMD_A_KEY_ALARM             = '623'
CMD_A_KEY_RESTORAL          = '624'
CMD_P_KEY_ALARM             = '625'
CMD_P_KEY_RESTORAL          = '626'
CMD_AUX_INPUT_ALARM         = '631'
CMD_AUX_INPUT_RESTORE       = '632'
CMD_PARTITION_READY         = '650'
CMD_PARTITION_NOT_READY     = '651'
CMD_PARTITION_ARMED         = '652'
CMD_PARTITION_READY_FORCE   = '653'
CMD_PARTITION_IN_ALARM      = '654'
CMD_PARTITION_DISARMED      = '655'
CMD_EXIT_DELAY              = '656'
CMD_ENTRY_DELAY             = '657'
CMD_KEYPAD_LOCKOUT          = '658'
CMD_KEYPAD_BLANKING         = '659'
CMD_COMMAND_OUTPUT_PROGRESS = '660'
CMD_INVALID_ACCESS_CODE     = '670'
CMD_FUNCTION_NOT_AVAILABLE  = '671'
CMD_FAIL_TO_ARM             = '672'
CMD_PARTITION_BUSY          = '673'
CMD_USER_CLOSING            = '700'
CMD_SPECIAL_CLOSING         = '701'
CMD_PARTIAL_CLOSING         = '702'
CMD_USER_OPENING            = '750'
CMD_SPECIAL_OPENING         = '751'
CMD_PANEL_BATTERY_TROUBLE   = '800'
CMD_PANEL_BATTERY_RESTORE   = '801'
CMD_PANEL_AC_TROUBLE        = '802'
CMD_PANEL_AC_RESTORE        = '803'
CMD_SYSTEM_BELL_TROUBLE     = '806'
CMD_SYSTEM_BELL_RESTORE     = '807'
CMD_TLM_LINE1_TROUBLE       = '810'
CMD_TLM_LINE1_RESTORE       = '811'
CMD_TLM_LINE2_TROUBLE       = '812'
CMD_TLM_LINE2_RESTORE       = '813'
CMD_FTC_TROUBLE             = '814'
CMD_BUFFER_NEAR_FULL        = '816'
CMD_WIRELESS_LOW_BATTERY    = '821'
CMD_WIRELESS_LOW_RESTORE    = '822'
CMD_WKEY_LOW_BATTERY        = '825'
CMD_WKEY_LOW_RESTORE        = '826'
CMD_HANDHELD_LOW_BATTERY    = '827'
CMD_HANDHELD_LOW_RESTORE    = '828'
CMD_GENERAL_SYSTEM_TAMPER   = '829'
CMD_GENERAL_TAMPER_RESTORE  = '830'
CMD_HOME_AUTO_TROUBLE       = '831'
CMD_HOME_AUTO_RESTORE       = '832'
CMD_TROUBLE_LED_ON          = '840'
CMD_TROUBLE_LED_OFF         = '841'
CMD_FIRE_TROUBLE            = '842'
CMD_FIRE_TROUBLE_RESTORE    = '843'
CMD_CODE_REQUIRED           = '900'
CMD_LCD_UPDATE              = '901'
CMD_LCD_CURSOR              = '902'
CMD_LED_STATUS              = '903'
CMD_BEEP_STATUS             = '904'
CMD_TONE_STATUS             = '905'
CMD_BUZZER_STATUS           = '906'
CMD_DOOR_CHIME              = '907'
CMD_SOFTWARE_VERSION        = '908'

# ---------------------------------------------------------------------------
# Friendly event name aliases
# ---------------------------------------------------------------------------

EVENTS = {
    # Zones
    'zone_open':            CMD_ZONE_OPEN,
    'zone_restored':        CMD_ZONE_RESTORED,
    'zone_alarm':           CMD_ZONE_ALARM,
    'zone_alarm_restore':   CMD_ZONE_ALARM_RESTORE,
    'zone_tamper':          CMD_ZONE_TAMPER,
    'zone_tamper_restore':  CMD_ZONE_TAMPER_RESTORE,
    'zone_fault':           CMD_ZONE_FAULT,
    'zone_fault_restore':   CMD_ZONE_FAULT_RESTORE,

    # Partitions
    'partition_ready':      CMD_PARTITION_READY,
    'partition_not_ready':  CMD_PARTITION_NOT_READY,
    'partition_armed':      CMD_PARTITION_ARMED,
    'partition_alarm':      CMD_PARTITION_IN_ALARM,
    'partition_disarmed':   CMD_PARTITION_DISARMED,
    'exit_delay':           CMD_EXIT_DELAY,
    'entry_delay':          CMD_ENTRY_DELAY,
    'keypad_lockout':       CMD_KEYPAD_LOCKOUT,
    'fail_to_arm':          CMD_FAIL_TO_ARM,

    # Open/close
    'user_closing':         CMD_USER_CLOSING,
    'user_opening':         CMD_USER_OPENING,
    'special_closing':      CMD_SPECIAL_CLOSING,
    'special_opening':      CMD_SPECIAL_OPENING,

    # Trouble / system
    'panel_battery_trouble':CMD_PANEL_BATTERY_TROUBLE,
    'panel_battery_restore':CMD_PANEL_BATTERY_RESTORE,
    'panel_ac_trouble':     CMD_PANEL_AC_TROUBLE,
    'panel_ac_restore':     CMD_PANEL_AC_RESTORE,
    'system_error':         CMD_SYSTEM_ERROR,
    'code_required':        CMD_CODE_REQUIRED,

    # Virtual keypad
    'lcd_update':           CMD_LCD_UPDATE,
    'lcd_cursor':           CMD_LCD_CURSOR,
    'led_status':           CMD_LED_STATUS,

    # Labels
    'broadcast_labels':     CMD_BROADCAST_LABELS,

    # Misc
    'software_version':     CMD_SOFTWARE_VERSION,
    'command_ack':          CMD_COMMAND_ACK,
    'command_error':        CMD_COMMAND_ERROR,
}

# Error code descriptions (command 502)
ERROR_CODES = {
    '017': 'Keybus Busy - Installer Mode',
    '021': 'Requested Partition is out of Range',
    '023': 'Partition is not Armed',
    '024': 'Partition is not Ready to Arm',
    '026': 'User Code Not Required',
    '028': 'Virtual Keypad is Disabled',
    '029': 'Not Valid Parameter',
    '030': 'Keypad Does Not Come Out of Blank Mode',
    '031': 'IT-100 is already in Thermostat Menu',
    '032': 'IT-100 is NOT in Thermostat Menu',
    '033': 'No response from thermostat or Escort module',
}

# Arm mode descriptions (command 652)
ARM_MODES = {
    '0': 'Away',
    '1': 'Stay',
    '2': 'Away, No Delay',
    '3': 'Stay, No Delay',
}

# Panic types (command 060)
PANIC_FIRE       = '1'
PANIC_AMBULANCE  = '2'
PANIC_PANIC      = '3'

# Baud rate values (command 080)
BAUD_RATES = {
    9600:   '0',
    19200:  '1',
    38400:  '2',
    57600:  '3',
    115200: '4',
}


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
    body     = raw[:-2]   # everything except the last 2 checksum chars
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

    result = {
        'command':  command,
        'data':     data,
        'checksum': checksum,
        'valid':    verify_checksum(raw),
        'parsed':   _parse_data(command, data),
    }
    return result


def _parse_data(command: str, data: str) -> dict:
    """Return command-specific parsed fields."""
    # --- Lookup tables ---
    LED_NAMES  = {
        '1': 'ready', '2': 'armed',     '3': 'memory',
        '4': 'bypass', '5': 'trouble',  '6': 'program',
        '7': 'fire',   '8': 'backlight', '9': 'ac',
    }
    STATE_NAMES     = {'0': 'off', '1': 'on', '2': 'flashing'}
    BAUD_RATE_CODES = {'0': 9600, '1': 19200, '2': 38400, '3': 57600, '4': 115200}

    # --- Command groups ---
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

    # --- Per-command parsers ---
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
# Main IT100 class
# ---------------------------------------------------------------------------

class IT100:
    """
    Interface to the DSC IT-100 Data Interface Module.

    Parameters
    ----------
    port : str
        Serial port, e.g. '/dev/ttyUSB0' or 'COM3'
    baud : int
        Baud rate (default 9600)
    timeout : float
        Read timeout in seconds (default 1.0)
    """

    def __init__(self, port: str, baud: int = 9600, timeout: float = 1.0):
        self.port    = port
        self.baud    = baud
        self.timeout = timeout

        self._serial:  Optional[serial.Serial] = None
        self._thread:  Optional[threading.Thread] = None
        self._running  = False
        self._lock     = threading.Lock()

        # Event listeners: command_code -> list of callables
        self._listeners: dict[str, list[Callable]] = {}

        # Pending auto-code responses: partition -> access code string
        self._code_callbacks: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self):
        """Open the serial port and start the background reader thread."""
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
        )
        self._running = True
        self._thread  = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()
        logger.info(f'Connected to IT-100 on {self.port} at {self.baud} baud')

    def disconnect(self):
        """Stop the reader thread and close the serial port."""
        self._running = False
        if self._serial and self._serial.is_open:
            self._serial.close()
        logger.info('Disconnected from IT-100')

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable):
        """
        Register a callback for an IT-100 event.

        The event name can be a 3-digit command code (e.g. '650') or a
        friendly alias from the EVENTS dict below.

        The callback receives the full packet dict returned by parse_packet:
            {
                'command':  '609',
                'data':     '001',
                'checksum': 'XX',
                'valid':    True,
                'parsed':   {'zone': 1},
            }

        Example:
            panel.on('zone_open', lambda pkt: print(pkt['parsed']['zone']))
            panel.on('609',       lambda pkt: print(pkt['parsed']['zone']))
        """
        code = EVENTS.get(event, event)   # resolve alias → code
        self._listeners.setdefault(code, []).append(callback)

    def _emit(self, packet: dict):
        """Fire all listeners registered for this command code, then wildcards."""
        code = packet['command']
        for cb in self._listeners.get(code, []) + self._listeners.get('*', []):
            try:
                cb(packet)
            except Exception as exc:
                logger.error('Listener error for %s: %s', code, exc)

    # ------------------------------------------------------------------
    # Background serial reader
    # ------------------------------------------------------------------

    def _reader_loop(self):
        buf = b''
        while self._running:
            try:
                chunk = self._serial.read(64)
                if not chunk:
                    continue
                buf += chunk
                while b'\r\n' in buf:
                    line, buf = buf.split(b'\r\n', 1)
                    logger.debug('RX raw bytes: %s', line.hex(' '))
                    raw = line.decode('latin-1').strip()
                    if raw:
                        self._handle_raw(raw)
            except serial.SerialException as exc:
                logger.error(f'Serial read error: {exc}')
                break

    def _handle_raw(self, raw: str):
        packet = parse_packet(raw)
        if packet is None:
            return
        if not packet['valid']:
            logger.warning(f'Bad checksum on packet: {raw!r}')
            return

        # Auto-handle code-required
        if packet['command'] == CMD_CODE_REQUIRED:
            partition = packet['parsed'].get('partition')
            if partition and partition in self._code_callbacks:
                self.send_code(self._code_callbacks.pop(partition))

        self._emit(packet)

    # ------------------------------------------------------------------
    # Low-level send
    # ------------------------------------------------------------------

    def _send(self, command: str, data: str = ''):
        packet = build_packet(command, data)
        with self._lock:
            self._serial.write(packet)
        logger.debug(f'TX {packet!r}')

    # ------------------------------------------------------------------
    # Application commands
    # ------------------------------------------------------------------

    def poll(self):
        """Verify that the communication channel is alive (cmd 000)."""
        self._send(CMD_POLL)

    def request_status(self):
        """Request a full snapshot of all zones and partitions (cmd 001)."""
        self._send(CMD_STATUS_REQUEST)

    def request_labels(self):
        """Request all programmable labels (cmd 002)."""
        self._send(CMD_LABELS_REQUEST)

    def set_time_date(self, hh: int, mm: int, MM: int, DD: int, YY: int):
        """
        Set the panel clock (cmd 010).
        hh=hour(0-23), mm=minute(0-59), MM=month(1-12),
        DD=day(1-31), YY=year(00-99, 2-digit)
        """
        data = f'{hh:02d}{mm:02d}{MM:02d}{DD:02d}{YY:02d}'
        self._send(CMD_SET_TIME_DATE, data)

    def command_output(self, partition: int, output: int):
        """Activate a command output (1-4) on a partition (1-8) (cmd 020)."""
        self._send(CMD_COMMAND_OUTPUT, f'{partition}{output}')

    def arm_away(self, partition: int = 1):
        """Arm a partition in AWAY mode (cmd 030)."""
        self._send(CMD_ARM_AWAY, str(partition))

    def arm_stay(self, partition: int = 1):
        """Arm a partition in STAY mode (cmd 031)."""
        self._send(CMD_ARM_STAY, str(partition))

    def arm_no_entry_delay(self, partition: int = 1):
        """Arm a partition with no entry delay (cmd 032)."""
        self._send(CMD_ARM_NO_ENTRY_DELAY, str(partition))

    def arm_with_code(self, partition: int, code: str):
        """
        Arm a partition supplying the access code directly (cmd 033).
        4-digit codes are automatically padded to 6 digits.
        """
        code = _pad_code(code)
        self._send(CMD_ARM_WITH_CODE, f'{partition}{code}')

    def disarm(self, partition: int, code: str):
        """
        Disarm a partition (cmd 040). Also silences any active alarm.
        4-digit codes are automatically padded to 6 digits.
        """
        code = _pad_code(code)
        self._send(CMD_DISARM, f'{partition}{code}')

    def send_code(self, code: str):
        """
        Send an access code in response to a Code Required (900) event
        (cmd 200). 4-digit codes are automatically padded to 6 digits.
        """
        code = _pad_code(code)
        self._send(CMD_CODE_SEND, code)

    def trigger_panic(self, panic_type: str = PANIC_PANIC):
        """
        Trigger a panic alarm (cmd 060).
        panic_type: PANIC_FIRE='1', PANIC_AMBULANCE='2', PANIC_PANIC='3'
        """
        self._send(CMD_TRIGGER_PANIC, panic_type)

    def key_press(self, key: str, long_press: bool = False):
        """
        Simulate a keypad keypress (cmd 070). Requires virtual keypad enabled.
        For a long press, set long_press=True (adds 1.5s delay before break).

        Key values:
            Digits    : '0'-'9'
            Star/Hash : '*', '#'
            FAP       : 'F', 'A', 'P'
            Function  : 'a'-'e'
            Arrows    : '<', '>'
            Both      : '='
            Break     : '^'
        """
        self._send(CMD_KEY_PRESSED, key)
        if long_press:
            time.sleep(1.5)
        self._send(CMD_KEY_PRESSED, '^')   # break

    def set_virtual_keypad(self, enabled: bool = True):
        """Enable or disable the virtual keypad (cmd 058)."""
        self._send(CMD_VIRTUAL_KEYPAD_CONTROL, '1' if enabled else '0')

    def set_time_stamp(self, enabled: bool):
        """Enable or disable timestamp prefix on all IT-100 commands (cmd 055)."""
        self._send(CMD_TIME_STAMP_CONTROL, '1' if enabled else '0')

    def set_time_broadcast(self, enabled: bool):
        """Enable or disable 4-minute time broadcasts (cmd 056)."""
        self._send(CMD_TIME_BROADCAST_CONTROL, '1' if enabled else '0')

    def set_temp_broadcast(self, enabled: bool):
        """Enable or disable 1-minute temperature broadcasts (cmd 057)."""
        self._send(CMD_TEMP_BROADCAST_CONTROL, '1' if enabled else '0')

    def change_baud_rate(self, baud: int):
        """
        Change the serial baud rate (cmd 080).
        Valid values: 9600, 19200, 38400, 57600, 115200
        """
        val = BAUD_RATES.get(baud)
        if val is None:
            raise ValueError(f'Unsupported baud rate: {baud}. Choose from {list(BAUD_RATES)}')
        self._send(CMD_BAUD_RATE_CHANGE, val)

    def get_temperature_set_point(self, thermostat: int):
        """Request thermostat set points (cmd 095). thermostat=1-4."""
        self._send(CMD_GET_TEMP_SET_POINT, str(thermostat))

    def change_temperature(self, thermostat: int, set_type: str,
                           mode: str, value: int = 0):
        """
        Change a thermostat set point (cmd 096).

        thermostat : 1-4
        set_type   : 'C' (cool) or 'H' (heat)
        mode       : '+' increment, '-' decrement, '=' set absolute
        value      : temperature value (used with mode '='), e.g. 72
        """
        val_str = f'{value:03d}'
        self._send(CMD_TEMPERATURE_CHANGE, f'{thermostat}{set_type}{mode}{val_str}')

    def save_temperature(self, thermostat: int):
        """Save thermostat set points to Escort module (cmd 097)."""
        self._send(CMD_SAVE_TEMP_SETTING, str(thermostat))

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def bypass_zone(self, zone: int, code: Optional[str] = None):
        """
        Bypass a zone using the virtual keypad sequence.
        If the panel requires a code, supply it via the code parameter.
        Zone must be 1-64.
        """
        self.set_virtual_keypad(True)
        self.key_press('*')
        self.key_press('1')
        if code:
            # Enter code digit by digit
            for digit in _pad_code(code):
                self.key_press(digit)
        for ch in f'{zone:02d}':
            self.key_press(ch)

    def arm_with_auto_code(self, partition: int, code: str,
                           mode: str = 'stay'):
        """
        Arm a partition and automatically respond to Code Required (900)
        events with the supplied code.

        mode: 'away', 'stay', 'no_delay'
        """
        _ARM_CMDS = {
            'away':     CMD_ARM_AWAY,
            'stay':     CMD_ARM_STAY,
            'no_delay': CMD_ARM_NO_ENTRY_DELAY,
        }
        if mode not in _ARM_CMDS:
            raise ValueError(f"Unknown mode: {mode!r}. Use 'away', 'stay', or 'no_delay'.")
        self._code_callbacks[partition] = code
        self._send(_ARM_CMDS[mode], str(partition))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pad_code(code: str) -> str:
    """Pad a 4-digit code to 6 digits as required by the protocol."""
    code = code.strip()
    if len(code) == 4:
        return code + '00'
    if len(code) == 6:
        return code
    raise ValueError(f'Access code must be 4 or 6 digits, got {len(code)}: {code!r}')


# ---------------------------------------------------------------------------
# Quick sanity check
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # Test checksum calculation with the example from the manual:
    # Partition Alarm on partition 3 → command=654, data=3
    # Expected checksum: D2
    cmd, data = '654', '3'
    ck = calculate_checksum(cmd, data)
    assert ck == 'D2', f'Checksum mismatch: {ck}'
    print(f'Checksum OK: {cmd}{data}{ck}\\r\\n')

    # Test packet building
    pkt = build_packet('000')   # Poll
    print(f'Poll packet: {pkt!r}')

    # Test packet parsing
    pkt_str = '6501CC'   # Partition Ready, partition 1
    parsed = parse_packet(pkt_str)
    print(f'Parsed: {parsed}')

    print('All self-tests passed.')
