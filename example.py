"""
example.py
----------
Demonstrates the IT100 queue-based event pattern.

All packets flow through a single queue.Queue.  A single handle() function
dispatches on pkt['command'].

Run:
    python example.py
"""

import queue
import time
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from dsc_it100 import (
    IT100,
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


# ---------------------------------------------------------------------------
# Collected state
# ---------------------------------------------------------------------------

labels: dict[int, str] = {}   # label_number -> label text


# ---------------------------------------------------------------------------
# Single handler — dispatches on pkt['command']
# ---------------------------------------------------------------------------

def handle(pkt: dict) -> None:
    cmd = pkt['command']
    d   = pkt['parsed']

    if cmd == CMD_ZONE_OPEN:
        print(f"[ZONE]       Zone {d['zone']} opened")

    elif cmd == CMD_ZONE_RESTORED:
        print(f"[ZONE]       Zone {d['zone']} closed/restored")

    elif cmd == CMD_ZONE_ALARM:
        print(f"[ALARM]      Zone {d['zone']} in ALARM (partition {d['partition']})")

    elif cmd == CMD_ZONE_ALARM_RESTORE:
        print(f"[ALARM]      Zone {d['zone']} alarm restored (partition {d['partition']})")

    elif cmd in (CMD_ZONE_TAMPER, CMD_ZONE_TAMPER_RESTORE):
        state = "TAMPER" if cmd == CMD_ZONE_TAMPER else "tamper restore"
        print(f"[TAMPER]     Zone {d['zone']} {state} (partition {d['partition']})")

    elif cmd == CMD_PARTITION_READY:
        print(f"[PARTITION]  Partition {d['partition']} READY")

    elif cmd == CMD_PARTITION_NOT_READY:
        print(f"[PARTITION]  Partition {d['partition']} NOT READY")

    elif cmd == CMD_PARTITION_ARMED:
        print(f"[PARTITION]  Partition {d['partition']} ARMED ({d.get('mode', '?')})")

    elif cmd == CMD_PARTITION_DISARMED:
        print(f"[PARTITION]  Partition {d['partition']} DISARMED")

    elif cmd == CMD_PARTITION_IN_ALARM:
        print(f"[ALARM]      Partition {d['partition']} IN ALARM")

    elif cmd == CMD_EXIT_DELAY:
        print(f"[PARTITION]  Partition {d['partition']} — exit delay")

    elif cmd == CMD_ENTRY_DELAY:
        print(f"[PARTITION]  Partition {d['partition']} — entry delay")

    elif cmd == CMD_KEYPAD_LOCKOUT:
        print(f"[PARTITION]  Partition {d['partition']} LOCKED OUT")

    elif cmd == CMD_FAIL_TO_ARM:
        print(f"[PARTITION]  Partition {d['partition']} FAILED TO ARM")

    elif cmd == CMD_USER_CLOSING:
        print(f"[OPEN/CLOSE] Partition {d['partition']} armed by user {d.get('user')}")

    elif cmd == CMD_USER_OPENING:
        print(f"[OPEN/CLOSE] Partition {d['partition']} disarmed by user {d.get('user')}")

    elif cmd == CMD_CODE_REQUIRED:
        print(f"[KEYPAD]     Code required on partition {d['partition']}")

    elif cmd == CMD_LCD_UPDATE:
        print(f"[LCD]        Line {d['line']}: {d.get('text', '')}")

    elif cmd == CMD_LED_STATUS:
        print(f"[LED]        {d.get('led', '?')} LED is {d.get('state', '?')}")

    elif cmd == CMD_SOFTWARE_VERSION:
        print(f"[SYSTEM]     IT-100 firmware v{d.get('version')}.{d.get('sub_version')}")

    elif cmd == CMD_COMMAND_ACK:
        print(f"[ACK]        Command {d.get('acknowledged_command')} acknowledged")

    elif cmd == CMD_COMMAND_ERROR:
        print("[ERROR]      Command received with bad checksum")

    elif cmd == CMD_SYSTEM_ERROR:
        print(f"[ERROR]      System error: {d.get('error_description')}")

    elif cmd == CMD_PANEL_BATTERY_TROUBLE:
        print("[TROUBLE]    Panel battery LOW")

    elif cmd == CMD_PANEL_BATTERY_RESTORE:
        print("[TROUBLE]    Panel battery restored")

    elif cmd == CMD_PANEL_AC_TROUBLE:
        print("[TROUBLE]    Panel AC power LOST")

    elif cmd == CMD_PANEL_AC_RESTORE:
        print("[TROUBLE]    Panel AC power restored")

    elif cmd == CMD_BROADCAST_LABELS:
        num = d.get('label_number')
        if num is not None:
            labels[num] = d.get('label', '')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    q     = queue.Queue()
    panel = IT100(port=SERIAL_PORT, baud=BAUD)

    # Single registration — every packet lands in the queue
    panel.on('*', q.put)

    with panel:
        print(f"Connected to IT-100 on {SERIAL_PORT}")

        # Verify comms and get a full zone/partition snapshot
        #panel.poll()
        panel.request_status()

        # Request labels; wait until 1.5 s of silence (max 15 s).
        # At 9600 baud 151 labels can take ~7 s.
        panel.request_labels()
        _last_label_at = time.monotonic()
        _deadline      = time.monotonic() + 15.0
        _labels_done   = False

        print("\nListening for events. Press Ctrl+C to stop.\n")
        try:
            while True:
                try:
                    pkt = q.get(timeout=0.1)
                except queue.Empty:
                    # Check if label collection is complete
                    if (not _labels_done
                            and labels
                            and (time.monotonic() - _last_label_at) >= 1.5):
                        _labels_done = True
                        print("\n--- Programmable Labels ---")
                        for num, text in sorted(labels.items()):
                            print(f"  [{num:3d}] {text}")
                        print("---------------------------\n")
                    elif (not _labels_done
                            and not labels
                            and time.monotonic() > _deadline):
                        _labels_done = True
                        print("\n[LABELS] No labels received (PC1616/1832/1864 panels only)\n")
                    continue

                handle(pkt)

                if pkt['command'] == CMD_BROADCAST_LABELS:
                    _last_label_at = time.monotonic()

        except KeyboardInterrupt:
            print("\nStopping.")

        print("Disconnecting.")


if __name__ == "__main__":
    main()
