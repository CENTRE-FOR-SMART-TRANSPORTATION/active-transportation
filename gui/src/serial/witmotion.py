import os
import serial
import struct
import datetime
import threading
import numpy as np
from queue import Queue, Empty
import src.serial.datatypes as dt
from PySide6.QtCore import Signal, QObject


GRAVITY = 9.80665  # m/s²
DEG_TO_RAD = np.pi / 180


class WitMotion(QObject):
    lastData = Signal(dict)

    def __init__(self, imu_port, baud_rate, save_data=False, save_path=None):
        super().__init__()

        self.serial = None
        self.running = False
        self.imu_port = imu_port
        self.baud_rate = baud_rate
        self.template = {**dt.time_template, **dt.imu_template}

        self._current_data = self.template.copy()
        self._last_data = self.template.copy()
        self._save_data = save_data
        self._save_path = os.path.join(
            save_path, f"witmotion_data_{imu_port[-1:]}.csv") if save_path else None
        self._rawbuffer = Queue()
        self._filebuffer = Queue()

        if self._save_data and self._save_path:
            try:
                with open(self._save_path, "w") as self._file:
                    self._file.write(
                        ",".join(self._current_data.keys()) + "\n")
            except Exception as e:
                print(f"Error opening file for writing: {e}")
                self._save_data = False

    def start(self):
        """Start reading from the IMU"""
        self.serial = serial.Serial(
            self.imu_port, self.baud_rate, timeout=0.01)
        self.running = True

        self._raw_data_thread = threading.Thread(
            target=self.read_raw, daemon=True)
        self._raw_data_thread.start()

        self._parse_thread = threading.Thread(
            target=self.parse_sensor_data, daemon=True)
        self._parse_thread.start()

        if self._save_data:
            self._save_thread = threading.Thread(
                target=self.save_data_thread, daemon=True)
            self._save_thread.start()

    def stop(self):
        """Stop reading from the IMU"""
        self.running = False

        if isinstance(self._raw_data_thread, threading.Thread) and self._raw_data_thread.is_alive():
            self._raw_data_thread.join()

        if isinstance(self._parse_thread, threading.Thread) and self._parse_thread.is_alive():
            self._parse_thread.join()

        if isinstance(self._save_thread, threading.Thread) and self._save_thread.is_alive():
            self._save_thread.join()

        if self.serial and self.serial.is_open:
            self.serial.close()

        if self._save_data:
            self.save_data()

    def read_raw(self):
        count = 0
        while self.running:
            try:
                if count == 0:
                    # Try reading fixed packet size
                    data = self.serial.read_until(b"U")
                    count += 1
                else:
                    data = self.serial.read(11)
                if data and len(data) > 10:
                    self._rawbuffer.put(data)
            except Exception as e:
                print(f"IMU Read Error: {e}")

    def _get_time(self, data):
        """Extracts timestamp from IMU data"""
        if len(data) < 10 or data[1] != 0x50:
            return None
        try:
            year, month, day, hour, minute, second = data[2:8]
            ms = (data[9] << 8) | data[8]  # Combine msL and msH
            return datetime.datetime(
                year=2000 + year, month=month, day=day,
                hour=hour, minute=minute, second=second,
                microsecond=ms * 1000
            )
        except Exception as e:
            print(f"Error parsing time: {e}")
            return None

    def _parse_sensor_data_helper(self, data, expected_cmd, scale_factor, expected_length=7):
        """Generic function to parse IMU sensor data"""
        if len(data) < expected_length or data[0] != expected_cmd:
            return None
        # print(data)
        return np.array(struct.unpack("<hhh", data[1:7])) / 32768.0 * scale_factor

    # def _get_acceleration(self, data):
    #     """Returns acceleration with gravity removed"""
    #     acc = self._parse_sensor_data(data, ord("Q"), 16.0)
    #     return acc - np.array([0, 0, GRAVITY]) if acc is not None else None

    # def _get_gyro(self, data):
    #     """Returns gyroscope values in radians per second"""
    #     gyro = self._parse_sensor_data(data, ord("R"), 2000.0)
    #     return gyro * DEG_TO_RAD if gyro is not None else None

    # def _get_angle(self, data):
    #     """Returns angles in radians"""
    #     angle = self._parse_sensor_data(data, ord("S"), 180.0)
    #     return angle * DEG_TO_RAD if angle is not None else None

    def _get_acceleration(self, data):
        return self._parse_sensor_data_helper(data, ord("Q"), 16.0)

    def _get_gyro(self, data):
        return self._parse_sensor_data_helper(data, ord("R"), 2000.0)

    def _get_angle(self, data):
        # TODO: Change yaw to use 360.
        return self._parse_sensor_data_helper(data, ord("S"), 180.0)

    def _get_magnetic(self, data):
        return self._parse_sensor_data_helper(data, ord("T"), 1.0)

    def _get_quaternion(self, data):
        """Parses quaternion data"""
        if len(data) < 9 or data[0] != ord("Y"):
            return None
        q = np.array(struct.unpack("<hhhh", data[1:9])) / 32768.0
        return np.array([q[1], q[2], q[3], q[0]])  # Rearrange to (x, y, z, w)

    def parse_sensor_data(self):
        """Read and process an IMU packet"""
        while self.running:
            try:
                s = self._rawbuffer.get(timeout=1)

                # Store timestamp once for efficiency
                now = datetime.datetime.now()
                epoch_time = now.timestamp() * 1000
                formatted_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")
                self._current_data.update(
                    {"systemepoch": epoch_time, "systemtime": formatted_time})

                # Extract sensor data
                data_extractors = {
                    # "time": self._get_time,
                    "acc": self._get_acceleration,
                    "gyro": self._get_gyro,
                    "angle": self._get_angle,
                    "quat": self._get_quaternion,
                }

                data_keys = {
                    # "time": ["imutime"],
                    "acc": ["accX", "accY", "accZ"],
                    "gyro": ["gyroX", "gyroY", "gyroZ"],
                    "angle": ["roll", "pitch", "yaw"],
                    "quat": ["qX", "qY", "qZ", "qW"],
                }

                for key, func in data_extractors.items():
                    result = func(s)
                    if result is not None:
                        # if key == "angle":  # Special yaw correction
                        # result[2] = (result[2] + 360) % 360
                        self._current_data.update(
                            dict(zip(data_keys[key], result)))

                # print(self._current_data)
                if all(self._current_data.get(k) is not None for k in sum(data_keys.values(), [])):
                    self._last_data = self._current_data.copy()
                    self._current_data = self.template.copy()
                    
                    self._last_data = {k: str(v) if isinstance(
                        v, (int, float)) else v for k, v in self._last_data.items()}
                    self.lastData.emit(self._last_data)

                    if self._save_data:
                        self._filebuffer.put(self._last_data)

            except Exception as e:
                print(f"IMU Read Error: {e!r}")

    def save_data_thread(self):
        while self.running:
            try:
                data = self._filebuffer.get(timeout=1)
                with open(self._save_path, "a") as f:
                    f.write(",".join(data.values()) + "\n")
            except Empty:
                continue  # Just wait again
            except Exception as e:
                print(f"Error writing to file: {e!r}")

    def save_data(self):
        try:
            with open(self._save_path, "a") as f:
                for data in self._filebuffer:
                    f.write(",".join(data.values()) + "\n")
            self._filebuffer.clear()
        except Exception as e:
            print(f"Error writing to file: {e}")

    def get_last_data(self):
        """Return the last complete data packet"""
        # self.lastData.emit(self._last_data)
        return self._last_data

    def __del__(self):
        """Cleanup resources on object destruction"""
        self.stop()


if __name__ == "__main__":
    imu = WitMotion(imu_port='/dev/ttyUSB0', baud_rate=115200,
                    save_data=True, save_path="test")
    imu.start()
    try:
        while True:
            # print(imu.get_last_data())
            pass
    except KeyboardInterrupt:
        imu.stop()
        print("IMU stopped.")
