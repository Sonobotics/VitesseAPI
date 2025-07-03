import ctypes
from ctypes import wintypes, create_string_buffer
import math
import platform
import os
import sys
import subprocess

# =========================== importing ftd2xx drivers ===========================

if sys.platform.startswith("win"):
	dll_path = os.getcwd()+"/Libraries/ftdiHandler.dll"
	lib = ctypes.CDLL(dll_path)
elif platform.machine() == 'x86_64':
	lib = ctypes.CDLL("./Libraries/ftdiHandler64.so")
	os.system('sudo rmmod ftdi_sio 2>/dev/null')
elif platform.machine() == 'aarch64':
	lib = ctypes.CDLL("./Libraries/ftdiHandler.so")
	subprocess.run(["sudo", "./Drivers/linux_arm_FTDI/unload_ftdi.sh"], check=True)
	os.system('sudo rmmod ftdi_sio 2>/dev/null')
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

# ============================== error status messages ==============================

STATUS_MESSAGES = {
    0: "Command successful",
    1: "Handle passed is invalid",
    2: "Device, or serial number, not found",
    3: "Handle used wasn't successfully opened",
    4: "I/O operation failed",
    5: "Memory allocation failed",
    6: "Invalid arguments parsed",
    7: "Invalid baud rate specified",
    8: "Tried to erase EEPROM without opening it for erase access",
    9: "Tried to write EEPROM without proper access",
    10: "Write to EEPROM or device register failed",
    11: "Could not read from EEPROM",
    12: "Could not write to EEPROM",
    13: "EEPROM erase operation failed",
    14: "Device lacks EEPROM",
    15: "EEPROM exists but is blank",
    16: "One or more function arguments are not valid",
    17: "Operation or feature not supported by the device",
    18: "A non-specific or undocumented error occurred"
}

# =========================== library classes and methods ===========================

# returns number of connected FTDI devices
def getNumDevices():
	num = lib.get_num_devices()
	if num == -1:
		raise Exception("Error getting number of devices")
	else:
		return num

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
			ftHandle = ctypes.c_void_p()
			return_code = lib.connect_device(ctypes.c_char_p(connID), ctypes.byref(ftHandle))
			if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Couldn't connect to device ({error_msg})")
			self.ftHandle = ftHandle.value

		elif connMode == "deviceNum":
			ftHandle = ctypes.c_void_p()
			return_code = lib.connect_device_num(connID, ctypes.byref(ftHandle))
			if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Couldn't connect to device ({error_msg})")
			self.ftHandle = ftHandle.value
		else:
			raise Exception("Invalid connection mode")
		

		# configures the ftdi device to use SPI (if required)
		if protocol == "SPI":
			return_code = lib.configureSPI(ctypes.c_void_p(self.ftHandle))
			if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Can't configure device ({error_msg})")

		elif protocol != "UART":
			raise Exception("Invalid connection protocol")
		
	
	# writes bytes, bytearray, int or str to device
	def write(self, data):
		if self.protocol == "UART":
			if isinstance(data, (bytes, bytearray)):	
				return_code = lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data), wintypes.DWORD(len(data)))
			elif isinstance(data, (int)):
				byteLength = math.ceil(data.bit_length() / 8)
				return_code = lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.to_bytes(byteLength, 'big')), wintypes.DWORD(byteLength))
			else:
				return_code = lib.uartWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.encode("utf-8")), wintypes.DWORD(len(data)))
			
			if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Can't write to device ({error_msg})")

		elif self.protocol == "SPI":
			if isinstance(data, (bytes, bytearray)):	
				return_code = lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data), len(data))
			elif isinstance(data, (int)):
				byteLength = math.ceil(data.bit_length() / 8)
				return_code = lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.to_bytes(byteLength, 'big')), byteLength)
			else:
				return_code = lib.spiWrite(ctypes.c_void_p(self.ftHandle), ctypes.c_char_p(data.encode("utf-8")), len(data))

			if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Can't write to device ({error_msg})")
		
	
	# reads data from device and returns as a byte array	
	def read(self, numBytes):
		if self.protocol == "UART":
			# Allocate buffer correctly
			data = (ctypes.c_char * numBytes)()  # Creates an array of c_ubyte

			# Get a proper pointer type
			data_ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_char))

			# Call spiRead with the correct pointer type
			return_code = lib.uartRead(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(numBytes), data_ptr)

			if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Can't read from device ({error_msg})")

			# Convert the buffer to a Python bytearray
			py_bytes = bytearray(data.raw) 
		
		elif self.protocol == "SPI":
			# Allocate buffer correctly
			data = (ctypes.c_char * numBytes)()  # Creates an array of c_ubyte

			# Get a proper pointer type
			data_ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_char))

			# Call spiRead with the correct pointer type
			return_code = lib.spiRead(ctypes.c_void_p(self.ftHandle), numBytes, data_ptr)

			if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Can't read from device ({error_msg})")

			# Convert the buffer to a Python bytearray
			py_bytes = bytearray(data.raw) 
	
		return py_bytes
	
	def readEEPROM(self):
		
		# Assume you already have an FT_HANDLE from your connect function
		ft_handle = ctypes.c_void_p(self.ftHandle)  # from your earlier context

		# Allocate output buffers
		manufacturer_buf = create_string_buffer(32)
		manufacturerId_buf = create_string_buffer(16)
		description_buf = create_string_buffer(64)
		serialNumber_buf = create_string_buffer(16)

		# Call the function
		return_code = lib.read_eeprom(
			ft_handle,
			manufacturer_buf,
			manufacturerId_buf,
			description_buf,
			serialNumber_buf
		)

		# Check result
		if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"EEPROM read failed ({error_msg})")

		# Convert to Python strings
		manufacturer = manufacturer_buf.value.decode('utf-8')
		manufacturer_id = manufacturerId_buf.value.decode('utf-8')
		description = description_buf.value.decode('utf-8')
		serial_number = serialNumber_buf.value.decode('utf-8')

		return {"Manufacturer": manufacturer, "Manufacturer ID": manufacturer_id, "Device": description, "Serial Number": serial_number}


	def writeEEPROM(self, manufacturer, manufacturer_id, description, serial_number):
		# Ensure inputs are encoded as bytes (c_char_p)
		manufacturer_b = manufacturer.encode('utf-8')
		manufacturer_id_b = manufacturer_id.encode('utf-8')
		description_b = description.encode('utf-8')
		serial_number_b = serial_number.encode('utf-8')

        # Call the C function
		return_code = lib.write_eeprom(
            ctypes.c_void_p(self.ftHandle),
            manufacturer_b,
            manufacturer_id_b,
            description_b,
            serial_number_b
        )

		if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"EEPROM write failed ({error_msg})")
		
		print("EEPROM write successful")

	def dumpEEPROM(self):
		return_code = lib.dump_eeprom(ctypes.c_void_p(self.ftHandle))
		if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Error dumping EEPROM ({error_msg})")
	
	# configure device timouts
	def setTimeouts(self, readTimeOut, writeTimeOut):
		return_code = lib.setTimeouts(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(readTimeOut), wintypes.DWORD(writeTimeOut))
		if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Error setting timeouts ({error_msg})")

	# configure device USB parameters
	def setUSBParameters(self, inTransferSize, outTransferSize):
		return_code = lib.setUSBParameters(ctypes.c_void_p(self.ftHandle), wintypes.DWORD(inTransferSize), wintypes.DWORD(outTransferSize))
		if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Error setting USB parameters ({error_msg})")

	# configure device latency timer
	def setLatencyTimer(self, timer):
		return_code = lib.setLatencyTimer(ctypes.c_void_p(self.ftHandle), wintypes.CHAR(timer))
		if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Error setting latency timer ({error_msg})")
			
	# configure device baud rate
	def setBaudRate(self, baudRate):
		return_code = lib.set_baud_rate(ctypes.c_void_p(self.ftHandle), baudRate)
		if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Error setting baud rate EEPROM ({error_msg})")
		
	# close connection to device
	def close(self):
		return_code = lib.close(ctypes.c_void_p(self.ftHandle))
		if return_code != 0:
				error_msg = STATUS_MESSAGES.get(return_code, f"Unknown status code: {return_code}")
				raise Exception(f"Error closing device ({error_msg})")