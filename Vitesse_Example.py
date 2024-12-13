from Vitesse_API import Vitesse
import signal

## Device Initialisation

serial_number = 'B'

spiDevice = Vitesse.Initialise(serial_number)

## Signal Parameters

numAverages = 100      ## Averages Range: 1 to 1000

numChips = 7           ## Chips Range = 5 to 13 (5 chips = 5 MHz, 6 chips = 4.17 MHz, 7 chips = 3.57 MHz, 8 chips = 3.13 MHz, 
                       ## 9 chips = 2.78 MHz, 10 chips = 2.5 MHz, 11 chips = 2.27 MHz, 12 chips = 2.08 MHz, 13 chips = 1.92 MHz)
                       ## (Excitation Frequency = 1 / numChips * 2 * 20e-9)

numCycles = 2          ## Cycles Range: 1 to 3

recordLength = 25e-6   ## Record Length Range: 0 to 100 us (8 CH), 0 to 200 us (4 CH), 0 to 800 us (8 CH)

PRF = 2000             ## PRF Range: 1 to 5000 Hz

channelsOnArray = [1, 1, 1, 1, 1, 1, 1, 1] ## Channels on e.g. [Channel 1 (on/off), Channel 2(on/off), etc.]
phaseArrayMicro = [0, 0, 0, 0, 0, 0, 0, 0] ## Phasing in microseconds for each channel e.g. [Channel 1 Phase (us), Channel 2 Phase (us), etc.]
delayArrayMicro = [0, 0, 0, 0, 0, 0, 0, 0] ## Delay in microseconds for each channel e.g. [Channel 1 Delay (us), Channel 2 Delay (us), etc.]

## Checking Validity of Signal Settings

Vitesse.Check_Validity(phaseArrayMicro, delayArrayMicro, recordLength, PRF)

## Settings Initialised on Vitesse

Vitesse.Change_Symbol(spiDevice, numChips, numCycles)
numChannelsOn, numChannelsOnArray = Vitesse.Channel_Enable(spiDevice, channelsOnArray)
Vitesse.Change_Averages(spiDevice, numAverages)
Vitesse.Change_PRF(spiDevice, PRF)
recordPoints = Vitesse.Change_Record_Length(spiDevice, recordLength)
Vitesse.Trigger_Phasing(spiDevice, phaseArrayMicro)
Vitesse.Record_Delay(spiDevice, delayArrayMicro)
print('Initialised Vitesse!')

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
    print('Device Closed!')