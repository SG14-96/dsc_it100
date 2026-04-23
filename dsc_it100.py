"""
dsc_it100.py
============
Async Python interface for the DSC IT-100 Data Interface Module.

Usage example:
    import asyncio

    async def main():
        async with IT100('/dev/ttyUSB0', baud=9600) as panel:
            panel.on('zone_open', lambda pkt: print(f"Zone {pkt['parsed']['zone']} opened"))
            panel.on('partition_alarm', lambda pkt: print(f"ALARM on partition {pkt['parsed']['partition']}"))
            await panel.poll()           # verify comms
            await panel.request_status() # get full zone/partition snapshot
            await asyncio.sleep(30)

    asyncio.run(main())
"""

import asyncio
import contextlib
import serial
import logging
from typing import Callable, Optional

from constants import (
    EVENTS, BAUD_RATES, PANIC_PANIC,
    CMD_POLL, CMD_STATUS_REQUEST, CMD_LABELS_REQUEST, CMD_SET_TIME_DATE,
    CMD_COMMAND_OUTPUT, CMD_ARM_AWAY, CMD_ARM_STAY, CMD_ARM_NO_ENTRY_DELAY,
    CMD_ARM_WITH_CODE, CMD_DISARM, CMD_CODE_SEND, CMD_TRIGGER_PANIC,
    CMD_KEY_PRESSED, CMD_BAUD_RATE_CHANGE, CMD_GET_TEMP_SET_POINT,
    CMD_TEMPERATURE_CHANGE, CMD_SAVE_TEMP_SETTING, CMD_TIME_STAMP_CONTROL,
    CMD_TIME_BROADCAST_CONTROL, CMD_TEMP_BROADCAST_CONTROL,
    CMD_VIRTUAL_KEYPAD_CONTROL, CMD_CODE_REQUIRED,
)
from utils import build_packet, parse_packet, _safe_coro, _safe_call, _pad_code

logger = logging.getLogger(__name__)


class IT100:
    """
    Async interface to the DSC IT-100 Data Interface Module.

    Parameters
    ----------
    port : str
        Serial port, e.g. '/dev/ttyUSB0' or 'COM3'
    baud : int
        Baud rate (default 9600)
    timeout : float
        Read timeout in seconds (default 1.0)

    Usage example::

        async with IT100('/dev/ttyUSB0') as panel:
            panel.on('zone_open', lambda pkt: print(pkt['parsed']))
            await panel.request_status()
            await asyncio.sleep(10)

    Callbacks registered via ``on()`` may be plain functions or coroutines;
    both are dispatched non-blocking from the event loop.
    """

    def __init__(self, port: str, baud: int = 9600, timeout: float = 1.0):
        self.port    = port
        self.baud    = baud
        self.timeout = timeout

        # Event loop captured at construction time (reference methodology)
        self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        self._serial: Optional[serial.Serial] = None
        self._task:   Optional[asyncio.Task]  = None

        # Generic on()-style listeners: command_code -> list of callables
        self._listeners: dict[str, list[Callable]] = {}

        # Pending auto-code responses: partition -> access code string
        self._code_callbacks: dict[int, str] = {}

        # Typed event handlers (reference library pattern)
        self._handler_zone_update:      Optional[Callable] = None
        self._handler_partition_update: Optional[Callable] = None
        self._handler_general_update:   Optional[Callable] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self):
        """Open the serial port and start the background reader task."""
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
        )
        self._task = asyncio.create_task(self._reader_loop())
        logger.info('Connected to IT-100 on %s at %d baud', self.port, self.baud)

    async def disconnect(self):
        """Cancel the reader task and close the serial port."""
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._serial and self._serial.is_open:
            self._serial.close()
        logger.info('Disconnected from IT-100')

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable):
        """
        Register a callback for an IT-100 event.

        The event name can be a 3-digit command code (e.g. '650') or a
        friendly alias from the EVENTS dict.

        The callback receives the full packet dict returned by parse_packet::

            {
                'command':  '609',
                'data':     '001',
                'checksum': 'XX',
                'valid':    True,
                'parsed':   {'zone': 1},
            }

        The callback can be a plain function or a coroutine function;
        both are dispatched non-blocking via the event loop.

        Example::

            panel.on('zone_open', lambda pkt: print(pkt['parsed']['zone']))

            async def on_alarm(pkt):
                await notify(pkt)

            panel.on('partition_alarm', on_alarm)
        """
        code = EVENTS.get(event, event)
        self._listeners.setdefault(code, []).append(callback)

    def _emit(self, packet: dict):
        """Schedule all listeners for this command code on the event loop (non-blocking)."""
        code = packet['command']
        for cb in self._listeners.get(code, []) + self._listeners.get('*', []):
            if asyncio.iscoroutinefunction(cb):
                self._loop.create_task(
                    _safe_coro(cb, packet, code),
                    name=f'it100-cb-{code}',
                )
            else:
                self._loop.call_soon(_safe_call, cb, packet, code)

    # ------------------------------------------------------------------
    # Typed event handler properties (reference library pattern)
    # ------------------------------------------------------------------
    # Each handler receives (driver, packet) where packet is the dict
    # returned by parse_packet.  Handlers may be plain functions or
    # coroutines; both are awaited/called inside _invoke_handler.
    #
    # handler_zone_update      — fired when a zone field is present
    # handler_partition_update — fired when a partition field is present
    #                            (and no zone field)
    # handler_general_update   — fired for every incoming packet

    @property
    def handler_zone_update(self) -> Optional[Callable]:
        return self._handler_zone_update

    @handler_zone_update.setter
    def handler_zone_update(self, value: Optional[Callable]):
        self._handler_zone_update = value

    @property
    def handler_partition_update(self) -> Optional[Callable]:
        return self._handler_partition_update

    @handler_partition_update.setter
    def handler_partition_update(self, value: Optional[Callable]):
        self._handler_partition_update = value

    @property
    def handler_general_update(self) -> Optional[Callable]:
        return self._handler_general_update

    @handler_general_update.setter
    def handler_general_update(self, value: Optional[Callable]):
        self._handler_general_update = value

    async def _invoke_handler(self, handler: Optional[Callable], packet: dict) -> None:
        """Call a typed handler, supporting both plain functions and coroutines."""
        if handler is None:
            return
        if asyncio.iscoroutinefunction(handler):
            await handler(self, packet)
        else:
            handler(self, packet)

    # ------------------------------------------------------------------
    # Background serial reader
    # ------------------------------------------------------------------

    async def _reader_loop(self):
        buf = b''
        while True:
            try:
                chunk = await self._loop.run_in_executor(None, self._serial.read, 64)
                if not chunk:
                    continue
                buf += chunk
                while b'\r\n' in buf:
                    line, buf = buf.split(b'\r\n', 1)
                    logger.debug('RX raw bytes: %s', line.hex(' '))
                    raw = line.decode('latin-1').strip()
                    if raw:
                        await self._handle_raw(raw)
            except serial.SerialException as exc:
                logger.error('Serial read error: %s', exc)
                break
            except asyncio.CancelledError:
                break

    async def _handle_raw(self, raw: str):
        packet = parse_packet(raw)
        if packet is None:
            return
        if not packet['valid']:
            logger.warning('Bad checksum on packet: %r', raw)
            return

        parsed = packet['parsed']
        cmd    = packet['command']

        # Auto-handle code-required
        if cmd == CMD_CODE_REQUIRED:
            partition = parsed.get('partition')
            if partition and partition in self._code_callbacks:
                await self.send_code(self._code_callbacks.pop(partition))

        # Typed handlers: zone or partition, then always general
        if 'zone' in parsed:
            await self._invoke_handler(self._handler_zone_update, packet)
        elif 'partition' in parsed:
            await self._invoke_handler(self._handler_partition_update, packet)
        await self._invoke_handler(self._handler_general_update, packet)

        # Generic on() listeners (non-blocking fire-and-forget)
        self._emit(packet)

    # ------------------------------------------------------------------
    # Low-level send
    # ------------------------------------------------------------------

    async def _send(self, command: str, data: str = ''):
        packet = build_packet(command, data)
        await self._loop.run_in_executor(None, self._serial.write, packet)
        logger.debug('TX %r', packet)

    # ------------------------------------------------------------------
    # Application commands
    # ------------------------------------------------------------------

    async def poll(self):
        """Verify that the communication channel is alive (cmd 000)."""
        await self._send(CMD_POLL)

    async def request_status(self):
        """Request a full snapshot of all zones and partitions (cmd 001)."""
        await self._send(CMD_STATUS_REQUEST)

    async def request_labels(self):
        """Request all programmable labels (cmd 002)."""
        await self._send(CMD_LABELS_REQUEST)

    async def set_time_date(self, hh: int, mm: int, MM: int, DD: int, YY: int):
        """
        Set the panel clock (cmd 010).
        hh=hour(0-23), mm=minute(0-59), MM=month(1-12),
        DD=day(1-31), YY=year(00-99, 2-digit)
        """
        data = f'{hh:02d}{mm:02d}{MM:02d}{DD:02d}{YY:02d}'
        await self._send(CMD_SET_TIME_DATE, data)

    async def command_output(self, partition: int, output: int):
        """Activate a command output (1-4) on a partition (1-8) (cmd 020)."""
        await self._send(CMD_COMMAND_OUTPUT, f'{partition}{output}')

    async def arm_away(self, partition: int = 1):
        """Arm a partition in AWAY mode (cmd 030)."""
        await self._send(CMD_ARM_AWAY, str(partition))

    async def arm_stay(self, partition: int = 1):
        """Arm a partition in STAY mode (cmd 031)."""
        await self._send(CMD_ARM_STAY, str(partition))

    async def arm_no_entry_delay(self, partition: int = 1):
        """Arm a partition with no entry delay (cmd 032)."""
        await self._send(CMD_ARM_NO_ENTRY_DELAY, str(partition))

    async def arm_with_code(self, partition: int, code: str):
        """
        Arm a partition supplying the access code directly (cmd 033).
        4-digit codes are automatically padded to 6 digits.
        """
        code = _pad_code(code)
        await self._send(CMD_ARM_WITH_CODE, f'{partition}{code}')

    async def disarm(self, partition: int, code: str):
        """
        Disarm a partition (cmd 040). Also silences any active alarm.
        4-digit codes are automatically padded to 6 digits.
        """
        code = _pad_code(code)
        await self._send(CMD_DISARM, f'{partition}{code}')

    async def send_code(self, code: str):
        """
        Send an access code in response to a Code Required (900) event
        (cmd 200). 4-digit codes are automatically padded to 6 digits.
        """
        code = _pad_code(code)
        await self._send(CMD_CODE_SEND, code)

    async def trigger_panic(self, panic_type: str = PANIC_PANIC):
        """
        Trigger a panic alarm (cmd 060).
        panic_type: PANIC_FIRE='1', PANIC_AMBULANCE='2', PANIC_PANIC='3'
        """
        await self._send(CMD_TRIGGER_PANIC, panic_type)

    async def key_press(self, key: str, long_press: bool = False):
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
        await self._send(CMD_KEY_PRESSED, key)
        if long_press:
            await asyncio.sleep(1.5)
        await self._send(CMD_KEY_PRESSED, '^')   # break

    async def set_virtual_keypad(self, enabled: bool = True):
        """Enable or disable the virtual keypad (cmd 058)."""
        await self._send(CMD_VIRTUAL_KEYPAD_CONTROL, '1' if enabled else '0')

    async def set_time_stamp(self, enabled: bool):
        """Enable or disable timestamp prefix on all IT-100 commands (cmd 055)."""
        await self._send(CMD_TIME_STAMP_CONTROL, '1' if enabled else '0')

    async def set_time_broadcast(self, enabled: bool):
        """Enable or disable 4-minute time broadcasts (cmd 056)."""
        await self._send(CMD_TIME_BROADCAST_CONTROL, '1' if enabled else '0')

    async def set_temp_broadcast(self, enabled: bool):
        """Enable or disable 1-minute temperature broadcasts (cmd 057)."""
        await self._send(CMD_TEMP_BROADCAST_CONTROL, '1' if enabled else '0')

    async def change_baud_rate(self, baud: int):
        """
        Change the serial baud rate (cmd 080).
        Valid values: 9600, 19200, 38400, 57600, 115200
        """
        val = BAUD_RATES.get(baud)
        if val is None:
            raise ValueError(f'Unsupported baud rate: {baud}. Choose from {list(BAUD_RATES)}')
        await self._send(CMD_BAUD_RATE_CHANGE, val)

    async def get_temperature_set_point(self, thermostat: int):
        """Request thermostat set points (cmd 095). thermostat=1-4."""
        await self._send(CMD_GET_TEMP_SET_POINT, str(thermostat))

    async def change_temperature(self, thermostat: int, set_type: str,
                                 mode: str, value: int = 0):
        """
        Change a thermostat set point (cmd 096).

        thermostat : 1-4
        set_type   : 'C' (cool) or 'H' (heat)
        mode       : '+' increment, '-' decrement, '=' set absolute
        value      : temperature value (used with mode '='), e.g. 72
        """
        val_str = f'{value:03d}'
        await self._send(CMD_TEMPERATURE_CHANGE, f'{thermostat}{set_type}{mode}{val_str}')

    async def save_temperature(self, thermostat: int):
        """Save thermostat set points to Escort module (cmd 097)."""
        await self._send(CMD_SAVE_TEMP_SETTING, str(thermostat))

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def bypass_zone(self, zone: int, code: Optional[str] = None):
        """
        Bypass a zone using the virtual keypad sequence.
        If the panel requires a code, supply it via the code parameter.
        Zone must be 1-64.
        """
        await self.set_virtual_keypad(True)
        await self.key_press('*')
        await self.key_press('1')
        if code:
            for digit in _pad_code(code):
                await self.key_press(digit)
        for ch in f'{zone:02d}':
            await self.key_press(ch)

    async def arm_with_auto_code(self, partition: int, code: str,
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
        await self._send(_ARM_CMDS[mode], str(partition))


# ---------------------------------------------------------------------------
# Quick sanity check
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from utils import calculate_checksum, build_packet, parse_packet

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
