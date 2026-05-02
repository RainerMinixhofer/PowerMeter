#pylint: disable=C0103
"""
Routine for reading Modbus registers from Orno OR-WE-517 Energy Meter
"""

import struct                             # for IEEE 754 float conversion
import json                              # for JSON MQTT payload
import paho.mqtt.client as mqtt          # MQTT client
from pymodbus.client import ModbusSerialClient  # RS-485/Modbus over serial

try:
    from mqtt_credentials import MQTT_USERNAME, MQTT_PASSWORD, MQTT_HOST
except ImportError as exc:
    raise RuntimeError(
        "Missing mqtt_credentials.py. Copy mqtt_credentials.template.py to "
        "mqtt_credentials.py and set your MQTT credentials."
    ) from exc

# Set DEBUG = True to print every register value to stdout during a run.
DEBUG = False

# Set BOOTSTRAP_STATES = True for a single run to publish default (zero) values
# for all states so the ioBroker MQTT adapter auto-creates the object tree.
# Switch back to False for normal operation to avoid publishing spurious zeros.
BOOTSTRAP_STATES = False

# --- MQTT broker connection settings ---
# MQTT_HOST is loaded from mqtt_credentials.py (not tracked by git).
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "powermeter"  # root of all published topics
MQTT_QOS = 1       # at-least-once delivery
MQTT_RETAIN = True  # broker retains last value so ioBroker sees it after restart
SAMPLE_TIME = 300   # intended polling interval in seconds (used externally, e.g. cron/systemd)

# Maps Modbus device address -> MQTT sub-topic name.
# Add further meters here if needed.
METER_TOPICS = {
    1: "Household",
    2: "Heatpump",
}

# Default payload used by bootstrap_mqtt_states() to seed the ioBroker object tree.
# All values are zero; keys match exactly the keys published during normal operation.
DEFAULT_METER_DATA = {
    "L1-Voltage (V)": 0,
    "L2-Voltage (V)": 0,
    "L3-Voltage (V)": 0,
    "Grid Frequency (Hz)": 0,
    "L1-Current (A)": 0,
    "L2-Current (A)": 0,
    "L3-Current (A)": 0,
    "Total Active Power (kW)": 0,
    "L1-Active Power (kW)": 0,
    "L2-Active Power (kW)": 0,
    "L3-Active Power (kW)": 0,
    "Total Reactive Power (kVar)": 0,
    "L1-Reactive Power (kVar)": 0,
    "L2-Reactive Power (kVar)": 0,
    "L3-Reactive Power (kVar)": 0,
    "Total Apparent Power (kVA)": 0,
    "L1-Apparent Power (kVA)": 0,
    "L2-Apparent Power (kVA)": 0,
    "L3-Apparent Power (kVA)": 0,
    "Total Power Faktor": 0,
    "L1-Power Factor": 0,
    "L2-Power Factor": 0,
    "L3-Power Factor": 0,
}


def read_holding_registers_compat(smartmeter, reg, count):
    """
    Read holding registers with API compatibility across pymodbus versions.

    Depending on version, the client may expect one of `device_id`, `slave`
    or `unit`, and may require keyword-only arguments for `count`.
    """
    # Try all known calling conventions in order from newest to oldest pymodbus.
    # The first one that does not raise TypeError is used for every subsequent call.
    attempts = [
        lambda: smartmeter.read_holding_registers(
            address=reg, count=count, device_id=smartmeter.unit
        ),
        lambda: smartmeter.read_holding_registers(
            address=reg, count=count, slave=smartmeter.unit
        ),
        lambda: smartmeter.read_holding_registers(
            address=reg, count=count, unit=smartmeter.unit
        ),
        lambda: smartmeter.read_holding_registers(reg, count, slave=smartmeter.unit),
        lambda: smartmeter.read_holding_registers(reg, count, unit=smartmeter.unit),
    ]

    last_type_error = None
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            last_type_error = exc  # keep going, try next variant

    # None of the variants matched; re-raise to surface the real problem.
    if last_type_error is not None:
        raise last_type_error

    raise RuntimeError("No compatible pymodbus read_holding_registers signature found")

def umwandeln_ieee(Wert):  #Umwandlung Array of int ( 4 byte) in float nach IEEE 754

    """
    Function for conversion of float register values into IEEE value
    """
    return struct.unpack('>f', struct.pack('>I', Wert))[0]

def write_to_iobroker(meternr, meter_data, mqtt_client):
    """
    Writes measurement data from meternr into ioBroker via MQTT.

    Parameters
    ----------
    meternr : Integer
        Modbus number of meter to be read
    meter_data : Dict
        Dictionary with measurement values
    mqtt_client : mqtt.Client
        Connected MQTT client instance

    Returns
    -------
    None.

    """
    # Resolve the friendly topic name for this meter (e.g. "Household").
    # Falls back to "meter<N>" for any unknown meter number.
    meter_topic = METER_TOPICS.get(meternr, f"meter{meternr}")
    topic_base = f"{MQTT_TOPIC_PREFIX}/{meter_topic}"

    # Publish each metric as its own retained topic so ioBroker can map
    # individual states, e.g. powermeter/Household/L1-Voltage (V)
    for key, value in meter_data.items():
        topic = f"{topic_base}/{key}"
        mqtt_client.publish(topic, payload=str(value), qos=MQTT_QOS, retain=MQTT_RETAIN)

    # Also publish a compact JSON payload for consumers that prefer one message.
    mqtt_client.publish(
        f"{topic_base}/json",
        payload=json.dumps(meter_data),
        qos=MQTT_QOS,
        retain=MQTT_RETAIN,
    )

    if DEBUG:
        print(f"Data written to ioBroker via MQTT topic base: {topic_base}")


def bootstrap_mqtt_states(meternr, mqtt_client):
    """
    Publish default retained states so ioBroker MQTT adapter can auto-create
    all expected objects in the MQTT tree.

    Only call this when BOOTSTRAP_STATES is True (once, to seed the tree).
    Calling it on every run would publish zeros before each real read and
    cause values in ioBroker to flip between 0 and the measured value.
    """
    if DEBUG:
        print(f"Bootstrapping MQTT states for meter {meternr}...")
    write_to_iobroker(meternr, DEFAULT_METER_DATA, mqtt_client)

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
        # pymodbus: read 1 register (2 bytes)
        result = read_holding_registers_compat(smartmeter, reg, 1)
        if result.isError():
            print("Read error reading register ", reg, "retry in next time interval")
            return 0
        return result.registers[0]
    except Exception as e:
        print("Read error reading register ", reg, e, "retry in next time interval")
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
        # pymodbus: read 2 registers (4 bytes)
        result = read_holding_registers_compat(smartmeter, reg, 2)
        if result.isError():
            print("Read error reading register ", reg, "retry in next time interval")
            return 0
        # Combine two 16-bit registers into a 32-bit integer (big-endian)
        return (result.registers[0] << 16) + result.registers[1]
    except Exception as e:
        print("Read error reading register ", reg, e, "retry in next time interval")
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
        # pymodbus: read 2 registers (4 bytes)
        result = read_holding_registers_compat(smartmeter, reg, 2)
        if result.isError():
            print("Read error reading register ", reg, "retry in next time interval")
            return 0
        # Combine two 16-bit registers into a 32-bit int, then convert to float
        value = (result.registers[0] << 16) + result.registers[1]
        return round(umwandeln_ieee(value), fractdig)
    except Exception as e:
        print("Read error reading register ", reg, e, "retry in next time interval")
        return 0

def read_from_meter(meternr):

    """
    Initialize adapter for RS485 Instrument. Parameters are:
        Port, Address, mode and that the RS485 port should not be closed again
        after the instrument has been accessed (faster).
    meternr specifies the Modbus # of the meter

    The routine returns a dictionary with values to be published via MQTT.
    """


    # Open the RS-485 serial port via the symlink created by the udev rule.
    # Settings match the OR-WE-517 default: 9600 baud, 8E1.
    smartmeter = ModbusSerialClient(
        port='/dev/ORNO',
        baudrate=9600,
        bytesize=8,
        parity='E',
        stopbits=1,
        timeout=0.6   # seconds to wait for a reply before treating it as an error
    )
    if not smartmeter.connect():
        raise IOError(f"Failed to connect to meter {meternr} on /dev/ORNO")
    # Store the Modbus device address on the client so helper functions can read it.
    smartmeter.unit = meternr

    #Adresse = smartmeter.read_register(2, 0, 3, False)
    # registeraddress, number_of_decimals=0, functioncode=3, signed=False

    # --- Device identification registers (reg 0-13) ---
    SerialNum = read_long(smartmeter, 0)       # 4-byte serial number
    if DEBUG:
        print("Serial number: ",SerialNum)

    ModbusID = read_reg(smartmeter, 2)         # Modbus slave address stored on device
    if DEBUG:
        print("Modbus ID: ",ModbusID)

    ModbusBaudrate = read_reg(smartmeter, 3)   # Baud rate code stored on device
    if DEBUG:
        print("Modbus Baudrate: ",ModbusBaudrate, " bps")

    SoftwareVer = read_float(smartmeter, 4, 2) # Firmware version
    if DEBUG:
        print("Software Version: ",SoftwareVer)

    HardwareVer = read_float(smartmeter, 6, 2) # Hardware revision
    if DEBUG:
        print("Hardware Version: ",HardwareVer)

    CTRate = read_reg(smartmeter, 8)           # Current transformer ratio
    if DEBUG:
        print("CT Rate: ",CTRate)

    S0Rate = read_float(smartmeter, 9, 1)      # S0 pulse output rate (impulses/kWh)
    if DEBUG:
        print("S0 output rate: ",S0Rate," imp/kWh")

    A3Code = read_reg(smartmeter, 11)          # Tariff/A3 code
    if DEBUG:
        print("A3 Code: ",A3Code)

    HolidayWeekendT = read_reg(smartmeter, 12) # Holiday/weekend tariff flag
    if DEBUG:
        print("Holiday-Weekend T: ", HolidayWeekendT)

    LCDCycleTime = read_reg(smartmeter, 13)    # LCD display rotation interval
    if DEBUG:
        print("LCD Cycle Time: ", LCDCycleTime)

    # --- Voltage and frequency (reg 14-20) ---
    L1Voltage = read_float(smartmeter, 14, 1)  # Phase 1 voltage in V
    if DEBUG:
        print("L1-Voltage: ", L1Voltage, " V")

    L2Voltage = read_float(smartmeter, 16, 1)  # Phase 2 voltage in V
    if DEBUG:
        print("L2-Voltage: ", L2Voltage, " V")

    L3Voltage = read_float(smartmeter, 18, 1)  # Phase 3 voltage in V
    if DEBUG:
        print("L3-Voltage: ", L3Voltage, " V")

    Frequency = read_float(smartmeter, 20, 2)  # Grid frequency in Hz
    if DEBUG:
        print("Grid Frequency: ", Frequency, " Hz")

    # --- Phase currents (reg 22-26) ---
    L1Current = read_float(smartmeter, 22, 2)  # Phase 1 current in A
    if DEBUG:
        print("L1-Current: ", L1Current, " A")

    L2Current = read_float(smartmeter, 24, 2)  # Phase 2 current in A
    if DEBUG:
        print("L2-Current:", L2Current, " A")

    L3Current = read_float(smartmeter, 26, 2)  # Phase 3 current in A
    if DEBUG:
        print("L3-Current:", L3Current, " A")

    # --- Active power (reg 28-34), unit kW ---
    TotalActivePower = read_float(smartmeter, 28, 3)
    if DEBUG:
        print("Total Active Power:", TotalActivePower, " kW")

    L1ActivePower = read_float(smartmeter, 30, 3)
    if DEBUG:
        print("L1-Active Power:", L1ActivePower, " kW")

    L2ActivePower = read_float(smartmeter, 32, 3)
    if DEBUG:
        print("L2-Active Power:", L2ActivePower, " kW")

    L3ActivePower = read_float(smartmeter, 34, 3)
    if DEBUG:
        print("L3-Active Power:", L3ActivePower, " kW")

    # --- Reactive power (reg 36-42), unit kVar ---
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

    # --- Apparent power (reg 44-50), unit kVA ---
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

    # --- Power factors (reg 52-58), dimensionless ---
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

    CRC = read_reg(smartmeter, 65)            # Internal CRC / checksum register
    if DEBUG:
        print("CRC: ",CRC)

    #CombinedCode = smartmeter.read_register(66, 0, 3, False)
    #if DEBUG:
    #    print("Combined Code: ",CombinedCode)

    # --- Energy counters (reg 256+), unit kWh / kVarh ---
    TotalActiveEnergy = read_float(smartmeter, 256, 2)      # Total (import+export) active energy
    if DEBUG:
        print("Total Active Energy:", TotalActiveEnergy, " kWh")

    L1TotalActiveEnergy = read_float(smartmeter, 258, 2)     # Phase 1
    if DEBUG:
        print("L1 Total Active Energy:", L1TotalActiveEnergy, " kWh")

    L2TotalActiveEnergy = read_float(smartmeter, 260, 2)     # Phase 2
    if DEBUG:
        print("L2 Total Active Energy:", L2TotalActiveEnergy, " kWh")

    L3TotalActiveEnergy = read_float(smartmeter, 262, 2)     # Phase 3
    if DEBUG:
        print("L3 Total Active Energy:", L3TotalActiveEnergy, " kWh")

    ForwardActiveEnergy = read_float(smartmeter, 264, 2)     # Import (consumed) active energy
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

    ReverseActiveEnergy = read_float(smartmeter, 272, 2)    # Export (fed-in) active energy
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

    TotalReactiveEnergy = read_float(smartmeter, 280, 2)    # Total reactive energy
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

    ForwardReactiveEnergy = read_float(smartmeter, 288, 2)  # Import reactive energy
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

    ReverseReactiveEnergy = read_float(smartmeter, 296, 2)  # Export reactive energy
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

    try:
        meter_data = {
            "L1-Voltage (V)": L1Voltage,
            "L2-Voltage (V)": L2Voltage,
            "L3-Voltage (V)": L3Voltage,
            "Grid Frequency (Hz)": Frequency,
            "L1-Current (A)": L1Current,
            "L2-Current (A)": L2Current,
            "L3-Current (A)": L3Current,
            "Total Active Power (kW)": TotalActivePower,
            "L1-Active Power (kW)": L1ActivePower,
            "L2-Active Power (kW)": L2ActivePower,
            "L3-Active Power (kW)": L3ActivePower,
            "Total Reactive Power (kVar)": TotalReactivePower,
            "L1-Reactive Power (kVar)": L1ReactivePower,
            "L2-Reactive Power (kVar)": L2ReactivePower,
            "L3-Reactive Power (kVar)": L3ReactivePower,
            "Total Apparent Power (kVA)": TotalApparentPower,
            "L1-Apparent Power (kVA)": L1ApparentPower,
            "L2-Apparent Power (kVA)": L2ApparentPower,
            "L3-Apparent Power (kVA)": L3ApparentPower,
            "Total Power Faktor": TotalPowerFactor,
            "L1-Power Factor": L1PowerFactor,
            "L2-Power Factor": L2PowerFactor,
            "L3-Power Factor": L3PowerFactor,
        }
        if DEBUG:
            print("MQTT Data-Object:", meter_data)
        return meter_data
    finally:
        smartmeter.close()

def main():
    """Connect to MQTT, optionally bootstrap states, then read and publish data from all meters."""
    # Connect to the MQTT broker with credentials from mqtt_credentials.py.
    mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()  # background thread handles MQTT network traffic

    try:
        # When BOOTSTRAP_STATES is True, publish zero-value defaults for all
        # states first so the ioBroker MQTT adapter creates the full object
        # tree. Set BOOTSTRAP_STATES = False after the first successful run.
        if BOOTSTRAP_STATES:
            bootstrap_mqtt_states(1, mqtt_client)
            bootstrap_mqtt_states(2, mqtt_client)

        # Read live data from meter 1 (Household) and publish it.
        meter_data = read_from_meter(1)
        write_to_iobroker(1, meter_data, mqtt_client)

        # Read live data from meter 2 (Heatpump) and publish it.
        meter_data = read_from_meter(2)
        write_to_iobroker(2, meter_data, mqtt_client)
    finally:
        # Always disconnect cleanly so the broker knows the client has gone.
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
