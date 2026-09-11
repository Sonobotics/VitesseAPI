from __future__ import annotations
import numpy as np
import math
import struct
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from VitesseAPI import Vitesse


def ext_temp(np_list: np.ndarray[Any, np.dtype[np.integer[Any]]]) -> float:
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
            "np_list must contain exactly two bytes: [byte2, byte3]")

    byte2, byte3 = np_list
    byte2 = int(byte2)
    byte3 = int(byte3)

    # Reconstruct the 15-bit RTD ADC code.
    data = (byte2 << 7) + (byte3 >> 1)

    # Convert the ADC code to resistance.
    ratio = data / 32768.0
    RREF = 3900  # Reference resistance in ohms.
    resistance = RREF * ratio

    # Apply the inverse Callendar-Van Dusen formula.
    iCVD_A = 3.9083e-3
    iCVD_B = -5.775e-7
    PT100_NOMINAL = 100.0  # ohms

    Z1 = -iCVD_A
    Z2 = iCVD_A ** 2 - (4 * iCVD_B)
    Z3 = (4 * iCVD_B) / PT100_NOMINAL
    Z4 = 2 * iCVD_B
    try:
        temp = Z2 + (Z3 * resistance)
        temp = (math.sqrt(temp) + Z1) / Z4
    except:
        temp = 0
    return temp


def int_temp(np_list: np.ndarray[Any, np.dtype[np.uint8]]) -> float:
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
        raise ValueError("Input must be a NumPy array of two uint8 bytes.")

    # Combine the two bytes into a 16-bit word.
    raw16 = (int(np_list[0]) << 8) | int(np_list[1])

    # Extract the top 12 bits containing the temperature code.
    temp_code = raw16 >> 4

    # Convert the temperature code to degrees Celsius.
    temperature_c = (temp_code * 503.975 / 4096.0) - 273.15

    return temperature_c


def dec_enc(bytes_array: np.ndarray[Any, np.dtype[np.uint8]]) -> int:
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
        raise ValueError("Expected exactly 4 bytes.")

    # Decode the bytes as a signed, big-endian integer.
    count = int.from_bytes(
        bytes(int(value) for value in bytes_array),
        byteorder='big',
        signed=True,
    )
    return count


def dec_enc_float(bytes_array: np.ndarray[Any, np.dtype[np.uint8]]) -> float:
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
        raise ValueError("Expected exactly 4 bytes.")

    # Decode the bytes as an unsigned, big-endian bit pattern.
    count = int.from_bytes(
        bytes(int(value) for value in bytes_array),
        byteorder='big',
        signed=False,
    )
    # Interpret the bit pattern as an IEEE-754 single-precision float.
    return struct.unpack('>f', struct.pack('>I', count))[0]


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
    assert len(bin_str) == 24, "Input must be a 24-bit binary string."

    # Parse the binary string as an unsigned integer.
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
    assert len(bin_str) == 16, "Input must be a 24-bit binary string."

    # Parse the binary string as an unsigned integer, then align it to 24 bits.
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
    major = (version_u16 >> 8) & 0xFF   # Extract bits 15-8.
    minor = (version_u16 >> 4) & 0xF    # Extract bits 7-4.
    beta = version_u16 & 0xF           # Extract bits 3-0.

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
        [str(value).splitlines() or [""] for value in row]
        for row in table_rows
    ]
    column_widths = [
        max(
            len(line)
            for row in split_rows
            for line in row[column]
        )
        for column in range(len(table_rows[0]))
    ]
    border = "+" + "+".join(
        "-" * (width + 2) for width in column_widths
    ) + "+"

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


def getVersion(obj: Vitesse) -> None:
    """
    Print the firmware and API version information for a Vitesse device.

    Parameters:
    -----------
    obj : Vitesse
        Device object containing ``versionArray``, ``apiVersion``, and
        ``maxChannels`` attributes.
    """
    version_u16 = obj.versionArray
    version_display = ""
    for i, element in enumerate(version_u16):
        if i != len(version_u16)-1:
            version_display = version_display + str(element) + "."
        else:
            version_display = version_display + str(element)

    api_version_display = ""
    version_u16 = obj.apiVersion
    for i, element in enumerate(version_u16):
        if i != len(version_u16)-1:
            api_version_display = api_version_display + str(element) + "."
        else:
            api_version_display = api_version_display + str(element)

    rows: list[list[str]] = [
        ["Firmware Version", f"{version_display}"],
        ["API Version", f"{api_version_display}"],
        ["Maximum Number of Channels", f"{obj.maxChannels}"],
    ]

    print("\nDevice and API Version:")
    _print_config_table(rows)


def getConfig(obj: Vitesse) -> None:
    """
    Print the current configuration parameters of a Vitesse device.

    Parameters:
    -----------
    obj : Vitesse
        Device object containing the configuration and channel attributes
        used to build the display table. Channel numbers are displayed using
        one-based numbering, while the object's arrays are not modified.
    """

    peripheralDescriptionArray = obj.peripheralDescriptionArray

    enabled_sensors = [
        sensor
        for sensor, enabled in zip(peripheralDescriptionArray, [1,1,1,1,1,1,1,1])
        if enabled and sensor != "NA"
    ]
    additional_data = "\n".join(
        str(enabled_sensors[index:index + 2])
        for index in range(0, len(enabled_sensors), 2)
    ) or "[]"
    receiving_channels = [channel + 1 for channel in obj.enabledChannelReceive]
    driving_channels = [channel + 1 for channel in obj.enabledChannelDrive]

    rows: list[list[str]] = [
        ["Excitation Frequency",
            f"{obj.excitationFrequency/1_000_000:.2f}", "MHz"],
        ["ADC Sampling Frequency",
            f"{int(obj.adcFrequency)/1_000_000:.2f}", "MHz"],
        ["Excitation Clock Frequency",
            f"{obj.excitationClockFrequency/1_000_000:.2f}", "MHz"],
        ["Pulse Repetition Frequency (PRF)", f"{obj.prf}", "Hz"],
        ["Number of Averages", f"{obj.numAverages}", ""],
        ["Record Length", f"{obj.recordLength*1e6}", "us"],
        ["Additional Data", additional_data, ""],
        ["Data Sampling Mode", f"{obj.samplingMode}", "bits"],
        ["Channels Receiving", f"{receiving_channels}", ""],
        ["Channels Driving", f"{driving_channels}", ""],
        ["Encoder CPR", f"{obj.encoderCpr}", ""],
        ["Encoder Wheelbase", f"{obj.wheelbase}", "mm"],
        ["Wheel Radius", f"{obj.wheelRadius}", "mm"],
    ]
    print("\nDevice Setting Configuration:")
    _print_config_table(rows)
