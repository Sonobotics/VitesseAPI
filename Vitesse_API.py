import sys
import sonoboticsFTDI as sbftdi
import time
import numpy as np
import signal

LOOP_COMPLETE = False

class Vitesse:
    def __init__(self):
        self.READ_DELAY = 500e-6
        self.MSG_BYTES = 3
        self.THRESHOLD_LEVEL = 0
        self.TRIGGER = 0
        self.ADC_FREQ = 50e6
        self.numDevices = 0
        self.num_averages = 100

    def Initialise(self):
        self.numDevices = sbftdi.getNumDevices()
        serialNumList = []
        serial_number = '0'

        for i in range(0, self.numDevices):
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

        self.spiDevice = sbftdi.ftdiChannel("SPI", "serialNum", serial_number.encode())

        initialarray = [0,0,0]
        while initialarray[-1] != 200 or initialarray[-2] != 200 or initialarray[-3] != 200:
            initialarray = np.frombuffer(self.spiDevice.read(1000), dtype = np.uint8)

        eepromData = self.spiDevice.readEEPROM()

        print('\n-----------Selected Device:-----------')

        for key in ['Device','Serial Number']:
            if key in eepromData:
                if key == 'Serial Number':
                    print(f"{key:<14}: {eepromData[key]}\n")
                if key == 'Device':
                    print(f"{key:<14}: {eepromData[key]}")
                    self.maxChannels = int(eepromData[key][0])

        Vitesse.ADC_Threshold(self)

    def Initialise_Ser_No(self, serial_number):
        global maxChannels

        serial_number = serial_number + 'B'
            
        self.spiDevice = sbftdi.ftdiChannel("SPI", "serialNum", serial_number.encode())

        eepromData = self.spiDevice.readEEPROM()

        print('\n-----------Selected Device:-----------')

        for key in ['Device','Serial Number']:
            if key in eepromData:
                if key == 'Serial Number':
                    print(f"{key:<14}: {eepromData[key]}\n")
                if key == 'Device':
                    print(f"{key:<14}: {eepromData[key]}")
                    self.maxChannels = int(eepromData[key][0])

        Vitesse.ADC_Threshold(self)
    
    def List_Devices(self):
        self.numDevices = sbftdi.getNumDevices()
        serialNumList = []
        devCount = 0

        for i in range(0, self.numDevices):
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
    
    def Check_Validity(self, phaseArrayMicro, delayArrayMicro, recordLength, PRF):
        if PRF == 0:
            print('PRF too low!')
            sys.exit(0)
        if (np.max(phaseArrayMicro) + np.max(delayArrayMicro)) / 1000000 + recordLength >= 1/PRF:
            print('Provided signal is invalid!')
            sys.exit(0)
        else:
            print('Signal is valid!\n')

    def Change_Symbol(self, num_chips, num_cycles):
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

            self.spiDevice.write(symbolByt)
            time.sleep(self.READ_DELAY)
            dataBack = self.spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'Symbol Change: {message}\n')

    def Channel_Enable(self, channelsOnArray):
        reversedChannelsOnArray = channelsOnArray[::-1]
        channelsOn = ''.join(map(str, reversedChannelsOnArray))
        channelByte = int(channelsOn[-8:],2)
        self.numChannelsOn = np.count_nonzero(reversedChannelsOnArray)
        self.numChannelsOnArray = [index for index, value in enumerate(reversedChannelsOnArray) if value == 1]

        if self.numChannelsOn > self.maxChannels:
            print('Maximum number of channels exceeded!\n')
            sys.exit(0)
        else:
            channel = ['2', 'a', 'a', 'a']
            channelStr = f'{ord(channel[0]):02x}{channelByte:02x}{ord(channel[1]):02x}{ord(channel[2]):02x}{ord(channel[3]):02x}'
            channelByt = bytes.fromhex(channelStr)

            self.spiDevice.write(channelByt)
            time.sleep(self.READ_DELAY)
            dataBack = self.spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'Channel: {message}\n')

    def Change_Averages(self, num_averages):
        num_averages_past = self.num_averages
        if num_averages > 1000:
            print('Maximum number of averages exceeded!\n')
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

            self.spiDevice.write(averageByt)
            time.sleep(self.READ_DELAY)
            dataBack = self.spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            if result == 50:
                message = 'Pass!'
                self.num_averages = num_averages
            elif result == 200:
                message = 'Fail!'
                self.num_averages = num_averages_past
            else:
                message = 'Invalid!'
                self.num_averages = num_averages_past

            if message == 'Fail!': print(f'Averages: {message}\n')

    def Change_PRF(self, PRF):
        if PRF > 20000:
            print('Maximum PRF exceeded!')
            sys.exit(0)
        elif PRF < 1:
            print('PRF too low!')
            sys.exit(0)
        else:
            PRFCount = int((1/PRF)/(1/self.ADC_FREQ))
            bitPRFVals = np.binary_repr(PRFCount, width=32)
            numPRFByte1 = int(bitPRFVals[-8:],2)
            numPRFByte2 = int(bitPRFVals[-16:-8],2)
            numPRFByte3 = int(bitPRFVals[-24:-16],2)
            numPRFByte4 = int(bitPRFVals[-32:-24],2)

            pulse = ['4']
            pulseStr = f'{ord(pulse[0]):02x}{numPRFByte1:02x}{numPRFByte2:02x}{numPRFByte3:02x}{numPRFByte4:02x}'
            pulseByt = bytes.fromhex(pulseStr)

            self.spiDevice.write(pulseByt)
            time.sleep(self.READ_DELAY)
            dataBack = self.spiDevice.read(1)
            result = int.from_bytes(dataBack, byteorder='big')
            message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
            if message == 'Fail!': print(f'PRF: {message}\n')

        self.PRF = PRF

    def ADC_Threshold(self):
        bitADCVals = np.binary_repr(self.THRESHOLD_LEVEL, width=8)
        numADCByte = int(bitADCVals[-8:],2)

        ADC = ['5',str(self.TRIGGER),'a','a']
        ADCStr = f'{ord(ADC[0]):02x}{ord(ADC[1]):02x}{numADCByte:02x}{ord(ADC[2]):02x}{ord(ADC[3]):02x}'
        ADCByt = bytes.fromhex(ADCStr)

        self.spiDevice.write(ADCByt)
        time.sleep(self.READ_DELAY)
        dataBack = self.spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'ADC: {message}\n')

    def Change_Record_Length(self, recordLength):
        self.recordPoints = int(recordLength * self.ADC_FREQ)
        bitRecVals = np.binary_repr(int(self.recordPoints), width=16)
        numRecByte1 = int(bitRecVals[-8:],2)
        numRecByte2 = int(bitRecVals[-16:-8],2)

        record = ['6', 'a', 'a']
        recordStr = f'{ord(record[0]):02x}{numRecByte1:02x}{numRecByte2:02x}{ord(record[1]):02x}{ord(record[2]):02x}'
        recordByt = bytes.fromhex(recordStr)

        self.spiDevice.write(recordByt)
        time.sleep(self.READ_DELAY)
        dataBack = self.spiDevice.read(1)
        result = int.from_bytes(dataBack, byteorder='big')
        message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
        if message == 'Fail!': print(f'Record Length: {message}\n')

    def Trigger_Phasing(self, phaseArrayMicro):
        phaseArray = np.ceil(np.array(phaseArrayMicro[::-1]) * self.ADC_FREQ / 1_000_000)
        phasingActive = any(phaseArray > 0)
        if phasingActive == False:
            phaseByt = b'7Naaa'
            self.spiDevice.write(phaseByt)
            time.sleep(self.READ_DELAY)
            dataBack = self.spiDevice.read(1)
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

                self.spiDevice.write(phaseByt)
                time.sleep(self.READ_DELAY)
                dataBack = self.spiDevice.read(1)
                result = int.from_bytes(dataBack, byteorder='big')
                message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
                if message == 'Fail!': print(f'TRIGGER Phase (CH{8-i}): {message}\n')

    def Record_Delay(self, delayArrayMicro):
        delayArray = np.ceil(np.array(delayArrayMicro[::-1]) * self.ADC_FREQ / 1_000_000)
        delayActive = any(delayArray > 0)
        if delayActive == False:
            delayByt = b'8Naaa'
            self.spiDevice.write(delayByt)
            time.sleep(self.READ_DELAY)
            dataBack = self.spiDevice.read(1)
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

                self.spiDevice.write(delayByt)
                time.sleep(self.READ_DELAY)
                dataBack = self.spiDevice.read(1)
                result = int.from_bytes(dataBack, byteorder='big')
                message = 'Pass!' if result == 50 else 'Invalid!' if result == 200 else 'Fail!'
                if message == 'Fail!': print(f'Record Delay (CH{8-i}): {message}\n')

    def Get_Array(self):
        while not LOOP_COMPLETE:
            self.spiDevice.write(b'faaaa')
            time.sleep(self.num_averages/self.PRF)

            ByteBack = 0

            while ByteBack != 100:
                Byte = self.spiDevice.read(1)
                time.sleep(self.READ_DELAY)
                ByteBack = np.frombuffer(Byte, dtype = np.uint8)
                
            if int(self.recordPoints*self.MSG_BYTES*self.numChannelsOn+2*self.numChannelsOn-1) < 64000:
                bytesBack = self.spiDevice.read(int(self.recordPoints*self.MSG_BYTES*self.numChannelsOn+2*self.numChannelsOn-1))
            else:
                bytesBack = self.spiDevice.read(int((self.recordPoints*self.MSG_BYTES*self.numChannelsOn+2*self.numChannelsOn-1)/2))
                bytesBack += self.spiDevice.read(int(self.recordPoints*self.MSG_BYTES*self.numChannelsOn+2*self.numChannelsOn-1)-int((self.recordPoints*self.MSG_BYTES*self.numChannelsOn+2*self.numChannelsOn-1)/2))

            array = np.frombuffer(bytesBack, dtype = np.uint8)
            array = np.insert(array, 0, 100)
            array = np.array(array, dtype = np.float16)
            
            channel = np.split(array, self.numChannelsOn)
            channel = [channel[1:-1] for channel in channel]
            
            bytearray = np.empty((self.numChannelsOn, self.recordPoints * self.MSG_BYTES // 3, 3), dtype=float)
            reshapearray = np.empty((self.numChannelsOn, self.recordPoints), dtype=float)
            normarray = np.empty((self.numChannelsOn, self.recordPoints), dtype=float)
            echosig = np.empty((self.numChannelsOn, self.recordPoints), dtype=float)
            
            for i in range(self.numChannelsOn):
                bytearray[i] = np.reshape(channel[i], (-1,3))
                reshapearray[i] = bytearray[i][:,0] + bytearray[i][:,1] * (2**8) + bytearray[i][:,2] * (2**16)
                normarray[i] = np.divide(reshapearray[i], self.num_averages)
                if self.numChannelsOnArray[i] == 2 or self.numChannelsOnArray[i] == 3 or self.numChannelsOnArray[i] == 4 or self.numChannelsOnArray[i] == 5:
                    echosig[i] = np.subtract(normarray[i], 2048) * -1
                else:
                    echosig[i] = np.subtract(normarray[i], 2048)

            return echosig

    def Close_Device(self):
        finalarray = [0,0,0]
        while finalarray[-1] != 200 or finalarray[-2] != 200 or finalarray[-3] != 200:
            finalarray = np.frombuffer(self.spiDevice.read(1000), dtype = np.uint8)
        self.Channel_Enable([0,0,0,0,0,0,0,0])
        self.spiDevice.close()