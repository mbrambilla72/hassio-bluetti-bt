"""Base device definition for V2 Protocol devices."""

from typing import List

from ..utils.commands import ReadHoldingRegisters
from ..utils.struct import DeviceStruct
from ..field_enums import ChargingMode#, UpsMode
from .BluettiDevice import BluettiDevice


class ProtocolV2Device(BluettiDevice):
    def __init__(self, address: str, type: str, sn: str):
        self.struct = DeviceStruct()

        # Device info
        self.struct.add_swap_string_field("device_type", 110, 6)
        self.struct.add_sn_field("serial_number", 116)

        # Battery
        self.struct.add_uint_field("total_battery_percent", 102)

        # Power IO
        self.struct.add_uint_field('dc_output_power', 140)
        self.struct.add_uint_field('ac_output_power', 142)
        self.struct.add_uint_field('dc_input_power', 144)
        self.struct.add_uint_field('ac_input_power', 146)
        self.struct.add_uint_field('total_inv_power', 148)
        self.struct.add_decimal_field('total_dc_consumption', 150, 1)
        self.struct.add_decimal_field('total_ac_consumption', 152, 1)
        self.struct.add_decimal_field('power_generation', 154, 1) # Total power generated since last reset (kwh)
        self.struct.add_decimal_field('total_grid_consumption', 156, 1)
        #self.struct.add_decimal_field('total_grid_feed', 158, 1) Unsure what this one is
        self.struct.add_enum_field("charging_mode", 160, ChargingMode)
        
        #self.struct.add_decimal_field('???', 162)
        #self.struct.add_decimal_field('???', 165)
        
        
        # Input Details (1100 - 1300)?
        self.struct.add_decimal_field('ac_input_voltage', 1314, 1)


        # Battery packs
        # self.struct.add_uint_field('pack_num_max', ?) # internal
        # self.struct.add_decimal_field('total_battery_voltage', ?, 1)
        # self.struct.add_uint_field('pack_num', ?) # internal
        # self.struct.add_decimal_field('pack_voltage', ?, 2)  # Full pack voltage
        # self.struct.add_uint_field('pack_battery_percent', ?)

        # Output state
        self.struct.add_bool_field('ac_output_on_switch', 2011)
        self.struct.add_bool_field('dc_output_on_switch', 2012)
        self.struct.add_bool_field('silent_charging_on', 2020)
        self.struct.add_bool_field('power_lifting_on', 2021)
        
        self.struct.add_bool_field('grid_enhancement_mode_on', 2225)

        # Pack selector
        # self.struct.add_uint_field('pack_num', ?) # internal
        
        #self.struct.add_enum_field("ups_mode", ???, UpsMode)


        super().__init__(address, type, sn)

    @property
    def polling_commands(self) -> List[ReadHoldingRegisters]:
        return [
            ReadHoldingRegisters(110, 6),
            ReadHoldingRegisters(116, 4),
            ReadHoldingRegisters(154, 1),
            ReadHoldingRegisters(102, 1),
            ReadHoldingRegisters(140, 1),
            ReadHoldingRegisters(142, 1),
            ReadHoldingRegisters(144, 1),
            ReadHoldingRegisters(146, 1),
            ReadHoldingRegisters(148, 1),
            ReadHoldingRegisters(150, 1),
            ReadHoldingRegisters(152, 1),
            ReadHoldingRegisters(154, 1),
            ReadHoldingRegisters(156, 1),
            #ReadHoldingRegisters(158, 1),
            ReadHoldingRegisters(160, 1),
            ReadHoldingRegisters(1314, 1),
            ReadHoldingRegisters(2011, 1),
            ReadHoldingRegisters(2012, 1),
            ReadHoldingRegisters(2020, 1),
            ReadHoldingRegisters(2021, 1),
            ReadHoldingRegisters(2225, 1),
        ]

    @property
    def writable_ranges(self) -> List[range]:
        return [range(2000, 2022),range(2200, 2226)]

    @property
    def pack_polling_commands(self) -> List[ReadHoldingRegisters]:
        return []
