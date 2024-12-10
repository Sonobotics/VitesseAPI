# SONUS Vitesse Python API

The SONUS Vitesse Python API is a high-performance interface designed to integrate and control the Sonobotics SONUS Vitesse data acquisition system through Python. This API enables users to configure the device, acquire data, and perform advanced operations seamlessly. Below is a comprehensive guide to the available functions and their usage.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Setup and Initialisation](#setup-and-initialisation)
3. [Function Descriptions](#function-descriptions)
   - [Initialise](#initialise)
   - [Change_Symbol](#change_symbol)
   - [Channel_Enable](#channel_enable)
   - [Change_Averages](#change_averages)
   - [Change_PRF](#change_prf)
   - [Change_Record_Length](#change_record_length)
   - [Trigger_Phasing](#trigger_phasing)
   - [Record_Delay](#record_delay)
   - [Get_Array](#get_array)
   - [Close_Device](#close_device)

---

## Introduction

The SONUS Vitesse Python API allows users to directly interact with the SONUS Vitesse data acquisition system for customised data manipulation. It provides high-speed functionality for configuring channels, setting parameters, and retrieving processed data in Python for further analysis.

---

## Setup and Initialisation

To use this API, ensure the following:
1. Python is installed on your system.
2. The `sonoboticsFTDI` library is installed and accessible.
3. The SONUS Vitesse device is connected and its serial number is known.

---

## Function Descriptions

### Initialise
Initialises the SONUS Vitesse device using its serial number. If the system is not Windows, it removes conflicting drivers.

**Parameters**:
- `serial_number` (string): Serial number of the device.

**Returns**:
- `spiDevice` object.

**Example:**
```python
spiDevice = Vitesse.Initialise('serial_number')
```

---

### Change_Symbol
Configures the device symbol parameters.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `num_chips`: Number of chips to be set.
- `num_cycles`: Number of cycles for the symbol.

**Example:**
```python
Vitesse.Change_Symbol(spiDevice, 4, 8)
```

---

### Channel_Enable
Activates specific channels on the device.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `channelsOnArray`: List of integers representing channels to enable (1 = ON, 0 = OFF).

**Returns**:
- `numChannelsOn` (int): Number of active channels.
- `numChannelsOnArray` (list): List of indices of active channels.

**Example:**
```python
numChannelsOn, numChannelsOnArray = Vitesse.Channel_Enable(spiDevice, [1, 0, 1, 0, 1, 0, 0, 1])
```

---

### Change_Averages
Configures the number of averaging cycles.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `num_averages`: Integer representing the number of averages.

**Range:**
- `num_averages`: 1 to 1000.

**Example:**
```python
Vitesse.Change_Averages(spiDevice, 16)
```

---

### Change_PRF
Sets the Pulse Repetition Frequency (PRF).

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `PRF`: Desired PRF in Hz.
- `adcFreq`: ADC clock frequency in Hz.

**Range:**
- `PRF`: 1 to 5000.

**Example:**
```python
Vitesse.Change_PRF(spiDevice, 1000, 30e6)
```

---

### Change_Record_Length
Configures the length of the data recording.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `recordLength`: Length of recording in seconds.
- `adcFreq`: ADC clock frequency in Hz.

**Returns**:
- `recordPoints` (int): Total number of data points recorded.

**Example:**
```python
recordPoints = Vitesse.Change_Record_Length(spiDevice, 100e-6, 30e6)
```

---

### Trigger_Phasing
Sets the trigger phasing for the channels.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `phaseArrayMicro`: List of phase values in microseconds for each channel.
- `adcFreq`: ADC clock frequency in Hz.

**Example:**
```python
Vitesse.Trigger_Phasing(spiDevice, [5, 3.2, 1, 0, 0, 0, 8, 0.5], 30e6)
```

---

### Record_Delay
Configures recording delays for each channel.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `delayArrayMicro`: List of delay values in microseconds for each channel.
- `adcFreq`: ADC clock frequency in Hz.

**Example:**
```python
Vitesse.Record_Delay(spiDevice, [5, 3.2, 1, 0, 0, 0, 8, 0.5], 30e6)
```

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
- `echosig` (array): Normalised and processed signal array.

**Example:**
```python
data = Vitesse.Get_Array(spiDevice, 100, 8, [0, 1, 2, 3, 4, 5, 6, 7], 1000, 1000)
```

---

### Close_Device
Closes the SPI connection with the device and clears the read buffer.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.

**Example:**
```python
Vitesse.Close_Device(spiDevice)
```

---

## Example Usage
```python
from Vitesse_API_S import Vitesse

serial_number = 'B'

spiDevice = Vitesse.Initialise(serial_number)

# signal parameters

num_averages = 100
num_chips = 7
num_cycles = 2
recordLength = 25e-6
PRF = 5000

channelsOnArray = [1, 0, 0, 0, 0, 0, 0, 0] # channels on
phaseArrayMicro = [0, 0, 0, 0, 0, 0, 0, 0] # phasing in microseconds
delayArrayMicro = [0, 0, 0, 0, 0, 0, 0, 0] # delay in microseconds

Vitesse.Change_Symbol(spiDevice, num_chips, num_cycles)
numChannelsOn, numChannelsOnArray = Vitesse.Channel_Enable(spiDevice, channelsOnArray)
Vitesse.Change_Averages(spiDevice, num_averages)
Vitesse.Change_PRF(spiDevice, PRF)
recordPoints = Vitesse.Change_Record_Length(spiDevice, recordLength)
Vitesse.Trigger_Phasing(spiDevice, phaseArrayMicro)
Vitesse.Record_Delay(spiDevice, delayArrayMicro)
print('')

# acquisition loop

count = 0

try:
    while True:
        count += 1
        array = Vitesse.Get_Array(spiDevice, num_averages, numChannelsOn, numChannelsOnArray, recordPoints, PRF)
        array = array.flatten()
        print('Signal (',count,'): ', array)

except KeyboardInterrupt:
    print('')
    print('Ctrl + C pressed!')
    print('')

finally:
    Vitesse.Channel_Enable(spiDevice, [0,0,0,0,0,0,0,0])
    Vitesse.Close_Device(spiDevice)
    print('')
    print('Device Closed!')
```

---

## Conclusion
This API provides a robust and efficient interface for interacting with the SONUS Vitesse system. With a focus on configurability and high-speed data handling, it is an essential tool for advanced signal acquisition and processing tasks.