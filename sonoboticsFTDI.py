import ctypes
from ctypes import wintypes
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

lib.uartRead.restype = ctypes.POINTER(ctypes.c_ubyte)
lib.uartRead.argtypes = [ctypes.c_void_p, wintypes.DWORD]

lib.spiRead.restype = ctypes.POINTER(ctypes.c_ubyte)
lib.spiRead.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

lib.uartWrite.argtypes = [ctypes.c_void_p, ctypes.c_char_p, wintypes.DWORD]
lib.spiWrite.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint8]

lib.connect_device.restype = ctypes.c_void_p
lib.connect_device_num.restype = ctypes.c_void_p

lib.set_baud_rate.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.configureSPI.argtypes = [ctypes.c_void_p]

lib.freeReadBuffer.argtypes = [ctypes.c_char_p]


# =========================== library classes and methods ===========================

# returns number of connected FTDI devices
def getNumDevices():
	return lib.get_num_devices()

# ftdi channel object
class ftdiChannel:
	# constructor
	# PROTOCOL: SPI/UART
	# CONNMODE: "serialNum"/"deviceNum"
	# CONNID: the device's serial number or device number
	def __init__(self, protocol, connMode, connID):	
		self.protocol = protocol
		self.connID = connID
		
		# gets the devices ftHandle
		if connMode == "serialNum":
			self.ftHandle = lib.connect_device(ctypes.c_char_p(connID))
		elif connMode == "deviceNum":
			self.ftHandle = lib.connect_device_num(connID)
		else:
			raise Exception("Invalid Connection Mode!")

		# configures the ftdi device to use SPI (if required)
		if protocol == "SPI":
			lib.configureSPI(ctypes.c_void_p(self.ftHandle))
		elif protocol != "UART":
			raise Exception("Invalid FTDI Protocol!")
	
	# writes bytes, bytearray, int or str to device
	def write(self, data):
		if self.protocol == "UART":
			if isinstance(data, (bytes, bytearray)):	
				lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data), wintypes.DWORD(len(data)))
			elif isinstance(data, (int)):
				byteLength = math.ceil(data.bit_length() / 8)
				lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.to_bytes(byteLength, 'big')), wintypes.DWORD(byteLength))
			else:
				lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.encode("utf-8")), wintypes.DWORD(len(data)))
			
		elif self.protocol == "SPI":
			if isinstance(data, (bytes, bytearray)):	
				lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data), len(data))
			elif isinstance(data, (int)):
				byteLength = math.ceil(data.bit_length() / 8)
				lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.to_bytes(byteLength, 'big')), byteLength)
			else:
				lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.encode("utf-8")), len(data))
		
	
	# reads data from device and returns as a byte array	
	def read(self, numBytes):
		if self.protocol == "UART":
			data = lib.uartRead(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(numBytes))
			py_bytes = bytearray(ctypes.string_at(data, numBytes))
			lib.freeReadBuffer(ctypes.cast(data, ctypes.c_char_p)); # frees the memory used in the c++ program to store the read buffer
		
		elif self.protocol == "SPI":
			data = lib.spiRead(ctypes.c_void_p(self.ftHandle), numBytes)
			py_bytes = bytearray(ctypes.string_at(data, numBytes))
			lib.freeReadBuffer(ctypes.cast(data, ctypes.c_char_p)); # frees the memory used in the c++ program to store the read buffer
		return py_bytes
	
	# configure device timouts
	def setTimeouts(self, readTimeOut, writeTimeOut):
		lib.setTimeouts(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(readTimeOut), wintypes.DWORD(writeTimeOut))
		
	# configure device USB parameters
	def setUSBParameters(self, inTransferSize, outTransferSize):
		lib.setUSBParameters(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(inTransferSize), wintypes.DWORD(outTransferSize))
	
	# configure device latency timer
	def setLatencyTimer(self, timer):
		lib.setLatencyTimer(ctypes.c_void_p(self.ftHandle), wintypes.CHAR(timer))
	
	# configure device baud rate
	def setBaudRate(self, baudRate):
		lib.set_baud_rate(ctypes.c_void_p(self.ftHandle), baudRate)
		
	# close connection to device
	def close(self):
		lib.close(ctypes.c_void_p(self.ftHandle))
		
		
	
