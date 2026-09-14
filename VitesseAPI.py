"""Python interface for SONUS Vitesse FPGA firmware."""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from pathlib import Path
import sys
import time
from types import FunctionType
from typing import Callable

if sys.version_info >= (3, 11):
    from typing import Optional, Self, Union
else:
    from typing_extensions import Optional, Self, Union

import numpy as np

from . import sonoboticsFTDI as sbftdi
from .utils import (
    bin16_to_int,
    bin24_to_int,
    dec_enc,
    dec_enc_float,
    decode_version,
    ext_temp,
    int_temp,
)

DEFAULT_ADC_FREQUENCY = int(50e6)
VALID_TARGET_CLOCKS = [int(50e6), int(25e6)]


@contextmanager
def initialise_vitesse(serial_number: Optional[str] = None, simulation: bool = False):
    """Open a Vitesse device and close it when the context exits."""

    vitesse = Vitesse().initialise(serial_number, simulation)
    try:
        yield vitesse
    finally:
        if vitesse.spi_device is not None:
            vitesse.close_device()


class Vitesse:
    """Control and acquire data from a SONUS Vitesse device."""

    def __init__(self):
        """Initialise the API state with default values."""
        self.spi_device: Optional[sbftdi.ftdiChannel] = None

        self.read_delay: float = 500e-6
        self.max_read_chunk = 64000
        self.threshold_level: int = 0
        self.trigger: int = 0

        self.adc_frequency: int = DEFAULT_ADC_FREQUENCY
        self.prf: int = 0
        self.record_length: float = 0
        self.phase_array_microseconds: list[float] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.delay_array_microseconds: list[float] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.sampling_mode: int = 24
        self.num_averages: int = 100
        self.max_channels: int = 0
        self.excitation_clock_frequency: int = int(200e6)
        self.excitation_frequency: int = int(3.6e6)
        self.num_chips: int = 0
        self.num_receive_channels: int = 0
        self.receive_channel_mask: list[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.enabled_receive_channels: list[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.num_drive_channels: int = 0
        self.drive_channel_mask: list[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.enabled_drive_channels: list[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.record_points: int = 0
        self.num_channels_from_fpga: int = 0
        self.polarity: str = "p"
        self.duty_cycle_1: float = 1.0
        self.duty_cycle_2: float = 0.0
        self.simulation: bool = False

        self.additional_bytes: int = 0
        self.total_data_bytes: int = 0
        self.total_bytes: int = 0
        self.message_array: list[int] = []
        self.message_bytes: int = 3

        self.version: int = 0
        self.version_array: list[int] = []
        self.api_version: list[int] = [26, 9, 0]

        self.internal_temperature: float = 0.0
        self.external_temperature: float = 0.0
        self.encoder_count_1: int = 0
        self.encoder_count_2: int = 0
        self.encoder_count_3: int = 0
        self.position_x: float = 0
        self.position_y: float = 0
        self.position_theta: float = 0

        self.peripheral_descriptions: list[str] = [
            "Internal Temperature",
            "External Temperature",
            "Encoder 1",
            "Encoder 2",
            "Encoder Cart X",
            "Encoder Cart Y",
            "Encoder Cart Theta",
            "Encoder 3",
        ]
        self.peripheral_decoders: list[FunctionType] = [
            int_temp,
            ext_temp,
            dec_enc,
            dec_enc,
            dec_enc_float,
            dec_enc_float,
            dec_enc_float,
            dec_enc,
        ]
        self.peripheral_byte_counts: list[int] = [2, 2, 4, 4, 4, 4, 4, 4]

        self.wheelbase: float = 0
        self.wheel_radius: float = 0
        self.encoder_cpr: float = 0
        self.encoder_cpr_1: float = 0
        self.encoder_cpr_2: float = 0
        self.wheel_radius_1: float = 0
        self.wheel_radius_2: float = 0
        self.wheelbase_1: float = 0
        self.wheelbase_2: float = 0

        self.shm: bool = False

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):  # type: ignore
        if self.spi_device is not None:
            self.close_device()

    def initialise(
        self, serial_number: Optional[str] = None, simulation: bool = False
    ) -> Self:
        """
        Initialise a physical or simulated Vitesse device.

        Parameters:
        -----------
        serial_number : str | None, optional
            Serial number of the device to open. The first available device is
            used when no serial number is supplied.
        simulation : bool, optional
            If True, initialise a simulated device.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        OSError
            If no Vitesse device is connected.
        ValueError
            If the supplied serial number does not identify a Vitesse device.
        """

        self.simulation = simulation
        if self.simulation:
            self.spi_device = sbftdi.ftdiChannel()
            self.max_channels = 8
            self._set_adc_threshold()
            self.version = 23
            self.version_array = [23, 1, 0]
            self.adc_frequency = DEFAULT_ADC_FREQUENCY
            return self

        devices = self.list_devices()
        serial_numbers = [serial_number for (serial_number, _, _) in devices]
        if len(devices) == 0:
            raise IOError("No Vitesse device connected")

        if isinstance(serial_number, str):
            if serial_number not in serial_numbers:
                raise ValueError(
                    "The serial number does not belong to a Vitesse device"
                )
        else:
            serial_number = serial_numbers[0]

        serial_number = serial_number + "B"

        self.spi_device = sbftdi.sonoboticsFtdiChannel(
            "SPI", "serialNum", serial_number.encode()
        )

        initial_buffer = [0, 0, 0]
        while (
            initial_buffer[-1] != 200
            or initial_buffer[-2] != 200
            or initial_buffer[-3] != 200
        ):
            initial_buffer = np.frombuffer(
                self.spi_device.read(1000), dtype=np.uint8)

        self.max_channels = devices[0][2]
        self._set_adc_threshold()

        try:
            self.version = self.get_version()
        except ValueError:
            self.version = 256

        self.version_array = decode_version(self.version)

        try:
            self.adc_frequency = self.get_frequency()
        except ValueError:
            self.adc_frequency = DEFAULT_ADC_FREQUENCY

        self.set_config()

        return self

    @staticmethod
    def list_devices() -> list[tuple[str, str, int]]:
        """
        List connected physical Vitesse devices.

        Returns:
        --------
        list[tuple[str, str, int]]
            Serial number, device name, and channel count for each device.
        """
        num_devices = sbftdi.getNumDevices()
        serial_numbers: list[str] = []
        devices: list[tuple[str, str, int]] = []

        for i in range(0, num_devices):
            try:
                spi_device = sbftdi.sonoboticsFtdiChannel(
                    "SPI", "deviceNum", i)
            except Exception:
                continue
            eeprom_data = spi_device.readEEPROM()

            manufacturer = eeprom_data["Manufacturer"]
            serial_number = eeprom_data["Serial Number"]
            device = eeprom_data["Device"]

            if (
                (manufacturer == "Sonobotics")
                and serial_number != "0"
                and serial_number not in serial_numbers
                and device[0].isdigit()
            ):
                devices.append((serial_number, device, int(device[0])))
                serial_numbers.append(serial_number)

            spi_device.close()

        return devices

    def _validate_configuration(
        self,
        phase_array_microseconds: Optional[list[float]] = None,
        delay_array_microseconds: Optional[list[float]] = None,
        record_length: Optional[float] = None,
        prf: Optional[int] = None,
    ) -> Self:
        """
        Validate timing-related configuration values.

        Parameters:
        -----------
        phase_array_microseconds : list[float] | None, optional
            Per-channel trigger phase in microseconds.
        delay_array_microseconds : list[float] | None, optional
            Per-channel record delay in microseconds.
        record_length : float | None, optional
            Acquisition record length in seconds.
        prf : int | None, optional
            Pulse repetition frequency in hertz.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If the PRF is out of range or the configured signal exceeds its
            repetition period.
        """
        if phase_array_microseconds is None:
            phase_array_microseconds = self.phase_array_microseconds
        if delay_array_microseconds is None:
            delay_array_microseconds = self.delay_array_microseconds
        if record_length is None:
            record_length = self.record_length
        active_prf = prf if prf else self.prf

        if active_prf <= 0 or active_prf > 5000:
            raise ValueError("PRF must be between 1 and 5000")
        if (
            np.max(phase_array_microseconds) + np.max(delay_array_microseconds)
        ) / 1000000 + record_length >= 1 / active_prf:
            raise ValueError("Provided signal is invalid")
        return self

    @staticmethod
    def _encode_spi_command(command: list[Union[str, int]]) -> bytes:
        """Encode a five-byte SPI command."""

        command_hex = ""
        for value in command:
            if isinstance(value, str):
                command_hex += f"{ord(value):02x}"
            else:
                command_hex += f"{value:02x}"
        return bytes.fromhex(command_hex)

    def _write_spi_device(self, command: list[Union[str, int]]) -> None:
        """
        Write a configuration command and validate its acknowledgement.

        Parameters:
        -----------
        command : list[str | int]
            Five command bytes represented by characters or integers.

        Raises:
        -------
        OSError
            If the SPI device is not initialised.
        ValueError
            If the device reports an invalid command.
        RuntimeError
            If the device returns an unexpected acknowledgement.
        """
        if self.spi_device is None:
            raise IOError("SPI device is not initialised")
        if self.simulation:
            return
        self.spi_device.write(self._encode_spi_command(command))
        time.sleep(self.read_delay)
        response = self.spi_device.read(1)
        result = int.from_bytes(response, byteorder="big")
        if result == 50:
            return
        elif result == 200:
            raise ValueError("Device returned invalid response")
        else:
            raise RuntimeError("Device operation failed")

    def _query_spi_device(
        self,
        command: list[Union[str, int]],
        response_size: int,
        timeout: float = 0.5,
    ) -> bytes:
        """
        Send an SPI query and return its payload.

        Parameters:
        -----------
        command : list[str | int]
            Five command bytes represented by characters or integers.
        response_size : int
            Expected number of response bytes.
        timeout : float, optional
            Maximum time to wait for the response in seconds.

        Returns:
        --------
        bytes
            Raw response payload.

        Raises:
        -------
        OSError
            If the SPI device is not initialised.
        TimeoutError
            If the complete response is not received before the timeout.
        ValueError
            If the device reports an invalid command.
        """

        if self.spi_device is None:
            raise IOError("SPI device is not initialised")

        self.spi_device.write(self._encode_spi_command(command))
        response = bytearray()
        deadline = time.monotonic() + timeout

        while len(response) < response_size and time.monotonic() < deadline:
            chunk = self.spi_device.read(response_size - len(response))
            if chunk:
                response.extend(chunk)
            else:
                time.sleep(self.read_delay)

        if len(response) != response_size:
            raise TimeoutError("SPI query timed out")
        if all(byte == 200 for byte in response):
            raise ValueError("Device returned invalid response")

        return bytes(response)

    def set_config(
        self,
        num_cycles: int = 2,
        receive_channels: list[int] = [1, 0, 0, 0, 0, 0, 0, 0],
        drive_channels: list[int] = [1, 0, 0, 0, 0, 0, 0, 0],
        prf: int = 1000,
        num_averages: int = 100,
        record_length: float = 50e-6,
        phase_array_microseconds: list[float] = [0, 0, 0, 0, 0, 0, 0, 0],
        delay_array_microseconds: list[float] = [0, 0, 0, 0, 0, 0, 0, 0],
        sampling_mode: int = 24,
        excitation_clock_frequency: int = int(200e6),
        excitation_frequency: int = int(3.6e6),
        target_clock: int = int(50e6),
        polarity: str = "p",
        duty_cycle_1: float = 1.0,
        duty_cycle_2: float = 0.0,
        wheel_radius: float = 39.8 / 2,
        wheel_radius_1: Optional[float] = None,
        wheel_radius_2: Optional[float] = None,
        encoder_cpr: int = 2048,
        encoder_cpr_1: Optional[float] = None,
        encoder_cpr_2: Optional[float] = None,
        wheelbase: float = 40,
        wheelbase_1: Optional[float] = None,
        wheelbase_2: Optional[float] = None,
    ) -> Self:
        """
        Configure the device in the required command order.

        Parameters:
        -----------
        num_cycles : int, optional
            Number of excitation cycles.
        receive_channels : list[int], optional
            Eight-element receive-channel enable mask.
        drive_channels : list[int], optional
            Eight-element drive-channel duty-cycle array.
        prf : int, optional
            Pulse repetition frequency in hertz.
        num_averages : int, optional
            Number of acquisitions to average.
        record_length : float, optional
            Acquisition record length in seconds.
        phase_array_microseconds : list[float], optional
            Per-channel trigger phase in microseconds.
        delay_array_microseconds : list[float], optional
            Per-channel record delay in microseconds.
        sampling_mode : int, optional
            ADC sample width in bits.
        excitation_clock_frequency : int, optional
            Excitation clock frequency in hertz.
        excitation_frequency : int, optional
            Requested excitation frequency in hertz.
        target_clock : int, optional
            Requested ADC clock frequency in hertz.
        polarity : str, optional
            Excitation polarity code.
        duty_cycle_1 : float, optional
            Duty-cycle profile 1 setting from 0 to 1.
        duty_cycle_2 : float, optional
            Duty-cycle profile 2 setting from 0 to 1.
        wheel_radius : float, optional
            Shared wheel radius used when individual values are omitted.
        wheel_radius_1 : float | None, optional
            Radius of encoder wheel 1.
        wheel_radius_2 : float | None, optional
            Radius of encoder wheel 2.
        encoder_cpr : int, optional
            Shared encoder counts per revolution used when individual values
            are omitted.
        encoder_cpr_1 : float | None, optional
            Counts per revolution for encoder 1.
        encoder_cpr_2 : float | None, optional
            Counts per revolution for encoder 2.
        wheelbase : float, optional
            Total wheelbase used when individual offsets are omitted.
        wheelbase_1 : float | None, optional
            Distance from encoder wheel 1 to the reference point.
        wheelbase_2 : float | None, optional
            Distance from encoder wheel 2 to the reference point.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """

        self._calculate_num_chips(
            excitation_clock_frequency, excitation_frequency)

        self.sampling_mode = sampling_mode

        wheel_radius_1 = wheel_radius if wheel_radius_1 is None else wheel_radius_1
        wheel_radius_2 = wheel_radius if wheel_radius_2 is None else wheel_radius_2
        encoder_cpr_1 = encoder_cpr if encoder_cpr_1 is None else encoder_cpr_1
        encoder_cpr_2 = encoder_cpr if encoder_cpr_2 is None else encoder_cpr_2
        wheelbase_1 = wheelbase / 2 if wheelbase_1 is None else wheelbase_1
        wheelbase_2 = wheelbase / 2 if wheelbase_2 is None else wheelbase_2

        return (
            self._validate_configuration(
                phase_array_microseconds,
                delay_array_microseconds,
                record_length,
                prf,
            )
            .set_symbol(self.num_chips, num_cycles, polarity)
            .set_duty_cycles(duty_cycle_1, duty_cycle_2, drive_channels, self.num_chips)
            .set_receive_channels(receive_channels)
            .set_drive_channels(drive_channels)
            .set_encoder_parameters(
                wheel_radius_1,
                wheel_radius_2,
                encoder_cpr_1,
                encoder_cpr_2,
                wheelbase_1,
                wheelbase_2,
                wheelbase,
                wheel_radius,
                encoder_cpr,
            )
            .clear_encoders()
            .set_sampling_mode(sampling_mode)
            .set_target_clock(target_clock)
            .set_averages(num_averages)
            .set_prf(prf)
            .set_record_length(record_length)
            .set_trigger_phasing(phase_array_microseconds)
            .set_record_delay(delay_array_microseconds)
            ._configure_packet_sizes()
        )

    def _calculate_num_chips(
        self, excitation_clock_frequency: int, excitation_frequency: int
    ) -> Self:
        """
        Calculate the excitation chip count from two frequencies.

        Parameters:
        -----------
        excitation_clock_frequency : int
            Excitation clock frequency in hertz.
        excitation_frequency : int
            Requested excitation frequency in hertz.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        if self.version < 6784:
            self.excitation_clock_frequency = 50e6
        else:
            self.excitation_clock_frequency = excitation_clock_frequency
        self.excitation_frequency = excitation_frequency
        self.num_chips = int(
            round((self.excitation_clock_frequency / 2) / excitation_frequency)
        )
        return self

    def set_symbol(self, num_chips: int, num_cycles: int, polarity: str) -> Self:
        """
        Set the excitation symbol configuration.

        Parameters:
        -----------
        num_chips : int
            Number of chips from 1 to 100.
        num_cycles : int
            Number of cycles from 1 to 3.
        polarity : str
            Excitation polarity code.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If the chip or cycle count is out of range.
        """
        if num_chips > 100 or num_chips < 1:
            raise ValueError("Number of chips is out of range")
        elif num_cycles > 3 or num_cycles < 1:
            raise ValueError("Number of cycles is out of range")
        else:
            symbol: list[Union[str, int]] = [
                "1",
                num_chips,
                num_cycles,
                polarity,
                "a",
            ]
            self._write_spi_device(symbol)
            return self

    def set_receive_channels(self, receive_channels: list[int]) -> Self:
        """
        Set the receive-channel enable mask.

        Parameters:
        -----------
        receive_channels : list[int]
            Eight-element array containing 0 for disabled channels and 1 for
            enabled channels.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If the enabled channel count exceeds the device capacity.
        """
        reversed_receive_channels = receive_channels[::-1]
        channel_bits = "".join(map(str, reversed_receive_channels))
        channel_byte = int(channel_bits[-8:], 2)
        self.num_receive_channels = int(
            np.count_nonzero(reversed_receive_channels))
        self.enabled_receive_channels = [
            index for index, value in enumerate(receive_channels) if value == 1
        ]
        self.num_receive_channels = int(
            np.count_nonzero(reversed_receive_channels))
        self.enabled_receive_channels = [
            index for index, value in enumerate(receive_channels) if value == 1
        ]
        if self.num_receive_channels > self.max_channels:
            raise ValueError("Maximum number of channels exceeded")
        else:
            channel: list[Union[str, int]] = ["2", channel_byte, "a", "a", "a"]
            self._write_spi_device(channel)
            return self

    def set_drive_channels(self, drive_channels: list[int]) -> Self:
        """
        Set the drive-channel enable mask.

        Parameters:
        -----------
        drive_channels : list[int]
            Eight-element array where zero disables a channel and any non-zero
            value enables it.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If more than eight channels are enabled.
        """

        if self.version < 6784:
            self.num_drive_channels = range(0, self.max_channels)
            self.enabled_drive_channels = range(0, self.max_channels)
            return self

        drive_channels = [1 if ch != 0 else 0 for ch in drive_channels]
        reversed_drive_channels = drive_channels[::-1]
        channel_bits = "".join(map(str, reversed_drive_channels))
        channel_byte = int(channel_bits[-8:], 2)
        self.num_drive_channels = int(
            np.count_nonzero(reversed_drive_channels))
        self.enabled_drive_channels = [
            index for index, value in enumerate(drive_channels) if value == 1
        ]
        if self.num_drive_channels > 8:
            raise ValueError("Maximum number of channels exceeded")
        channel: list[Union[str, int]] = ["d", channel_byte, "a", "a", "a"]
        self._write_spi_device(channel)
        return self

    def set_duty_cycles(
        self,
        duty_cycle_1: float,
        duty_cycle_2: float,
        channel_duty_cycles: list[float],
        num_chips: int,
    ) -> Self:
        """
        Configure two duty-cycle profiles and select a profile for each channel.

        Parameters:
        -----------
        duty_cycle_1 : float
            Profile 1 duty-cycle setting from 0 to 1.
        duty_cycle_2 : float
            Profile 2 duty-cycle setting from 0 to 1.
        channel_duty_cycles : list[float]
            Eight channel values. Each non-zero value must match one of the two
            duty-cycle profiles.
        num_chips : int
            Number of chips per excitation cycle.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If a duty cycle, chip count, array length, or channel profile is
            invalid.
        """
        self._set_duty_cycle_profiles(duty_cycle_1, duty_cycle_2, num_chips)
        return self._set_channel_duty_cycles(channel_duty_cycles)

    def _set_duty_cycle_profiles(
        self, duty_cycle_1: float, duty_cycle_2: float, num_chips: int
    ) -> Self:
        """
        Configure the two FPGA duty-cycle profiles.

        Parameters:
        -----------
        duty_cycle_1 : float
            Profile 1 duty-cycle setting from 0 to 1.
        duty_cycle_2 : float
            Profile 2 duty-cycle setting from 0 to 1.
        num_chips : int
            Number of chips per excitation cycle.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If a duty cycle or chip count is invalid.
        """
        if self.version < 6784:
            return self

        if not 0.0 <= duty_cycle_1 <= 1.0:
            raise ValueError("Duty cycle 1 must be between 0 and 1")

        if not 0.0 <= duty_cycle_2 <= 1.0:
            raise ValueError("Duty cycle 2 must be between 0 and 1")

        if not 1 <= num_chips <= 100:
            raise ValueError("Number of chips must be between 1 and 100")

        self.duty_cycle_1 = float(duty_cycle_1)
        self.duty_cycle_2 = float(duty_cycle_2)

        # Input 1.0 represents maximum power, corresponding to a
        # physical high-time duty cycle of 0.5.
        physical_duty_1 = self.duty_cycle_1 / 2.0
        physical_duty_2 = self.duty_cycle_2 / 2.0

        total_chips = num_chips * 2

        high_chips_1 = round(total_chips * physical_duty_1 / 2) * 2
        high_chips_2 = round(total_chips * physical_duty_2 / 2) * 2

        low_chips_1 = total_chips - high_chips_1
        low_chips_2 = total_chips - high_chips_2

        self._write_spi_device(
            [
                "j",
                high_chips_1,
                high_chips_2,
                low_chips_1,
                low_chips_2,
            ]
        )

        return self

    def _set_channel_duty_cycles(self, channel_duty_cycles: list[float]) -> Self:
        """
        Select a configured duty-cycle profile for each channel.

        Parameters:
        -----------
        channel_duty_cycles : list[float]
            Eight channel values. Each non-zero value must match one of the
            configured duty-cycle profiles.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If the array length or a channel profile is invalid.
        """
        if self.version < 6784:
            return self

        if len(channel_duty_cycles) != 8:
            raise ValueError(
                "Channel duty cycles must contain exactly 8 values")

        profile_selection: list[int] = []

        for channel_index, value in enumerate(channel_duty_cycles):
            if np.isclose(value, 0.0):
                profile_selection.append(0)
            elif np.isclose(value, self.duty_cycle_1):
                profile_selection.append(0)
            elif np.isclose(value, self.duty_cycle_2):
                profile_selection.append(1)
            elif np.isclose(value, 1.0):
                profile_selection.append(0)
            else:
                raise ValueError(
                    f"Channel {channel_index + 1} value {value} does not "
                    f"match profile 1 ({self.duty_cycle_1}) or "
                    f"profile 2 ({self.duty_cycle_2})"
                )

        profile_byte = sum(
            selection << channel for channel, selection in enumerate(profile_selection)
        )

        self._write_spi_device(["k", profile_byte, "a", "a", "a"])

        return self

    def set_power_control(self, power_control: bool) -> Self:
        """
        Control the external power-control GPIO.

        Parameters:
        -----------
        power_control : bool
            True to assert the signal or False to deassert it.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        TypeError
            If power_control is not a Boolean value.
        """
        if not self.shm:
            return self

        if not isinstance(power_control, bool):
            raise TypeError("Power control must be True or False")

        power_byte = int(power_control)

        power: list[Union[str, int]] = ["e", power_byte, "a", "a", "a"]
        self._write_spi_device(power)

        return self

    def set_sampling_mode(self, sampling_mode: int) -> Self:
        """
        Set the ADC sample width for supported firmware.

        Parameters:
        -----------
        sampling_mode : int
            ADC sample width in bits. A value of 16 selects two-byte samples;
            all other values select the firmware's 24-bit default.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        if self.version < 6784:
            return self

        self.sampling_mode = sampling_mode

        if self.sampling_mode == 16:
            sampling_byte = 2
        else:  # Because the default case is 24 bits
            sampling_byte = 1

        sampling_command: list[Union[str, int]] = [
            "b",
            sampling_byte,
            "a",
            "a",
            "a",
        ]
        self._write_spi_device(sampling_command)
        return self

    def _write_counter_clear_mask(self, counter_clear_mask: list[int]) -> Self:
        """
        Write the FPGA counter-clear mask for supported firmware.

        Parameters:
        -----------
        counter_clear_mask : list[int]
            Eight-element counter-clear mask.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If more than five counters are selected.
        """
        if self.version < 6784:
            return self

        reversed_counter_clear_mask = counter_clear_mask[::-1]
        counter_clear_bits = "".join(map(str, reversed_counter_clear_mask))
        counter_clear_byte = int(counter_clear_bits[-8:], 2)
        self.num_clear_counters = int(
            np.count_nonzero(reversed_counter_clear_mask))
        self.enabled_clear_counters = [
            index
            for index, value in enumerate(reversed_counter_clear_mask)
            if value == 1
        ]

        if self.num_clear_counters > 5:
            raise ValueError("Maximum number of clear counters exceeded")
        else:
            counter_clear_command: list[Union[str, int]] = [
                "x",
                counter_clear_byte,
                "a",
                "a",
                "a",
            ]
            self._write_spi_device(counter_clear_command)
        return self

    def set_target_clock(self, target_clock: int) -> Self:
        """
        Set the closest supported FPGA target clock.

        Parameters:
        -----------
        target_clock : int
            Requested clock frequency in hertz.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        if self.version < 6784:
            return self

        if target_clock not in VALID_TARGET_CLOCKS:
            target_clock = min(VALID_TARGET_CLOCKS,
                               key=lambda x: abs(x - target_clock))

        if target_clock == int(100e6):
            clock_control_mask = [1, 0, 0, 0, 0, 0, 0, 0]
        elif target_clock == int(50e6):
            clock_control_mask = [0, 1, 0, 0, 0, 0, 0, 0]
        elif target_clock == int(25e6):
            clock_control_mask = [0, 0, 1, 0, 0, 0, 0, 0]
        else:
            clock_control_mask = [0, 1, 0, 0, 0, 0, 0, 0]

        clock_control_mask_reversed = clock_control_mask
        counter_clear_bits = "".join(map(str, clock_control_mask_reversed))
        counter_clear_byte = int(counter_clear_bits[-8:], 2)
        self.num_clear_counters = int(
            np.count_nonzero(clock_control_mask_reversed))
        self.selected_clock_bits = [
            index
            for index, value in enumerate(clock_control_mask_reversed)
            if value == 1
        ]

        if self.num_clear_counters > 5:
            raise ValueError("Maximum number of clear counters exceeded")
        else:
            clock_command: list[Union[str, int]] = [
                "c",
                counter_clear_byte,
                "a",
                "a",
                "a",
            ]
            self._write_spi_device(clock_command)
        try:
            self.adc_frequency = self.get_frequency()
        except ValueError:
            self.adc_frequency = DEFAULT_ADC_FREQUENCY

        return self

    def clear_encoders(self) -> Self:
        """
        Clear all encoder counters.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        if self.version < 6784:
            return self

        self._write_counter_clear_mask([1, 0, 0, 0, 0, 0, 0, 0])
        self._write_counter_clear_mask([0, 0, 0, 0, 0, 0, 0, 0])
        return self

    def set_averages(self, num_averages: int) -> Self:
        """
        Set the number of A-scans averaged per acquisition.

        Parameters:
        -----------
        num_averages : int
            Number of averages from 1 to 1000.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If num_averages is outside the supported range.
        """
        if num_averages > 1000:
            raise ValueError("Maximum number of averages exceeded")
        elif num_averages < 1:
            raise ValueError("Number of averages is too low")
        else:
            average_bits = np.binary_repr(num_averages, width=16)

            average: list[Union[str, int]] = [
                "3",
                int(average_bits[-8:], 2),
                int(average_bits[-16:-8], 2),
                "a",
                "a",
            ]
            self._write_spi_device(average)
            self.num_averages = num_averages
            return self

    def set_prf(self, prf: int) -> Self:
        """
        Set the pulse repetition frequency.

        Parameters:
        -----------
        prf : int
            Pulse repetition frequency from 1 to 5000 hertz.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If prf is outside the supported range.
        """
        if prf > 5000:
            raise ValueError("Maximum PRF exceeded")
        elif prf < 1:
            raise ValueError("PRF is too low")
        else:
            prf_count = int((1 / prf) / (1 / self.excitation_clock_frequency))
            prf_bits = np.binary_repr(prf_count, width=32)
            pulse: list[Union[str, int]] = [
                "4",
                int(prf_bits[-8:], 2),
                int(prf_bits[-16:-8], 2),
                int(prf_bits[-24:-16], 2),
                int(prf_bits[-32:-24]),
            ]

            self._write_spi_device(pulse)
            self.prf = prf
            return self

    def set_encoder_parameters(
        self,
        wheel_radius_1: float,
        wheel_radius_2: float,
        encoder_cpr_1: float,
        encoder_cpr_2: float,
        wheelbase_1: float,
        wheelbase_2: float,
        wheelbase: float,
        radius: float,
        cpr: float,
    ) -> Self:
        """
        Set encoder geometry and conversion coefficients.

        Parameters:
        -----------
        wheel_radius_1 : float
            Radius of encoder wheel 1.
        wheel_radius_2 : float
            Radius of encoder wheel 2.
        encoder_cpr_1 : float
            Counts per revolution for encoder 1.
        encoder_cpr_2 : float
            Counts per revolution for encoder 2.
        wheelbase_1 : float
            Distance from encoder wheel 1 to the reference point.
        wheelbase_2 : float
            Distance from encoder wheel 2 to the reference point.
        wheelbase : float
            Shared wheelbase from both encoder wheels to the reference point.
        radius : float
            Shared wheel radius from both encoder wheels to the reference point.
        cpr : float
            Shared counts per revolution for both wheels.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        if self.version >= 6800:
            try:
                k1 = np.float32(2 * np.pi * wheel_radius_1 / encoder_cpr_1)
                k2 = np.float32(2 * np.pi * wheel_radius_2 / encoder_cpr_2)
                wheelbase_total = wheelbase_1 + wheelbase_2
                inverse_wheelbase = np.float32(1 / wheelbase_total)

                self.encoder_cpr_1 = encoder_cpr_1
                self.encoder_cpr_2 = encoder_cpr_2
                self.wheel_radius_1 = wheel_radius_1
                self.wheel_radius_2 = wheel_radius_2
                self.wheelbase_1 = wheelbase_1
                self.wheelbase_2 = wheelbase_2
                self.encoder_cpr = encoder_cpr_1
                self.wheel_radius = wheel_radius_1
                self.wheelbase = wheelbase_1 + wheelbase_2

                k1_symbol = list(k1.tobytes())
                k2_symbol = list(k2.tobytes())
                wheelbase1_symbol = list(np.float32(wheelbase_1).tobytes())
                wheelbase2_symbol = list(np.float32(wheelbase_2).tobytes())
                inverse_wheelbase_symbol = list(inverse_wheelbase.tobytes())

                symbols = [
                    k1_symbol,
                    k2_symbol,
                    wheelbase1_symbol,
                    wheelbase2_symbol,
                    inverse_wheelbase_symbol,
                ]
                char_array = ["l", "m", "h", "i", "o"]

                for i, symbol in enumerate(symbols):
                    pulse: list[Union[str, int]] = [
                        char_array[i],
                        symbol[0],
                        symbol[1],
                        symbol[2],
                        symbol[3],
                    ]
                    self._write_spi_device(pulse)

                return self
            except Exception:
                return self
        elif self.version >= 6784:
            try:
                wheelbase_float32 = np.float32(1 / wheelbase)
                wheelbase_symbols = list(wheelbase_float32.tobytes())
                pulse: list[Union[str, int]] = [
                    "h",
                    wheelbase_symbols[0],
                    wheelbase_symbols[1],
                    wheelbase_symbols[2],
                    wheelbase_symbols[3],
                ]
                self._write_spi_device(pulse)
                self.wheelbase = wheelbase

                radius_float32 = np.float32(radius)
                cpr_float32 = np.float32(cpr)
                k1 = np.float32(2 * np.pi * radius_float32 / cpr_float32)
                k1_symbol = list(k1.tobytes())
                pulse: list[Union[str, int]] = [
                    "i",
                    k1_symbol[0],
                    k1_symbol[1],
                    k1_symbol[2],
                    k1_symbol[3],
                ]
                self._write_spi_device(pulse)
                self.wheel_radius = radius
                self.encoder_cpr = cpr
                return self

            except Exception:
                return self
        elif self.version < 6784:
            return self
        else:
            return self

    def get_version(self) -> int:
        """
        Read the packed firmware version from the FPGA.

        Returns:
        --------
        int
            Packed 16-bit firmware version.
        """

        if self.simulation:
            return 23

        try:
            response = self._query_spi_device(["v", "a", "a", "a", "a"], 2)
        except ValueError:
            return 256
        return (response[0] << 8) | response[1]

    def get_frequency(self) -> int:
        """
        Read the ADC sampling frequency from the FPGA.

        Returns:
        --------
        int
            ADC sampling frequency in hertz.
        """

        if self.simulation or self.version < 6784:
            return DEFAULT_ADC_FREQUENCY

        response = self._query_spi_device(["s", "a", "a", "a", "a"], 1)
        return int(response[0] * 1_000_000)

    def _set_adc_threshold(self) -> Self:
        """
        Write the configured ADC threshold and trigger mode.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        adc_bits = np.binary_repr(self.threshold_level, width=8)
        adc_byte = int(adc_bits[-8:], 2)

        adc_command: list[Union[str, int]] = [
            "5",
            str(self.trigger),
            adc_byte,
            "a",
            "a",
        ]
        self._write_spi_device(adc_command)
        return self

    def set_record_length(self, record_length: float) -> Self:
        """
        Set the acquisition record length.

        Parameters:
        -----------
        record_length : float
            Record length in seconds.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        self.record_length = record_length
        self.record_points = int(record_length * self.adc_frequency)
        record_length_bits = np.binary_repr(int(self.record_points), width=16)
        record_length_byte_1 = int(record_length_bits[-8:], 2)
        record_length_byte_2 = int(record_length_bits[-16:-8], 2)

        record: list[Union[str, int]] = [
            "6",
            record_length_byte_1,
            record_length_byte_2,
            "a",
            "a",
        ]
        self._write_spi_device(record)
        return self

    def set_trigger_phasing(self, phase_array_microseconds: list[float]) -> Self:
        """
        Set the trigger phase for each channel.

        Parameters:
        -----------
        phase_array_microseconds : list[float]
            Per-channel trigger phase in microseconds.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        self.phase_array_microseconds = phase_array_microseconds
        phase_cycles = np.ceil(
            np.array(phase_array_microseconds[::-1]
                     ) * self.adc_frequency / 1_000_000
        )
        phasing_active = any(phase_cycles > 0)
        if not phasing_active:
            phase_command: list[Union[str, int]] = [x for x in "7Naaa"]
            self._write_spi_device(phase_command)
        else:
            phase_indices = [
                index for index, value in enumerate(phase_cycles) if value != 0
            ]
            for i in phase_indices:
                phase_value = phase_cycles[i]
                phase_byte_1 = int(7 - i)
                phase_bits = np.binary_repr(int(phase_value), width=24)
                phase_byte_2 = int(phase_bits[-8:], 2)
                phase_byte_3 = int(phase_bits[-16:-8], 2)
                phase_byte_4 = int(phase_bits[-24:-16], 3)
                phase: list[Union[str, int]] = [
                    "7",
                    phase_byte_1,
                    phase_byte_2,
                    phase_byte_3,
                    phase_byte_4,
                ]
                self._write_spi_device(phase)
        return self

    def set_record_delay(self, delay_array_microseconds: list[float]) -> Self:
        """
        Set the acquisition delay for each channel.

        Parameters:
        -----------
        delay_array_microseconds : list[float]
            Per-channel record delay in microseconds.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        self.delay_array_microseconds = delay_array_microseconds
        delay_cycles = np.ceil(
            np.array(delay_array_microseconds[::-1]
                     ) * self.adc_frequency / 1_000_000
        )
        delay_active = any(delay_cycles > 0)
        if not delay_active:
            phase_command: list[Union[str, int]] = [x for x in "8Naaa"]
            self._write_spi_device(phase_command)
        else:
            delay_indices = [
                index for index, value in enumerate(delay_cycles) if value != 0
            ]
            for i in delay_indices:
                delay_value = delay_cycles[i]
                delay_byte_1 = int(7 - i)
                delay_bits = np.binary_repr(int(delay_value), width=24)
                delay_byte_2 = int(delay_bits[-8:], 2)
                delay_byte_3 = int(delay_bits[-16:-8], 2)
                delay_byte_4 = int(delay_bits[-24:-16], 3)
                delay: list[Union[str, int]] = [
                    "8",
                    delay_byte_1,
                    delay_byte_2,
                    delay_byte_3,
                    delay_byte_4,
                ]
                self._write_spi_device(delay)
        return self

    def _configure_packet_sizes(self) -> Self:
        """
        Calculate acquisition and peripheral packet sizes.

        Returns:
        --------
        Self
            The current instance for method chaining.
        """
        if self.version < 6784:
            return self
        if self.sampling_mode == 16:
            self.message_bytes = 2
        else:
            self.message_bytes = 3
        self.additional_bytes = sum(self.peripheral_byte_counts) + 2
        self.total_data_bytes = int(
            self.record_points * self.message_bytes * self.num_receive_channels
            + 2 * self.num_receive_channels
            - 1
        )
        self.total_bytes = self.total_data_bytes + self.additional_bytes

        return self

    def get_peripheral_data(self) -> list:
        """
        Return the peripheral values decoded during the latest acquisition.

        Returns:
        --------
        list
            Decoded peripheral values in firmware packet order.
        """
        return self.message_array

    def get_array(self) -> np.ndarray[tuple[int, int], np.dtype[np.float64]]:
        """
        Acquire echo data and decode the accompanying peripheral values.

        Returns:
        --------
        np.ndarray
            Echo samples with shape ``(num_receive_channels, record_points)``.

        Raises:
        -------
        OSError
            If the SPI device is not initialised.
        """
        if self.simulation:
            if self.adc_frequency <= 0:
                self.adc_frequency = DEFAULT_ADC_FREQUENCY
            if self.record_points <= 0:
                if self.record_length and self.record_length > 0:
                    self.record_points = int(
                        self.record_length * self.adc_frequency)
                else:
                    self.record_points = 2048
            if self.num_receive_channels <= 0:
                self.num_receive_channels = 1

            sim_dir = Path(__file__).resolve().parent / "simulator"
            sim_files = [
                sim_dir / "sample_ascan_6.25mm.npy",
                sim_dir / "sample_ascan_12.5mm.npy",
                sim_dir / "sample_ascan_18.75mm.npy",
                sim_dir / "sample_ascan_25mm.npy",
            ]

            switch_period_s = 5.0
            now = time.monotonic()

            if not hasattr(self, "_sim_file_index"):
                self._sim_file_index = 0
            if not hasattr(self, "_sim_last_switch_t"):
                self._sim_last_switch_t = now

            elapsed = now - self._sim_last_switch_t
            steps = int(elapsed // switch_period_s)
            if steps > 0:
                self._sim_file_index = (
                    self._sim_file_index + steps) % len(sim_files)
                self._sim_last_switch_t += steps * switch_period_s

            sim_file = sim_files[self._sim_file_index]

            clean: np.ndarray[tuple[int, int], np.dtype[np.float64]] = np.load(
                sim_file
            ).astype(float)
            if clean.ndim == 1:
                clean = clean.reshape(1, -1)
            clean = clean[: self.num_receive_channels, : self.record_points]

            noise_std = 100.0
            accumulator = np.zeros_like(clean)

            for _ in range(self.num_averages):
                accumulator += clean + \
                    np.random.normal(0.0, noise_std, clean.shape)

            echo_signal = accumulator / self.num_averages
            self.message_array = []
            return echo_signal

        if self.version < 6784:
            return self._get_array_legacy()

        if self.spi_device is None:
            raise IOError("SPI device is not initialised")

        self.spi_device.write(b"faaaa")
        time.sleep(self.num_averages / self.prf)

        response_byte = 0
        while response_byte != 100:
            response_chunk = self.spi_device.read(1)
            time.sleep(self.read_delay)
            response_byte = np.frombuffer(response_chunk, dtype=np.uint8)

        response_bytes = bytearray()
        remaining_bytes = self.total_bytes

        while remaining_bytes > self.max_read_chunk:
            response_bytes += self.spi_device.read(self.max_read_chunk)
            remaining_bytes -= self.max_read_chunk
        response_bytes += self.spi_device.read(remaining_bytes)

        array = np.frombuffer(response_bytes, dtype=np.uint8)
        array = np.insert(array, 0, 100)

        data_start = len(array) - 1 - self.additional_bytes + 2
        self.message_array = []

        for description, decoder, byte_count in zip(
            self.peripheral_descriptions,
            self.peripheral_decoders,
            self.peripheral_byte_counts,
        ):
            indices = np.arange(data_start, data_start + byte_count)
            data_start += byte_count

            result = decoder(array[indices])

            self.message_array.append(result)

            if description == "Internal Temperature":
                self.internal_temperature = result
            elif description == "External Temperature":
                self.external_temperature = result
            elif description == "Encoder 1":
                self.encoder_count_1 = result
            elif description == "Encoder 2":
                self.encoder_count_2 = result
            elif description == "Encoder Cart X":
                self.position_x = result
            elif description == "Encoder Cart Y":
                self.position_y = result
            elif description == "Encoder Cart Theta":
                self.position_theta = result
            elif description == "Encoder 3":
                self.encoder_count_3 = result

        indices_to_delete = np.arange(-1 * (self.additional_bytes + 1), -1)
        array = np.delete(array, indices_to_delete)
        arr_uint8 = array.astype(np.uint8)

        def _to_binary(x: int) -> str:
            """Convert one byte to an eight-character binary string."""
            return format(x, "08b")

        binary_strings = np.vectorize(_to_binary)(arr_uint8)

        channel = np.split(binary_strings, self.num_receive_channels)
        channel = [ch[1:-1] for ch in channel]

        byte_array = np.empty(
            (
                self.num_receive_channels,
                self.record_points,
                self.message_bytes,
            ),
            dtype="<U8",
        )
        reshaped_array = np.empty(
            (self.num_receive_channels, self.record_points), dtype=float
        )
        normalised_array = np.empty(
            (self.num_receive_channels, self.record_points), dtype=float
        )
        echo_signal = np.empty(
            (self.num_receive_channels, self.record_points), dtype=float
        )

        for i in range(self.num_receive_channels):
            byte_array[i] = np.reshape(channel[i], (-1, self.message_bytes))
            temp: list[float] = []
            for row in byte_array[i]:
                joined = "".join(row.tolist())
                if self.message_bytes == 2:
                    temp.append(bin16_to_int(joined))
                elif self.message_bytes == 3:
                    temp.append(bin24_to_int(joined))
            reshaped_array[i] = np.array(temp)
            normalised_array[i] = np.divide(
                reshaped_array[i], self.num_averages)

            if self.max_channels <= 4:
                inversion_array = [0, 3]
            else:
                inversion_array = [0, 1, 6, 7]

            if self.enabled_receive_channels[i] in inversion_array:
                echo_signal[i] = np.subtract(normalised_array[i], 2048) * -1
            else:
                echo_signal[i] = np.subtract(normalised_array[i], 2048)

        return echo_signal

    def _get_array_legacy(
        self,
    ) -> np.ndarray[tuple[int, int], np.dtype[np.float64]]:
        """
        Acquire echo data from a legacy firmware packet.

        Returns:
        --------
        np.ndarray
            Echo samples with shape ``(num_receive_channels, record_points)``.

        Raises:
        -------
        OSError
            If the SPI device is not initialised.
        """
        if self.spi_device is None:
            raise IOError("SPI device is not initialised")

        additional_bytes = 30

        self.spi_device.write(b"faaaa")
        time.sleep(self.num_averages / self.prf)

        response_byte = 0

        while response_byte != 100:
            response_chunk = self.spi_device.read(1)
            time.sleep(self.read_delay)
            response_byte = np.frombuffer(response_chunk, dtype=np.uint8)

        remaining_bytes = (
            int(
                self.record_points * self.message_bytes * self.num_receive_channels
                + 2 * self.num_receive_channels
                - 1
            )
            + additional_bytes
        )
        response_bytes = bytearray()
        while remaining_bytes > self.max_read_chunk:
            remaining_bytes -= self.max_read_chunk
            response_bytes += self.spi_device.read(self.max_read_chunk)
        response_bytes += self.spi_device.read(remaining_bytes)

        array = np.frombuffer(response_bytes, dtype=np.uint8)
        array = np.insert(array, 0, 100)

        self.internal_temperature = None
        self.external_temperature = None
        self.encoder_count_1 = None
        self.encoder_count_2 = None
        self.position_x = None
        self.position_y = None
        self.position_theta = None
        self.encoder_count_3 = None

        indices_to_delete = np.arange(-1 * (additional_bytes + 1), -1)
        array = np.delete(array, indices_to_delete)

        array = np.array(array, dtype=np.float16)

        channel = np.split(array, self.num_receive_channels)
        channel = [channel[1:-1] for channel in channel]

        raw_sample_bytes = np.empty(
            (
                self.num_receive_channels,
                self.record_points * self.message_bytes // 3,
                3,
            ),
            dtype=float,
        )
        reshaped_array = np.empty(
            (self.num_receive_channels, self.record_points), dtype=float
        )
        normalised_array = np.empty(
            (self.num_receive_channels, self.record_points), dtype=float
        )
        echo_signal = np.empty(
            (self.num_receive_channels, self.record_points), dtype=float
        )

        if self.max_channels <= 4:
            inversion_array = [0, 3]
        else:
            inversion_array = [0, 1, 6, 7]

        for i in range(self.num_receive_channels):
            raw_sample_bytes[i] = np.reshape(channel[i], (-1, 3))
            reshaped_array[i] = (
                raw_sample_bytes[i][:, 0]
                + raw_sample_bytes[i][:, 1] * (2**8)
                + raw_sample_bytes[i][:, 2] * (2**16)
            )
            normalised_array[i] = np.divide(
                reshaped_array[i], self.num_averages)
            if self.enabled_receive_channels[i] in inversion_array:
                echo_signal[i] = np.subtract(normalised_array[i], 2048) * -1
            else:
                echo_signal[i] = np.subtract(normalised_array[i], 2048)

        return echo_signal

    def set_sleep_time(self, sleep_time: int) -> Self:
        """
        Set the external microcontroller sleep time.

        Parameters:
        -----------
        sleep_time : int
            Sleep time in minutes from 0 to 20000.

        Returns:
        --------
        Self
            The current instance for method chaining.

        Raises:
        -------
        ValueError
            If sleep_time is outside the supported range.
        """
        if not self.shm:
            return self

        if sleep_time > 20000:
            raise ValueError("Maximum sleep time of 20000 exceeded")
        elif sleep_time < 0:
            raise ValueError("Sleep time cannot be negative")
        else:
            sleep_time_bits = np.binary_repr(sleep_time * 12, width=32)
            pulse: list[Union[str, int]] = [
                "r",
                int(sleep_time_bits[-8:], 2),
                "a",
                "a",
                "a",
            ]

            self._write_spi_device(pulse)
            return self

    def _detect_shm_capability(self) -> bool:
        """
        Detect whether the connected device supports SHM commands.

        Returns:
        --------
        bool
            True if the device supports SHM commands, False otherwise.
        """

        try:
            response = self._query_spi_device(["g", "a", "a", "a", "a"], 1)
            value = response[0]
            self.shm = True
        except (IOError, RuntimeError, TimeoutError, ValueError):
            value = 0
            self.shm = False
        return self.shm

    def close_device(self) -> None:
        """
        Close the Vitesse device connection.

        Raises:
        -------
        OSError
            If the SPI device is not initialised.
        """
        if self.spi_device is None:
            raise IOError("SPI device is not initialised")

        if not self.simulation:
            final_buffer = [0, 0, 0]
            while (
                final_buffer[-1] != 200
                or final_buffer[-2] != 200
                or final_buffer[-3] != 200
            ):
                final_buffer = np.frombuffer(
                    self.spi_device.read(1000), dtype=np.uint8)

        self.set_receive_channels([0, 0, 0, 0, 0, 0, 0, 0])
        self.spi_device.close()

        self.spi_device = None
