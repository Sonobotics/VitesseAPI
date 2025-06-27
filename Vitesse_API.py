import sys
import sonoboticsFTDI as sbftdi
import time
import numpy as np
import signal

READ_DELAY = 500e-6
MSG_BYTES = 3
THRESHOLD_LEVEL = 0
TRIGGER = 0
ADC_FREQ = 50e6
LOOP_COMPLETE = False

class Vitesse:
    def Handle_Keyboard_Interrupt(signum, frame):
        global LOOP_COMPLETE
        LOOP_COMPLETE = True

    signal.signal(signal.SIGINT, Handle_Keyboard_Interrupt)

    def Initialise():
        global maxChannels

        numDevices = sbftdi.getNumDevices()
        serialNumList = []
        serial_number = '0'

        for i in range(0, numDevices):
            spiDevice = sbftdi.ftdiChannel("SPI", "deviceNum", i)
            eepromData = spiDevice.readEEPROM()

            manufacturer = eepromData.get('Manufacturer')
            serial_number = eepromData.get('Serial Number')

            if manufacturer == 'Sonobotics' and serial_number not in serialNumList:
                spiDevice.close()
                break

            spiDevice.close()

        if serial_number == '0' or manufacturer != 'Sonobotics':
            print('No Sonobotics devices connected!')
            sys.exit(0)

        serial_number = serial_number + 'B'

        spiDevice = sbftdi.ftdiChannel("SPI", "serialNum", serial_number.encode())

        eepromData = spiDevice.readEEPROM()

        print('\n-----------Selected Device:-----------')

        for key in ['Device','Serial Number']:
            if key in eepromData:
                if key == 'Serial Number':
                    print(f"{key:<14}: {eepromData[key]}\n")
                if key == 'Device':
                    print(f"{key:<14}: {eepromData[key]}")
                    maxChannels = int(eepromData[key][0])

        Vitesse.ADC_Threshold(spiDevice, THRESHOLD_LEVEL, TRIGGER)

        return spiDevice

    def Initialise_Ser_No(serial_number):
        global maxChannels

        serial_number = serial_number + 'B'
            
        spiDevice = sbftdi.ftdiChannel("SPI", "serialNum", serial_number.encode())

        eepromData = spiDevice.readEEPROM()

        print('\n-----------Selected Device:-----------')

        for key in ['Device','Serial Number']:
            if key in eepromData:
                if key == 'Serial Number':
                    print(f"{key:<14}: {eepromData[key]}\n")
                if key == 'Device':
                    print(f"{key:<14}: {eepromData[key]}")
                    maxChannels = int(eepromData[key][0])

        Vitesse.ADC_Threshold(spiDevice, THRESHOLD_LEVEL, TRIGGER)

        return spiDevice
    
    def List_Devices():
        numDevices = sbftdi.getNumDevices()
        serialNumList = []
        devCount = 0

        for i in range(0, numDevices):
            spiDevice = sbftdi.ftdiChannel("SPI", "deviceNum", i)
            eepromData = spiDevice.readEEPROM()

            manufacturer = eepromData.get('Manufacturer')
            serial_number = eepromData.get('Serial Number')

            if manufacturer != 'Sonobotics' or serial_number in serialNumList:
                spiDevice.close()
            else:
                devCount += 1

                print(f'\n---------------Device {devCount}---------------')

                for key in ['Device', 'Serial Number']:
                    if key in eepromData:
                        print(f"{key:<14}: {eepromData[key]}")

                serialNumList.append(serial_number)

                spiDevice.close()

        if devCount == 0:
            print('No Sonobotics devices connected!')
            sys.exit(0)
    
    def Check_Validity(phaseArrayMicro, delayArrayMicro, recordLength, PRF):
        if PRF == 0:
            print('PRF too low!')
            sys.exit(0)
        if (np.max(phaseArrayMicro) + np.max(delayArrayMicro)) / 1000000 + recordLength >= 1/PRF:
            print('Provided signal is invalid!')
            sys.exit(0)
        else:
            print('Signal is valid!\n')

    def Change_Symbol(spiDevice, num_chips, num_cycles):
        if num_chips > 13 or num_chips < 5:
            print('Number of chips out of range!')
            sys.exit(0)
        elif num_cycles > 3 or num_cycles < 1:
            print('Number of cycles out of range!')
            sys.exit(0)
        else:
            symbolByte1 = int(num_chips)
            symbolByte2 = int(num_cycles)

            symbol = ['1', 'p', 'a']
            symbolStr = f'{ord(symbol[0]):02x}{symbolByte1:02x}{symbolByte2:02x}{ord(symbol[1]):02x}{ord(symbol[2]):02x}'
            symbolByt = bytes.fromhex(symbolStr)

            spiDevice.write(symbolByt)
            time.sleep(READ_DELAY)
            dataBack = spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'Symbol Change: {message}\n')

    def Channel_Enable(spiDevice, channelsOnArray):
        reversedChannelsOnArray = channelsOnArray[::-1]
        channelsOn = ''.join(map(str, reversedChannelsOnArray))
        channelByte = int(channelsOn[-8:],2)
        numChannelsOn = np.count_nonzero(reversedChannelsOnArray)
        numChannelsOnArray = [index for index, value in enumerate(reversedChannelsOnArray) if value == 1]

        if numChannelsOn > maxChannels:
            print('Maximum number of channels exceeded!')
            sys.exit(0)
        else:
            channel = ['2', 'a', 'a', 'a']
            channelStr = f'{ord(channel[0]):02x}{channelByte:02x}{ord(channel[1]):02x}{ord(channel[2]):02x}{ord(channel[3]):02x}'
            channelByt = bytes.fromhex(channelStr)

            spiDevice.write(channelByt)
            time.sleep(READ_DELAY)
            dataBack = spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'Channel: {message}\n')

        return numChannelsOn, numChannelsOnArray

    def Change_Averages(spiDevice, num_averages):
        if num_averages > 1000:
            print('Maximum number of averages exceeded!')
            sys.exit(0)
        elif num_averages < 1:
            print('Number of averages too low!')
            sys.exit(0)
        else:
            bitAveVals = np.binary_repr(num_averages, width=16)
            numAveByte1 = int(bitAveVals[-8:],2)
            numAveByte2 = int(bitAveVals[-16:-8],2)

            average = ['3', 'a', 'a']
            averageStr = f'{ord(average[0]):02x}{numAveByte1:02x}{numAveByte2:02x}{ord(average[1]):02x}{ord(average[2]):02x}'
            averageByt = bytes.fromhex(averageStr)

            spiDevice.write(averageByt)
            time.sleep(READ_DELAY)
            dataBack = spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'Averages: {message}\n') 

    def Change_PRF(spiDevice, PRF):
        if PRF > 20000:
            print('Maximum PRF exceeded!')
            sys.exit(0)
        elif PRF < 1:
            print('PRF too low!')
            sys.exit(0)
        else:
            PRFCount = int((1/PRF)/(1/ADC_FREQ))
            bitPRFVals = np.binary_repr(PRFCount, width=32)
            numPRFByte1 = int(bitPRFVals[-8:],2)
            numPRFByte2 = int(bitPRFVals[-16:-8],2)
            numPRFByte3 = int(bitPRFVals[-24:-16],2)
            numPRFByte4 = int(bitPRFVals[-32:-24],2)

            pulse = ['4']
            pulseStr = f'{ord(pulse[0]):02x}{numPRFByte1:02x}{numPRFByte2:02x}{numPRFByte3:02x}{numPRFByte4:02x}'
            pulseByt = bytes.fromhex(pulseStr)

            spiDevice.write(pulseByt)
            time.sleep(READ_DELAY)
            dataBack = spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'PRF: {message}\n')

    def ADC_Threshold(spiDevice, THRESHOLD_LEVEL, TRIGGER):
        bitADCVals = np.binary_repr(THRESHOLD_LEVEL, width=8)
        numADCByte = int(bitADCVals[-8:],2)

        ADC = ['5',str(TRIGGER),'a','a']
        ADCStr = f'{ord(ADC[0]):02x}{ord(ADC[1]):02x}{numADCByte:02x}{ord(ADC[2]):02x}{ord(ADC[3]):02x}'
        ADCByt = bytes.fromhex(ADCStr)

        spiDevice.write(ADCByt)
        time.sleep(READ_DELAY)
        dataBack = spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'ADC: {message}\n')

    def Change_Record_Length(spiDevice, recordLength):
        recordPoints = int(recordLength * ADC_FREQ)
        bitRecVals = np.binary_repr(int(recordPoints), width=16)
        numRecByte1 = int(bitRecVals[-8:],2)
        numRecByte2 = int(bitRecVals[-16:-8],2)

        record = ['6', 'a', 'a']
        recordStr = f'{ord(record[0]):02x}{numRecByte1:02x}{numRecByte2:02x}{ord(record[1]):02x}{ord(record[2]):02x}'
        recordByt = bytes.fromhex(recordStr)

        spiDevice.write(recordByt)
        time.sleep(READ_DELAY)
        dataBack = spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'Record Length: {message}\n')

        return recordPoints

    def Trigger_Phasing(spiDevice, phaseArrayMicro):
        phaseArray = np.ceil(np.array(phaseArrayMicro[::-1]) * ADC_FREQ / 1_000_000)
        phasingActive = any(phaseArray > 0)
        if phasingActive == False:
            phaseByt = b'7Naaa'
            spiDevice.write(phaseByt)
            time.sleep(READ_DELAY)
            dataBack = spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'No Trigger Phasing: {message}\n') 
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
                time.sleep(READ_DELAY)
                dataBack = spiDevice.read(1)
                result = int.from_bytes(dataBack, byteorder='big')
                message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
                if message == 'Fail!': print(f'TRIGGER Phase (CH{8-i}): {message}\n')

    def Record_Delay(spiDevice, delayArrayMicro):
        delayArray = np.ceil(np.array(delayArrayMicro[::-1]) * ADC_FREQ / 1_000_000)
        delayActive = any(delayArray > 0)
        if delayActive == False:
            delayByt = b'8Naaa'
            spiDevice.write(delayByt)
            time.sleep(READ_DELAY)
            dataBack = spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'No Record Delay: {message}\n') 
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
                time.sleep(READ_DELAY)
                dataBack = spiDevice.read(1)
                result = int.from_bytes(dataBack, byteorder='big')
                message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
                if message == 'Fail!': print(f'Record Delay (CH{8-i}): {message}\n')

    def Get_Array(spiDevice, num_averages, numChannelsOn, numChannelsOnArray, recordPoints, PRF):
        while not LOOP_COMPLETE:
            spiDevice.write(b'faaaa')
            time.sleep(num_averages/PRF)

            ByteBack = 0

            while ByteBack != 100:
                Byte = spiDevice.read(1)
                time.sleep(READ_DELAY)
                ByteBack = np.frombuffer(Byte, dtype = np.uint8)
                
            if int(recordPoints*MSG_BYTES*numChannelsOn+2*numChannelsOn-1) < 64000:
                bytesBack = spiDevice.read(int(recordPoints*MSG_BYTES*numChannelsOn+2*numChannelsOn-1))
            else:
                bytesBack = spiDevice.read(int((recordPoints*MSG_BYTES*numChannelsOn+2*numChannelsOn-1)/2))
                bytesBack += spiDevice.read(int(recordPoints*MSG_BYTES*numChannelsOn+2*numChannelsOn-1)-int((recordPoints*MSG_BYTES*numChannelsOn+2*numChannelsOn-1)/2))

            array = np.frombuffer(bytesBack, dtype = np.uint8)
            array = np.insert(array, 0, 100)
            array = np.array(array, dtype = np.float16)
            
            channel = np.split(array, numChannelsOn)
            channel = [channel[1:-1] for channel in channel]
            
            bytearray = np.empty((numChannelsOn, recordPoints * MSG_BYTES // 3, 3), dtype=float)
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
        finalarray = [0,1,0]
        while finalarray[-1] != finalarray[-2] or finalarray[-2] != finalarray[-3]:
            finalarray = np.frombuffer(spiDevice.read(10), dtype = np.uint8)
        Vitesse.Channel_Enable(spiDevice, [0,0,0,0,0,0,0,0])
        spiDevice.close()