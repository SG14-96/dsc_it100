"""
simple.py
---------
Demonstrates the IT100 typed handler pattern.

Mirrors the structure from examples/simple.py in the kostko/dsc-it100 repo:
  instantiate driver → set handler properties → connect → run forever

Run (from repo root, with package installed):
    python examples/simple.py
"""

import asyncio
import time
import logging

from dsc_it100 import IT100
from dsc_it100.constants import (
    CMD_ZONE_OPEN, CMD_ZONE_RESTORED,
    CMD_ZONE_ALARM, CMD_ZONE_ALARM_RESTORE,
    CMD_ZONE_TAMPER, CMD_ZONE_TAMPER_RESTORE,
    CMD_PARTITION_READY, CMD_PARTITION_NOT_READY,
    CMD_PARTITION_ARMED, CMD_PARTITION_DISARMED,
    CMD_PARTITION_IN_ALARM,
    CMD_EXIT_DELAY, CMD_ENTRY_DELAY,
    CMD_KEYPAD_LOCKOUT, CMD_FAIL_TO_ARM,
    CMD_USER_CLOSING, CMD_USER_OPENING,
    CMD_CODE_REQUIRED,
    CMD_LCD_UPDATE, CMD_LED_STATUS,
    CMD_SOFTWARE_VERSION,
    CMD_COMMAND_ACK, CMD_COMMAND_ERROR, CMD_SYSTEM_ERROR,
    CMD_PANEL_BATTERY_TROUBLE, CMD_PANEL_BATTERY_RESTORE,
    CMD_PANEL_AC_TROUBLE, CMD_PANEL_AC_RESTORE,
    CMD_BROADCAST_LABELS,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.disable(logging.CRITICAL)  # temporarily disabled

SERIAL_PORT = "/dev/ttyS0"
BAUD        = 9600
USER_CODE   = "7321"
PARTITION   = 1

labels: dict[int, str] = {}
_last_label_at: float = 0.0


def handle_zone_update(driver, pkt):
    cmd = pkt['command']
    d   = pkt['parsed']

    if cmd == CMD_ZONE_OPEN:
        print(f"[ZONE]   Zone {d['zone']} opened")
    elif cmd == CMD_ZONE_RESTORED:
        print(f"[ZONE]   Zone {d['zone']} closed/restored")
    elif cmd == CMD_ZONE_ALARM:
        print(f"[ALARM]  Zone {d['zone']} in ALARM (partition {d['partition']})")
    elif cmd == CMD_ZONE_ALARM_RESTORE:
        print(f"[ALARM]  Zone {d['zone']} alarm restored (partition {d['partition']})")
    elif cmd == CMD_ZONE_TAMPER:
        print(f"[TAMPER] Zone {d['zone']} TAMPER (partition {d['partition']})")
    elif cmd == CMD_ZONE_TAMPER_RESTORE:
        print(f"[TAMPER] Zone {d['zone']} tamper restore (partition {d['partition']})")


def handle_partition_update(driver, pkt):
    cmd = pkt['command']
    d   = pkt['parsed']
    p   = d.get('partition', '?')

    if cmd == CMD_PARTITION_READY:
        print(f"[PART]   Partition {p} READY")
    elif cmd == CMD_PARTITION_NOT_READY:
        print(f"[PART]   Partition {p} NOT READY")
    elif cmd == CMD_PARTITION_ARMED:
        print(f"[PART]   Partition {p} ARMED ({d.get('mode', '?')})")
    elif cmd == CMD_PARTITION_DISARMED:
        print(f"[PART]   Partition {p} DISARMED")
    elif cmd == CMD_PARTITION_IN_ALARM:
        print(f"[ALARM]  Partition {p} IN ALARM")
    elif cmd == CMD_EXIT_DELAY:
        print(f"[PART]   Partition {p} — exit delay")
    elif cmd == CMD_ENTRY_DELAY:
        print(f"[PART]   Partition {p} — entry delay")
    elif cmd == CMD_KEYPAD_LOCKOUT:
        print(f"[PART]   Partition {p} LOCKED OUT")
    elif cmd == CMD_FAIL_TO_ARM:
        print(f"[PART]   Partition {p} FAILED TO ARM")
    elif cmd == CMD_USER_CLOSING:
        print(f"[O/C]    Partition {p} armed by user {d.get('user')}")
    elif cmd == CMD_USER_OPENING:
        print(f"[O/C]    Partition {p} disarmed by user {d.get('user')}")
    elif cmd == CMD_CODE_REQUIRED:
        print(f"[KEYPAD] Code required on partition {p}")


def handle_general_update(driver, pkt):
    global _last_label_at

    cmd = pkt['command']
    d   = pkt['parsed']

    if cmd == CMD_LCD_UPDATE:
        print(f"[LCD]    Line {d['line']}: {d.get('text', '')}")
    elif cmd == CMD_LED_STATUS:
        print(f"[LED]    {d.get('led', '?')} LED is {d.get('state', '?')}")
    elif cmd == CMD_SOFTWARE_VERSION:
        print(f"[SYS]    IT-100 firmware v{d.get('version')}.{d.get('sub_version')}")
    elif cmd == CMD_COMMAND_ACK:
        print(f"[ACK]    Command {d.get('acknowledged_command')} acknowledged")
    elif cmd == CMD_COMMAND_ERROR:
        print("[ERROR]  Command received with bad checksum")
    elif cmd == CMD_SYSTEM_ERROR:
        print(f"[ERROR]  System error: {d.get('error_description')}")
    elif cmd == CMD_PANEL_BATTERY_TROUBLE:
        print("[TROUBLE] Panel battery LOW")
    elif cmd == CMD_PANEL_BATTERY_RESTORE:
        print("[TROUBLE] Panel battery restored")
    elif cmd == CMD_PANEL_AC_TROUBLE:
        print("[TROUBLE] Panel AC power LOST")
    elif cmd == CMD_PANEL_AC_RESTORE:
        print("[TROUBLE] Panel AC power restored")
    elif cmd == CMD_BROADCAST_LABELS:
        num = d.get('label_number')
        if num is not None:
            labels[num] = d.get('label', '')
            _last_label_at = time.monotonic()


async def main():
    panel = IT100(SERIAL_PORT, baud=BAUD)
    panel.handler_zone_update      = handle_zone_update
    panel.handler_partition_update = handle_partition_update
    panel.handler_general_update   = handle_general_update
    await panel.connect()

    # Yield once so the reader task gets its first chance to start,
    # then send startup commands in order.
    await asyncio.sleep(0)
    await panel.poll()            # confirm link is alive
    await panel.request_status()  # snapshot all zones and partitions
    await panel.request_labels()  # fetch programmable labels (arrives as many packets)

    try:
        await asyncio.Future()  # run until cancelled
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await panel.disconnect()



if __name__ == "__main__":
    asyncio.run(main())
