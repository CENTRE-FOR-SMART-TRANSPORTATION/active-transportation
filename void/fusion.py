"""
    Note: Modify sudo visudo to not ask for password
    sudo visudo
    youruser (name of the user) ALL=(ALL) NOPASSWD: /bin/date
y
    To sync with ntp server:
    sudo sntp -Ss -M 128 0.de.pool.ntp.org
"""

import os
import sys
import serial
import platform
import threading
from pyubx2 import UBXReader, UBXMessage
from datetime import datetime, timedelta, timezone
from prettytable import PrettyTable

# Check if the system is Linux
if platform.system() == "Linux":
    device_path = (
        "/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00"
    )
    setTime = True
    clear = "clear"
    # device_path = "/dev/ttyACM0"
elif platform.system() == "Windows":  
    device_path = "COM12"
    setTime = False
    clear = "cls"



template = {
    "GPS Time": None,
    "GPS Posix Time": None,
    "System Time": None,
    "Latitude": None,
    "Longitude": None,
    "Altitude": None,
    # "Azimuth": None,
    "Roll": None,
    "Pitch": None,
    "Yaw": None,
    "AccX": None,
    "AccY": None,
    "AccZ": None,
    "AngX": None,
    "AngY": None,
    "AngZ": None,
    "GyroX": None,
    "GyroY": None,
    "GyroZ": None,
}

status_template = {
    "Fusion Mode": 0,
    "IMU Status": 0,
    "INS Status": 0,
    "GPS Fix": 0,
    "No. of Satellites": 0,
    "GPS Accuracy (H, V)": (0, 0),
    "Roll Accuracy": 0,
    "Pitch Accuracy": 0,
    "Yaw Accuracy": 0,
}

calib_status_template = {
    "Gyro Y": "Not Calibrated",
    "Gyro X": "Not Calibrated",
    "Gyro Z": "Not Calibrated",
    "Acc X": "Not Calibrated",
    "Acc Y": "Not Calibrated",
    "Acc Z": "Not Calibrated",
}


def display_values(data, status, calib_status):
    if None not in list(data.values()):
        os.system(clear)  # Clear screen
        # data_table = PrettyTable(list(data.keys()))
        # data_table.add_row(list(data.values()))

        # status_table = PrettyTable(list(status.keys()))
        # status_table.add_row(list(status.values()))

        # calib_status_table = PrettyTable(list(calib_status.keys()))
        # calib_status_table.add_row(list(calib_status.values()))

        sys.stdout.write(f"\033[H{data}\n\n{status}\n\n{calib_status}\n")
        # print(data, status, calib_status)
        sys.stdout.flush()
    # if None not in list(data.values()):
    #     print(data.values())
    #     print(status.values())
    #     print(calib_status.values())


def process_parsed_data(raw_data, parsed_data):
    if hasattr(parsed_data, "identity"):
        msg_type = parsed_data.identity

        if msg_type == "NAV-PVT":
            s = parsed_data.iTOW / 1000
            time = GPS_EPOCH + timedelta(seconds=s - GPS_UTC_OFFSET)
            iso_time = (
                f"{parsed_data.year}-{parsed_data.month:02}-{parsed_data.day:02}T"
                f"{time.strftime('%H:%M:%S.%f')}Z"
            )
            epoch_time = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=timezone.utc
            )
            epoch_time = epoch_time.timestamp()
            data["System Time"] = datetime.now().timestamp()
            data["GPS Time"] = iso_time
            data["GPS Posix Time"] = f"{epoch_time:.3f}"
            data["Latitude"] = parsed_data.lat
            data["Longitude"] = parsed_data.lon
            data["Altitude"] = parsed_data.hMSL / 1000
            status["GPS Fix"] = parsed_data.fixType
            status["GPS Accuracy (H, V)"] = (
                parsed_data.hAcc / 1000,
                parsed_data.vAcc / 1000,
            )
            global gpstime, fix
            gpstime = iso_time
            fix = parsed_data.fixType

        elif msg_type == "NAV-ATT":
            data["Roll"] = parsed_data.roll
            data["Pitch"] = parsed_data.pitch
            data["Yaw"] = parsed_data.heading
            status["Roll Accuracy"] = parsed_data.accRoll
            status["Pitch Accuracy"] = parsed_data.accPitch
            status["Yaw Accuracy"] = parsed_data.accHeading

        elif msg_type == "ESF-MEAS":
            for i in range(1, parsed_data.numMeas + 1):
                data_type = getattr(parsed_data, f"dataType_0{i}")
                data_field = getattr(parsed_data, f"dataField_0{i}")
                if data_type == 16:
                    data["GyroX"] = data_field / 1000
                elif data_type == 17:
                    data["GyroY"] = data_field / 1000
                elif data_type == 18:
                    data["GyroZ"] = data_field / 1000

        elif msg_type == "ESF-INS":
            data["AngX"] = parsed_data.xAngRate
            data["AngY"] = parsed_data.yAngRate
            data["AngZ"] = parsed_data.zAngRate
            data["AccX"] = parsed_data.xAccel
            data["AccY"] = parsed_data.yAccel
            data["AccZ"] = parsed_data.zAccel

        elif msg_type == "ESF-STATUS":
            status["IMU Status"] = (
                "Initialized"
                if parsed_data.imuInitStatus == 2
                else ("Initializing" if parsed_data.imuInitStatus == 1 else "No")
            )
            status["INS Status"] = (
                "Initialized"
                if parsed_data.insInitStatus == 2
                else ("Initializing" if parsed_data.insInitStatus == 1 else "No")
            )
            status["Fusion Mode"] = parsed_data.fusionMode
            # Sensor type mapping
            sensor_types = {
                5: "Gyro X",
                13: "Acc X",
                14: "Acc Y",
                16: "Acc Z",
                17: "Gyro Y",
                18: "Gyro Z",
            }

            for i in range(1, parsed_data.numSens + 1):
                try:
                    sensor_type = getattr(parsed_data, f"type_{i:02d}")
                    calib_status_value = getattr(parsed_data, f"calibStatus_{i:02d}")

                    if sensor_type in sensor_types:
                        sensor_name = sensor_types[sensor_type]
                        calib_status[sensor_name] = (
                            "Calibrated"
                            if calib_status_value in [2, 3]
                            else (
                                "Calibrating"
                                if calib_status_value == 1
                                else "Not Calibrated"
                            )
                        )
                except AttributeError:
                    print(f"Warning: Missing sensor data for index {i}")

        elif msg_type in ["GNGGA", "GPGGA", "GNGNS", "GPGNS"]:
            data["Latitude"] = parsed_data.lat
            data["Longitude"] = parsed_data.lon
            data["Altitude"] = parsed_data.alt
            status["No. of Satellites"] = parsed_data.numSV

        elif msg_type == "GNVTG":
            data["Azimuth"] = parsed_data.cogt


def process_data():
    global data, status, calib_status
    data = template.copy()
    status = status_template.copy()
    calib_status = calib_status_template.copy()
    while True:
        try:
            if ser.in_waiting:
                raw_data, parsed_data = ubr.read()
                raw_file.write(bytes(raw_data))
                raw_file.flush()
                if parsed_data:
                    parsed_file.write(f"{parsed_data}\n")
                    parsed_file.flush()
                    process_parsed_data(raw_data, parsed_data)
                    display_values(data, status, calib_status)
                    if None not in list(data.values()):
                        imu_data = ", ".join(str(value) for value in data.values())
                        # print(imu_data)
                        data_file.write(imu_data + "\n")
                        data_file.flush()
                        print(data)
                        data = template.copy()
                        status = status_template.copy()
                        calib_status = calib_status_template.copy()
        except KeyboardInterrupt:
            print("Exiting...")
            global event
            event = False
            break
        except Exception as e:
            print(f"Error in process_data: {e}")


def backup_data():
    print("Inside backup_data")
    backup_msg = b"\xb5\x62\x09\x14\x04\x00\x00\x00\x00\x00"
    clear_msg = b"\xb5\x62\x09\x14\x04\x00\x01\x00\x00\x00"

    if (
        status["GPS Fix"] > 2
        and status["Fusion Mode"] == 1
        and "Not Calibrated" not in calib_status.values()
    ):
        # Send backup signal
        ser.write(clear_msg)
        for raw_data, parsed_data in ubr:
            if parsed_data.identity == "UPD-ACK-ACK":
                print("Clear success!")
                check = 1
            elif parsed_data.identity == "UBX-ACK-NAK":
                print("Clear failed!")
                check = 0
                break
        if check:
            ser.write(backup_msg)
            for raw_data, parsed_data in ubr:
                if parsed_data.identity == "UPD-SOS-ACK":
                    if parsed_data.response == 1:
                        print("Backup success!")
                    else:
                        print("Backup failed!")


def set_time():
    print("Inside set time")
    if fix > 2:
        print("Time set to")
        os.system('sudo date --set="%s"' % gpstime)
    # Schedule next execution after 5 seconds
    # backup_data()
    threading.Timer(1, set_time).start()


def main():
    global ser, ubr, GPS_EPOCH, GPS_UTC_OFFSET, fix, gpstime, event, data, status, calib_status, raw_file, parsed_file, data_file
    data = template.copy()
    status = status_template.copy()
    calib_status = calib_status_template.copy()
    event = True
    fix = 0
    gpstime = None
    ser = serial.Serial(
        device_path,
        baudrate=115200,
        timeout=1,
    )
    ubr = UBXReader(ser, protfilter=7)
    GPS_EPOCH = datetime(1980, 1, 6)
    GPS_UTC_OFFSET = 18

    time = datetime.now()
    time = time.strftime("%Y-%m-%d_%H-%M-%S")
    record_dir = f"{time}_record"
    if os.path.exists(record_dir):
        os.rmdir(record_dir)

    os.mkdir(f"{record_dir}")

    raw_file = open(f"{record_dir}/raw.bin", "wb")
    parsed_file = open(f"{record_dir}/parsed.txt", "w")
    data_file = open(f"{record_dir}/data.txt", "w")
    header = ", ".join(data.keys())
    data_file.write(header + "\n")
    data_file.flush()

    if setTime:
        set_time()
        
    process_data()


if __name__ == "__main__":
    main()
