from Vitesse_API import Vitesse
import matplotlib.pyplot as plt

## Device Initialisation

V = Vitesse()       ## Instantiates Vitesse instance
V.List_Devices()    ## Lists all available Sonobotics devices
V.Initialise()      ## Initialises device enumerated first

serial_number = '1'                  ## Serial number entry
# V.Initialise_Ser_No(serial_number) ## Initialises device based on serial number

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

V.Check_Validity(phaseArrayMicro, delayArrayMicro, recordLength, PRF)

## Settings Initialised on Vitesse

V.Channel_Enable(channelsOnArray)
V.Change_Symbol(numChips, numCycles)
V.Change_Averages(numAverages)
V.Change_PRF(PRF)
V.Change_Record_Length(recordLength)
V.Trigger_Phasing(phaseArrayMicro)
V.Record_Delay(delayArrayMicro)
print('Initialised Vitesse!\n')

## Plot Initialisation

fig, ax = plt.subplots()
ln1, = plt.plot([], [])
x_data1, y_data1 = [], []
ax.set_xlim(0, V.recordPoints*V.numChannelsOn)
ax.set_ylim(-2048, 2048)
ax.set_xlabel('Time')
ax.set_ylabel('Arb. Amplitude')

## Acquisition Loop

count = 0

try:
    while True:
        ## Acquiring Data
        count += 1
        array = V.Get_Array()

        ## Plotting Code (shows all channels in order in one graph)
        array = array.flatten()
        x_data1 = range(0, len(array))
        y_data1 = array
        ln1.set_data(x_data1, y_data1)
        plt.pause(0.001)
except KeyboardInterrupt:
    print('Operation Interrupted.\n')
finally:
    V.Close_Device()
    print('Device Closed!\n')