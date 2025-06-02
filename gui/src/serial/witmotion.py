import os
import time
import serial
import struct
import datetime
import threading
import numpy as np
import src.serial.datatypes as dt

from queue import Queue, Empty
from PySide6.QtCore import QObject


GRAVITY = 9.80665  # m/s²
DEG_TO_RAD = np.pi / 180


class WitMotion(QObject):
    def __init__(self, **kwargs):
        super().__init__()
        self.imu_port = kwargs.get("imu_port", None)
        self.baud_rate = kwargs.get("baud_rate", 115200)
        self.socket = kwargs.get("socket", None)
        self.save_data = kwargs.get("save_data", False)
        self.save_path = kwargs.get("save_path", None)
        self.imu_queue = kwargs.get("imu_queue", None)
        self.imu_error_queue = kwargs.get("imu_error_queue", None)
        self.display_timer = kwargs.get("display_timer", 1)

        self.serial = None
        self.running = False
        self.template = {**dt.time_template, **dt.imu_template}

        self._current_data = self.template.copy()
        self._last_data = self.template.copy()
        if self.save_data:
            base_dir = self.save_path or "."
            base_filename = f"witmotion_data"
            count = 1

            while True:
                filename = f"{base_filename}_{count}.csv"
                full_path = os.path.join(base_dir, filename)
                if not os.path.exists(full_path):
                    break
                count += 1

            self.save_path = full_path

        self._rawbuffer = Queue()
        self._filebuffer = Queue()

        self._raw_data_thread = None
        self._parse_thread = None
        self._save_thread = None
        if self.save_data and self.save_path:
            try:
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
                with open(self.save_path, "w") as f:
                    f.write(",".join(self._current_data.keys()) + "\n")
            except Exception as e:
                print(f"Error opening file for writing: {e}")
                self.save_data = False

        self.start()

    def start(self):
        try:
            """Start reading from the IMU"""
            if self.imu_port:
                self.serial = serial.Serial(
                    self.imu_port, self.baud_rate, timeout=1)
            elif self.socket:
                pass
            else:
                raise ValueError("No valid IMU port or socket provided")

            self.running = True
            
            if self.imu_port is not None:
                self._raw_data_thread = threading.Thread(target=self._read_raw)
                self._raw_data_thread.start()
            # else:
            #     self.socket.readyRead.connect(self._read_socket_data)
            elif self.socket is not None:
                print('socket ready')
                self._raw_data_thread = threading.Thread(target=self._read_raw)
                self._raw_data_thread.start()

            self._parse_thread = threading.Thread(
                target=self._parse_sensor_data)
            self._parse_thread.start()

            if self.save_data:
                self._save_thread = threading.Thread(
                    target=self._save_data_thread)
                self._save_thread.start()

            if self.imu_queue is not None:
                while True:
                    print("Sending data", self._last_data)
                    self.imu_queue.put(self._last_data)
                    time.sleep(self.display_timer)

        except Exception as e:
            print(f"Serial port error: {e}")
            if self.imu_error_queue is not None:
                self.imu_error_queue.put(f"Serial port error: {e}")
        
    def _read_socket_data(self):
        self._raw_data_thread = threading.Thread(target=self._read_raw)
        self._raw_data_thread.start()


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

    def _read_raw(self):
        if self.imu_port is not None:
            count = 0
            while self.running:
                try:
                    if count == 0:
                        # Try reading fixed packet size
                        data = self.serial.read_until(b"U")
                        # data = self.serial.read(10`)
                        count += 1
                    else:
                        data = self.serial.read(11)
                    if data and len(data) > 10:
                        self._rawbuffer.put(data)
                except Exception as e:
                    print(f"IMU Read Error: {e}")
        elif self.socket is not None:
            while self.running:
                try:
                    data = self.socket.get(timeout=1)  # This is a multiprocessing.Queue
                    if data and len(data) > 10:
                        self._rawbuffer.put(data)
                except Empty:
                    print('EMPTY QUEUE')
                    continue
                except Exception as e:
                    print(f"Queue Read Error: {e}")


    def _parse_sensor_data(self):
        """Read and process an IMU packet"""

        def _parse_sensor_data_helper(data, expected_cmd, scale_factor, expected_length=7):
            """Generic function to parse IMU sensor data"""
            if len(data) < expected_length or data[0] != expected_cmd:
                return None
            return np.array(struct.unpack("<hhh", data[1:7])) / 32768.0 * scale_factor

        def _get_time(data):
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

        def _get_acceleration(data):
            return _parse_sensor_data_helper(data, ord("Q"), 16.0)

        def _get_gyro(data):
            return _parse_sensor_data_helper(data, ord("R"), 2000.0)

        def _get_angle(data):
            # TODO: Change yaw to use 360.
            return _parse_sensor_data_helper(data, ord("S"), 180.0)

        def _get_magnetic(data):
            return _parse_sensor_data_helper(data, ord("T"), 1.0)

        def _get_quaternion(data):
            """Parses quaternion data"""
            if len(data) < 9 or data[0] != ord("Y"):
                return None
            q = np.array(struct.unpack("<hhhh", data[1:9])) / 32768.0
            # Rearrange to (x, y, z, w)
            return np.array([q[1], q[2], q[3], q[0]])

        while self.running:
            try:
                s = self._rawbuffer.get(timeout=1)

                # Store timestamp once for efficiency
                now = datetime.datetime.now()
                epoch_time = now.timestamp() * 1000
                formatted_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")
                self._current_data.update(
                    {"systemepoch": epoch_time, "systemtime": formatted_time, "imutime": 0})

                # Extract sensor data
                data_extractors = {
                    # "time": self._get_time,
                    "acc": _get_acceleration,
                    "gyro": _get_gyro,
                    "angle": _get_angle,
                    "quat": _get_quaternion,
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
                        if key == "angle":  # Special yaw correction
                            result[0] = result[0] * DEG_TO_RAD
                            result[1] = result[1] * DEG_TO_RAD
                            result[2] = ((result[2] + 360) % 360) * DEG_TO_RAD
                        self._current_data.update(
                            dict(zip(data_keys[key], result)))

                if all(self._current_data.get(k) is not None for k in sum(data_keys.values(), [])):
                    self._last_data = self._current_data.copy()
                    self._current_data = self.template.copy()

                    self._last_data = {k: str(v) if isinstance(
                        v, (int, float)) else v for k, v in self._last_data.items()}

                    if self.save_data:
                        self._filebuffer.put(self._last_data)

                    

            except Exception as e:
                print(f"IMU Read Error: {e!r}")

    def _save_data_thread(self):
        with open(self.save_path, "a", buffering=1) as f:
            data_batch = []  # List to collect data packets
            while self.running:
                try:
                    data = self._filebuffer.get(timeout=1)
                    # Collect data in the batch
                    data_batch.append(",".join(data.values()))

                    # Check if we have collected 100 data packets
                    if len(data_batch) >= 5:
                        # Write the batch to the file
                        f.write("\n".join(data_batch) + "\n")
                        data_batch.clear()  # Clear the batch after writing
                except Exception as e:
                    print(f"Error writing to file: {e}")
                except Empty:
                    continue

            # Write any remaining data in the batch when the thread stops
            if data_batch:
                f.write("\n".join(data_batch) + "\n")

    def get_last_data(self):
        """Return the last complete data packet"""
        return self._last_data

    def __del__(self):
        """Cleanup resources on object destruction"""
        self.stop()


if __name__ == "__main__":
    imu = WitMotion(imu_port=None, baud_rate=115200,
                    save_data=True, save_path="test")
    imu.start()
    try:
        while True:
            print(imu.get_last_data())
            pass
    except KeyboardInterrupt:
        imu.stop()
        print("IMU stopped.")
