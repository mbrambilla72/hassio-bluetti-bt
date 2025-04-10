"""AC2A fields."""

from typing import List

from ..field_enums import ChargingMode
from ..utils.commands import ReadHoldingRegisters
from ..base_devices.ProtocolV2Device import ProtocolV2Device

class AC2A(ProtocolV2Device):
    def __init__(self, address: str, sn: str):
        super().__init__(address, "AC2A", sn)

 # Core (100)
        self.struct.add_uint_field('total_battery_percent', 102)
        self.struct.add_decimal_field('estimated_time_hr', 104,1)
        self.struct.add_swap_string_field('device_type', 110, 6)
        self.struct.add_sn_field('serial_number', 116)
        self.struct.add_uint_field('dc_output_power', 140)
        self.struct.add_uint_field('ac_output_power', 142)
        self.struct.add_uint_field('dc_input_power', 144)
        self.struct.add_uint_field('ac_input_power', 146)

        # Input Details (1100 - 1300)
        self.struct.add_swap_string_field('device_type', 1101, 6)
        self.struct.add_sn_field('serial_number', 1107)
        self.struct.add_uint_field('num_packs_connected', 1209)
        self.struct.add_bool_field('charging_from_internal_dc', 1210)
        self.struct.add_uint_field('internal_dc_input_power', 1212)
        self.struct.add_decimal_field('internal_dc_input_voltage', 1213, 1)
        self.struct.add_decimal_field('internal_dc_input_current', 1214, 1)
        self.struct.add_bool_field('charging_from_pack_dc', 1218)
        self.struct.add_uint_field('pack_dc_input_power', 1220)
        self.struct.add_decimal_field('pack_dc_input_voltage', 1221, 1)
        self.struct.add_decimal_field('pack_dc_input_current', 1222, 1)
        self.struct.add_decimal_field('ac_input_frequency', 1300, 1)
        self.struct.add_uint_field('internal_ac_input_power', 1313)
        self.struct.add_decimal_field('ac_input_voltage', 1314, 1)
        self.struct.add_decimal_field('ac_input_current', 1315, 1)

        # Output Details (1400 - 1500)
        self.struct.add_uint_field('total_dc_output_power', 1400)
        self.struct.add_uint_field('dc_usb_output_power', 1404)
        self.struct.add_uint_field('dc_12v_output_power', 1406)
        self.struct.add_uint_field('dc_output_uptime_minutes', 1410)
        self.struct.add_uint_field('ac_output_power', 1420)
        self.struct.add_uint_field('ac_output_uptime_minutes', 1424)
        self.struct.add_uint_field('ac_output_power', 1430)
        self.struct.add_decimal_field('ac_output_frequency', 1500, 1)
        self.struct.add_bool_field('ac_output_on', 1509)
        self.struct.add_uint_field('battery_inputoutput_power', 1510)
        self.struct.add_decimal_field('ac_output_voltage', 1511, 1)
        self.struct.add_decimal_field('ac_output_amps', 1512, 1)

        # Controls (2000)
        self.struct.add_bool_field('ac_output_on', 2011)
        self.struct.add_bool_field('dc_output_on', 2012)
        self.struct.add_bool_field('dc_eco_on', 2014)
        self.struct.add_uint_field('dc_eco_hours', 2015)
        self.struct.add_uint_field('dc_eco_watts', 2016)
        self.struct.add_bool_field('ac_eco_on', 2017)
        self.struct.add_uint_field('ac_eco_hours', 2018)
        self.struct.add_uint_field('ac_eco_watts', 2019)
        self.struct.add_enum_field('charging_mode', 2020, ChargingMode)
        self.struct.add_bool_field('power_lifting_on', 2021)

        # More Controls (2200)
        self.struct.add_bool_field('grid_enhancement_mode_on', 2225)

        # Battery Data Register (6000)
        self.struct.add_decimal_field('total_battery_voltage', 6003, 2)

        # Battery Data Register (6100)
        self.struct.add_swap_string_field('battery_type', 6101, 6)
        self.struct.add_sn_field('pack_serial_number', 6107)
        self.struct.add_decimal_field('pack_voltage', 6111, 2)
        self.struct.add_uint_field('pack_battery_percent', 6113)
        self.struct.add_version_field('bcu_version', 6175)

        # this is usefule for investigating the available data
        # registers = {0:21,100:67,700:6,720:49,1100:51,1200:90,1300:31,1400:48,1500:30,2000:67,2200:29,3000:27,6000:31,6100:100,6300:52,7000:5}
        # for k in registers:
        #     for v in range(registers[k]):
        #         self.struct.add_uint_field('testI' + str(v+k), v+k)

    @property
    def polling_commands(self) -> List[ReadHoldingRegisters]:
        return self.struct.get_read_holding_registers()
    

    @property
    def writable_ranges(self) -> List[range]:
        return super().writable_ranges + [
            range(2000, 2225)
        ]
