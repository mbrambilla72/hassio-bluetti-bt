"""AC2A fields."""

from ..base_devices.ProtocolV2Device import ProtocolV2Device


class AC2A(ProtocolV2Device):
    def __init__(self, address: str, sn: str):
        super().__init__(address, "AC2A", sn)

        # Status flags
        self.struct.add_bool_field('ac_output_on', 1509)
        self.struct.add_bool_field('dc_output_on', 2012)
        self.struct.add_bool_field('power_lifting_on', 2021)
