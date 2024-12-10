import sys
import os
import sonoboticsFTDI as sbftdi
import time
import numpy as np

# message parameters

readDelay = 500e-6
msgBytes = 3
threshold_level = 0
trigger = 0

class Vitesse:
    def Initialise(serial_number):
        if sys.platform.startswith("win") == False:
            os.system('sudo rmmod ftdi_sio 2>/dev/null')

        if serial_number[-1] == 'A':
            print('Serial number ends in wrong character!')
            sys.exit(0)
            
        spiDevice = sbftdi.ftdiChannel("SPI", "serialNum", serial_number.encode())

        Vitesse.ADC_Threshold(spiDevice, threshold_level, trigger)

        return spiDevice

    def Change_Symbol(spiDevice, num_chips, num_cycles):
        symbolByte1 = int(num_chips)
        symbolByte2 = int(num_cycles)

        symbol = ['1', 'p', 'a']
        symbolStr = f'{ord(symbol[0]):02x}{symbolByte1:02x}{symbolByte2:02x}{ord(symbol[1]):02x}{ord(symbol[2]):02x}'
        symbolByt = bytes.fromhex(symbolStr)

        spiDevice.write(symbolByt)
        time.sleep(readDelay)
        dataBack = spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'Symbol Change: {message}')

    def Channel_Enable(spiDevice, channelsOnArray):
        channelsOn = ''.join(map(str, channelsOnArray))
        channelByte = int(channelsOn[-8:],2)
        numChannelsOn = np.count_nonzero(channelsOnArray)

        numChannelsOnArray = [index for index, value in enumerate(channelsOnArray) if value == 1]

        channel = ['2', 'a', 'a', 'a']
        channelStr = f'{ord(channel[0]):02x}{channelByte:02x}{ord(channel[1]):02x}{ord(channel[2]):02x}{ord(channel[3]):02x}'
        channelByt = bytes.fromhex(channelStr)

        spiDevice.write(channelByt)
        time.sleep(readDelay)
        dataBack = spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'Channel: {message}')

        return numChannelsOn, numChannelsOnArray

    def Change_Averages(spiDevice, num_averages):
        bitAveVals = np.binary_repr(num_averages, width=16)
        numAveByte1 = int(bitAveVals[-8:],2)
        numAveByte2 = int(bitAveVals[-16:-8],2)

        average = ['3', 'a', 'a']
        averageStr = f'{ord(average[0]):02x}{numAveByte1:02x}{numAveByte2:02x}{ord(average[1]):02x}{ord(average[2]):02x}'
        averageByt = bytes.fromhex(averageStr)

        spiDevice.write(averageByt)
        time.sleep(readDelay)
        dataBack = spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'Averages: {message}') 

    def Change_PRF(spiDevice, PRF, adcFreq):
        PRFCount = int((1/PRF)/(1/adcFreq))
        bitPRFVals = np.binary_repr(PRFCount, width=32)
        numPRFByte1 = int(bitPRFVals[-8:],2)
        numPRFByte2 = int(bitPRFVals[-16:-8],2)
        numPRFByte3 = int(bitPRFVals[-24:-16],2)
        numPRFByte4 = int(bitPRFVals[-32:-24],2)

        pulse = ['4']
        pulseStr = f'{ord(pulse[0]):02x}{numPRFByte1:02x}{numPRFByte2:02x}{numPRFByte3:02x}{numPRFByte4:02x}'
        pulseByt = bytes.fromhex(pulseStr)

        spiDevice.write(pulseByt)
        time.sleep(readDelay)
        dataBack = spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'PRF: {message}')

    def ADC_Threshold(spiDevice, threshold_level, trigger):
        bitADCVals = np.binary_repr(threshold_level, width=8)
        numADCByte = int(bitADCVals[-8:],2)

        ADC = ['5',str(trigger),'a','a']
        ADCStr = f'{ord(ADC[0]):02x}{ord(ADC[1]):02x}{numADCByte:02x}{ord(ADC[2]):02x}{ord(ADC[3]):02x}'
        ADCByt = bytes.fromhex(ADCStr)

        spiDevice.write(ADCByt)
        time.sleep(readDelay)
        dataBack = spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'ADC: {message}')

    def Change_Record_Length(spiDevice, recordLength, adcFreq):
        recordPoints = int(recordLength * adcFreq)
        bitRecVals = np.binary_repr(int(recordPoints), width=16)
        numRecByte1 = int(bitRecVals[-8:],2)
        numRecByte2 = int(bitRecVals[-16:-8],2)

        record = ['6', 'a', 'a']
        recordStr = f'{ord(record[0]):02x}{numRecByte1:02x}{numRecByte2:02x}{ord(record[1]):02x}{ord(record[2]):02x}'
        recordByt = bytes.fromhex(recordStr)

        spiDevice.write(recordByt)
        time.sleep(readDelay)
        dataBack = spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'Record Length: {message}')

        return recordPoints

    def Trigger_Phasing(spiDevice, phaseArrayMicro, adcFreq):
        phaseArray = np.ceil(np.array(phaseArrayMicro) * adcFreq / 1_000_000)
        phasingActive = any(phaseArray > 0)
        if phasingActive == False:
            phaseByt = b'7Naaa'
            spiDevice.write(phaseByt)
            time.sleep(readDelay)
            dataBack = spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'No Trigger Phasing: {message}') 
        else:
            phase_indices = [index for index, value in enumerate(phaseArray) if value != 0]
            for i in phase_indices:
                phaseVal = phaseArray[i]
                numPhaseByte1 = int(7-i)
                bitPhaseVals = np.binary_repr(int(phaseVal), width=24)
                numPhaseByte2 = int(bitPhaseVals[-8:],2)
                numPhaseByte3 = int(bitPhaseVals[-16:-8],2)
                numPhaseByte4 = int(bitPhaseVals[-24:-16],3)
                phase = ['7']
                phaseStr = f'{ord(phase[0]):02x}{numPhaseByte1:02x}{numPhaseByte2:02x}{numPhaseByte3:02x}{numPhaseByte4:02x}'
                phaseByt = bytes.fromhex(phaseStr)

                spiDevice.write(phaseByt)
                time.sleep(readDelay)
                dataBack = spiDevice.read(1)
                result = int.from_bytes(dataBack, byteorder='big')
                message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
                if message == 'Fail!': print(f'Trigger Phase (CH{8-i}): {message}')

    def Record_Delay(spiDevice, delayArrayMicro, adcFreq):
        delayArray = np.ceil(np.array(delayArrayMicro) * adcFreq / 1_000_000)
        delayActive = any(delayArray > 0)
        if delayActive == False:
            delayByt = b'8Naaa'
            spiDevice.write(delayByt)
            time.sleep(readDelay)
            dataBack = spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'No Record Delay: {message}') 
        else:
            delay_indices = [index for index, value in enumerate(delayArray) if value != 0]
            for i in delay_indices:
                delayVal = delayArray[i]
                numDelayByte1 = int(7-i)
                bitDelayVals = np.binary_repr(int(delayVal), width=24)
                numDelayByte2 = int(bitDelayVals[-8:],2)
                numDelayByte3 = int(bitDelayVals[-16:-8],2)
                numDelayByte4 = int(bitDelayVals[-24:-16],3)
                delay = ['8']
                delayStr = f'{ord(delay[0]):02x}{numDelayByte1:02x}{numDelayByte2:02x}{numDelayByte3:02x}{numDelayByte4:02x}'
                delayByt = bytes.fromhex(delayStr)

                spiDevice.write(delayByt)
                time.sleep(readDelay)
                dataBack = spiDevice.read(1)
                result = int.from_bytes(dataBack, byteorder='big')
                message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
                if message == 'Fail!': print(f'Record Delay (CH{8-i}): {message}')

    def Get_Array(spiDevice, num_averages, numChannelsOn, numChannelsOnArray, recordPoints, PRF):
        spiDevice.write(b'faaaa')
        time.sleep(num_averages/PRF)

        ByteBack = 0

        while ByteBack != 100:
            Byte = spiDevice.read(1)
            time.sleep(readDelay)
            ByteBack = np.frombuffer(Byte, dtype = np.uint8)
            
        if int(recordPoints*msgBytes*numChannelsOn+2*numChannelsOn-1) < 64000:
            bytesBack = spiDevice.read(int(recordPoints*msgBytes*numChannelsOn+2*numChannelsOn-1))
        else:
            bytesBack = spiDevice.read(int((recordPoints*msgBytes*numChannelsOn+2*numChannelsOn-1)/2))
            bytesBack += spiDevice.read(int(recordPoints*msgBytes*numChannelsOn+2*numChannelsOn-1)-int((recordPoints*msgBytes*numChannelsOn+2*numChannelsOn-1)/2))

        array = np.frombuffer(bytesBack, dtype = np.uint8)
        array = np.insert(array, 0, 100)
        array = np.array(array, dtype = np.float16)
        
        channel = np.split(array, numChannelsOn)
        channel = [channel[1:-1] for channel in channel]
        
        bytearray = np.empty((numChannelsOn, recordPoints * msgBytes // 3, 3), dtype=float)
        reshapearray = np.empty((numChannelsOn, recordPoints), dtype=float)
        normarray = np.empty((numChannelsOn, recordPoints), dtype=float)
        echosig = np.empty((numChannelsOn, recordPoints), dtype=float)
        
        for i in range(numChannelsOn):
            bytearray[i] = np.reshape(channel[i], (-1,3))
            reshapearray[i] = bytearray[i][:,0] + bytearray[i][:,1] * (2**8) + bytearray[i][:,2] * (2**16)
            normarray[i] = np.divide(reshapearray[i], num_averages)
            if numChannelsOnArray[i] == 2 or numChannelsOnArray[i] == 3 or numChannelsOnArray[i] == 4 or numChannelsOnArray[i] == 5:
                echosig[i] = np.subtract(normarray[i], 2048) * -1
            else:
                echosig[i] = np.subtract(normarray[i], 2048)

        return echosig

    def Close_Device(spiDevice):
        spiDevice.read(100000)
        spiDevice.close()
