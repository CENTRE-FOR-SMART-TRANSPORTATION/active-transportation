"""
    Note: Modify sudo visudo to not ask for password
    sudo visudo
    youruser (name of the user) ALL=(ALL) NOPASSWD: /bin/date

    To sync with ntp server:
    sudo sntp -Ss -M 128 0.de.pool.ntp.org
"""

import os
import serial
import platform
import argparse
import threading
from IMU import IMUData
from pyubx2 import UBXReader
from datetime import datetime, timedelta, timezone

# Check if the system is Linux
if platform.system() == "Linux":
    device_path = (
        "/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00"
    )
    # device_path = "/dev/ttyACM0"
elif platform.system() == "Windows":
    device_path = "COM10"


template = {
    "Time": None,
    "Posix Time": None,
    "System Time": None,
    "Latitude": None,
    "Longitude": None,
    "Altitude (MSL)": None,
    "Azimuth": None,
    "Mode": None,
    "Satellites": None,
    "Roll": None,
    "Pitch": None,
    "Original Yaw": None,
    "Yaw": None,
    "AccX": None,
    "AccY": None,
    "AccZ": None,
    "GyroX": None,
    "GyroY": None,
    "GyroZ": None,
}

def display_values(data):
    header = ", ".join(data.keys())
    os.system("clear")  # For Linux/Mac, use 'cls' for Windows
    print(f"{header}")
    print(f"{' | '.join(map(str, data))} ")

def process_parsed_data(parsed_data):
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
            data["System Time"] = datetime.now().timestamp().strftime("%Y-%m-%d %H:%M:%S.%f")
            data["Time"] = iso_time
            data["Posix Time"] = f"{epoch_time:.3f}"
            global gpstime, fix
            gpstime = iso_time
            fix = parsed_data.fixType

            imu_time = imu.last_data["Time"]
            if imu_time.strftime("%Y-%m-%d %H:%M:%S") == iso_time.strftime("%Y-%m-%d %H:%M:%S"):
                data["Roll"] = imu.last_data["Roll"]
                data["Pitch"] = imu.last_data["Pitch"]
                data["Yaw"] = imu.last_data["Yaw"]
                data["Original Yaw"] = imu.last_data["Original Yaw"]
                data["AccX"] = imu.last_data["AccX"]
                data["AccY"] = imu.last_data["AccY"]
                data["AccZ"] = imu.last_data["AccZ"]
                data["GyroX"] = imu.last_data["GyroX"]
                data["GyroY"] = imu.last_data["GyroY"]
                data["GyroZ"] = imu.last_data["GyroZ"]

        elif msg_type in ["GNGGA", "GPGGA", "GNGNS", "GPGNS"]:
            data["Latitude"] = parsed_data.lat
            data["Longitude"] = parsed_data.lon
            data["Altitude (MSL)"] = parsed_data.alt
            data["Satellites"] = parsed_data.numSV
            data["Mode"] = parsed_data.quality

        elif msg_type in ["GNRMC", "GPRMC"]:
            date = parsed_data.date
            time = parsed_data.time
            iso_time = (
                f"{date[4:6]}-{date[2:4]}-{date[0:2]}T"
                f"{time[0:2]}:{time[2:4]}:{time[4:6]}.{time[6:]}Z"
            )
            epoch_time = datetime.strptime(iso_time, "%y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=timezone.utc
            )
            epoch_time = epoch_time.timestamp()
            data["Time"] = iso_time
            data["Posix Time"] = f"{epoch_time:.3f}"
            data["System Time"] = datetime.now().timestamp().strftime("%Y-%m-%d %H:%M:%S.%f")
            data["Latitude"] = parsed_data.lat
            data["Longitude"] = parsed_data.lon
            data["Azimuth"] = parsed_data.cog
            
            imu_time = imu.last_data["Time"]
            if imu_time.strftime("%Y-%m-%d %H:%M:%S") == iso_time.strftime("%Y-%m-%d %H:%M:%S"):
                data["Roll"] = imu.last_data["Roll"]
                data["Pitch"] = imu.last_data["Pitch"]
                data["Yaw"] = imu.last_data["Yaw"]
                data["Original Yaw"] = imu.last_data["Original Yaw"]
                data["AccX"] = imu.last_data["AccX"]
                data["AccY"] = imu.last_data["AccY"]
                data["AccZ"] = imu.last_data["AccZ"]
                data["GyroX"] = imu.last_data["GyroX"]
                data["GyroY"] = imu.last_data["GyroY"]
                data["GyroZ"] = imu.last_data["GyroZ"]

        elif msg_type in ["GNTHS", "GPTHS"]:
            data["Azimuth"] = parsed_data.headt

        elif msg_type == "GNVTG":
            data["Azimuth"] = parsed_data.cogt


def process_data():
    global data
    data = template.copy()
    while True:
        try:
            if ser.in_waiting:
                raw_data, parsed_data = ubr.read()
                raw_file.write(bytes(raw_data))
                raw_file.flush()
                if parsed_data:
                    parsed_file.write(f"{parsed_data}\n")
                    parsed_file.flush()
                    process_parsed_data(parsed_data)
                    if None not in list(data.values()):
                        display_values(data)
                        final_data = ", ".join(str(value) for value in data.values())
                        data_file.write(final_data + "\n")
                        data_file.flush()
                        data = template.copy()
        except KeyboardInterrupt:
            print("Exiting...")
            global event
            event = False
            break
        except Exception as e:
            print(f"Error in process_data: {e}")

def set_time():
    print("Inside set time")
    if fix > 2:
        print("Time set to")
        os.system('sudo date --set="%s"' % gpstime)
    threading.Timer(1, set_time).start()


def main(args):
    global ser, ubr, imu, GPS_EPOCH, GPS_UTC_OFFSET, fix, gpstime, event, data, raw_file, parsed_file, data_file
    data = template.copy()
    event = True
    fix = 0
    gpstime = None
    imu_port = args.imu_port
    baud_rate = args.baud_rate

    ser = serial.Serial(
        device_path,
        baudrate=115200,
        timeout=1,
    )
    ubr = UBXReader(ser, protfilter=7)

    imu = IMUData(imu_port, baud_rate)
    imu.start()
    print(f"Connected to IMU on {imu_port}")

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

    set_time()
    process_data()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read GPS and IMU data.")
    parser.add_argument(
        "--imu_port",
        type=str,
        default="/dev/ttyUSB0",
        help="The serial port for the IMU (default: /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--baud_rate",
        type=int,
        default=115200,
        help="The baud rate for the IMU (default: 115200)",
    )

    args = parser.parse_args()
    main(args)
