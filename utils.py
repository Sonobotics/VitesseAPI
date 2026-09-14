"""Conversion and display utilities for the Vitesse API."""

from __future__ import annotations

import math
import struct
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from VitesseAPI import Vitesse


def ext_temp(np_list: np.ndarray) -> float:
    """
    Convert two-byte RTD data into degrees Celsius.

    The input is interpreted as a PT100 measurement using a 3900-ohm
    reference resistor.

    Parameters:
    -----------
    np_list : np.ndarray
        Two-byte RTD data in [byte2, byte3] order.

    Returns:
    --------
    float
        The calculated temperature in degrees Celsius.

    Raises:
    -------
    ValueError
        If the input does not contain exactly two bytes.
    """
    if len(np_list) != 2:
        raise ValueError(
            "Input must contain exactly two bytes: [byte2, byte3]")

    byte2, byte3 = np_list
    byte2 = int(byte2)
    byte3 = int(byte3)

    data = (byte2 << 7) + (byte3 >> 1)

    ratio = data / 32768.0
    reference_resistance = 3900
    resistance = reference_resistance * ratio

    cvd_a = 3.9083e-3
    cvd_b = -5.775e-7
    pt100_nominal = 100.0

    z1 = -cvd_a
    z2 = cvd_a**2 - (4 * cvd_b)
    z3 = (4 * cvd_b) / pt100_nominal
    z4 = 2 * cvd_b
    try:
        temp = z2 + (z3 * resistance)
        temp = (math.sqrt(temp) + z1) / z4
    except ValueError:
        temp = 0
    return temp


def int_temp(np_list: np.ndarray) -> float:
    """
    Convert the FPGA/XADC internal temperature register to degrees Celsius.

    The top 12 bits of the 16-bit input word contain the temperature code.

    Parameters:
    -----------
    np_list : np.ndarray of shape (2,), dtype=np.uint8
        The 16-bit XADC DRP readout, split into two bytes.

    Returns:
    --------
    float
        The temperature in degrees Celsius.

    Raises:
    -------
    ValueError
        If the input is not a two-element ``np.uint8`` array.
    """
    if len(np_list) != 2 or np_list.dtype != np.uint8:
        raise ValueError("Input must be a NumPy array of two uint8 bytes")

    raw16 = (int(np_list[0]) << 8) | int(np_list[1])
    temp_code = raw16 >> 4
    temperature_c = (temp_code * 503.975 / 4096.0) - 273.15

    return temperature_c


def dec_enc(bytes_array: np.ndarray) -> int:
    """
    Decode a signed 32-bit encoder count from four MSB-first bytes.

    Parameters:
    -----------
    bytes_array : np.ndarray
        Four encoder bytes in most-significant-byte-first order.

    Returns:
    --------
    int
        The signed encoder count.

    Raises:
    -------
    ValueError
        If the input does not contain exactly four bytes.
    """
    if len(bytes_array) != 4:
        raise ValueError("Expected exactly 4 bytes")

    count = int.from_bytes(bytes_array, byteorder="big", signed=True)
    return count


def dec_enc_float(bytes_array: np.ndarray) -> float:
    """
    Decode a 32-bit IEEE-754 floating-point value from four MSB-first bytes.

    Parameters:
    -----------
    bytes_array : np.ndarray
        Four bytes in most-significant-byte-first order.

    Returns:
    --------
    float
        The decoded single-precision floating-point value.

    Raises:
    -------
    ValueError
        If the input does not contain exactly four bytes.
    """
    if len(bytes_array) != 4:
        raise ValueError("Expected exactly 4 bytes")

    count = int.from_bytes(bytes_array, byteorder="big", signed=False)
    return struct.unpack(">f", struct.pack(">I", count))[0]


def bin24_to_int(bin_str: str) -> int:
    """
    Convert a 24-bit binary string to an unsigned integer.

    Parameters:
    -----------
    bin_str : str
        A 24-character binary string.

    Returns:
    --------
    int
        The unsigned integer represented by the binary string.
    """
    assert len(bin_str) == 24, "Input must be a 24-bit binary string"
    val = int(bin_str, 2)

    return val


def bin16_to_int(bin_str: str) -> int:
    """
    Convert a 16-bit binary string to a 24-bit-aligned unsigned integer.

    Parameters:
    -----------
    bin_str : str
        A 16-character binary string.

    Returns:
    --------
    int
        The parsed value shifted left by eight bits.
    """
    assert len(bin_str) == 16, "Input must be a 16-bit binary string"
    val = int(bin_str, 2) << 8

    return val


def decode_version(version_u16: int) -> list[int]:
    """
    Decode a packed 16-bit version number into [major, minor, beta].

    Parameters:
    -----------
    version_u16 : int
        Packed version value with major in bits 15-8, minor in bits 7-4,
        and beta in bits 3-0.

    Returns:
    --------
    list[int]
        The version components in major, minor, beta order.
    """
    major = (version_u16 >> 8) & 0xFF
    minor = (version_u16 >> 4) & 0xF
    beta = version_u16 & 0xF

    return [major, minor, beta]


def _print_config_table(
    rows: list[list[str]], headers: list[str] | None = None
) -> None:
    """
    Print configuration rows as a bordered, aligned table.

    Parameters:
    -----------
    rows : list[list[str]]
        Table rows. Cell values may contain newline-separated text.
    headers : list[str] | None, optional
        Optional header row printed above the data rows.
    """
    table_rows = [headers, *rows] if headers else rows
    split_rows = [
        [str(value).splitlines() or [""] for value in row] for row in table_rows
    ]
    column_widths = [
        max(len(line) for row in split_rows for line in row[column])
        for column in range(len(table_rows[0]))
    ]
    border = "+" + "+".join("-" * (width + 2) for width in column_widths) + "+"

    print(border)
    for row_index, row in enumerate(split_rows):
        row_height = max(len(cell_lines) for cell_lines in row)
        for line_index in range(row_height):
            cells = [
                f" {cell_lines[line_index] if line_index < len(cell_lines) else '':<{column_widths[column]}} "
                for column, cell_lines in enumerate(row)
            ]
            print("|" + "|".join(cells) + "|")
        if headers and row_index == 0:
            print(border)
    print(border)


def get_version(obj: Vitesse) -> None:
    """
    Print the firmware and API version information for a Vitesse device.

    Parameters:
    -----------
    obj : Vitesse
        Device object containing ``version_array``, ``api_version``, and
        ``max_channels`` attributes.
    """
    version_u16 = obj.version_array
    version_display = ""
    for i, element in enumerate(version_u16):
        if i != len(version_u16) - 1:
            version_display = version_display + str(element) + "."
        else:
            version_display = version_display + str(element)

    api_version_display = ""
    version_u16 = obj.api_version
    for i, element in enumerate(version_u16):
        if i != len(version_u16) - 1:
            api_version_display = api_version_display + str(element) + "."
        else:
            api_version_display = api_version_display + str(element)

    rows: list[list[str]] = [
        ["Firmware Version", f"{version_display}"],
        ["API Version", f"{api_version_display}"],
        ["Maximum Number of Channels", f"{obj.max_channels}"],
    ]

    print("\nDevice and API Version:")
    _print_config_table(rows)


def get_config(obj: Vitesse) -> None:
    """
    Print the current configuration parameters of a Vitesse device.

    Parameters:
    -----------
    obj : Vitesse
        Device object containing the configuration and channel attributes
        used to build the display table. Channel numbers are displayed using
        one-based numbering, while the object's arrays are not modified.
    """

    peripheral_descriptions = obj.peripheral_descriptions

    enabled_sensors = [
        sensor
        for sensor, enabled in zip(peripheral_descriptions, [1, 1, 1, 1, 1, 1, 1, 1])
        if enabled and sensor != "NA"
    ]
    additional_data = (
        "\n".join(
            str(enabled_sensors[index: index + 2])
            for index in range(0, len(enabled_sensors), 2)
        )
        or "[]"
    )
    receiving_channels = [
        channel + 1 for channel in obj.enabled_receive_channels]
    driving_channels = [channel + 1 for channel in obj.enabled_drive_channels]

    rows: list[list[str]] = [
        [
            "Excitation Frequency",
            f"{obj.excitation_frequency/1_000_000:.2f}",
            "MHz",
        ],
        [
            "ADC Sampling Frequency",
            f"{int(obj.adc_frequency)/1_000_000:.2f}",
            "MHz",
        ],
        [
            "Excitation Clock Frequency",
            f"{obj.excitation_clock_frequency/1_000_000:.2f}",
            "MHz",
        ],
        ["Pulse Repetition Frequency (PRF)", f"{obj.prf}", "Hz"],
        ["Number of Averages", f"{obj.num_averages}", ""],
        ["Record Length", f"{obj.record_length*1e6}", "us"],
        ["Additional Data", additional_data, ""],
        ["Data Sampling Mode", f"{obj.sampling_mode}", "bits"],
        ["Channels Receiving", f"{receiving_channels}", ""],
        ["Channels Driving", f"{driving_channels}", ""],
        ["Encoder CPR", f"{obj.encoder_cpr}", ""],
        ["Encoder Wheelbase", f"{obj.wheelbase}", "mm"],
        ["Wheel Radius", f"{obj.wheel_radius}", "mm"],
    ]
    print("\nDevice Setting Configuration:")
    _print_config_table(rows)


globals()["getVersion"] = get_version
globals()["getConfig"] = get_config
