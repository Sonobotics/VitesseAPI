# SONUS Vitesse Python API

API version: **27.0.0**. The API version is independent of the connected device's firmware version.

The SONUS Vitesse Python API is a high-performance interface designed to integrate and control the Sonobotics SONUS Vitesse data acquisition system through Python. The API enables users to configure the device, acquire ultrasonic data, read peripheral information and work with the integrated encoder system.

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
   - [Prerequisites](#prerequisites)
   - [Driver Installation](#driver-installation)
3. [Quick Start](#quick-start)
4. [Key Features](#key-features)
   - [Context Manager Support](#context-manager-support)
   - [Method Chaining](#method-chaining)
   - [Channel and Duty-Cycle Arrays](#channel-and-duty-cycle-arrays)
5. [API Reference](#api-reference)
   - [Vitesse Class](#vitesse-class)
   - [Device Management](#device-management)
   - [Device Configuration](#device-configuration)
   - [Data Acquisition](#data-acquisition)
   - [SHM Functions](#shm-functions)
   - [Utility Functions](#utility-functions)
   - [Common Device Attributes](#common-device-attributes)
6. [Examples](#examples)

## Introduction

The SONUS Vitesse Python API provides a comprehensive interface for the SONUS Vitesse data acquisition system. It supports device discovery, excitation and acquisition configuration, multi-channel operation, amplitude steering, encoder configuration, peripheral decoding and simulated data acquisition.

The API supports 1, 2, 4 and 8-channel SONUS Vitesse devices. Channel configuration arrays always contain eight values, with unused channels set to `0`.

Version 27.0.0 adds packed acquisition with `get_packet()` and offline waveform decoding with `VitesseAPI.utils.decode_packet()`. It also improves numeric waveform decoding and adds optional native ARM64 acquisition through the included FTDI library. Existing method names and signatures remain available.

## Installation

### Prerequisites

1. Python 3.8 or later. Python 3.9 or later is strongly recommended.
2. Install the required packages from the root of the VitesseAPI folder:

   ```bash
   pip install -r requirements.txt
   ```

### Driver Installation

#### Windows

Navigate to the `drivers/windows_FTDI` folder and run:

```text
CDM212364_Setup.exe
```

#### Linux x86_64

Navigate to the VitesseAPI folder and run:

```bash
cd drivers
sudo bash x86_64_install.sh
```

#### Linux ARM

Navigate to the VitesseAPI folder and run:

```bash
cd drivers
sudo bash arm_install.sh
```

## Quick Start

The recommended approach is to use `Vitesse` as a context manager. This ensures that the device connection is closed when the block exits, including when an exception or `KeyboardInterrupt` occurs.

```python
from VitesseAPI import Vitesse

with Vitesse().initialise() as vitesse:
    vitesse.set_config(
        excitation_frequency=3.6e6,
        num_cycles=2,
        drive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        receive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        num_averages=100,
        prf=1000,
        record_length=50e-6,
    )

    array = vitesse.get_array()
    print(f"Acquired data shape: {array.shape}")
```

To connect to a specific device, pass its serial number to `initialise()`:

```python
with Vitesse().initialise(serial_number="1") as vitesse:
    array = vitesse.get_array()
```

## Key Features

### Context Manager Support

The `Vitesse` class implements Python's context manager protocol, allowing it to be used with the `with` statement.

```python
from VitesseAPI import Vitesse

with Vitesse().initialise() as vitesse:
    data = vitesse.get_array()
```

The standalone context manager is also available from the API module:

```python
from VitesseAPI.VitesseAPI import initialise_vitesse

with initialise_vitesse() as vitesse:
    data = vitesse.get_array()
```

### Method Chaining

Configuration methods return the current `Vitesse` instance, allowing multiple methods to be chained together.

```python
with Vitesse().initialise() as vitesse:
    vitesse.set_averages(100) \
        .set_prf(1000) \
        .set_record_length(50e-6)
```

For a complete configuration, `set_config()` is recommended because it applies the settings in the correct order.

### Channel and Duty-Cycle Arrays

Receive and drive arrays contain eight values corresponding to channels 1 to 8:

```python
receive_channels = [1, 1, 0, 0, 0, 0, 0, 0]
```

This enables channels 1 and 2 for acquisition.

The `drive_channels` array also selects the duty-cycle profile used by each enabled channel. Each value should be:

- `0` to disable the channel
- The value of `duty_cycle_1` to enable the channel using profile 1
- The value of `duty_cycle_2` to enable the channel using profile 2
- `1` to enable the channel using profile 1

For example:

```python
duty_cycle_1 = 0.50
duty_cycle_2 = 0.25

drive_channels = [
    duty_cycle_1,
    duty_cycle_2,
    0,
    0,
    0,
    0,
    0,
    0,
]
```

This enables channel 1 with the first profile and channel 2 with the second profile.

## API Reference

### Vitesse Class

The `Vitesse` class is the main interface for controlling a SONUS Vitesse device.

```python
from VitesseAPI import Vitesse

vitesse = Vitesse()
```

### Device Management

#### `Vitesse.list_devices() -> list[tuple[str, str, int]]`

Lists the connected physical SONUS Vitesse devices. Simulated devices are not included.

Each returned tuple contains:

```text
(serial_number, device_name, number_of_channels)
```

```python
devices = Vitesse.list_devices()

for serial_number, device_name, number_of_channels in devices:
    print(
        f"Device: {device_name}, "
        f"Serial: {serial_number}, "
        f"Channels: {number_of_channels}"
    )
```

#### `initialise(serial_number: str | None = None, simulation: bool = False) -> Self`

Initialises a physical or simulated Vitesse device.

**Parameters:**

- `serial_number`: Serial number of the device to open. If omitted, the first available Vitesse device is used.
- `simulation`: If `True`, initialises a simulated 8-channel device. Defaults to `False`.

**Returns:**

- `Self`: The current instance for method chaining.

```python
vitesse = Vitesse().initialise()

# Connect to a specific device
vitesse = Vitesse().initialise(serial_number="1")

# Use simulated data
vitesse = Vitesse().initialise(simulation=True)
```

#### `initialise_vitesse(serial_number: str | None = None, simulation: bool = False)`

Provides a standalone context manager that initialises the device and closes it when the context exits.

```python
from VitesseAPI.VitesseAPI import initialise_vitesse

with initialise_vitesse(serial_number="1") as vitesse:
    data = vitesse.get_array()
```

#### `close_device() -> None`

Disables all receive channels, closes the FTDI connection and clears the stored device handle. It is strongly recommended to use a context manager or call `close_device()` before the application exits.

### Device Configuration

#### `set_config(...) -> Self`

Configures the device using the correct command order. This is recommended over setting each parameter manually.

```python
set_config(
    num_cycles=2,
    receive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
    drive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
    prf=1000,
    num_averages=100,
    record_length=50e-6,
    phase_array_microseconds=[0, 0, 0, 0, 0, 0, 0, 0],
    delay_array_microseconds=[0, 0, 0, 0, 0, 0, 0, 0],
    sampling_mode=24,
    excitation_clock_frequency=200_000_000,
    excitation_frequency=3_600_000,
    target_clock=50_000_000,
    polarity="p",
    duty_cycle_1=1.0,
    duty_cycle_2=0.0,
    wheel_radius=19.9,
    wheel_radius_1=None,
    wheel_radius_2=None,
    encoder_cpr=2048,
    encoder_cpr_1=None,
    encoder_cpr_2=None,
    wheelbase=40,
    wheelbase_1=None,
    wheelbase_2=None,
)
```

**Parameters:**

- `num_cycles`: Number of excitation cycles from 1 to 3.
- `receive_channels`: Eight-element receive-channel enable array.
- `drive_channels`: Eight-element drive-channel and duty-cycle selection array.
- `prf`: Pulse repetition frequency from 1 to 5000 Hz.
- `num_averages`: Number of acquisitions to average from 1 to 1000.
- `record_length`: Acquisition record length in seconds.
- `phase_array_microseconds`: Eight trigger-phase values in microseconds.
- `delay_array_microseconds`: Eight record-delay values in microseconds.
- `sampling_mode`: ADC sample width. Use `16` for two-byte samples or `24` for the default three-byte samples.
- `excitation_clock_frequency`: Excitation clock frequency in Hz.
- `excitation_frequency`: Requested excitation frequency in Hz.
- `target_clock`: Requested ADC clock frequency in Hz. The nearest supported value of 25 or 50 MHz is selected.
- `polarity`: Excitation polarity code sent to the FPGA. The default is `"p"`.
- `duty_cycle_1`: First duty-cycle profile from `0.0` to `1.0`.
- `duty_cycle_2`: Second duty-cycle profile from `0.0` to `1.0`.
- `wheel_radius`: Shared wheel radius used when individual wheel radii are omitted.
- `wheel_radius_1`, `wheel_radius_2`: Individual encoder wheel radii.
- `encoder_cpr`: Shared encoder counts per revolution used when individual values are omitted.
- `encoder_cpr_1`, `encoder_cpr_2`: Individual encoder counts per revolution.
- `wheelbase`: Total wheelbase used when individual wheelbase values are omitted.
- `wheelbase_1`, `wheelbase_2`: Distances from each encoder wheel to the reference point. Each defaults to half of `wheelbase`.

`set_config()` calculates `num_chips` from `excitation_clock_frequency` and `excitation_frequency`. It also clears the encoder counters as part of the configuration sequence.

#### `set_symbol(num_chips: int, num_cycles: int, polarity: str) -> Self`

Sets the excitation symbol configuration.

**Parameters:**

- `num_chips`: Number of chips from 1 to 100.
- `num_cycles`: Number of excitation cycles from 1 to 3.
- `polarity`: Excitation polarity code.

```python
vitesse.set_symbol(num_chips=28, num_cycles=2, polarity="p")
```

#### `set_receive_channels(receive_channels: list[int]) -> Self`

Sets the receive-channel enable array.

```python
vitesse.set_receive_channels([1, 1, 0, 0, 0, 0, 0, 0])
```

The number of enabled receive channels must not exceed `max_channels` for the connected device.

#### `set_drive_channels(drive_channels: list[int]) -> Self`

Enables each drive channel with a non-zero array value. When configuring amplitude steering, call `set_duty_cycles()` as well so each non-zero value selects the intended duty-cycle profile.

```python
vitesse.set_drive_channels([1, 1, 0, 0, 0, 0, 0, 0])
```

#### `set_duty_cycles(duty_cycle_1: float, duty_cycle_2: float, channel_duty_cycles: list[float], num_chips: int) -> Self`

Configures two duty-cycle profiles and selects one profile for each channel.

**Parameters:**

- `duty_cycle_1`: First profile value from `0.0` to `1.0`.
- `duty_cycle_2`: Second profile value from `0.0` to `1.0`.
- `channel_duty_cycles`: Eight values matching `duty_cycle_1`, `duty_cycle_2`, `1` or `0`.
- `num_chips`: Number of chips per excitation cycle.

```python
vitesse.set_duty_cycles(
    duty_cycle_1=0.50,
    duty_cycle_2=0.25,
    channel_duty_cycles=[0.50, 0.25, 0, 0, 0, 0, 0, 0],
    num_chips=vitesse.num_chips,
)
```

The user-facing profile value represents the available output level. Internally, a value of `1.0` corresponds to a physical high-time duty cycle of `0.5`.

#### `set_sampling_mode(sampling_mode: int) -> Self`

Sets the ADC sample width on firmware that supports selectable sampling modes.

- `16` selects two-byte samples.
- Any other value selects the firmware's default 24-bit mode.

```python
vitesse.set_sampling_mode(24)
```

#### `set_target_clock(target_clock: int) -> Self`

Sets the FPGA target clock. Supported values are 25 and 50 MHz. If another frequency is supplied, the nearest supported frequency is selected.

```python
vitesse.set_target_clock(50_000_000)
```

The `adc_frequency` attribute is refreshed from the FPGA after the clock is changed.

#### `set_averages(num_averages: int) -> Self`

Sets the number of A-scans averaged during each acquisition.

```python
vitesse.set_averages(100)
```

The supported range is 1 to 1000.

#### `set_prf(prf: int) -> Self`

Sets the Pulse Repetition Frequency in Hz.

```python
vitesse.set_prf(1000)
```

The supported range is 1 to 5000 Hz.

#### `set_record_length(record_length: float) -> Self`

Sets the acquisition record length in seconds and updates `record_points` using the current `adc_frequency`.

```python
vitesse.set_record_length(50e-6)
```

#### `set_trigger_phasing(phase_array_microseconds: list[float]) -> Self`

Sets the trigger phase for each channel in microseconds.

```python
vitesse.set_trigger_phasing([0, 0.5, 1.0, 1.5, 0, 0, 0, 0])
```

#### `set_record_delay(delay_array_microseconds: list[float]) -> Self`

Sets the acquisition delay for each channel in microseconds.

```python
vitesse.set_record_delay([0, 5, 0, 0, 0, 0, 0, 0])
```

#### `set_encoder_parameters(...) -> Self`

Configures the encoder geometry and the count-to-distance conversion coefficients.

```python
vitesse.set_encoder_parameters(
    wheel_radius_1=40,
    wheel_radius_2=40,
    encoder_cpr_1=1000,
    encoder_cpr_2=1000,
    wheelbase_1=30,
    wheelbase_2=30,
    wheelbase=60,
    radius=40,
    cpr=1000,
)
```

For firmware version 26.9.0 and later, the individual wheel parameters are used. Firmware versions from 26.8.0 to below 26.9.0 use the shared `wheelbase`, `radius` and `cpr` parameters. Older firmware ignores this command.

For normal use, it is simpler to provide these values through `set_config()`.

#### `clear_encoders() -> Self`

Clears all FPGA encoder counters on supported firmware.

```python
vitesse.clear_encoders()
```

#### `get_version() -> int`

Reads and returns the packed 16-bit firmware version from the FPGA.

```python
packed_version = vitesse.get_version()
print(packed_version)
```

For example, firmware version 26.9.0 is packed as `0x1A90`, which is decimal `6800`. Use `vitesse.version_array` or `VitesseAPI.utils.get_version()` for a human-readable version.

#### `get_frequency() -> int`

Reads and returns the ADC sampling frequency in Hz.

```python
adc_frequency = vitesse.get_frequency()
print(f"ADC frequency: {adc_frequency / 1e6:.0f} MHz")
```

### Data Acquisition

#### `get_array() -> np.ndarray`

Acquires echo data for every enabled receive channel and decodes the peripheral values appended by the FPGA.

**Returns:**

- A two-dimensional NumPy array with shape `(num_receive_channels, record_points)`.
- Each row contains the samples from one enabled receive channel.
- The array uses `float64` values, with averaging normalisation, the ADC offset and channel polarity correction applied.

```python
data = vitesse.get_array()

print(f"Data shape: {data.shape}")
print(f"First enabled channel: {data[0]}")
```

Calling `get_array()` also updates the peripheral attributes described under [Common Device Attributes](#common-device-attributes).

#### `get_packet() -> Optional[bytearray]`

Starts a new acquisition and returns the packed device payload without decoding the waveform samples or peripheral values. Use this method when storing or forwarding device bytes for decoding later. Use `get_array()` when a decoded NumPy waveform is required.

**Returns:**

- An independently owned `bytearray` containing sample bytes, remaining channel markers and the peripheral trailer. Later acquisitions do not overwrite this buffer.
- `None` in simulation mode. Use `get_array()` to acquire simulated waveforms.

The initial ready byte (`0x64`) is consumed while waiting for the device and is not included in the returned payload. The API does not add a header, timestamp, channel identifiers or configuration information. The returned bytes are not a self-describing capture file.

```python
import json
from pathlib import Path
from VitesseAPI import Vitesse

with Vitesse().initialise() as vitesse:
    vitesse.set_config(
        excitation_frequency=3.6e6,
        num_cycles=2,
        drive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        receive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        num_averages=100,
        prf=1000,
        record_length=50e-6,
    )

    packet = vitesse.get_packet()
    if packet is not None:
        metadata = {
            "api_version": list(vitesse.api_version),
            "firmware_version": list(vitesse.version_array),
            "adc_frequency": vitesse.adc_frequency,
            "record_points": vitesse.record_points,
            "message_bytes": vitesse.message_bytes,
            "num_averages": vitesse.num_averages,
            "prf": vitesse.prf,
            "max_channels": vitesse.max_channels,
            "enabled_receive_channels": list(vitesse.enabled_receive_channels),
            "payload_bytes": len(packet),
        }
        Path("capture.bin").write_bytes(packet)
        Path("capture.json").write_text(json.dumps(metadata, indent=2))
```

Configure the device with `set_config()` before acquisition so that packet sizes match the selected channels, record length and sampling mode. Keep the configuration metadata with stored payloads; these values cannot be recovered from the payload alone.

**Packet layout:**

- Samples are ordered by the zero-based channel indices in `enabled_receive_channels`.
- For channel row `i`, samples start at offset `i * (record_points * message_bytes + 2)`. Read `record_points * message_bytes` sample bytes from that offset; the remaining bytes contain channel framing and peripheral data.
- Legacy firmware uses little-endian, three-byte samples. Extended-protocol firmware uses big-endian samples with two or three bytes according to the configured sampling mode.
- The sample bytes still represent the device's accumulated ADC values. `get_packet()` does not divide by `num_averages`, subtract the ADC offset or correct channel polarity. It does not apply filtering, rectification or thickness calculations.
- The peripheral trailer depends on the firmware. Retain it when forwarding or storing packets rather than treating the entire payload as contiguous waveform samples.

Calling `get_packet()` leaves `message_array`, temperature, encoder and position attributes unchanged. Consequently, `get_peripheral_data()` still returns the values from the latest decoded acquisition. A subsequent call to `get_array()` starts another acquisition; it does not decode the packet already returned by `get_packet()`. Use `decode_packet(packet, metadata)` to decode the existing packet.

**Raises:**

- `OSError` if the SPI device is not initialised, a native acquisition fails, the ready-poll deadline expires or a payload read is incomplete.
- Other device-driver errors may propagate from the underlying SPI connection.

The method blocks while acquisition and reads complete. The ready-poll deadline is three seconds after the averaging wait, checked between read operations; it is not a fixed timeout for the whole call. Driver read timeouts also apply. Serialize acquisition and configuration calls on each device instance.

Both `get_array()` and `get_packet()` are available on Windows, Linux AMD64 and Linux ARM64. The supplied ARM64 FTDI library performs acquisition in C++ through optional native entry points. Windows and AMD64 currently coordinate acquisition in Python using native SPI reads. If those optional entry points are absent, the API uses the Python acquisition path. The native libraries are included in the API; the separate QUANTA Radxa server is not required to use these methods.

#### `get_peripheral_data() -> list`

Returns the peripheral values decoded during the latest call to `get_array()`.

The values are returned in the following order:

1. Internal temperature
2. External temperature
3. Encoder count 1
4. Encoder count 2
5. Encoder cart X position
6. Encoder cart Y position
7. Encoder cart angle
8. Encoder count 3

```python
vitesse.get_array()
peripheral_data = vitesse.get_peripheral_data()
print(peripheral_data)
```

### SHM Functions

#### `set_power_control(power_control: bool) -> Self`

Controls the external power-control GPIO on an SHM system.

```python
vitesse.set_power_control(True)
```

- `True` asserts the power-control signal.
- `False` deasserts the power-control signal.
- The command is skipped when `vitesse.shm` is `False`.

#### `set_sleep_time(sleep_time: int) -> Self`

Sets the external microcontroller sleep time in minutes on an SHM system.

```python
vitesse.set_sleep_time(60)
```

The supported range is 0 to 20000 minutes. The command is skipped when `vitesse.shm` is `False`.

### Utility Functions

The utility functions are available from `VitesseAPI.utils`.

#### `decode_packet(packet: bytes | bytearray | memoryview, metadata: Mapping) -> np.ndarray`

Decodes the waveform in an existing `get_packet()` payload. This standalone function does not connect to a device or start an acquisition. Import it from `VitesseAPI.utils`.

**Parameters:**

- `packet`: The complete payload returned by `get_packet()`, or its saved bytes. Memory views must be contiguous.
- `metadata`: The configuration used to acquire this specific packet. The JSON metadata saved in the preceding example can be passed directly.

The following metadata fields are required:

| Field | Description |
|---|---|
| `firmware_version` | Firmware version as `[major, minor, patch]` |
| `record_points` | Positive number of samples per enabled receive channel |
| `message_bytes` | Sample width: `3` for legacy firmware, `2` or `3` for extended firmware |
| `num_averages` | Number of averaged acquisitions, from 1 to 1000 |
| `max_channels` | Maximum channel count for the device, from 1 to 8 |
| `enabled_receive_channels` | Unique zero-based channel indices in the payload's row order |
| `payload_bytes` | Complete payload length recorded when the packet was acquired |

Additional fields, including `api_version`, `adc_frequency` and `prf`, are accepted and ignored by the waveform decoder.

**Returns:**

- An independently owned `float64` NumPy array with shape `(len(enabled_receive_channels), record_points)`.
- The same sample scaling, averaging normalisation, ADC offset and channel polarity correction as `get_array()` for the corresponding packet.

To decode the files saved in the preceding example:

```python
import json
from pathlib import Path
from VitesseAPI.utils import decode_packet

packet = Path("capture.bin").read_bytes()
metadata = json.loads(Path("capture.json").read_text())
waveform = decode_packet(packet, metadata)

print(f"Data shape: {waveform.shape}")
print(f"First enabled channel: {waveform[0]}")
```

For an in-memory acquisition, pass `packet` and `metadata` directly to `decode_packet()` without writing files. The decoder does not modify either argument, and later changes to a mutable packet buffer do not change the returned array.

The decoder supports legacy 24-bit packets and extended 16/24-bit packets with the standard peripheral trailer used by this API. Peripheral values are skipped and device attributes are not updated. No filtering, rectification or thickness calculation is applied. The function checks required metadata and payload length; it does not infer missing settings or verify the contents of framing and peripheral bytes.

**Raises:**

- `TypeError` if `packet` is not a contiguous byte buffer or `metadata` is not a mapping.
- `ValueError` if required metadata is missing or invalid, or the packet length is inconsistent with its configuration.

#### `get_version(vitesse: Vitesse) -> None`

Prints the firmware version, API version and maximum supported channel count as a formatted table.

```python
from VitesseAPI.utils import get_version

get_version(vitesse)
```

#### `get_config(vitesse: Vitesse) -> None`

Prints the current acquisition, channel and encoder configuration as a formatted table.

```python
from VitesseAPI.utils import get_config

get_config(vitesse)
```

### Common Device Attributes

The following attributes are available after initialisation and configuration. Peripheral values are refreshed by `get_array()`.

| Attribute | Description |
| --- | --- |
| `spi_device` | Active FTDI device connection, or `None` when closed |
| `version` | Packed firmware version as an integer |
| `version_array` | Firmware version as `[major, minor, patch]` |
| `api_version` | API version as `[major, minor, patch]` |
| `max_channels` | Maximum number of channels supported by the connected device |
| `adc_frequency` | Current ADC sampling frequency in Hz |
| `excitation_clock_frequency` | Excitation clock frequency in Hz |
| `excitation_frequency` | Requested excitation frequency in Hz |
| `num_chips` | Calculated number of excitation chips |
| `prf` | Pulse repetition frequency in Hz |
| `num_averages` | Number of acquisitions averaged |
| `record_length` | Acquisition record length in seconds |
| `record_points` | Number of samples recorded per enabled channel |
| `sampling_mode` | ADC sample width in bits |
| `phase_array_microseconds` | Per-channel trigger phases in microseconds |
| `delay_array_microseconds` | Per-channel record delays in microseconds |
| `num_receive_channels` | Number of enabled receive channels |
| `enabled_receive_channels` | Zero-based indices of the enabled receive channels |
| `num_drive_channels` | Number of enabled drive channels |
| `enabled_drive_channels` | Zero-based indices of the enabled drive channels |
| `duty_cycle_1` | First configured duty-cycle profile |
| `duty_cycle_2` | Second configured duty-cycle profile |
| `internal_temperature` | Latest decoded FPGA internal temperature |
| `external_temperature` | Latest decoded RTD temperature |
| `encoder_count_1` | Latest count from encoder 1 |
| `encoder_count_2` | Latest count from encoder 2 |
| `encoder_count_3` | Latest count from encoder 3 |
| `position_x` | Latest decoded encoder-cart X position |
| `position_y` | Latest decoded encoder-cart Y position |
| `position_theta` | Latest decoded encoder-cart angle |
| `wheel_radius` | Shared or active encoder wheel radius |
| `wheel_radius_1` | Encoder wheel 1 radius |
| `wheel_radius_2` | Encoder wheel 2 radius |
| `encoder_cpr` | Shared or active encoder counts per revolution |
| `encoder_cpr_1` | Encoder 1 counts per revolution |
| `encoder_cpr_2` | Encoder 2 counts per revolution |
| `wheelbase` | Total encoder wheelbase |
| `wheelbase_1` | Distance from encoder wheel 1 to the reference point |
| `wheelbase_2` | Distance from encoder wheel 2 to the reference point |
| `shm` | Whether SHM-specific commands are enabled |

## Examples

### Basic Data Acquisition

```python
from VitesseAPI import Vitesse

with Vitesse().initialise() as vitesse:
    vitesse.set_config(
        excitation_frequency=3.6e6,
        num_cycles=2,
        drive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        receive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        num_averages=100,
        prf=1000,
        record_length=50e-6,
    )

    for acquisition_index in range(10):
        data = vitesse.get_array()
        print(f"Acquisition {acquisition_index + 1}: {data.flatten()}")
```

### Multi-Channel Acquisition with Duty-Cycle Profiles

```python
from VitesseAPI import Vitesse

duty_cycle_1 = 0.50
duty_cycle_2 = 0.25

drive_channels = [
    duty_cycle_1,
    duty_cycle_2,
    duty_cycle_1,
    duty_cycle_2,
    0,
    0,
    0,
    0,
]

with Vitesse().initialise() as vitesse:
    vitesse.set_config(
        excitation_frequency=3.6e6,
        num_cycles=2,
        drive_channels=drive_channels,
        receive_channels=[1, 1, 1, 1, 0, 0, 0, 0],
        duty_cycle_1=duty_cycle_1,
        duty_cycle_2=duty_cycle_2,
        num_averages=100,
        prf=1000,
        record_length=50e-6,
    )

    data = vitesse.get_array()
    print(data.shape)
```

### Encoder Configuration and Position Data

```python
from VitesseAPI import Vitesse

with Vitesse().initialise() as vitesse:
    vitesse.set_config(
        drive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        receive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        encoder_cpr=1000,
        wheel_radius=40,
        wheelbase=60,
    )

    data = vitesse.get_array()

    print(
        f"Encoder counts: "
        f"{vitesse.encoder_count_1}, "
        f"{vitesse.encoder_count_2}, "
        f"{vitesse.encoder_count_3}"
    )
    print(
        f"Position: "
        f"X={vitesse.position_x}, "
        f"Y={vitesse.position_y}, "
        f"Theta={vitesse.position_theta}"
    )
```

### Multi-Channel Plotting with Phasing

```python
import matplotlib.pyplot as plt

from VitesseAPI import Vitesse

with Vitesse().initialise() as vitesse:
    vitesse.set_config(
        drive_channels=[1, 1, 1, 1, 0, 0, 0, 0],
        receive_channels=[1, 1, 1, 1, 0, 0, 0, 0],
        phase_array_microseconds=[0, 0.5, 1.0, 1.5, 0, 0, 0, 0],
        num_averages=100,
        record_length=50e-6,
    )

    data = vitesse.get_array()

    figure, axes = plt.subplots(2, 2, figsize=(10, 6))
    for channel_index, axis in enumerate(axes.flat):
        axis.plot(data[channel_index])
        axis.set_title(f"Channel {channel_index + 1}")
        axis.set_xlabel("Sample")
        axis.set_ylabel("Amplitude")

    figure.tight_layout()
    plt.show()
```

### Real-Time Plotting

```python
import matplotlib.pyplot as plt
import numpy as np

from VitesseAPI import Vitesse
from VitesseAPI.utils import get_config, get_version

with Vitesse().initialise() as vitesse:
    vitesse.set_config(
        excitation_frequency=3.6e6,
        num_cycles=2,
        drive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        receive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        num_averages=100,
        prf=1000,
        record_length=50e-6,
    )

    get_version(vitesse)
    get_config(vitesse)

    figure, axis = plt.subplots()
    line, = axis.plot([], [])
    axis.set_xlim(0, vitesse.record_length * 1e6)
    axis.set_ylim(-2048, 2048)
    axis.set_xlabel("Time (us)")
    axis.set_ylabel("Arb. Amplitude")

    try:
        while True:
            array = vitesse.get_array().flatten()
            time_microseconds = (
                np.arange(len(array)) / vitesse.adc_frequency * 1e6
            )
            line.set_data(time_microseconds, array)
            plt.pause(0.001)
    except KeyboardInterrupt:
        print("Operation interrupted")
```

### Simulated Data

```python
import matplotlib.pyplot as plt

from VitesseAPI import Vitesse

with Vitesse().initialise(simulation=True) as vitesse:
    vitesse.set_config(
        receive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        drive_channels=[1, 0, 0, 0, 0, 0, 0, 0],
        num_averages=100,
        record_length=50e-6,
    )

    data = vitesse.get_array()
    plt.plot(data[0])
    plt.xlabel("Sample")
    plt.ylabel("Amplitude")
    plt.show()
```
