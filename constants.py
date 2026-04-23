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
    # System / comms
    'command_ack':              CMD_COMMAND_ACK,
    'command_error':            CMD_COMMAND_ERROR,
    'system_error':             CMD_SYSTEM_ERROR,
    'software_version':         CMD_SOFTWARE_VERSION,
    'time_date_broadcast':      CMD_TIME_DATE_BROADCAST,
    'ring_detected':            CMD_RING_DETECTED,
    'baud_rate_set':            CMD_BAUD_RATE_SET,
    'broadcast_labels':         CMD_BROADCAST_LABELS,

    # Zones
    'zone_open':                CMD_ZONE_OPEN,
    'zone_restored':            CMD_ZONE_RESTORED,
    'zone_alarm':               CMD_ZONE_ALARM,
    'zone_alarm_restore':       CMD_ZONE_ALARM_RESTORE,
    'zone_tamper':              CMD_ZONE_TAMPER,
    'zone_tamper_restore':      CMD_ZONE_TAMPER_RESTORE,
    'zone_fault':               CMD_ZONE_FAULT,
    'zone_fault_restore':       CMD_ZONE_FAULT_RESTORE,

    # Special zone / panic alarms
    'duress_alarm':             CMD_DURESS_ALARM,
    'f_key_alarm':              CMD_F_KEY_ALARM,
    'f_key_restoral':           CMD_F_KEY_RESTORAL,
    'a_key_alarm':              CMD_A_KEY_ALARM,
    'a_key_restoral':           CMD_A_KEY_RESTORAL,
    'p_key_alarm':              CMD_P_KEY_ALARM,
    'p_key_restoral':           CMD_P_KEY_RESTORAL,
    'aux_input_alarm':          CMD_AUX_INPUT_ALARM,
    'aux_input_restore':        CMD_AUX_INPUT_RESTORE,

    # Partitions
    'partition_ready':          CMD_PARTITION_READY,
    'partition_not_ready':      CMD_PARTITION_NOT_READY,
    'partition_armed':          CMD_PARTITION_ARMED,
    'partition_ready_force':    CMD_PARTITION_READY_FORCE,
    'partition_alarm':          CMD_PARTITION_IN_ALARM,
    'partition_disarmed':       CMD_PARTITION_DISARMED,
    'exit_delay':               CMD_EXIT_DELAY,
    'entry_delay':              CMD_ENTRY_DELAY,
    'keypad_lockout':           CMD_KEYPAD_LOCKOUT,
    'keypad_blanking':          CMD_KEYPAD_BLANKING,
    'command_output_progress':  CMD_COMMAND_OUTPUT_PROGRESS,
    'invalid_access_code':      CMD_INVALID_ACCESS_CODE,
    'function_not_available':   CMD_FUNCTION_NOT_AVAILABLE,
    'fail_to_arm':              CMD_FAIL_TO_ARM,
    'partition_busy':           CMD_PARTITION_BUSY,

    # Open / close
    'user_closing':             CMD_USER_CLOSING,
    'special_closing':          CMD_SPECIAL_CLOSING,
    'partial_closing':          CMD_PARTIAL_CLOSING,
    'user_opening':             CMD_USER_OPENING,
    'special_opening':          CMD_SPECIAL_OPENING,

    # Trouble — panel
    'panel_battery_trouble':    CMD_PANEL_BATTERY_TROUBLE,
    'panel_battery_restore':    CMD_PANEL_BATTERY_RESTORE,
    'panel_ac_trouble':         CMD_PANEL_AC_TROUBLE,
    'panel_ac_restore':         CMD_PANEL_AC_RESTORE,
    'system_bell_trouble':      CMD_SYSTEM_BELL_TROUBLE,
    'system_bell_restore':      CMD_SYSTEM_BELL_RESTORE,
    'ftc_trouble':              CMD_FTC_TROUBLE,
    'buffer_near_full':         CMD_BUFFER_NEAR_FULL,
    'general_system_tamper':    CMD_GENERAL_SYSTEM_TAMPER,
    'general_tamper_restore':   CMD_GENERAL_TAMPER_RESTORE,
    'home_auto_trouble':        CMD_HOME_AUTO_TROUBLE,
    'home_auto_restore':        CMD_HOME_AUTO_RESTORE,
    'fire_trouble':             CMD_FIRE_TROUBLE,
    'fire_trouble_restore':     CMD_FIRE_TROUBLE_RESTORE,

    # Trouble — telephone line
    'tlm_line1_trouble':        CMD_TLM_LINE1_TROUBLE,
    'tlm_line1_restore':        CMD_TLM_LINE1_RESTORE,
    'tlm_line2_trouble':        CMD_TLM_LINE2_TROUBLE,
    'tlm_line2_restore':        CMD_TLM_LINE2_RESTORE,

    # Trouble — wireless
    'wireless_low_battery':     CMD_WIRELESS_LOW_BATTERY,
    'wireless_low_restore':     CMD_WIRELESS_LOW_RESTORE,
    'wkey_low_battery':         CMD_WKEY_LOW_BATTERY,
    'wkey_low_restore':         CMD_WKEY_LOW_RESTORE,
    'handheld_low_battery':     CMD_HANDHELD_LOW_BATTERY,
    'handheld_low_restore':     CMD_HANDHELD_LOW_RESTORE,

    # Trouble LED
    'trouble_led_on':           CMD_TROUBLE_LED_ON,
    'trouble_led_off':          CMD_TROUBLE_LED_OFF,

    # Virtual keypad
    'code_required':            CMD_CODE_REQUIRED,
    'lcd_update':               CMD_LCD_UPDATE,
    'lcd_cursor':               CMD_LCD_CURSOR,
    'led_status':               CMD_LED_STATUS,
    'beep_status':              CMD_BEEP_STATUS,
    'tone_status':              CMD_TONE_STATUS,
    'buzzer_status':            CMD_BUZZER_STATUS,
    'door_chime':               CMD_DOOR_CHIME,

    # Thermostat / temperature
    'indoor_temp':              CMD_INDOOR_TEMP,
    'outdoor_temp':             CMD_OUTDOOR_TEMP,
    'thermostat_set_points':    CMD_THERMOSTAT_SET_POINTS,
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
