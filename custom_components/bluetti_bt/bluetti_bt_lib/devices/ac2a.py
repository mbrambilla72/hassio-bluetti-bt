"""AC2A fields."""

from ..base_devices.ProtocolV2Device import ProtocolV2Device


class AC2A(ProtocolV2Device):
    def __init__(self, address: str, sn: str):
        super().__init__(address, "AC2A", sn)
