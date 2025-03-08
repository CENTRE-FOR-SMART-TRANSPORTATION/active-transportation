"""
This script reads GPS and IMU data and writes it to a file.
The GPS data is read from the gpsd daemon, and the IMU data is read from a WitMotion IMU.
"""

import os
import gpsd
import time
import struct
import serial
import argparse
import datetime
import threading
import numpy as np

class IMUData:
    def __init__(self, imu_port="/dev/ttyUSB0", baud_rate=115200):
        self.serial = None
        self.running = False
        self.timer = None
        self.imu_port = imu_port
        self.baud_rate = baud_rate
        self.current_data = template.copy()  # Holds incomplete packet
        self.last_data = template.copy()  # Holds the last complete packet

    def start(self):
        """Start reading from the IMU"""
        self.serial = serial.Serial(self.imu_port, self.baud_rate, timeout=1)
        self.running = True
        self.schedule_update()

    def stop(self):
        """Stop reading from the IMU"""
        self.running = False
        if self.timer:
            self.timer.cancel()
        if self.serial and self.serial.is_open:
            self.serial.close()

    def schedule_update(self):
        """Schedule the next update"""
        if self.running:
            self.timer = threading.Timer(-1, self.update)
            self.timer.start()

    def get_acceleration(self, data):
        if len(data) < 7:
            return None
        cmd = struct.unpack("c", data[0:1])[0]
        if cmd == b"Q":  # 0x54
            return np.array(struct.unpack("<hhh", data[1:7])) / 32768.0 * 16.0
        return None

    def get_gyro(self, data):
        if len(data) < 7:
            return None
        cmd = struct.unpack("c", data[0:1])[0]
        if cmd == b"R":  # 0x54
            return np.array(struct.unpack("<hhh", data[1:7])) / 32768.0 * 2000.0
        return None

    def get_angle(self, data):
        if len(data) < 7:
            return
        cmd = struct.unpack("c", data[0:1])[0]
        if cmd == b"S":  # 0x53
            return np.array(struct.unpack("<hhh", data[1:7])) / 32768.0 * 180.0
        return None

    def update(self):
        """Read and process a packet"""
        try:
            s = self.serial.read_until(b"U")  # Read one IMU packet (11 bytes)
            self.current_data["Time"] = datetime.datetime.now().isoformat()

            accel = self.get_acceleration(s)
            gyro = self.get_gyro(s)
            angle = self.get_angle(s)

            if accel is not None:
                accel = accel.tolist()
                self.current_data["accel_X"] = accel[0]
                self.current_data["accel_Y"] = accel[1]
                self.current_data["accel_Z"] = accel[2]

            if gyro is not None:
                gyro = gyro.tolist()
                self.current_data["gyro_X"] = gyro[0]
                self.current_data["gyro_Y"] = gyro[1]
                self.current_data["gyro_Z"] = gyro[2]

            if angle is not None:
                angle = angle.tolist()
                self.current_data["roll"] = angle[0]
                self.current_data["pitch"] = angle[1]
                self.current_data["original_yaw"] = angle[2]
                self.current_data["yaw"] = (angle[2] + 360) % 360

            if None not in self.current_data.values():
                self.last_data = self.current_data.copy()
                self.current_data = template.copy()

        except Exception as e:
            print(f"IMU Read Error: {e}")

        finally:
            self.schedule_update()


# Data structure template
template = {
    "time": None,
    "accel_X": None,
    "accel_Y": None,
    "accel_Z": None,
    "gyro_X": None,
    "gyro_Y": None,
    "gyro_Z": None,
    "roll": None,
    "pitch": None,
    "original_yaw": None,
    "yaw": None,
}


def main(args):
    # Configure the serial connection
    imu_port = args.imu_port
    baud_rate = args.baud_rate

    # Connect to the gpsd daemon
    gpsd.connect()
    print("Connected to gpsd")

    # GPS data template
    gps_info = {
        "time": None,
        "system_time": datetime.datetime.now().isoformat(),
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "azimuth": None,
        "mode": None,
        "satellites": None,
    }

    imu = IMUData(imu_port, baud_rate)
    imu.start()
    print(f"Connected to IMU on {imu_port}")

    # Create a file name based on current date and time
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"{timestamp}.txt"

    # Open the file for writing
    with open(filename, "w") as file:
        print(f"Writing GPS and IMU data to file: {filename}")

        # Write headers
        header = ", ".join(gps_info.keys()) + ", " + ", ".join(imu.last_data.keys())
        file.write(header + "\n")

        try:
            while True:
                # Fetch current GPS data
                try:
                    gps_data = gpsd.get_current()
                    gps_info = {
                        "time": gps_data.get_time().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "system_time": datetime.datetime.now().isoformat(),
                        "latitude": gps_data.lat,
                        "longitude": gps_data.lon,
                        "altitude": gps_data.alt,
                        "azimuth": gps_data.track,
                        "mode": gps_data.mode,
                        "satellites": gps_data.sats,
                    }
                except Exception as e:
                    gps_info = {"error": str(e)}

                # Get latest IMU data
                imu_data = ", ".join(str(value) for value in imu.last_data.values())

                # Write the combined data to the file
                file_data = (
                    ", ".join(str(value) for value in gps_info.values())
                    + ", "
                    + imu_data
                )
                file.write(file_data + "\n")
                file.flush()

                # Print to console for real-time feedback
                file_data_list = file_data.split(", ")
                formatted_last_9 = [
                    f"{float(value):.3f}" if value != "None" else value
                    for value in file_data_list[-9:]
                ]
                output_data = file_data_list[:-9] + formatted_last_9

                # Print the formatted data
                os.system("clear")  # For Linux/Mac, use 'cls' for Windows
                print(f"{header}")
                print(f"{' | '.join(map(str, output_data))} ")
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nExiting GPS and IMU reader.")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            imu.stop()
            print("Exited")


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
