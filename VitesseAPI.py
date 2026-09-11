# API Compatible with binary version 26.9.0 and below
from __future__ import annotations
from types import FunctionType
from .utils import bin24_to_int, bin16_to_int, int_temp, ext_temp, dec_enc, dec_enc_float, decode_version
from . import sonoboticsFTDI as sbftdi
import time
import numpy as np
import sys
if sys.version_info >= (3, 11):
    from typing import Self, Optional, Union
else:
    from typing_extensions import Self, Optional, Union
from contextlib import contextmanager
from pathlib import Path

# Global constants
DEFAULT_ADC_FREQ = int(50e6)
VALID_TARGET_CLOCK = [int(50e6), int(25e6)]


@contextmanager
def initialiseVitesse(serialNumber: Optional[str] = None, simulation: bool = False):
    V = Vitesse().initialise(serialNumber, simulation)
    try:
        yield V
    finally:
        if V.spiDevice is not None:
            V.closeDevice()


class Vitesse:
    """
    Vitesse Python Wrapper
    """

    def __init__(self):
        """
        Initializes the Vitesse object with default values.
        """
        # SPI device object
        self.spiDevice: Optional[sbftdi.ftdiChannel] = None

        # Message transfer variables
        self.READ_DELAY: float = 500e-6
        self.MAX_READ_CHUNK = 64000
        self.THRESHOLD_LEVEL: int = 0
        self.TRIGGER: int = 0

        # Vitesse configuration parameters
        self.adcFrequency: int = DEFAULT_ADC_FREQ
        self.prf: int = 0
        self.recordLength: float = 0
        self.phaseArrayMicro: list[float] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.delayArrayMicro: list[float] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.samplingMode: int = 24
        self.numAverages: int = 100
        self.maxChannels: int = 0
        self.excitationClockFrequency: int = int(200e6)
        self.excitationFrequency: int = int(3.6e6)
        self.numChips: int = 0
        self.numChannelsOnReceive: int = 0
        self.ChannelsOnReceive: list[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.enabledChannelReceive: list[int] = [
            0, 0, 0, 0, 0, 0, 0, 0]
        self.numChannelsOnDrive: int = 0
        self.ChannelsOnDrive:  list[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.enabledChannelDrive: list[int] = [0, 0, 0, 0, 0, 0, 0, 0]
        self.recordPoints: int = 0
        self.numChannelsFromFPGA: int = 0
        self.polarity: str = 'p'
        self.dutyCycle1: float = 1.0
        self.dutyCycle2: float = 0.0
        self.simulation: bool = False

        # FPGA message decoding variables
        self.additionalBytes: int = 0
        self.totalDataBytes: int = 0
        self.totalBytes: int = 0
        self.messageArray: list[int] = []
        self.messageBytes: int = 3

        # Version information
        self.version: int = 0
        self.versionArray: list[int] = []
        self.apiVersion: list[int] = [26, 9, 0]

        # Peripheral data variables
        self.internalTemp: float = 0.0
        self.externalTemp: float = 0.0
        self.encoderIndex1: int = 0
        self.encoderIndex2: int = 0
        self.encoderIndex3: int = 0
        self.positionX: float = 0
        self.positionY: float = 0
        self.positionTheta: float = 0

        # Peripheral decoding arrays
        self.peripheralDescriptionArray: list[str] = ["Internal Temperature", "External Temperature",
                                                      "Encoder 1", "Encoder 2", "Encoder Cart X", "Encoder Cart Y", "Encoder Cart Theta", "Encoder 3"]
        self.peripheralDecodeArray: list[FunctionType] = [int_temp, ext_temp, dec_enc, dec_enc,
                                                          dec_enc_float, dec_enc_float, dec_enc_float, dec_enc]
        self.peripheralBytesArray: list[int] = [2, 2, 4, 4, 4, 4, 4, 4]

        # Encoder parameter variables
        self.wheelbase: float = 0
        self.wheelRadius: float = 0
        self.encoderCpr: float = 0
        self.encoderCpr1: float = 0
        self.encoderCpr2: float = 0
        self.wheelRadius1: float = 0
        self.wheelRadius2: float = 0
        self.wheelbase1: float = 0
        self.wheelbase2: float = 0

        # Additional variables
        self.SHM: bool = False

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):  # type: ignore
        if self.spiDevice is not None:
            self.closeDevice()

    def initialise(self, serialNumber: Optional[str] = None, simulation: bool = False) -> Self:
        """
        Initialises a connected Vitesse device, or a virtual (simulated) device if simulation == True.

        Args:
            serialNumber (Optional[str], optional):
            The serial number of the Vitesse device to connect.
            If not provided, it could choose any of the connected Vitesse devices (if any).

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError: The provided serial number does not belong to a Vitesse device.
            IOError: No SPI device found, or none of the devices is a Vitesse device.
        """

        self.simulation = simulation
        if self.simulation:
            self.spiDevice = sbftdi.ftdiChannel()
            self.maxChannels = 8
            self.setAdcThreshold()
            self.version = 23
            self.versionArray = [23, 1, 0]
            self.adcFrequency = DEFAULT_ADC_FREQ
            return self

        devices = self.listDevices()
        serialNumbers = [serialNumber for (serialNumber, _, _) in devices]
        if len(devices) == 0:
            raise IOError("No Vitesse device connected.")

        if type(serialNumber) == str:
            if serialNumber not in serialNumbers:
                raise ValueError(
                    "The serial number indicated does not belong to a Vitesse device.")
        else:
            serialNumber = serialNumbers[0]

        serialNumber = serialNumber + "B"

        self.spiDevice = sbftdi.sonoboticsFtdiChannel(
            "SPI", "serialNum", serialNumber.encode())

        # Clearing the buffer
        initialarray = [0, 0, 0]
        while initialarray[-1] != 200 or initialarray[-2] != 200 or initialarray[-3] != 200:
            initialarray = np.frombuffer(
                self.spiDevice.read(1000), dtype=np.uint8)

        self.maxChannels = devices[0][2]
        self.setAdcThreshold()

        try:
            self.version = self.getVersion()
        except ValueError:
            # Handle for legacy FPGA binaries
            self.version = 256

        self.versionArray = decode_version(self.version)

        try:
            self.adcFrequency = self.getFrequency()
        except ValueError:
            # Handle for legacy FPGA binaries
            self.adcFrequency = DEFAULT_ADC_FREQ

        # Load default parameters
        self.setConfig()

        return self

    @staticmethod
    def listDevices() -> list[tuple[str, str, int]]:
        """
        Lists the actual Vitesse devices currently connected to the device. Virtual devices are not counted.

        Returns:
            devices (list[(serialNumber: str, deviceName: str, numberOfChannels: int)]): list of tuples containing Vitesse device information.
        """
        numDevices = sbftdi.getNumDevices()
        serialNumbers: list[str] = []
        devices: list[tuple[str, str, int]] = []

        for i in range(0, numDevices):
            try:
                spiDevice = sbftdi.sonoboticsFtdiChannel("SPI", "deviceNum", i)
            except Exception:
                # Cannot connect to a device, probably because it's locked by other process; omit it
                continue
            eepromData = spiDevice.readEEPROM()

            manufacturer = eepromData['Manufacturer']
            serialNumber = eepromData['Serial Number']
            device = eepromData['Device']

            if ((manufacturer == 'Sonobotics')
                    and serialNumber != "0"
                    and serialNumber not in serialNumbers
                    and device[0].isdigit()):
                devices.append((serialNumber, device, int(device[0])))
                serialNumbers.append(serialNumber)

            spiDevice.close()

        return devices

    def checkValidity(self, phaseArrayMicro: Optional[list[float]] = None, delayArrayMicro: Optional[list[float]] = None, recordLength: Optional[float] = None, PRF: Optional[int] = None) -> Self:
        """
        Checks validity of a set of Vitesse configuration parameters.

        Args:
            phaseArrayMicro (list[float]): Phasing in microseconds for each channel e.g. [Channel 1 Phase (us), Channel 2 Phase (us), etc.]
            delayArrayMicro (list[float]): Delay in microseconds for each channel e.g. [Channel 1 Delay (us), Channel 2 Delay (us), etc.]
            recordLength (float): Record Length Range
            PRF (int): PRF Range: 1 to 5000 Hz

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError
        """
        if phaseArrayMicro is None:
            phaseArrayMicro = self.phaseArrayMicro
        if delayArrayMicro is None:
            delayArrayMicro = self.delayArrayMicro
        if recordLength is None:
            recordLength = self.recordLength
        activePrf = PRF if PRF else self.prf

        if activePrf <= 0 or activePrf > 5000:
            raise ValueError('PRF value invalid')
        if (np.max(phaseArrayMicro) + np.max(delayArrayMicro)) / 1000000 + recordLength >= 1/activePrf:
            raise ValueError('Provided signal is invalid')
        return self

    def _writeSpiDevice(self, chars: list[Union[str, int]]) -> None:
        """
        Writes data to the SPI device and raises exceptions on failure.

        Args:
            chars (list[Union[str, int]]): List of bytes as characters/integers to send to the device.

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            IOError: If SPI device is not initialised.
            ValueError: If device returns invalid response (200).
            RuntimeError: If device operation fails (other response codes).
        """
        if self.spiDevice is None:
            raise IOError(
                "SPI Device not initialised. Perhaps you forgot to call initialise()")
        if self.simulation:
            # Do not write anything in simulation mode
            return
        channelStr = ""
        for char in chars:
            if type(char) == str:
                channelStr += f"{ord(char):02x}"
            else:
                channelStr += f"{char:02x}"
        channelByt = bytes.fromhex(channelStr)

        self.spiDevice.write(channelByt)
        time.sleep(self.READ_DELAY)
        dataBack = self.spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        if result == 50:
            return
        elif result == 200:
            raise ValueError("Device returned invalid response")
        else:
            raise RuntimeError("Device operation failed")

    def setConfig(self,
                  numCycles:            int = 2,
                  channelsOnReceive:    list[int] = [1, 0, 0, 0, 0, 0, 0, 0],
                  channelsOnDrive:     list[int] = [1, 0, 0, 0, 0, 0, 0, 0],
                  PRF:                  int = 1000,
                  numAverages:          int = 100,
                  recordLength:         float = 50e-6,
                  phaseArrayMicro:      list[float] = [0, 0, 0, 0, 0, 0, 0, 0],
                  delayArrayMicro:      list[float] = [0, 0, 0, 0, 0, 0, 0, 0],
                  samplingMode:         int = 24,
                  excitationClockFrequency:       int = int(200e6),
                  excitationFrequency:          int = int(3.6e6),
                  targetClock:          int = int(50e6),
                  polarity:             str = 'p',
                  dutyCycle1: float = 1.0,
                  dutyCycle2: float = 0.0,
                  wheelRadius:          float = 39.8/2,
                  wheelRadius1: Optional[float] = None,
                  wheelRadius2: Optional[float] = None,
                  encoderCpr:           int = 2048,
                  encoderCpr1: Optional[float] = None,
                  encoderCpr2: Optional[float] = None,
                  wheelbase:     float = 40,
                  wheelbase1: Optional[float] = None,
                  wheelbase2: Optional[float] = None
                  ) -> Self:
        """
        Configures the Vitesse device with the specified parameters.
        This is recommended over setting each parameter manually, since this ensures the
        correct precedence of the parameters.

        Returns:
            Self: Returns the instance for method chaining.
        """

        self.setNumChips(excitationClockFrequency, excitationFrequency)

        self.samplingMode = samplingMode

        # Set encoder parameters, using provided values or defaults if not provided
        wheelRadius1 = wheelRadius if wheelRadius1 is None else wheelRadius1
        wheelRadius2 = wheelRadius if wheelRadius2 is None else wheelRadius2
        encoderCpr1 = encoderCpr if encoderCpr1 is None else encoderCpr1
        encoderCpr2 = encoderCpr if encoderCpr2 is None else encoderCpr2
        wheelbase1 = wheelbase / 2 if wheelbase1 is None else wheelbase1
        wheelbase2 = wheelbase / 2 if wheelbase2 is None else wheelbase2

        return self.checkValidity(phaseArrayMicro, delayArrayMicro, recordLength, PRF) \
            .setSymbol(self.numChips, numCycles, polarity) \
            .setDutyCycles(dutyCycle1, dutyCycle2, channelsOnDrive, self.numChips) \
            .setChannelReceive(channelsOnReceive) \
            .setChannelDrive(channelsOnDrive) \
            .setEncoderParameters(wheelRadius1, wheelRadius2, encoderCpr1, encoderCpr2, wheelbase1, wheelbase2, wheelbase, wheelRadius, encoderCpr) \
            .clearEncoders() \
            .setSamplingMode(samplingMode) \
            .setClockControlEnable(targetClock) \
            .setAverages(numAverages) \
            .setPrf(PRF) \
            .setRecordLength(recordLength) \
            .setTriggerPhasing(phaseArrayMicro) \
            .setRecordDelay(delayArrayMicro) \
            .configureAttributes()

    def setNumChips(self, excitationClockFrequency: int, excitationFrequency: int) -> Self:
        """
        Sets the excitation clock frequency, excitation frequency and the number of chips calculated from the two values.

        Args:
            excitationClockFrequency (int)
            excitationFrequency (int)

        Returns:
            Self: Returns the instance for method chaining.
        """
        if self.version < 6784:
            self.excitationClockFrequency = 50e6
        else:
            self.excitationClockFrequency = excitationClockFrequency
        self.excitationFrequency = excitationFrequency
        self.numChips = int(
            round((self.excitationClockFrequency / 2) / excitationFrequency))
        return self

    def setSymbol(self, numChips: int, numCycles: int, polarity: str) -> Self:
        """
        Sets the symbol configuration for the Vitesse device.

        Args:
            numChips (int): Number of chips (range: 1-100).
            numCycles (int): Number of cycles (range: 1-3).

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError: If numChips or numCycles are out of range.
            RuntimeError: If device operation fails.
        """
        if numChips > 100 or numChips < 1:
            raise ValueError('Number of chips out of range.')
        elif numCycles > 3 or numCycles < 1:
            raise ValueError('Number of cycles out of range.')
        else:
            symbol: list[Union[str, int]] = [
                '1', numChips, numCycles, polarity, 'a']
            self._writeSpiDevice(symbol)
            return self

    def setChannelReceive(self, channelsOnReceive: list[int]) -> Self:
        """
        Enables/disables channels on the Vitesse device.

        Args:
            channelsOnReceive (list[int]): Array of 0s and 1s indicating which channels to enable.

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError: If maximum number of channels is exceeded.
            RuntimeError: If device operation fails.
        """
        reversedchannelsOnReceive = channelsOnReceive[::-1]
        channelsOn = ''.join(map(str, reversedchannelsOnReceive))
        channelByte = int(channelsOn[-8:], 2)
        self.numChannelsOnReceive = int(
            np.count_nonzero(reversedchannelsOnReceive))
        self.enabledChannelReceive = [
            index for index, value in enumerate(channelsOnReceive) if value == 1]
        self.numChannelsOnReceive = int(
            np.count_nonzero(reversedchannelsOnReceive))
        self.enabledChannelReceive = [
            index for index, value in enumerate(channelsOnReceive) if value == 1]
        if self.numChannelsOnReceive > self.maxChannels:
            raise ValueError('Maximum number of channels exceeded!\n')
        else:
            channel: list[Union[str, int]] = ['2', channelByte, 'a', 'a', 'a']
            self._writeSpiDevice(channel)
            return self

    def setChannelDrive(self, channelsOnDrive: list[int]) -> Self:
        """
        Enables/disables driving channels on the Vitesse device.

        Args:
            channelsOnDrive (list[int]): Array of 0s and 1s indicating which channels to enable.

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError: If maximum number of channels is exceeded.
            RuntimeError: If device operation fails.
        """

        if self.version < 6784:
            self.numChannelsOnDrive = range(0, self.maxChannels)
            self.enabledChannelDrive = range(0, self.maxChannels)
            return self

        channelsOnDrive = [1 if ch != 0 else 0 for ch in channelsOnDrive]
        reversedchannelsOnDrive = channelsOnDrive[::-1]
        channelsOn = ''.join(map(str, reversedchannelsOnDrive))
        channelByte = int(channelsOn[-8:], 2)
        self.numChannelsOnDrive = int(
            np.count_nonzero(reversedchannelsOnDrive))
        self.enabledChannelDrive = [
            index for index, value in enumerate(channelsOnDrive) if value == 1]
        if self.numChannelsOnDrive > 8:
            raise ValueError('Maximum number of channels exceeded!\n')
        channel: list[Union[str, int]] = ['d', channelByte, 'a', 'a', 'a']
        self._writeSpiDevice(channel)
        return self

    def setDutyCycles(self, dutyCycle1: float, dutyCycle2: float, channelDutyCycles: list[float], numChips: int) -> Self:
        """
        Configure two duty-cycle profiles and select a profile for each channel.

        Args:
            dutyCycle1: Profile 1 power setting, from 0.0 to 1.0.
            dutyCycle2: Profile 2 power setting, from 0.0 to 1.0.
            channelDutyCycles: Eight channel values. Each non-zero value must
                match dutyCycle1 or dutyCycle2.
            numChips: Number of chips per excitation cycle.
        """
        if self.version < 6784:
            return self

        if not 0.0 <= dutyCycle1 <= 1.0:
            raise ValueError("dutyCycle1 must be between 0 and 1.")

        if not 0.0 <= dutyCycle2 <= 1.0:
            raise ValueError("dutyCycle2 must be between 0 and 1.")

        if not 1 <= numChips <= 100:
            raise ValueError("numChips must be between 1 and 100.")

        if len(channelDutyCycles) != 8:
            raise ValueError(
                "channelDutyCycles must contain exactly 8 values."
            )

        self.dutyCycle1 = float(dutyCycle1)
        self.dutyCycle2 = float(dutyCycle2)

        # Input 1.0 represents maximum power, corresponding to a
        # physical high-time duty cycle of 0.5.
        physicalDuty1 = self.dutyCycle1 / 2.0
        physicalDuty2 = self.dutyCycle2 / 2.0

        totalChips = numChips * 2

        numChipsHigh1 = round(
            totalChips * physicalDuty1 / 2
        ) * 2
        numChipsHigh2 = round(
            totalChips * physicalDuty2 / 2
        ) * 2

        numChipsLow1 = totalChips - numChipsHigh1
        numChipsLow2 = totalChips - numChipsHigh2

        self._writeSpiDevice(['j',numChipsHigh1,numChipsHigh2,numChipsLow1,numChipsLow2,])

        # Select profile 1 or 2 for each channel.
        profileSelection: list[int] = []

        for channelIndex, value in enumerate(channelDutyCycles):
            if np.isclose(value, 0.0):
                # Disabled channel: selection is irrelevant.
                profileSelection.append(0)
            elif np.isclose(value, self.dutyCycle1):
                profileSelection.append(0)
            elif np.isclose(value, self.dutyCycle2):
                profileSelection.append(1)
            elif np.isclose(value, 1.0):
                # Supports binary channel-enable arrays by selecting profile 1.
                profileSelection.append(0)
            else:
                raise ValueError(
                    f"Channel {channelIndex + 1} value {value} does not "
                    f"match profile 1 ({self.dutyCycle1}) or "
                    f"profile 2 ({self.dutyCycle2})."
                )

        profileByte = sum(
            selection << channel
            for channel, selection in enumerate(profileSelection)
        )

        self._writeSpiDevice(['k', profileByte, 'a', 'a', 'a'])

        return self

    def setPowerControl(self, powerControl: bool) -> Self:
        """
        Controls the external power-control GPIO.

        Args:
            powerControl: True to assert the power-control signal;
                          False to deassert it.

        Returns:
            Self: The current instance for method chaining.
        """
        if not self.SHM:
            return self

        if not isinstance(powerControl, bool):
            raise TypeError("powerControl must be True or False")

        powerByte = int(powerControl)

        power: list[Union[str, int]] = [
            'e', powerByte, 'a', 'a', 'a'
        ]
        self._writeSpiDevice(power)

        return self

    def setSamplingMode(self, samplingMode: int) -> Self:
        """
        Sets the sampling mode on the Vitesse device.
        Not compatible with (thus will be skipped on) legacy binaries where version number is not present.

        Args:
            samplingMode (int): Length in bits of the appended sampling data.

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError: If maximum number of sampling modes is exceeded.
            RuntimeError: If device operation fails.
        """
        # backward compatible with older firmware
        if (self.version < 6784):
            return self

        self.samplingMode = samplingMode

        if self.samplingMode == 16:
            samplingByte = 2
        else:  # Because the default case in the SV code is 24 bits
            samplingByte = 1

        samplingCommand: list[Union[str, int]] = [
            'b', samplingByte, 'a', 'a', 'a']
        self._writeSpiDevice(samplingCommand)
        return self

    def clearCounterEnable(self, clearCountersOnArray: list[int]) -> Self:
        """
        Clears counters on the Vitesse device.
        Not compatible with (thus will be skipped on) legacy binaries where version number is not present.

        Args:
            clearCountersOnArray (list[int]): Array of 0s and 1s indicating which counters to clear.

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError: If maximum number of clear counters is exceeded.
            RuntimeError: If device operation fails.
        """
        # backward compatible with older firmware
        if (self.version < 6784):
            return self

        reversedClearCountersOnArray = clearCountersOnArray[::-1]
        clearCountersOn = ''.join(map(str, reversedClearCountersOnArray))
        clearCounterByte = int(clearCountersOn[-8:], 2)
        self.numClearCountersOn = int(
            np.count_nonzero(reversedClearCountersOnArray))
        self.numClearCountersOnArray = [index for index, value in enumerate(
            reversedClearCountersOnArray) if value == 1]

        if self.numClearCountersOn > 5:
            raise ValueError('Maximum number of clear counters exceeded!\n')
        else:
            clearCounter: list[Union[str, int]] = [
                'x', clearCounterByte, 'a', 'a', 'a']
            self._writeSpiDevice(clearCounter)
        return self

    def setClockControlEnable(self, targetClock: int) -> Self:
        """
        Set the clock control for the FPGA.

        :param targetClock: the target clock frequency. If the entered frequency is not among the
            supported frequencies, the frequency will be rounded to the nearest supported frequency.
        :type targetClock: int
        :return: Returns the instance for method chaining.
        :rtype: Self
        """
        # backward compatible with older firmware
        if (self.version < 6784):
            return self

        validClocks = [int(100e6), int(50e6), int(25e6)]

        if targetClock not in validClocks:
            targetClock = min(validClocks, key=lambda x: abs(x - targetClock))

        # Target Clock here will never evaluate to 100e6 or the fallback since it is not in VALID_CLOCKS.
        if targetClock == int(100e6):
            clockControlArray = [1, 0, 0, 0, 0, 0, 0, 0]
        elif targetClock == int(50e6):
            clockControlArray = [0, 1, 0, 0, 0, 0, 0, 0]
        elif targetClock == int(25e6):
            clockControlArray = [0, 0, 1, 0, 0, 0, 0, 0]
        else:
            clockControlArray = [0, 1, 0, 0, 0, 0, 0, 0]

        reversedclockControlArray = clockControlArray
        clearCountersOn = ''.join(map(str, reversedclockControlArray))
        clearCounterByte = int(clearCountersOn[-8:], 2)
        self.numClearCountersOn = int(
            np.count_nonzero(reversedclockControlArray))
        self.numclockControlArray = [index for index, value in enumerate(
            reversedclockControlArray) if value == 1]

        if self.numClearCountersOn > 5:
            raise ValueError('Maximum number of clear counters exceeded!\n')
        else:
            clearCounterCommand: list[Union[str, int]] = [
                'c', clearCounterByte, 'a', 'a', 'a']
            self._writeSpiDevice(clearCounterCommand)
        try:
            self.adcFrequency = self.getFrequency()
        except ValueError:
            # Handle for legacy FPGA binaries
            self.adcFrequency = DEFAULT_ADC_FREQ

        return self

    def clearEncoders(self):
        """
        Clears the encoders on the FPGA.

        Returns:
            Self: Returns the instance for method chaining.
        """
        # backward compatible with older firmware
        if (self.version < 6784):
            return self

        self.clearCounterEnable([1, 0, 0, 0, 0, 0, 0, 0])
        self.clearCounterEnable([0, 0, 0, 0, 0, 0, 0, 0])
        return self

    def setAverages(self, numAverages: int) -> Self:
        """
        Sets the number of A-Scans to average over before returning an averaged A-Scan.

        Args:
            numAverages (int): Number of averages (range: 1-1000).

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError: If numAverages is out of range.
            RuntimeError: If device operation fails.
        """
        if numAverages > 1000:
            raise ValueError('Maximum number of averages exceeded!\n')
        elif numAverages < 1:
            raise ValueError('Number of averages too low!')
        else:
            bitAveVals = np.binary_repr(numAverages, width=16)

            average: list[Union[str, int]] = [
                '3', int(bitAveVals[-8:], 2), int(bitAveVals[-16:-8], 2), 'a', 'a']
            self._writeSpiDevice(average)
            # Update number of averages upon success
            self.numAverages = numAverages
            return self

    def setPrf(self, PRF: int) -> Self:
        """
        Sets the Pulse Repetition Frequency (PRF) of the device.

        Args:
            PRF (int): Pulse Repetition Frequency in Hz (range: 1-5000).

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            ValueError: If PRF is out of range.
            RuntimeError: If device operation fails.
        """
        if PRF > 5000:
            raise ValueError('Maximum PRF exceeded.')
        elif PRF < 1:
            raise ValueError('PRF too low.')
        else:
            PRFCount = int((1/PRF)/(1/self.excitationClockFrequency))
            bitPRFVals = np.binary_repr(PRFCount, width=32)
            pulse: list[Union[str, int]] = ['4', int(bitPRFVals[-8:], 2), int(
                bitPRFVals[-16:-8], 2), int(bitPRFVals[-24:-16], 2), int(bitPRFVals[-32:-24])]

            self._writeSpiDevice(pulse)
            self.prf = PRF
            return self

    def setEncoderParameters(self, wheelRadius1: float, wheelRadius2: float, encoderCpr1: float, encoderCpr2: float, wheelbase1: float, wheelbase2: float, wheelbase: float, radius: float, CPR: float) -> Self:
        if self.version >= 6800:
            try:
                k1 = np.float32(2 * np.pi * wheelRadius1 / encoderCpr1)
                k2 = np.float32(2 * np.pi * wheelRadius2 / encoderCpr2)
                l = wheelbase1 + wheelbase2
                l_inv = np.float32(1/l)

                self.encoderCpr1 = encoderCpr1
                self.encoderCpr2 = encoderCpr2
                self.wheelRadius1 = wheelRadius1
                self.wheelRadius2 = wheelRadius2
                self.wheelbase1 = wheelbase1
                self.wheelbase2 = wheelbase2
                self.encoderCpr = encoderCpr1
                self.wheelRadius = wheelRadius1
                self.wheelbase = wheelbase1 + wheelbase2

                k1_symbol = list(k1.tobytes())
                k2_symbol = list(k2.tobytes())
                wheelbase1_symbol = list(np.float32(wheelbase1).tobytes())
                wheelbase2_symbol = list(np.float32(wheelbase2).tobytes())
                l_inv_symbol = list(l_inv.tobytes())

                symbol_Array = [k1_symbol, k2_symbol,
                                wheelbase1_symbol, wheelbase2_symbol, l_inv_symbol]
                char_array = ['l', 'm', 'h', 'i', 'o']

                for i, symbol in enumerate(symbol_Array):
                    pulse: list[Union[str, int]] = [char_array[i],
                                                    symbol[0], symbol[1], symbol[2], symbol[3]]
                    self._writeSpiDevice(pulse)

                return self
            except:
                return self
        elif (self.version >= 6784):
            try:
                wheelbase_float32 = np.float32(1/wheelbase)
                wheelbase_symbols = list(wheelbase_float32.tobytes())
                pulse: list[Union[str, int]] = ['h', wheelbase_symbols[0],
                                                wheelbase_symbols[1], wheelbase_symbols[2], wheelbase_symbols[3]]
                self._writeSpiDevice(pulse)
                self.wheelbase = wheelbase

                radius_float32 = np.float32(radius)
                CPR_float32 = np.float32(CPR)
                k1 = np.float32(2*np.pi*radius_float32/CPR_float32)
                k1_symbol = list(k1.tobytes())
                pulse: list[Union[str, int]] = ['i', k1_symbol[0],
                                                k1_symbol[1], k1_symbol[2], k1_symbol[3]]
                self._writeSpiDevice(pulse)
                self.wheelRadius = radius
                self.encoderCpr = CPR
                return self

            except:
                return self
        elif (self.version < 6784):
            return self
        else:
            return self

    def getVersion(self) -> int:
        """
        Get the bitstream version from the FPGA.
        Pattern:
        1) Try to send via _writeSpiDevice (expects/consumes 1 status byte).
        2) If that fails (likely no status for 'v'), resend raw.
        3) Read exactly two data bytes (hi, lo), skipping any stray status markers.
        4) Returns the version if success, -1 if failed.

        :return: The FPGA bitstream version.
        :rtype: int
        """
        if self.simulation:
            return 23

        if self.spiDevice is None:
            raise IOError(
                "SPI Device not initialised. Perhaps you forgot to call initialise()")

        version_command: list[Union[str, int]] = ['v', 'a', 'a', 'a', 'a']

        try:
            self._writeSpiDevice(version_command)
        except ValueError:
            raise ValueError(
                "getVersion: device returned 'Invalid' (200) for version command.")
        except RuntimeError:
            self.spiDevice.write(b'vaaaa')

        got = bytearray()
        deadline = time.monotonic() + 0.5

        while time.monotonic() < deadline and len(got) < 2:
            chunk = self.spiDevice.read(1)
            if not chunk:
                time.sleep(self.READ_DELAY)
                continue
            b = chunk[0]
            if b in (50, 200):
                continue
            got.append(b)

        if len(got) < 2:
            raise TimeoutError(f"getVersion: timeout; received={list(got)}")

        hi, lo = got[0], got[1]
        version_u16 = (hi << 8) | lo
        return version_u16

    def getFrequency(self) -> int:
        """
        Get the ADC sampling frequency (single byte) from the FPGA.
        Matches the existing pattern: send via _writeSpiDevice, then read.

        :return: The ADC sampling frequency.
        :rtype: int
        """

        if self.simulation or self.version < 6784:
            return DEFAULT_ADC_FREQ
        if self.spiDevice is None:
            raise IOError(
                "SPI Device not initialised. Perhaps you forgot to call initialise()")

        freq_command: list[Union[str, int]] = ['s', 'a', 'a', 'a', 'a']

        try:
            self._writeSpiDevice(freq_command)
        except ValueError:
            raise ValueError(
                "getFrequency: device returned 'Invalid' (200) for frequency command.")
        except RuntimeError:
            self.spiDevice.write(b'saaaa')
            time.sleep(self.READ_DELAY)

        time.sleep(self.READ_DELAY)
        b = self.spiDevice.read(1)
        if not b:
            raise TimeoutError("getFrequency: timeout (no byte).")

        val = b[0]
        if val in (50, 200):
            time.sleep(self.READ_DELAY)
            b = self.spiDevice.read(1)
            if not b:
                raise TimeoutError("getFrequency: timeout after status byte.")
            val = b[0]

        return int(val*1000000)

    def setAdcThreshold(self) -> Self:
        """
        Sets the ADC threshold level on the device.

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            RuntimeError: If device operation fails.
        """
        bitADCVals = np.binary_repr(self.THRESHOLD_LEVEL, width=8)
        numADCByte = int(bitADCVals[-8:], 2)

        ADC: list[Union[str, int]] = [
            '5', str(self.TRIGGER), numADCByte, 'a', 'a']
        self._writeSpiDevice(ADC)
        return self

    def setRecordLength(self, recordLength: float) -> Self:
        """
        Sets the record length for data acquisition.

        Args:
            recordLength (float): Record length in seconds. Range varies by channel count:
                                 0-100 us (8 CH), 0-200 us (4 CH), 0-800 us (1 CH).

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            RuntimeError: If device operation fails.
        """
        self.recordLength = recordLength
        self.recordPoints = int(recordLength * self.adcFrequency)
        bitRecVals = np.binary_repr(int(self.recordPoints), width=16)
        numRecByte1 = int(bitRecVals[-8:], 2)
        numRecByte2 = int(bitRecVals[-16:-8], 2)

        record: list[Union[str, int]] = [
            '6', numRecByte1, numRecByte2, 'a', 'a']
        self._writeSpiDevice(record)
        return self

    def setTriggerPhasing(self, phaseArrayMicro: list[float]) -> Self:
        """
        Sets the trigger phasing for each channel.

        Args:
            phaseArrayMicro (list[float]): Phase delays in microseconds for each channel.

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            RuntimeError: If device operation fails.
        """
        self.phaseArrayMicro = phaseArrayMicro
        phaseArray = np.ceil(
            np.array(phaseArrayMicro[::-1]) * self.adcFrequency / 1_000_000)
        phasingActive = any(phaseArray > 0)
        if phasingActive == False:
            phaseByt: list[Union[str, int]] = [x for x in '7Naaa']
            self._writeSpiDevice(phaseByt)
        else:
            phaseIndices = [index for index,
                            value in enumerate(phaseArray) if value != 0]
            for i in phaseIndices:
                phaseVal = phaseArray[i]
                numPhaseByte1 = int(7-i)
                bitPhaseVals = np.binary_repr(int(phaseVal), width=24)
                numPhaseByte2 = int(bitPhaseVals[-8:], 2)
                numPhaseByte3 = int(bitPhaseVals[-16:-8], 2)
                numPhaseByte4 = int(bitPhaseVals[-24:-16], 3)
                phase: list[Union[str, int]] = ['7', numPhaseByte1,
                                                numPhaseByte2, numPhaseByte3, numPhaseByte4]
                self._writeSpiDevice(phase)
        return self

    def setRecordDelay(self, delayArrayMicro: list[float]) -> Self:
        """
        Sets the record delay for each channel.

        Args:
            delayArrayMicro (list[float]): Delay values in microseconds for each channel.

        Returns:
            Self: Returns the instance for method chaining.

        Raises:
            RuntimeError: If device operation fails.
        """
        self.delayArrayMicro = delayArrayMicro
        delayArray = np.ceil(
            np.array(delayArrayMicro[::-1]) * self.adcFrequency / 1_000_000)
        delayActive = any(delayArray > 0)
        if delayActive == False:
            phaseByt: list[Union[str, int]] = [x for x in '8Naaa']
            self._writeSpiDevice(phaseByt)
        else:
            delayIndices = [index for index,
                            value in enumerate(delayArray) if value != 0]
            for i in delayIndices:
                delayVal = delayArray[i]
                numDelayByte1 = int(7-i)
                bitDelayVals = np.binary_repr(int(delayVal), width=24)
                numDelayByte2 = int(bitDelayVals[-8:], 2)
                numDelayByte3 = int(bitDelayVals[-16:-8], 2)
                numDelayByte4 = int(bitDelayVals[-24:-16], 3)
                delay: list[Union[str, int]] = ['8', numDelayByte1,
                                                numDelayByte2, numDelayByte3, numDelayByte4]
                self._writeSpiDevice(delay)
        return self

    def configureAttributes(self) -> Self:
        """
        Configure the packet size from the FPGA based on configured parameters.

        :return: Chaining self.
        :rtype: Self
        """
        if (self.version < 6784):
            return self
        if self.samplingMode == 16:
            self.messageBytes = 2
        else:
            self.messageBytes = 3
        self.additionalBytes = sum(self.peripheralBytesArray) + 2
        self.totalDataBytes = int(
            self.recordPoints * self.messageBytes * self.numChannelsOnReceive + 2 * self.numChannelsOnReceive - 1)
        self.totalBytes = self.totalDataBytes + self.additionalBytes

        return self

    def getPeripheralData(self):
        return self.messageArray

    def getArray(self) -> np.ndarray[tuple[int, int], np.dtype[np.float64]]:
        """
        Acquires data array from the Vitesse device, including peripheral messages
        and dynamic decoding based on sampling mode.

        Returns:
            numpy.ndarray: Echo signal data for all enabled channels with shape
                        (numChannelsOn, recordPoints).

        Raises:
            IOError: If SPI device is not initialised.
            ValueError: If sampling configuration is invalid.
        """
        if self.simulation:
            # If in simulation mode, then reads in default parameters and pre-recorded
            # A-Scans, add random noise to the output, and then return the simulated result.
            if self.adcFrequency <= 0:
                self.adcFrequency = DEFAULT_ADC_FREQ
            if self.recordPoints <= 0:
                if self.recordLength and self.recordLength > 0:
                    self.recordPoints = int(
                        self.recordLength * self.adcFrequency)
                else:
                    self.recordPoints = 2048
            if self.numChannelsOnReceive <= 0:
                self.numChannelsOnReceive = 1

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
                sim_file).astype(float)
            if clean.ndim == 1:
                clean = clean.reshape(1, -1)
            clean = clean[: self.numChannelsOnReceive, : self.recordPoints]

            noise_std = 100.0
            accumulator = np.zeros_like(clean)

            for _ in range(self.numAverages):
                accumulator += clean + \
                    np.random.normal(0.0, noise_std, clean.shape)

            echoSignal = accumulator / self.numAverages
            self.messageArray = []
            return echoSignal

        if (self.version < 6784):
            return self._getArrayLegacy()

        if self.spiDevice is None:
            raise IOError(
                "SPI Device not initialised. Perhaps you forgot to call initialise()")

        self.spiDevice.write(b'faaaa')
        time.sleep(self.numAverages / self.prf)

        byteBack = 0
        while byteBack != 100:
            Byte = self.spiDevice.read(1)
            time.sleep(self.READ_DELAY)
            byteBack = np.frombuffer(Byte, dtype=np.uint8)

        bytesBack = bytearray()
        remainingBytes = self.totalBytes

        while remainingBytes > self.MAX_READ_CHUNK:
            bytesBack += self.spiDevice.read(self.MAX_READ_CHUNK)
            remainingBytes -= self.MAX_READ_CHUNK
        bytesBack += self.spiDevice.read(remainingBytes)

        array = np.frombuffer(bytesBack, dtype=np.uint8)
        array = np.insert(array, 0, 100)  # Sentinel

        dataStartingPoint = len(array) - 1 - self.additionalBytes + 2
        self.messageArray = []
        msg_array: list[str] = []

        for description, decoder, byteCount in zip(
            self.peripheralDescriptionArray,
            self.peripheralDecodeArray,
            self.peripheralBytesArray,
        ):
            indices = np.arange(
                dataStartingPoint,
                dataStartingPoint + byteCount
            )
            dataStartingPoint += byteCount

            result = decoder(array[indices])

            self.messageArray.append(result)
            msg_array.append(f"{description}: {result}")

            if description == "Internal Temperature":
                self.internalTemp = result
            elif description == "External Temperature":
                self.externalTemp = result
            elif description == "Encoder 1":
                self.encoderIndex1 = result
            elif description == "Encoder 2":
                self.encoderIndex2 = result
            elif description == "Encoder Cart X":
                self.positionX = result
            elif description == "Encoder Cart Y":
                self.positionY = result
            elif description == "Encoder Cart Theta":
                self.positionTheta = result
            elif description == "Encoder 3":
                self.encoderIndex3 = result

        indicesToDelete = np.arange(-1 * (self.additionalBytes + 1), -1)
        array = np.delete(array, indicesToDelete)
        arr_uint8 = array.astype(np.uint8)

        def _to_binary(x: int) -> str:
            return format(x, '08b')
        binary_strings = np.vectorize(_to_binary)(arr_uint8)

        channel = np.split(binary_strings, self.numChannelsOnReceive)
        channel = [ch[1:-1] for ch in channel]

        byteArray = np.empty(
            (self.numChannelsOnReceive, self.recordPoints, self.messageBytes), dtype='<U8')
        reshapeArray = np.empty(
            (self.numChannelsOnReceive, self.recordPoints), dtype=float)
        normArray = np.empty(
            (self.numChannelsOnReceive, self.recordPoints), dtype=float)
        echoSignal = np.empty(
            (self.numChannelsOnReceive, self.recordPoints), dtype=float)

        for i in range(self.numChannelsOnReceive):
            byteArray[i] = np.reshape(channel[i], (-1, self.messageBytes))
            temp: list[float] = []
            for row in byteArray[i]:
                joined = ''.join(row.tolist())
                if self.messageBytes == 2:
                    temp.append(bin16_to_int(joined))
                elif self.messageBytes == 3:
                    temp.append(bin24_to_int(joined))
            reshapeArray[i] = np.array(temp)
            normArray[i] = np.divide(reshapeArray[i], self.numAverages)

            if self.maxChannels <= 4:
                inversionArray = [0, 3]
            else:
                inversionArray = [0, 1, 6, 7]

            # Conditional inversion for specific channel IDs
            if self.enabledChannelReceive[i] in inversionArray:
                echoSignal[i] = np.subtract(normArray[i], 2048) * -1
            else:
                echoSignal[i] = np.subtract(normArray[i], 2048)

        return echoSignal

    def _getArrayLegacy(self) -> np.ndarray[tuple[int, int], np.dtype[np.float64]]:
        """
        Acquires data array from older Vitesse devices. Older legacy version,
        only triggered as a fallback.

        Returns:
            numpy.ndarray: Echo signal data for all enabled channels with shape
                          (numChannelsOn, recordPoints).

        Raises:
            IOError: If SPI device is not initialised.
        """
        if self.spiDevice is None:
            raise IOError(
                "SPI Device not initialised. Perhaps you forgot to call initialise()")

        additionalBytes = 30

        self.spiDevice.write(b'faaaa')
        time.sleep(self.numAverages/self.prf)

        byteBack = 0

        while byteBack != 100:
            Byte = self.spiDevice.read(1)
            time.sleep(self.READ_DELAY)
            byteBack = np.frombuffer(Byte, dtype=np.uint8)

        remainingBytes = int(self.recordPoints*self.messageBytes *
                             self.numChannelsOnReceive+2*self.numChannelsOnReceive-1) + additionalBytes
        bytesBack = bytearray()
        while remainingBytes > self.MAX_READ_CHUNK:
            remainingBytes -= self.MAX_READ_CHUNK
            bytesBack += self.spiDevice.read(self.MAX_READ_CHUNK)
        bytesBack += self.spiDevice.read(remainingBytes)

        array = np.frombuffer(bytesBack, dtype=np.uint8)
        array = np.insert(array, 0, 100)

        self.internalTemp = None
        self.externalTemp = None
        self.encoderIndex1 = None
        self.encoderIndex2 = None
        self.positionX = None
        self.positionY = None
        self.positionTheta = None
        self.encoderIndex3 = None

        indicesToDelete = np.arange(-1 * (additionalBytes + 1), -1)
        array = np.delete(array, indicesToDelete)

        array = np.array(array, dtype=np.float16)

        channel = np.split(array, self.numChannelsOnReceive)
        channel = [channel[1:-1] for channel in channel]

        rawperipheralBytesArray = np.empty(
            (self.numChannelsOnReceive, self.recordPoints * self.messageBytes // 3, 3), dtype=float)
        reshapeArray = np.empty(
            (self.numChannelsOnReceive, self.recordPoints), dtype=float)
        normArray = np.empty(
            (self.numChannelsOnReceive, self.recordPoints), dtype=float)
        echoSignal = np.empty(
            (self.numChannelsOnReceive, self.recordPoints), dtype=float)

        if self.maxChannels <= 4:
            inversionArray = [0, 3]
        else:
            inversionArray = [0, 1, 6, 7]

        for i in range(self.numChannelsOnReceive):
            rawperipheralBytesArray[i] = np.reshape(channel[i], (-1, 3))
            reshapeArray[i] = rawperipheralBytesArray[i][:, 0] + rawperipheralBytesArray[i][:,
                                                                                            1] * (2**8) + rawperipheralBytesArray[i][:, 2] * (2**16)
            normArray[i] = np.divide(reshapeArray[i], self.numAverages)
            # Conditional inversion for specific channel IDs
            if self.enabledChannelReceive[i] in inversionArray:
                echoSignal[i] = np.subtract(normArray[i], 2048) * -1
            else:
                echoSignal[i] = np.subtract(normArray[i], 2048)

        return echoSignal

    def setSleepTime(self, sleepTime: int) -> Self:
        """
        Set the sleep time for an external microcontroller.
        The input is the sleep time in minutes.

        :param sleepTime: The sleep time, measured in minutes (Valid Range: 0-20000)
        :type sleepTime: int
        :return: Returns the instance for method chaining.
        :rtype: Self
        """
        if not self.SHM:
            return self

        if sleepTime > 20000:
            raise ValueError('Maximum sleep time of 20000 exceeded.')
        elif sleepTime < 0:
            raise ValueError('Sleep time cannot be negative.')
        else:
            bitSTVals = np.binary_repr(sleepTime*12, width=32)
            pulse: list[Union[str, int]] = [
                'r', int(bitSTVals[-8:], 2), 'a', 'a', 'a']

            self._writeSpiDevice(pulse)
            return self

    def checkShm(self) -> int:
        """
        This function checks whether the connected system is a Vitesse device with SHM capabilities.
        """
        try:
            if self.spiDevice is None:
                raise IOError(
                    "SPI Device not initialised. Perhaps you forgot to call initialise()")

            check_shm_command: list[Union[str, int]] = [
                'g', 'a', 'a', 'a', 'a']

            try:
                self._writeSpiDevice(check_shm_command)
            except ValueError:
                raise ValueError(
                    "check_shm_command: device returned 'Invalid' (200) for checkShm command.")
            except RuntimeError:
                self.spiDevice.write(b'gaaaa')
                time.sleep(self.READ_DELAY)

            time.sleep(self.READ_DELAY)
            b = self.spiDevice.read(1)
            if not b:
                raise TimeoutError("check_shm: timeout (no byte).")

            val = b[0]
            if val in (50, 200):
                time.sleep(self.READ_DELAY)
                b = self.spiDevice.read(1)
                if not b:
                    raise TimeoutError("check_shm: timeout after status byte.")
                val = b[0]
            self.SHM = True
        except:
            val = 0
            self.SHM = False
        return val

    def closeDevice(self) -> None:
        """
        Closes the connection to the Vitesse device.

        Raises:
            IOError: If SPI device is not initialised.
        """
        if self.spiDevice is None:
            raise IOError(
                "SPI Device not initialised. Perhaps you forgot to call initialise()")

        if not self.simulation:
            # Clearing the buffer
            finalarray = [0, 0, 0]
            while finalarray[-1] != 200 or finalarray[-2] != 200 or finalarray[-3] != 200:
                finalarray = np.frombuffer(
                    self.spiDevice.read(1000), dtype=np.uint8)
            return

        self.setChannelReceive([0, 0, 0, 0, 0, 0, 0, 0])
        self.spiDevice.close()

        self.spiDevice = None
