"""
Routine for reading Modbus registers from Orno OR-WE-517 Energy Meter
"""

#pylint: disable=C0103,R0912,R0914,R0915

import struct
import binascii
import urllib3 #pylint: disable=E0401
import minimalmodbus #pylint: disable=E0401

DEBUG = False
URL = "http://homematic.ps.minixhofer.com"
SAMPLE_TIME = 300
#Definition of ISEIDs for writing to homematic
#Ise-IDs can be listed with the command http://<Homematic IP>/addons/xmlapi/sysvarlist.cgi
HMISEIDS = ["26084,26085,26086,26087,26088,26089,26090,26091,26092,26093,26094," \
            "26095,26096,26097,26098,26099,26100,26101,26102,26103,26104,26105,26106",
            "26411,26412,26413,26414,26415,26416,26417,26418,26419,26420,26421," \
            "26422,26423,26424,26425,26426,26427,26428,26429,26430,26431,26432,26433"]

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

def write_to_homematic(meternr, hmdata):
    """
    Writes measurement data from meternr into Homematic using the ISE-IDs
    specified in HMISEIDS[<meternr>]

    Parameters
    ----------
    meternr : Integer
        Modbus number of meter to be read
    hmdata : String
        String to be written into Homematic with XML-API call

    Returns
    -------
    None.

    """
    try:
        http = urllib3.PoolManager()
        request = URL + "/config/xmlapi/statechange.cgi?ise_id=" \
                        + HMISEIDS[meternr-1] + "&new_value=" + hmdata
        http.request('GET', request)
        if DEBUG:
            print('Data written to Raspberrymatic.')
            print('GET request: ',request)
    except IOError:
        print('URLError. Trying again in next time interval.')

def read_reg(smartmeter, reg):
    """
    Parameters
    ----------
    smartmeter : Integer
        Modbus number of meter to be read
    reg : Integer
        Register number to be read (2-byte register)

    Returns
    -------
    Integer
        Returns content of 2-byte register

    Routine encapsulates read_register method of minimalmodbus with error
    handling
    """
    try:
        return smartmeter.read_register(reg, 0, 3, False)
    except IOError:
        print("Read error reading register ", reg, "retry in next time interval")
        return 0

def read_long(smartmeter, reg):
    """
    Parameters
    ----------
    smartmeter : Integer
        Modbus number of meter to be read
    reg : Integer
        Register number to be read (4-byte register)

    Returns
    -------
    Long
        Returns content of 4-byte register

    Routine encapsulates read_long method of minimalmodbus with error
    handling
    """
    try:
        return smartmeter.read_long(reg, 3, False, 0)
    except IOError:
        print("Read error reading register ", reg, "retry in next time interval")
        return 0

def read_float(smartmeter, reg, fractdig):
    """
    Parameters
    ----------
    smartmeter : Integer
        Modbus number of meter to be read
    reg : Integer
        Register number to be read (8-byte float register)
    fractdig: Integer
        Numbers of fractional digits after decimal point the float should be
        rounded to.

    Returns
    -------
    Float
        Returns content of 8-byte float register converted via ieee float convention

    Routine encapsulates read_long method of minimalmodbus with error
    handling and conversion into ieee float
    """
    try:
        return round(umwandeln_ieee(smartmeter.read_long(reg, 3, False, 0)), fractdig)
    except IOError:
        print("Read error reading register ", reg, "retry in next time interval")
        return 0

def read_from_meter(meternr):

    """
    Initialize adapter for RS485 Instrument. Parameters are:
        Port, Address, mode and that the RS485 port should not be closed again
        after the instrument has been accessed (faster).
    meternr specifies the Modbus # of the meter

    The routine returns the hmdata string to be written into Homematic
    using write_to_homematic
    """

    smartmeter = minimalmodbus.Instrument('/dev/ORNO', meternr, mode='rtu',
                                          close_port_after_each_call=True, debug=False)

    smartmeter.serial.baudrate = 9600 # Baud
    smartmeter.serial.bytesize = 8
    smartmeter.serial.parity   = minimalmodbus.serial.PARITY_EVEN # vendor default is EVEN
    smartmeter.serial.stopbits = 1
    smartmeter.serial.timeout  = 0.6  # seconds

    smartmeter.clear_buffers_before_each_transaction = True

    smartmeter.debug = False # set to "True" for debug mode

    #Adresse = smartmeter.read_register(2, 0, 3, False)
    # registeraddress, number_of_decimals=0, functioncode=3, signed=False

    SerialNum = read_long(smartmeter, 0)
    if DEBUG:
        print("Serial number: ",SerialNum)

    ModbusID = read_reg(smartmeter, 2)
    if DEBUG:
        print("Modbus ID: ",ModbusID)

    ModbusBaudrate = read_reg(smartmeter, 3)
    if DEBUG:
        print("Modbus Baudrate: ",ModbusBaudrate, " bps")

    SoftwareVer = read_float(smartmeter, 4, 2)
    if DEBUG:
        print("Software Version: ",SoftwareVer)

    HardwareVer = read_float(smartmeter, 6, 2)
    if DEBUG:
        print("Hardware Version: ",HardwareVer)

    CTRate = read_reg(smartmeter, 8)
    if DEBUG:
        print("CT Rate: ",CTRate)

    S0Rate = read_float(smartmeter, 9, 1)
    if DEBUG:
        print("S0 output rate: ",S0Rate," imp/kWh")

    A3Code = read_reg(smartmeter, 11)
    if DEBUG:
        print("A3 Code: ",A3Code)

    HolidayWeekendT = read_reg(smartmeter, 12)
    if DEBUG:
        print("Holiday-Weekend T: ", HolidayWeekendT)

    LCDCycleTime = read_reg(smartmeter, 13)
    if DEBUG:
        print("LCD Cycle Time: ", LCDCycleTime)

    L1Voltage = read_float(smartmeter, 14, 1)
    if DEBUG:
        print("L1-Voltage: ", L1Voltage, " V")

    L2Voltage = read_float(smartmeter, 16, 1)
    if DEBUG:
        print("L2-Voltage: ", L2Voltage, " V")

    L3Voltage = read_float(smartmeter, 18, 1)
    if DEBUG:
        print("L3-Voltage: ", L3Voltage, " V")

    Frequency= read_float(smartmeter, 20, 2)
    if DEBUG:
        print("Grid Frequency: ", Frequency, " Hz")

    L1Current = read_float(smartmeter, 22, 2)
    if DEBUG:
        print("L1-Current: ", L1Current, " A")

    L2Current = read_float(smartmeter, 24, 2)
    if DEBUG:
        print("L2-Current:", L2Current, " A")

    L3Current = read_float(smartmeter, 26, 2)
    if DEBUG:
        print("L3-Current:", L3Current, " A")

    Current_Total = round(L1Current+L2Current+L3Current,3)
    if DEBUG:
        print("Current Sum:", Current_Total, " A")

    TotalActivePower = read_float(smartmeter, 28, 3)
    if DEBUG:
        print("Total Active Power:", TotalActivePower, " kW")

    L1ActivePower= read_float(smartmeter, 30, 3)
    if DEBUG:
        print("L1-Active Power:", L1ActivePower, " kW")

    L2ActivePower= read_float(smartmeter, 32, 3)
    if DEBUG:
        print("L2-Active Power:", L2ActivePower, " kW")

    L3ActivePower= read_float(smartmeter, 34, 3)
    if DEBUG:
        print("L3-Active Power:", L3ActivePower, " kW")

    TotalReactivePower = read_float(smartmeter, 36, 3)
    if DEBUG:
        print("Total Reactive Power:", TotalReactivePower, " kVar")

    L1ReactivePower = read_float(smartmeter, 38, 3)
    if DEBUG:
        print("L1-Reactive Power:", L1ReactivePower, " kVar")

    L2ReactivePower = read_float(smartmeter, 40, 3)
    if DEBUG:
        print("L2-Reactive Power:", L2ReactivePower, " kVar")

    L3ReactivePower = read_float(smartmeter, 42, 3)
    if DEBUG:
        print("L3-Reactive Power:", L3ReactivePower, " kVar")

    TotalApparentPower = read_float(smartmeter, 44, 3)
    if DEBUG:
        print("Total Apparent Power:", TotalApparentPower, " kVA")

    L1ApparentPower = read_float(smartmeter, 46, 3)
    if DEBUG:
        print("L1-Apparent Power:", L1ApparentPower, " kVA")

    L2ApparentPower = read_float(smartmeter, 48, 3)
    if DEBUG:
        print("L2-Apparent Power:", L2ApparentPower, " kVA")

    L3ApparentPower = read_float(smartmeter, 50, 3)
    if DEBUG:
        print("L3-Apparent Power:", L3ApparentPower, " kVA")

    TotalPowerFactor = read_float(smartmeter, 52, 2)
    if DEBUG:
        print("Total Power Faktor:", TotalPowerFactor)

    L1PowerFactor = read_float(smartmeter, 54, 2)
    if DEBUG:
        print("L1-Power Factor:", L1PowerFactor)

    L2PowerFactor = read_float(smartmeter, 56, 2)
    if DEBUG:
        print("L2-Power Factor:", L2PowerFactor)

    L3PowerFactor = read_float(smartmeter, 58, 2)
    if DEBUG:
        print("L3-Power Factor:", L3PowerFactor)

    #Time = smartmeter.read_long(60, 3, False, 0)
    #Time = Time + 2^32*smartmeter.read_long(62, 3, False, 0)
    #if DEBUG:
    #    print("Time: ",Time)

    CRC = read_reg(smartmeter, 65)
    if DEBUG:
        print("CRC: ",CRC)

    #CombinedCode = smartmeter.read_register(66, 0, 3, False)
    #if DEBUG:
    #    print("Combined Code: ",CombinedCode)

    TotalActiveEnergy = read_float(smartmeter, 256, 2)
    if DEBUG:
        print("Total Active Energy:", TotalActiveEnergy, " kWh")

    L1TotalActiveEnergy = read_float(smartmeter, 258, 2)
    if DEBUG:
        print("L1 Total Active Energy:", L1TotalActiveEnergy, " kWh")

    L2TotalActiveEnergy = read_float(smartmeter, 260, 2)
    if DEBUG:
        print("L2 Total Active Energy:", L2TotalActiveEnergy, " kWh")

    L3TotalActiveEnergy = read_float(smartmeter, 262, 2)
    if DEBUG:
        print("L3 Total Active Energy:", L3TotalActiveEnergy, " kWh")

    ForwardActiveEnergy = read_float(smartmeter, 264, 2)
    if DEBUG:
        print("Forward Active Energy:", ForwardActiveEnergy, " kWh")

    L1ForwardActiveEnergy = read_float(smartmeter, 266, 2)
    if DEBUG:
        print("L1 Forward Active Energy:", L1ForwardActiveEnergy, " kWh")

    L2ForwardActiveEnergy = read_float(smartmeter, 268, 2)
    if DEBUG:
        print("L2 Forward Active Energy:", L2ForwardActiveEnergy, " kWh")

    L3ForwardActiveEnergy = read_float(smartmeter, 270, 2)
    if DEBUG:
        print("L3 Forward Active Energy:", L3ForwardActiveEnergy, " kWh")

    ReverseActiveEnergy = read_float(smartmeter, 272, 2)
    if DEBUG:
        print("Reverse Active Energy:", ReverseActiveEnergy, " kWh")

    L1ReverseActiveEnergy = read_float(smartmeter, 274, 2)
    if DEBUG:
        print("L1 Reverse Active Energy:", L1ReverseActiveEnergy, " kWh")

    L2ReverseActiveEnergy = read_float(smartmeter, 276, 2)
    if DEBUG:
        print("L2 Reverse Active Energy:", L2ReverseActiveEnergy, " kWh")

    L3ReverseActiveEnergy = read_float(smartmeter, 278, 2)
    if DEBUG:
        print("L3 Reverse Active Energy:", L3ReverseActiveEnergy, " kWh")

    TotalReactiveEnergy = read_float(smartmeter, 280, 2)
    if DEBUG:
        print("Total Reactive Energy:", TotalReactiveEnergy, " kVarh")

    L1TotalReactiveEnergy = read_float(smartmeter, 282, 2)
    if DEBUG:
        print("L1 Reactive Energy:", L1TotalReactiveEnergy, " kVarh")

    L2TotalReactiveEnergy = read_float(smartmeter, 284, 2)
    if DEBUG:
        print("L2 Reactive Energy:", L2TotalReactiveEnergy, " kVarh")

    L3TotalReactiveEnergy = read_float(smartmeter, 286, 2)
    if DEBUG:
        print("L3 Reactive Energy:", L3TotalReactiveEnergy, " kVarh")

    ForwardReactiveEnergy = read_float(smartmeter, 288, 2)
    if DEBUG:
        print("Forward Reactive Energy:", ForwardReactiveEnergy, " kVarh")

    L1ForwardReactiveEnergy = read_float(smartmeter, 290, 2)
    if DEBUG:
        print("L1 Forward Reactive Energy:", L1ForwardReactiveEnergy, " kVarh")

    L2ForwardReactiveEnergy = read_float(smartmeter, 292, 2)
    if DEBUG:
        print("L2 Forward Reactive Energy:", L2ForwardReactiveEnergy, " kVarh")

    L3ForwardReactiveEnergy = read_float(smartmeter, 294, 2)
    if DEBUG:
        print("L3 Forward Reactive Energy:", L3ForwardReactiveEnergy, " kVarh")

    ReverseReactiveEnergy = read_float(smartmeter, 296, 2)
    if DEBUG:
        print("Reverse Reactive Energy:", ReverseReactiveEnergy, " kVarh")

    L1ReverseReactiveEnergy = read_float(smartmeter, 298, 2)
    if DEBUG:
        print("L1 Reverse Reactive Energy:", L1ReverseReactiveEnergy, " kVarh")

    L2ReverseReactiveEnergy = read_float(smartmeter, 300, 2)
    if DEBUG:
        print("L2 Reverse Reactive Energy:", L2ReverseReactiveEnergy, " kVarh")

    L3ReverseReactiveEnergy = read_float(smartmeter, 302, 2)
    if DEBUG:
        print("L3 Reverse Reactive Energy:", L3ReverseReactiveEnergy, " kVarh")

    smartmeter.serial.close()

    hmdata = ('%(L1V).1f,%(L2V).1f,%(L3V).1f,%(f).2f,%(L1I).2f,%(L2I).2f,%(L3I).2f,'
              '%(TAP)d,%(L1AP)d,%(L2AP)d,%(L3AP)d,'
              '%(TRP)d,%(L1RP)d,%(L2RP)d,%(L3RP)d,'
              '%(TSP)d,%(L1SP)d,%(L2SP)d,%(L3SP)d,'
              '%(TPF).2f,%(L1PF).2f,%(L2PF).2f,%(L3PF).2f') % \
        {"L1V": L1Voltage, "L2V": L2Voltage, "L3V": L3Voltage,
         "f": Frequency,
         "L1I": L1Current,"L2I": L2Current,"L3I": L3Current,
         "TAP": TotalActivePower*1000,
         "L1AP": L1ActivePower*1000, "L2AP": L2ActivePower*1000, "L3AP": L3ActivePower*1000,
         "TRP": TotalReactivePower*1000,
         "L1RP": L1ReactivePower*1000, "L2RP": L2ReactivePower*1000, "L3RP": L3ReactivePower*1000,
         "TSP": TotalApparentPower*1000,
         "L1SP": L1ApparentPower*1000, "L2SP": L2ApparentPower*1000, "L3SP": L3ApparentPower*1000,
         "TPF": TotalPowerFactor,
         "L1PF": L1PowerFactor, "L2PF": L2PowerFactor, "L3PF": L3PowerFactor}
    if DEBUG:
        print("HM Data-String:",hmdata)
    return hmdata

hmstring=read_from_meter(1)
write_to_homematic(1, hmstring)
hmstring=read_from_meter(2)
write_to_homematic(2, hmstring)
