"""
Routine for reading Modbus registers from Orno OR-WE-517 Energy Meter
"""

#pylint: disable=C0103

import struct
import binascii
import minimalmodbus #pylint: disable=E0401

def umwandeln_ieee(Wert):  #Umwandlung Array of int ( 4 byte) in float nach IEEE 754

    """
    Function for conversion of float register values into IEEE value
    """

    Wert2=str(hex(Wert))

    Wert2=Wert2.replace('0x', '')

    if Wert2=='0':
        Wert2='00000000'

    Wert3=struct.unpack('>f', binascii.unhexlify(Wert2))[0]

    return Wert3

# Initialize adapter for RS485 Instrument. Parameters are:
#    Port, Address, mode and that the RS485 port should be closed again
#    after the instrument has been accessed.

smartmeter = minimalmodbus.Instrument('/dev/ttyUSB1', 1, mode='rtu',
                                      close_port_after_each_call=True, debug=False)

smartmeter.serial.baudrate = 9600 # Baud
smartmeter.serial.bytesize = 8
smartmeter.serial.parity   = minimalmodbus.serial.PARITY_EVEN # vendor default is EVEN
smartmeter.serial.stopbits = 1
smartmeter.serial.timeout  = 0.6  # seconds

# Good practice
#smartmeter.close_port_after_each_call = True

smartmeter.clear_buffers_before_each_transaction = False

smartmeter.debug = False # set to "True" for debug mode

#Adresse = smartmeter.read_register(2, 0, 3, False)
# registeraddress, number_of_decimals=0, functioncode=3, signed=False

SerialNum = smartmeter.read_long(0, 3, False,0)
print("Serial number: ",SerialNum)

ModbusID = smartmeter.read_register(2, 0, 3, False)
print("Modbus ID: ",ModbusID)

ModbusBaudrate = smartmeter.read_register(3, 0, 3, False)
print("Modbus Baudrate: ",ModbusBaudrate)

SoftwareVer = round(umwandeln_ieee(smartmeter.read_long(4, 3, False, 0)),2)
print("Software Version: ",SoftwareVer)

HardwareVer = round(umwandeln_ieee(smartmeter.read_long(6, 3, False, 0)),2)
print("Hardware Version: ",HardwareVer)

CTRate = smartmeter.read_register(8, 0, 3, False)
print("CT Rate: ",CTRate)

S0Rate = umwandeln_ieee(smartmeter.read_long(9, 3, False, 0))
print("S0 output rate: ",S0Rate)

A3Code = smartmeter.read_register(11, 0, 3, False)
print("A3 Code: ",A3Code)

LCDCycleTime = smartmeter.read_register(13, 0, 3, False)
print("LCD Cycle Time: ", LCDCycleTime)

L1Voltage = round(umwandeln_ieee(smartmeter.read_long(14, 3, False, 0)),1)
print("L1-Voltage: ", L1Voltage, " V")

L2Voltage = round(umwandeln_ieee(smartmeter.read_long(16, 3, False, 0)),1)
print("L2-Voltage: ", L2Voltage, " V")

L3Voltage = round(umwandeln_ieee(smartmeter.read_long(18, 3, False, 0)),1)
print("L3-Voltage: ", L3Voltage, " V")

Frequency= round(umwandeln_ieee(smartmeter.read_long(20, 3, False, 0)),2)
print("Grid Frequency: ", Frequency, " Hz")

L1Current = round(umwandeln_ieee(smartmeter.read_long(22, 3, False, 0)),1)
print("L1-Current: ", L1Current, " A")

L2Current = round(umwandeln_ieee(smartmeter.read_long(24, 3, False, 0)),1)
print("L2-Current:", L2Current, " A")

L3Current = round(umwandeln_ieee(smartmeter.read_long(26, 3, False, 0)),1)
print("L3-Current:", L3Current, " A")

Current_Total = L1Current+L2Current+L3Current
print("Current Sum:", Current_Total, " A")

TotalActivePower = round(umwandeln_ieee(smartmeter.read_long(28, 3, False, 0)),2)
print("Total Active Power:", TotalActivePower, " kW")

L1ActivePower= round(umwandeln_ieee(smartmeter.read_long(30, 3, False, 0)),2)
print("L1-Active Power:", L1ActivePower, " kW")

L2ActivePower= round(umwandeln_ieee(smartmeter.read_long(32, 3, False, 0)),2)
print("L2-Active Power:", L2ActivePower, " kW")

L3ActivePower= round(umwandeln_ieee(smartmeter.read_long(34, 3, False, 0)),2)
print("L3-Active Power:", L3ActivePower, " kW")

TotalReactivePower = round(umwandeln_ieee(smartmeter.read_long(36, 3, False, 0)),2)
print("Total Reactive Power:", TotalReactivePower, " kVar")

L1ReactivePower = round(umwandeln_ieee(smartmeter.read_long(38, 3, False, 0)),2)
print("L1-Reactive Power:", L1ReactivePower, " kVar")

L2ReactivePower = round(umwandeln_ieee(smartmeter.read_long(40, 3, False, 0)),2)
print("L2-Reactive Power:", L2ReactivePower, " kVar")

L3ReactivePower = round(umwandeln_ieee(smartmeter.read_long(42, 3, False, 0)),2)
print("L3-Reactive Power:", L3ReactivePower, " kVar")

TotalApparentPower = round(umwandeln_ieee(smartmeter.read_long(44, 3, False, 0)),2)
print("Total Apparent Power:", TotalApparentPower, " kVA")

L1ApparentPower = round(umwandeln_ieee(smartmeter.read_long(46, 3, False, 0)),2)
print("L1-Apparent Power:", L1ApparentPower, " kVA")

L2ApparentPower = round(umwandeln_ieee(smartmeter.read_long(48, 3, False, 0)),2)
print("L2-Apparent Power:", L2ApparentPower, " kVA")

L3ApparentPower = round(umwandeln_ieee(smartmeter.read_long(50, 3, False, 0)),2)
print("L3-Apparent Power:", L3ApparentPower, " kVA")

TotalPowerFactor = round(umwandeln_ieee(smartmeter.read_long(52, 3, False, 0)),2)
print("Total Power Faktor:", TotalPowerFactor)

L1PowerFactor = round(umwandeln_ieee(smartmeter.read_long(54, 3, False, 0)),2)
print("L1-Power Factor:", L1PowerFactor)

L2PowerFactor = round(umwandeln_ieee(smartmeter.read_long(56, 3, False, 0)),2)
print("L2-Power Factor:", L2PowerFactor)

L3PowerFactor = round(umwandeln_ieee(smartmeter.read_long(58, 3, False, 0)),2)
print("L3-Power Factor:", L3PowerFactor)

CRC = smartmeter.read_register(65, 0, 3, False)
print("CRC: ",CRC)

#CombinedCode = smartmeter.read_register(66, 0, 3, False)
#print("Combined Code: ",CombinedCode)

TotalActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(256, 3, False, 0)),2)
print("Total Active Energy:", TotalActiveEnergy, " kWh")

L1TotalActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(258, 3, False, 0)),2)
print("L1 Total Active Energy:", L1TotalActiveEnergy, " kWh")

L2TotalActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(260, 3, False, 0)),2)
print("L2 Total Active Energy:", L2TotalActiveEnergy, " kWh")

L3TotalActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(262, 3, False, 0)),2)
print("L3 Total Active Energy:", L3TotalActiveEnergy, " kWh")

ForwardActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(264, 3, False, 0)),2)
print("Forward Active Energy:", ForwardActiveEnergy, " kWh")

L1ForwardActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(266, 3, False, 0)),2)
print("L1 Forward Active Energy:", L1ForwardActiveEnergy, " kWh")

L2ForwardActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(268, 3, False, 0)),2)
print("L2 Forward Active Energy:", L2ForwardActiveEnergy, " kWh")

L3ForwardActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(270, 3, False, 0)),2)
print("L3 Forward Active Energy:", L3ForwardActiveEnergy, " kWh")

ReverseActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(272, 3, False, 0)),2)
print("Reverse Active Energy:", ReverseActiveEnergy, " kWh")

L1ReverseActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(274, 3, False, 0)),2)
print("L1 Reverse Active Energy:", L1ReverseActiveEnergy, " kWh")

L2ReverseActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(276, 3, False, 0)),2)
print("L2 Reverse Active Energy:", L2ReverseActiveEnergy, " kWh")

L3ReverseActiveEnergy = round(umwandeln_ieee(smartmeter.read_long(278, 3, False, 0)),2)
print("L3 Reverse Active Energy:", L3ReverseActiveEnergy, " kWh")

TotalReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(280, 3, False, 0)),2)
print("Total Reactive Energy:", TotalReactiveEnergy, " kVarh")

L1TotalReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(282, 3, False, 0)),2)
print("L1 Total Reactive Energy:", L1TotalReactiveEnergy, " kVarh")

L2TotalReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(284, 3, False, 0)),2)
print("L2 Total Reactive Energy:", L2TotalReactiveEnergy, " kVarh")

L3TotalReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(286, 3, False, 0)),2)
print("L3 Total Reactive Energy:", L3TotalReactiveEnergy, " kVarh")

ForwardReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(288, 3, False, 0)),2)
print("Forward Reactive Energy:", ForwardReactiveEnergy, " kVarh")

L1ForwardReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(290, 3, False, 0)),2)
print("L1 Forward Reactive Energy:", L1ForwardReactiveEnergy, " kVarh")

L2ForwardReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(292, 3, False, 0)),2)
print("L2 Forward Reactive Energy:", L2ForwardReactiveEnergy, " kVarh")

L3ForwardReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(294, 3, False, 0)),2)
print("L3 Forward Reactive Energy:", L3ForwardReactiveEnergy, " kVarh")

ReverseReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(296, 3, False, 0)),2)
print("Reverse Reactive Energy:", ReverseReactiveEnergy, " kVarh")

L1ReverseReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(298, 3, False, 0)),2)
print("L1 Reverse Reactive Energy:", L1ReverseReactiveEnergy, " kVarh")

L2ReverseReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(300, 3, False, 0)),2)
print("L2 Reverse Reactive Energy:", L2ReverseReactiveEnergy, " kVarh")

L3ReverseReactiveEnergy = round(umwandeln_ieee(smartmeter.read_long(302, 3, False, 0)),2)
print("L3 Reverse Reactive Energy:", L3ReverseReactiveEnergy, " kVarh")
