# SONUS Vitesse Python API

The SONUS Vitesse Python API is a high-performance interface designed to integrate and control the Sonobotics SONUS Vitesse data acquisition system through Python. This API enables users to configure the device, acquire data, and perform advanced operations seamlessly. Below is a comprehensive guide to the available functions and their usage.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Setup and Initialization](#setup-and-initialization)
3. [Function Descriptions](#function-descriptions)
   - [Initialise](#initialise)
   - [Change_Symbol](#change_symbol)
   - [Channel_Enable](#channel_enable)
   - [Change_Averages](#change_averages)
   - [Change_PRF](#change_prf)
   - [ADC_Threshold](#adc_threshold)
   - [Change_Record_Length](#change_record_length)
   - [Trigger_Phasing](#trigger_phasing)
   - [Record_Delay](#record_delay)
   - [Get_Array](#get_array)
   - [Close_Device](#close_device)

---

## Introduction

The SONUS Vitesse Python API allows users to directly interact with the SONUS Vitesse data acquisition system for customized data manipulation. It provides high-speed functionality for configuring channels, setting parameters, and retrieving processed data in Python for further analysis.

---

## Setup and Initialization

To use this API, ensure the following:
1. Python is installed on your system.
2. The `sonoboticsFTDI` library is installed and accessible.
3. The SONUS Vitesse device is connected and its serial number is known.

---

## Function Descriptions

### Initialise
Initializes the SONUS Vitesse device using its serial number. If the system is not Windows, it removes conflicting drivers.

**Parameters**:
- `serial_number` (string): Serial number of the device.

**Returns**:
- `spiDevice` object.

---

### Change_Symbol
Configures the device symbol parameters.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `num_chips`: Number of chips to be set.
- `num_cycles`: Number of cycles for the symbol.

---

### Channel_Enable
Activates specific channels on the device.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `channelsOnArray`: List of integers representing channels to enable (1 = ON, 0 = OFF).

**Returns**:
- `numChannelsOn` (int): Number of active channels.
- `numChannelsOnArray` (list): List of indices of active channels.

---

### Change_Averages
Configures the number of averaging cycles.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `num_averages`: Integer representing the number of averages.

---

### Change_PRF
Sets the Pulse Repetition Frequency (PRF).

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `PRF`: Desired PRF in Hz.
- `adcFreq`: ADC clock frequency in Hz.

---

### ADC_Threshold
Sets the ADC threshold and trigger mode.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `threshold_level`: Integer representing the threshold level.
- `trigger`: Trigger mode (e.g., 0 for off, 1 for on).

---

### Change_Record_Length
Configures the length of the data recording.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `recordLength`: Length of recording in seconds.
- `adcFreq`: ADC clock frequency in Hz.

**Returns**:
- `recordPoints` (int): Total number of data points recorded.

---

### Trigger_Phasing
Sets the trigger phasing for the channels.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `phaseArrayMicro`: List of phase values in microseconds for each channel.
- `adcFreq`: ADC clock frequency in Hz.

---

### Record_Delay
Configures recording delays for each channel.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `delayArrayMicro`: List of delay values in microseconds for each channel.
- `adcFreq`: ADC clock frequency in Hz.

---

### Get_Array
Acquires the processed signal array from the device.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `num_averages`: Number of averaging cycles.
- `numChannelsOn`: Number of active channels.
- `numChannelsOnArray`: List of active channel indices.
- `recordPoints`: Total number of data points recorded.
- `PRF`: Pulse Repetition Frequency in Hz.

**Returns**:
- `echosig` (array): Normalized and processed signal array.

---

### Close_Device
Closes the SPI connection with the device and clears the read buffer.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.

---

This API is designed for advanced users familiar with signal processing and hardware configurations. For additional support or queries, please contact Sonobotics.

