import logging
import bluetti_crypt
from ctypes import *


_LOGGER = logging.getLogger(__name__)

class bleEncrypt:
    def __init__(self):
        # self.cryptoClient = bluetti_crypt.BluettiCrypt()
        # bluetti_crypt.test_module()
        pass

    def start(self, enable: bool = True):
        self.cryptoClient = bluetti_crypt.BluettiCrypt()
        self.enable = enable
        software_version = self.cryptoClient.get_software_version()
        _LOGGER.info('Crypt module software version: ' + str(software_version))

    def encrypt_link(self, data: bytearray):
        if (False == self.enable):
            return 3
        _LOGGER.info(' encrypt link data: ' + data.hex())

        message, ret = self.cryptoClient.ble_crypt_link_handler(bytes(data))
        _LOGGER.info(' ble crypt link result: ' + str(ret) + ' message: ' + message.hex())
        return ret, message

    def send_message(self, data: bytearray):
        if (False == self.enable):
            return len(data), data
        _LOGGER.info(f'send message: ' + data.hex())

        message = self.cryptoClient.encrypt_data(bytes(data))
        _LOGGER.info(f' send encrypt message: {message.hex()}')
        return len(message), message

    def message_handle(self, data: bytearray):
        if (False == self.enable):
            return len(data), data
        message = self.cryptoClient.decrypt_data(bytes(data))
        _LOGGER.info('receive message: ' + message.hex())
        return len(message), message
