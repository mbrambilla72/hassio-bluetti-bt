"""Device reader."""

import asyncio
import logging
from typing import Any, Callable, List, cast
import async_timeout
from bleak import BleakClient, BleakError, BleakScanner

from ..base_devices.BluettiDevice import BluettiDevice
from ..const import NOTIFY_UUID, RESPONSE_TIMEOUT, WRITE_UUID
from ..exceptions import BadConnectionError, ModbusError, ParseError
from ..utils.commands import ReadHoldingRegisters
from .encrypt import bleEncrypt

_LOGGER = logging.getLogger(__name__)


class DeviceReader:
    def __init__(
        self,
        bleak_client: BleakClient,
        bluetti_device: BluettiDevice,
        future_builder_method: Callable[[], asyncio.Future[Any]],
        persistent_conn: bool = False,
        polling_timeout: int = 45,
        max_retries: int = 5,
    ) -> None:
        self.client = bleak_client
        self.bluetti_device = bluetti_device
        self.create_future = future_builder_method
        self.persistent_conn = persistent_conn
        self.polling_timeout = polling_timeout
        self.max_retries = max_retries

        self.has_notifier = False
        self.notify_future: asyncio.Future[Any] | None = None
        self.current_command = None
        self.notify_response = bytearray()

        # polling mutex to guard against switches
        self.polling_lock = asyncio.Lock()

        self.cryptModule = bleEncrypt()

        self.is_crypting = False
        self.enable_crypt = False

    async def read_data(
        self, filter_registers: List[ReadHoldingRegisters] | None = None
    ) -> dict | None:
        _LOGGER.info("Reading data")

        if self.bluetti_device is None:
            _LOGGER.error("Device is None")
            return None

        polling_commands = self.bluetti_device.polling_commands
        pack_commands = self.bluetti_device.pack_polling_commands
        if filter_registers is not None:
            polling_commands = filter_registers
            pack_commands = []
        _LOGGER.info("Polling commands: " + ",".join([f"{c.starting_address}-{c.starting_address + c.quantity - 1}" for c in polling_commands]))
        _LOGGER.info("Pack comands: " + ",".join([f"{c.starting_address}-{c.starting_address + c.quantity - 1}" for c in pack_commands]))

        parsed_data: dict = {}

        # Whether encryption is supported
        devices = await BleakScanner.discover(timeout=10)
        for d in devices:
            if str(self.bluetti_device.type) == "Handsfree":
                bluetti_device_name = str(self.bluetti_device.type) + " " + str(self.bluetti_device.sn)
            else:
                bluetti_device_name = str(self.bluetti_device.type) + str(self.bluetti_device.sn)
            if bluetti_device_name == d.name:
                for(type, value) in d._metadata["manufacturer_data"].items():
                    if value == b'BLUETTF':
                        self.enable_crypt = True
                        break
                else:
                    continue
                break

        async with self.polling_lock:
            try:
                async with async_timeout.timeout(self.polling_timeout):
                    # Reconnect if not connected
                    for attempt in range(1, self.max_retries + 1):
                        try:
                            if not self.client.is_connected:
                                
                                self.cryptModule.start(self.enable_crypt)   # start bluetti crypt module
                                await self.client.connect()

                                # Check if we need to encrypt the link
                                if self.enable_crypt is True:
                                    self.is_crypting = True

                            break
                        except Exception as e:
                            if attempt == self.max_retries:
                                raise e # pass exception on max_retries attempt
                            else:
                                _LOGGER.warning(
                                    f"Connect unsucessful (attempt {attempt}): {e}. Retrying..."
                                )
                                await asyncio.sleep(2)

                    # Attach notifier if needed
                    if not self.has_notifier:
                        await self.client.start_notify(
                            NOTIFY_UUID, self._notification_handler
                        )
                        self.has_notifier = True

                    # Encrypt link if needed
                    if self.is_crypting is True:
                        isSuccess = await self._encrypt_link()
                        if isSuccess == 1:
                            self.is_crypting = False
                            _LOGGER.info(f'bluetti device connect success!')
                        elif isSuccess == -1:
                            if self.has_notifier:
                                try:
                                    await self.client.stop_notify(NOTIFY_UUID)
                                except:
                                    # Ignore errors here
                                    pass
                                self.has_notifier = False
                            await self.client.disconnect()
                            self.is_crypting = False
                            return None

                        if self.is_crypting is True:
                            return None

                    # Execute polling commands
                    for command in polling_commands:
                        try:
                            body = command.parse_response(
                                await self._async_send_command(command)
                            )
                            _LOGGER.debug("Raw data: %s", body)
                            parsed = self.bluetti_device.parse(
                                command.starting_address, body
                            )
                            _LOGGER.debug("Parsed data: %s", parsed)
                            parsed_data.update(parsed)
                        except ParseError:
                            _LOGGER.warning("Got a parse exception")

                    # Execute pack polling commands
                    if len(pack_commands) > 0 and len(self.bluetti_device.pack_num_field) == 1:
                        _LOGGER.debug("Polling battery packs")
                        for pack in range(1, self.bluetti_device.pack_num_max + 1):
                            _LOGGER.debug("Setting pack_num to %i", pack)

                            # Set current pack number
                            command = self.bluetti_device.build_setter_command(
                                "pack_num", pack
                            )
                            body = command.parse_response(
                                await self._async_send_command(command)
                            )
                            _LOGGER.debug("Raw data set: %s", body)

                            # Check set pack_num
                            set_pack = int.from_bytes(body, byteorder='big')
                            if set_pack is not pack:
                                _LOGGER.warning("Pack polling failed (pack_num %i doesn't match expected %i)", set_pack, pack)
                                continue

                            if self.bluetti_device.pack_num_max > 1:
                                # We need to wait after switching packs 
                                # for the data to be available
                                await asyncio.sleep(5)
                            
                            for command in pack_commands:
                                # Request & parse result for each pack
                                try:
                                    body = command.parse_response(
                                        await self._async_send_command(command)
                                    )
                                    parsed = self.bluetti_device.parse(
                                        command.starting_address, body
                                    )
                                    _LOGGER.debug("Parsed data: %s", parsed)

                                    for key, value in parsed.items():
                                        # Ignore likely unavailable pack data
                                        if value != 0:
                                            parsed_data.update({key + str(pack): value})

                                except ParseError:
                                    _LOGGER.warning("Got a parse exception...")

            except TimeoutError as err:
                _LOGGER.error(f"Polling timed out ({self.polling_timeout}s). Trying again later", exc_info=err)
                return None
            except BleakError as err:
                _LOGGER.error("Bleak error: %s", err)
                return None
            finally:
                # Disconnect if connection not persistant
                if not self.persistent_conn:
                    if self.has_notifier:
                        try:
                            await self.client.stop_notify(NOTIFY_UUID)
                        except:
                            # Ignore errors here
                            pass
                        self.has_notifier = False
                    await self.client.disconnect()

            # Check if dict is empty
            if not parsed_data:
                return None

            return parsed_data

    async def _encrypt_link(self):
            """Encrypt link with Bluetti device"""

            retries = 0
            while retries < 6:
                try:
                    self.notify_future = self.create_future()
                    self.notify_response = bytearray()
                    # Wait for response
                    res = await asyncio.wait_for(
                        self.notify_future,
                        timeout=30)
                    # use crypt module to connect bluetti device
                    status, response = self.cryptModule.encrypt_link(self.notify_response)

                    if (3 == status):
                        """ Read the Serial Number and determine if it is authorized """
                        read_commands = self.bluetti_device.read_sn_command
                        for read_sn_command in read_commands:
                            length, cmd = self.cryptModule.send_message(bytes(read_sn_command.cmd))
                            await self.client.write_gatt_char(
                                WRITE_UUID,
                                bytes(cmd))
                    elif (4 == status):
                        """ Encrypt link connected """
                        logging.info(f'client connect success')
                        return 1
                    elif (0 <= status and 0 < len(response)):
                        """ Pass-Through data to the bluetti encrypt module """
                        await self.client.write_gatt_char(
                            WRITE_UUID,
                            bytes(response))
                        logging.info(f'client send authen data:' + response.hex())

                    retries += 1

                except asyncio.TimeoutError:
                    retries += 1
                    logging.warning(f' encrypt link timeout ')
            if retries == 5:
                logging.warning(f'client not receive authen data, now to disconnect')
                return -1
            return 0

    async def _async_send_command(self, command: ReadHoldingRegisters) -> bytes:
        """Send command and return response"""
        try:
            # Prepare to make request
            self.current_command = command
            self.notify_future = self.create_future()
            self.notify_response = bytearray()

            # Make request
            _LOGGER.debug("Requesting %s", command)

            # encrypt message
            length, cmd = self.cryptModule.send_message(bytes(command))
            modbus_cmd = command
            modbus_cmd.cmd = cmd
            logging.debug("send len: " + str(length) + " message: " + cmd.hex())
            self.current_command = modbus_cmd

            await self.client.write_gatt_char(WRITE_UUID, bytes(modbus_cmd))

            # Wait for response
            res = await asyncio.wait_for(self.notify_future, timeout=RESPONSE_TIMEOUT)

            # Process data
            _LOGGER.debug("Got %s bytes", len(res))
            return cast(bytes, res)

        except TimeoutError:
            _LOGGER.debug("Polling single command timed out")
        except ModbusError as err:
            _LOGGER.debug(
                "Got an invalid request error for %s: %s",
                command,
                err,
            )
        except (BadConnectionError, BleakError) as err:
            # Ignore other errors
            pass

        # caught an exception, return empty bytes object
        return bytes()

    def _notification_handler(self, _sender: int, data: bytearray):
        """Handle bt data."""

        # Ignore notifications we don't expect
        if self.notify_future is None or self.notify_future.done():
            _LOGGER.warning("Unexpected notification")
            return

        # If something went wrong, we might get weird data.
        if data == b"AT+NAME?\r" or data == b"AT+ADV?\r":
            err = BadConnectionError("Got AT+ notification")
            self.notify_future.set_exception(err)
            return

        # Save data
        self.notify_response.extend(data)

        if self.is_crypting is False:
            lenght, response = self.cryptModule.message_handle(data)
            if (0 >= lenght):
                msg = f'Failed to decrypt response {lenght} : {data.hex()}'
                self.notify_future.set_exception(ParseError(msg))
                return

            if len(response) == self.current_command.response_size():
                if self.current_command.is_valid_response(response):
                    self.notify_future.set_result(response)
                else:
                    self.notify_future.set_exception(ParseError("Failed checksum"))
            elif self.current_command.is_exception_response(response):
                # We got a MODBUS command exception
                msg = f"MODBUS Exception {self.current_command}: {response[2]}"
                self.notify_future.set_exception(ModbusError(msg))
        else:
            """ Bluetooth is establishing an encrypted channel and Pass-Through data to the bluetti encryption module """
            _LOGGER.debug(f' bluetooth is encrypting... ')
            self.notify_future.set_result(self.notify_response)
