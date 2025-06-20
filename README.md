# SONUS Vitesse Python API

The SONUS Vitesse Python API is a high-performance interface designed to integrate and control the Sonobotics SONUS Vitesse data acquisition system through Python. This API enables users to configure the device, acquire data, and perform advanced operations seamlessly. Below is a comprehensive guide to the available functions and their usage.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Setup and Initialisation](#setup-and-initialisation)
   - [Python and Git Installation](#python-and-git-installation)
   - [Windows Driver Installation](#windows_driver_installation)
   - [Linux x86_64 Driver Installation](#linux-x86_64-driver-installation)
   - [Linux ARM Driver Installation](#linux-ARM-driver-installation)
3. [Function Descriptions](#function-descriptions)
   - [Initialise](#initialise)
   - [Initialise_Ser_No](#initialise_ser_no)
   - [List_Devices](#list_devices)
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

### Python and Git Installation

To install the API on your system, firstly download Python from https://www.python.org/downloads/ and Git from https://git-scm.com/downloads. Then, once these steps are complete, clone the VitesseAPI github onto your system using the below steps:

```bash
git clone https://github.com/SONOBOTICS-paddy/VitesseAPI.git
cd VitesseAPI
pip install -r requirements.txt
```

### Windows Driver Installation

To install the drivers for Windows, navigate to the 'Drivers' folder, open the 'windows_FTDI' folder and run the executable within it.

### Linux x86_64 Driver Installation

To install the drivers for an x86_64 Linux computer, navigate to the 'VitesseAPI' folder and run the following commands:

```bash
cd Drivers
sudo bash x86_64_install.sh
```

### Linux ARM Driver Installation

To install the drivers for an ARM Linux computer, navigate to the 'VitesseAPI' folder and run the following commands:

```bash
cd Drivers
sudo bash arm_install.sh
```

---

## Function Descriptions

### Initialise
Initialises the SONUS Vitesse device which is enumerated first.

**Returns**:
- `spiDevice` object.

**Example:**
```python
spiDevice = Vitesse.Initialise()
```

---

### Initialise_Ser_No
Initialises the SONUS Vitesse device using its serial number.

**Parameters**:
- `serial_number` (string): Serial number of the device.

**Returns**:
- `spiDevice` object.

**Example:**
```python
spiDevice = Vitesse.Initialise_Ser_No(serial_number)
```

---

### List_Devices
Lists all connected Sonobotics devices with their device type and serial number.

**Example:**
```python
spiDevice = Vitesse.List_Devices()
```

---

### Check_Validity
Checks the validity of the input signal to the Vitesse, ensuring that the system does not lose synchronisation.

**Parameters**:
- `phaseArrayMicro`: List of phase values in microseconds for each channel.
- `delayArrayMicro`: List of delay values in microseconds for each channel.
- `recordLength`: Length of recording in seconds.
- `PRF`: Desired PRF in Hz.

**Returns**:
- `spiDevice` object.

**Example:**
```python
Vitesse.Check_Validity(phaseArrayMicro, delayArrayMicro, recordLength, PRF)
```

---

### Change_Symbol
Configures the device excitation symbol parameters.

**Parameters**:
- `spiDevice`: Device object returned by `Initialise`.
- `num_chips`: Number of chips to be set.
- `num_cycles`: Number of cycles for the symbol.

**Range:**
- `num_chips`: 5 to 13.
- `num_cycles`: 1 to 3.

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
from Vitesse_API import Vitesse
import signal

## Device Initialisation

Vitesse.List_Devices()  ## Lists all available Sonobotics devices
serial_number = '1'     ## Serial number entry

spiDevice = Vitesse.Initialise()                       ## Initialises device enumerated first
# spiDevice = Vitesse.Initialise_Ser_No(serial_number) ## Initialises device based on serial number

## Signal Parameters

numAverages = 100      ## Averages Range: 1 to 1000
numChips = 7           ## Chips Range = 5 to 13 (5 chips = 5 MHz, 6 chips = 4.17 MHz, 7 chips = 3.57 MHz, 8 chips = 3.13 MHz, 
                       ## 9 chips = 2.78 MHz, 10 chips = 2.5 MHz, 11 chips = 2.27 MHz, 12 chips = 2.08 MHz, 13 chips = 1.92 MHz)
                       ## (Excitation Frequency = 1 / numChips * 2 * 20e-9)
numCycles = 2          ## Cycles Range: 1 to 3
recordLength = 25e-6   ## Record Length Range: 0 to 100 us (8 CH), 0 to 200 us (4 CH), 0 to 800 us (8 CH)
PRF = 1000             ## PRF Range: 1 to 5000 Hz
channelsOnArray = [1, 0, 0, 0, 0, 0, 0, 0] ## Channels on e.g. [Channel 1 (on/off), Channel 2(on/off), etc.]
phaseArrayMicro = [0, 0, 0, 0, 0, 0, 0, 0] ## Phasing in microseconds for each channel e.g. [Channel 1 Phase (us), Channel 2 Phase (us), etc.]
delayArrayMicro = [0, 0, 0, 0, 0, 0, 0, 0] ## Delay in microseconds for each channel e.g. [Channel 1 Delay (us), Channel 2 Delay (us), etc.]

## Checking Validity of Signal Settings

Vitesse.Check_Validity(phaseArrayMicro, delayArrayMicro, recordLength, PRF)

## Settings Initialised on Vitesse

numChannelsOn, numChannelsOnArray = Vitesse.Channel_Enable(spiDevice, channelsOnArray)
Vitesse.Change_Symbol(spiDevice, numChips, numCycles)
Vitesse.Change_Averages(spiDevice, numAverages)
Vitesse.Change_PRF(spiDevice, PRF)
recordPoints = Vitesse.Change_Record_Length(spiDevice, recordLength)
Vitesse.Trigger_Phasing(spiDevice, phaseArrayMicro)
Vitesse.Record_Delay(spiDevice, delayArrayMicro)
print('Initialised Vitesse!\n')

## Code to Check Get_Array is Complete Before Closing Device

loop_complete = False
def handle_keyboard_interrupt(signum, frame):
    global loop_complete
    loop_complete = True
signal.signal(signal.SIGINT, handle_keyboard_interrupt)

## Acquisition Loop

count = 0

try:
    while not loop_complete:
        count += 1
        array = Vitesse.Get_Array(spiDevice, numAverages, numChannelsOn, numChannelsOnArray, recordPoints, PRF)
        array = array.flatten()
        print('Signal (', count, '): ', array)

finally:
    Vitesse.Close_Device(spiDevice)
    print('\nDevice Closed!\n')
```

---

## Conclusion
This API provides a robust and efficient interface for interacting with the SONUS Vitesse system. With a focus on configurability and high-speed data handling, it is an essential tool for advanced signal acquisition and processing tasks.