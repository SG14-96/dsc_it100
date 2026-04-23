# dsc-it100

Async Python driver for the DSC IT-100 serial integration module.

## Installation

```bash
pip install dsc-it100
```

## Quick start

```python
import asyncio
from dsc_it100 import IT100
from dsc_it100.constants import CMD_ZONE_OPEN, CMD_PARTITION_ARMED

def handle_zone_update(driver, pkt):
    d = pkt['parsed']
    if pkt['command'] == CMD_ZONE_OPEN:
        print(f"Zone {d['zone']} opened")

def handle_partition_update(driver, pkt):
    d = pkt['parsed']
    if pkt['command'] == CMD_PARTITION_ARMED:
        print(f"Partition {d['partition']} armed ({d['mode']})")

def handle_general_update(driver, pkt):
    print(f"Event {pkt['command']}: {pkt['parsed']}")

async def main():
    panel = IT100('/dev/ttyUSB0', baud=9600)
    panel.handler_zone_update      = handle_zone_update
    panel.handler_partition_update = handle_partition_update
    panel.handler_general_update   = handle_general_update
    await panel.connect()
    await asyncio.sleep(0)
    await panel.poll()
    await panel.request_status()
    await panel.request_labels()
    try:
        await asyncio.Future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await panel.disconnect()

asyncio.run(main())
```

## Event handlers

| Property | Fires when |
|---|---|
| `handler_zone_update` | packet contains a zone field (open, close, alarm, tamper, fault) |
| `handler_partition_update` | packet contains a partition field but no zone (ready, armed, disarmed, delay, alarm) |
| `handler_general_update` | every incoming packet (catch-all) |

Each handler receives `(driver, packet)` where `packet` is:

```python
{
    'command':  '609',       # 3-digit IT-100 command code
    'data':     '001',       # raw data field
    'checksum': 'CC',
    'valid':    True,
    'parsed':   {'zone': 1}, # command-specific parsed fields
}
```

Handlers may be plain functions or coroutines.

## Commands

```python
await panel.poll()
await panel.request_status()
await panel.request_labels()
await panel.arm_away(partition=1)
await panel.arm_stay(partition=1)
await panel.arm_with_code(partition=1, code='1234')
await panel.disarm(partition=1, code='1234')
await panel.trigger_panic()
await panel.bypass_zone(zone=3, code='1234')
```

## Requirements

- Python 3.10+
- pyserial
