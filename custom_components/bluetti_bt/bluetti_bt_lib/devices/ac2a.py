"""AC2A fields."""

from typing import List

from ..field_enums import ChargingMode
from ..utils.commands import ReadHoldingRegisters
from ..base_devices.ProtocolV2Device import ProtocolV2Device

class AC2A(ProtocolV2Device):
    def __init__(self, address: str, sn: str):
        super().__init__(address, "AC2A", sn)

        # Power stats
        self.struct.add_uint_field('dc_output_power', 140)
        self.struct.add_uint_field('ac_output_power', 142)
        self.struct.add_uint_field('dc_input_power', 144)
        self.struct.add_uint_field('ac_input_power', 146)

    @property
    def polling_commands(self) -> List[ReadHoldingRegisters]:
        # Automatically generate polling ranges based on fields defined above
        return self.struct.get_read_holding_registers()

    @property
    def writable_ranges(self) -> List[range]:
        return super().writable_ranges + [
            range(2000, 2022),
            range(2200, 2226)
        ]
