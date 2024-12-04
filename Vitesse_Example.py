import matplotlib.pyplot as plt
from Vitesse_API_S import Vitesse

serial_number = 'AB'

spiDevice = Vitesse.Initialise(serial_number)

# signal parameters

num_averages = 100
num_chips = 7
num_cycles = 2
adcFreq = 50e6
recordLength = 25e-6
PRF = 5000
threshold_level = 0
trigger = 0
channelsOnArray = [0, 0, 0, 0, 0, 0, 0, 1] # channels on
phaseArrayMicro = [0, 0, 0, 0, 0, 0, 0, 0] # phasing in microseconds
delayArrayMicro = [0, 0, 0, 0, 0, 0, 0, 0] # delay in microseconds

Vitesse.Change_Symbol(spiDevice, num_chips, num_cycles)
numChannelsOn, numChannelsOnArray = Vitesse.Channel_Enable(spiDevice, channelsOnArray)
Vitesse.Change_Averages(spiDevice, num_averages)
Vitesse.Change_PRF(spiDevice, PRF, adcFreq)
Vitesse.ADC_Threshold(spiDevice, threshold_level, trigger)
recordPoints = Vitesse.Change_Record_Length(spiDevice, recordLength, adcFreq)
Vitesse.Trigger_Phasing(spiDevice, phaseArrayMicro, adcFreq)
Vitesse.Record_Delay(spiDevice, delayArrayMicro, adcFreq)
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