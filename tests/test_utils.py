import pytest
from dsc_it100.utils import calculate_checksum, build_packet, verify_checksum, parse_packet, _pad_code


class TestCalculateChecksum:
    def test_known_value(self):
        # "6501" → ord('6')+ord('5')+ord('0')+ord('1') = 54+53+48+49 = 204 = 0xCC
        assert calculate_checksum('650', '1') == 'CC'

    def test_command_only(self):
        # "000" → 48+48+48 = 144 = 0x90
        assert calculate_checksum('000') == '90'

    def test_wraps_at_256(self):
        # Build a string whose ASCII sum exceeds 255 to verify 8-bit truncation
        result = calculate_checksum('999', '999999')
        total = sum(ord(c) for c in '999999999') & 0xFF
        assert result == f'{total:02X}'

    def test_uppercase(self):
        result = calculate_checksum('650', '1')
        assert result == result.upper()


class TestBuildPacket:
    def test_returns_bytes(self):
        assert isinstance(build_packet('000'), bytes)

    def test_ends_with_crlf(self):
        pkt = build_packet('000')
        assert pkt.endswith(b'\r\n')

    def test_structure(self):
        pkt = build_packet('650', '1').decode('ascii')
        assert pkt.startswith('6501')
        assert pkt[:-2].endswith('CC')

    def test_no_data(self):
        pkt = build_packet('000').decode('ascii').rstrip('\r\n')
        assert pkt[:3] == '000'
        assert len(pkt) == 5   # 3 cmd + 2 checksum


class TestVerifyChecksum:
    def test_valid_packet(self):
        assert verify_checksum('6501CC') is True

    def test_invalid_checksum(self):
        assert verify_checksum('6501FF') is False

    def test_strips_crlf(self):
        assert verify_checksum('6501CC\r\n') is True

    def test_too_short(self):
        assert verify_checksum('650') is False

    def test_minimum_length_valid(self):
        # 3-char command with no data: "000" + checksum "90" = "00090"
        assert verify_checksum('00090') is True


class TestParsePacket:
    def test_returns_none_on_short_input(self):
        assert parse_packet('650') is None

    def test_basic_structure(self):
        result = parse_packet('6501CC')
        assert result['command'] == '650'
        assert result['data'] == '1'
        assert result['checksum'] == 'CC'
        assert result['valid'] is True
        assert isinstance(result['parsed'], dict)

    def test_strips_whitespace(self):
        result = parse_packet('  6501CC  ')
        assert result['command'] == '650'

    def test_invalid_checksum_flagged(self):
        result = parse_packet('6501FF')
        assert result['valid'] is False

    def test_partition_ready_parsed(self):
        # CMD_PARTITION_READY = '650', data = partition number
        result = parse_packet('6501CC')
        assert result['parsed']['partition'] == 1

    def test_zone_open_parsed(self):
        # CMD_ZONE_OPEN = '609', data = zone number '001'
        raw = '609001'
        checksum = calculate_checksum('609', '001')
        result = parse_packet(f'609001{checksum}')
        assert result['parsed']['zone'] == 1

    def test_system_error_parsed(self):
        # CMD_SYSTEM_ERROR = '502', error code '017'
        checksum = calculate_checksum('502', '017')
        result = parse_packet(f'502017{checksum}')
        assert result['parsed']['error_code'] == '017'
        assert 'Installer Mode' in result['parsed']['error_description']

    def test_unknown_command_returns_empty_parsed(self):
        checksum = calculate_checksum('999')
        result = parse_packet(f'999{checksum}')
        assert result['parsed'] == {}

    def test_software_version_parsed(self):
        # CMD_SOFTWARE_VERSION = '908', data e.g. '0100' → version='01', sub='00'
        checksum = calculate_checksum('908', '0100')
        result = parse_packet(f'9080100{checksum}')
        assert result['parsed']['version'] == '01'
        assert result['parsed']['sub_version'] == '00'

    def test_led_status_parsed(self):
        # CMD_LED_STATUS = '903', data e.g. '11' → led='ready', state='on'
        checksum = calculate_checksum('903', '11')
        result = parse_packet(f'90311{checksum}')
        assert result['parsed']['led'] == 'ready'
        assert result['parsed']['state'] == 'on'

    def test_baud_rate_set_parsed(self):
        # CMD_BAUD_RATE_SET = '580', data '0' → 9600
        checksum = calculate_checksum('580', '0')
        result = parse_packet(f'5800{checksum}')
        assert result['parsed']['baud_rate'] == 9600


class TestPadCode:
    def test_four_digit_padded(self):
        assert _pad_code('1234') == '123400'

    def test_six_digit_unchanged(self):
        assert _pad_code('123456') == '123456'

    def test_strips_whitespace(self):
        assert _pad_code('  1234  ') == '123400'

    def test_invalid_length_raises(self):
        with pytest.raises(ValueError):
            _pad_code('123')

    def test_invalid_length_5_raises(self):
        with pytest.raises(ValueError):
            _pad_code('12345')
