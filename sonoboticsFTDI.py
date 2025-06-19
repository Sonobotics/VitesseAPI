import ctypes
from ctypes import wintypes, create_string_buffer
import math
import ctypes
import os
import sys
import platform

# =========================== importing ftd2xx drivers ===========================

if sys.platform.startswith("win"):
	dll_path = os.getcwd()+"/Libraries/ftdiHandler.dll"
	lib = ctypes.CDLL(dll_path)
elif platform.machine() == 'x86_64':
	lib = ctypes.CDLL("./Libraries/ftdiHandler64.so")
elif platform.machine() == 'aarch64':
	lib = ctypes.CDLL("./Libraries/ftdiHandler.so")
else:
	print('Incompatible with this operating system!')
	sys.exit(0)
	
# =========================== c++ function setup ===========================

lib.uartRead.restype = ctypes.c_int
lib.uartRead.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_char)]
lib.spiRead.restype = ctypes.c_int
lib.spiRead.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_char)]
lib.uartWrite.argtypes = [ctypes.c_void_p, ctypes.c_char_p, wintypes.DWORD]
lib.uartWrite.restype = ctypes.c_int
lib.spiWrite.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint8]
lib.spiWrite.restype = ctypes.c_int
lib.connect_device.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
lib.connect_device.restype = ctypes.c_int
lib.connect_device_num.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
lib.connect_device_num.restype = ctypes.c_int
lib.set_baud_rate.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.set_baud_rate.restype = ctypes.c_int
lib.read_eeprom.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_char)]
lib.read_eeprom.restype = ctypes.c_int
lib.dump_eeprom.argtypes = [ctypes.c_void_p]
lib.dump_eeprom.restype = ctypes.c_int
lib.write_eeprom.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_char)]
lib.write_eeprom.restype = ctypes.c_int
lib.configureSPI.argtypes = [ctypes.c_void_p]
lib.freeReadBuffer.argtypes = [ctypes.c_char_p]
lib.close.restype = ctypes.c_int
lib.setTimeouts.restype = ctypes.c_int
lib.setUSBParameters.restype = ctypes.c_int

# =========================== library classes and methods ===========================

def getNumDevices():
	num = lib.get_num_devices()
	if num == -1:
		raise Exception("Error Getting Number of Devices!")
	else:
		return num

class ftdiChannel:
	def __init__(self, protocol, connMode, connID):	
		self.protocol = protocol
		self.connID = connID
		
		if connMode == "serialNum":
			ftHandle = ctypes.c_void_p()
			return_code = lib.connect_device(ctypes.c_char_p(connID), ctypes.byref(ftHandle))
			
			if return_code == 1:
				raise Exception("Can't Connect to Device!")
			self.ftHandle = ftHandle.value

		elif connMode == "deviceNum":
			ftHandle = ctypes.c_void_p()
			return_code = lib.connect_device_num(connID, ctypes.byref(ftHandle))

			if return_code == 1:
				raise Exception("Can't Connect To Device!")
			self.ftHandle = ftHandle.value

		else:
			raise Exception("Invalid Connection Mode!")
		
		if protocol == "SPI":
			return_code = lib.configureSPI(ctypes.c_void_p(self.ftHandle))
			if return_code == 1:
				raise Exception("Can't Configure SPI!")

		elif protocol != "UART":
			raise Exception("Invalid FTDI Protocol!")
		
	def write(self, data):
		if self.protocol == "UART":
			if isinstance(data, (bytes, bytearray)):	
				return_code = lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data), wintypes.DWORD(len(data)))
			elif isinstance(data, (int)):
				byteLength = math.ceil(data.bit_length() / 8)
				return_code = lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.to_bytes(byteLength, 'big')), wintypes.DWORD(byteLength))
			else:
				return_code = lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.encode("utf-8")), wintypes.DWORD(len(data)))
			
			if return_code == 1:
				raise Exception("UART Write Error!")

		elif self.protocol == "SPI":
			if isinstance(data, (bytes, bytearray)):	
				return_code = lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data), len(data))
			elif isinstance(data, (int)):
				byteLength = math.ceil(data.bit_length() / 8)
				return_code = lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.to_bytes(byteLength, 'big')), byteLength)
			else:
				return_code = lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.encode("utf-8")), len(data))

			if return_code == 1:
				raise Exception("SPI Write Error!")
			
	def read(self, numBytes):
		if self.protocol == "UART":
			data = (ctypes.c_char * numBytes)()
			data_ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_char))
			return_code = lib.uartRead(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(numBytes), data_ptr)

			if return_code == 1:
				raise Exception("UART Read Error!")

			py_bytes = bytearray(data.raw) 
		
		elif self.protocol == "SPI":
			data = (ctypes.c_char * numBytes)()
			data_ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_char))
			return_code = lib.spiRead(ctypes.c_void_p(self.ftHandle), numBytes, data_ptr)

			if return_code == 1:
				raise Exception("SPI Read Error!")

			py_bytes = bytearray(data.raw) 
	
		return py_bytes
	
	def readEEPROM(self):
		ft_handle = ctypes.c_void_p(self.ftHandle)

		manufacturer_buf = create_string_buffer(32)
		manufacturerId_buf = create_string_buffer(16)
		description_buf = create_string_buffer(64)
		serialNumber_buf = create_string_buffer(16)

		result = lib.read_eeprom(
			ft_handle,
			manufacturer_buf,
			manufacturerId_buf,
			description_buf,
			serialNumber_buf
		)

		if result != 0:
			raise Exception("EEPROM read failed!")

		manufacturer = manufacturer_buf.value.decode('utf-8')
		manufacturer_id = manufacturerId_buf.value.decode('utf-8')
		description = description_buf.value.decode('utf-8')
		serial_number = serialNumber_buf.value.decode('utf-8')

		return {"Manufacturer": manufacturer, "Manufacturer ID": manufacturer_id, "Device": description, "Serial Number": serial_number}


	def writeEEPROM(self, manufacturer, manufacturer_id, description, serial_number):
		manufacturer_b = manufacturer.encode('utf-8')
		manufacturer_id_b = manufacturer_id.encode('utf-8')
		description_b = description.encode('utf-8')
		serial_number_b = serial_number.encode('utf-8')

		result = lib.write_eeprom(
            ctypes.c_void_p(self.ftHandle),
            manufacturer_b,
            manufacturer_id_b,
            description_b,
            serial_number_b
        )

		if result != 0:
			raise Exception("EEPROM write failed.")
		print("EEPROM write successful.")

	def dumpEEPROM(self):
		return_code = lib.dump_eeprom(ctypes.c_void_p(self.ftHandle))
		if return_code == 1:
			raise Exception("Error Dumping EEPROM!")
	
	def setTimeouts(self, readTimeOut, writeTimeOut):
		return_code = lib.setTimeouts(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(readTimeOut), wintypes.DWORD(writeTimeOut))
		if return_code == 1:
			raise Exception("Error Setting Timeouts!")

	def setUSBParameters(self, inTransferSize, outTransferSize):
		return_code = lib.setUSBParameters(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(inTransferSize), wintypes.DWORD(outTransferSize))
		if return_code == 1:
			raise Exception("Error Setting USB Parameters!")

	def setLatencyTimer(self, timer):
		return_code = lib.setLatencyTimer(ctypes.c_void_p(self.ftHandle), wintypes.CHAR(timer))
		if return_code == 1:
			raise Exception("Error Setting Latency Timer!")
			
	def setBaudRate(self, baudRate):
		return_code = lib.set_baud_rate(ctypes.c_void_p(self.ftHandle), baudRate)
		if return_code == 1:
			raise Exception("Error Setting Baud Rate!")
		
	def close(self):
		return_code = lib.close(ctypes.c_void_p(self.ftHandle))
		if return_code == 1:
			raise Exception("Error Closing Device!")