import struct
import serial
import threading
import numpy as np
import datetime
import os
import datatypes as dt


GRAVITY = 9.80665  # m/s²
DEG_TO_RAD = np.pi / 180


class WitMotion:
    def __init__(self, imu_port="/dev/ttyUSB0", baud_rate=115200, save_data=False, save_path=None):
        self.serial = None
        self.running = False
        self.timer = None
        self.imu_port = imu_port
        self.baud_rate = baud_rate
        self.template = {**dt.time_template, **dt.imu_template}
        self._current_data = self.template.copy()
        self._last_data = self.template.copy()
        self._save_data = save_data
        self._save_path = os.path.join(
            save_path, "witmotion_data.csv") if save_path else None
        self._filebuffer = []

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
        self.serial = serial.Serial(self.imu_port, self.baud_rate, timeout=1)
        self.running = True
        self.schedule_update()

    def stop(self):
        """Stop reading from the IMU"""
        if self._save_data:
            self.save_data()

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

    def _parse_sensor_data(self, data, expected_cmd, scale_factor, expected_length=7):
        """Generic function to parse IMU sensor data"""
        if len(data) < expected_length or data[0] != expected_cmd:
            return None
        return np.array(struct.unpack("<hhh", data[1:7])) / 32768.0 * scale_factor

    def _get_acceleration(self, data):
        """Returns acceleration with gravity removed"""
        acc = self._parse_sensor_data(data, ord("Q"), 16.0)
        return acc - np.array([0, 0, GRAVITY]) if acc is not None else None

    def _get_gyro(self, data):
        """Returns gyroscope values in radians per second"""
        gyro = self._parse_sensor_data(data, ord("R"), 2000.0)
        return gyro * DEG_TO_RAD if gyro is not None else None

    def _get_angle(self, data):
        """Returns angles in radians"""
        angle = self._parse_sensor_data(data, ord("S"), 180.0)
        return angle * DEG_TO_RAD if angle is not None else None

    # def _get_acceleration(self, data):
    #     return self._parse_sensor_data(data, ord("Q"), 16.0)

    # def _get_gyro(self, data):
    #     return self._parse_sensor_data(data, ord("R"), 2000.0)

    # def _get_angle(self, data):
    #     return self._parse_sensor_data(data, ord("S"), 180.0)

    # def _get_magnetic(self, data):
    #     return self._parse_sensor_data(data, ord("T"), 1.0)

    def _get_quaternion(self, data):
        """Parses quaternion data"""
        if len(data) < 9 or data[0] != ord("Y"):
            return None
        q = np.array(struct.unpack("<hhhh", data[1:9])) / 32768.0
        return np.array([q[1], q[2], q[3], q[0]])  # Rearrange to (x, y, z, w)

    def update(self):
        """Read and process an IMU packet"""
        try:
            s = self.serial.read_until(b"U")  # Read one IMU packet (11 bytes)
            if len(s) < 11:
                return  # Ignore incomplete packets

            # Store timestamp once for efficiency
            now = datetime.datetime.now()
            epoch_time = now.timestamp() * 1000
            formatted_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")

            # Extract sensor data
            data_extractors = {
                "acc": self._get_acceleration,
                "gyro": self._get_gyro,
                "angle": self._get_angle,
                "quat": self._get_quaternion,
            }

            data_keys = {
                "acc": ["accX", "accY", "accZ"],
                "gyro": ["gyroX", "gyroY", "gyroZ"],
                "angle": ["roll", "pitch", "yaw"],
                "quat": ["qX", "qY", "qZ", "qW"],
            }

            for key, func in data_extractors.items():
                result = func(s)
                if result is not None:
                    if key == "angle":  # Special yaw correction
                        result[2] = (result[2] + 360) % 360
                    self._current_data.update(
                        dict(zip(data_keys[key], result)))

            # Ensure we have complete data before storing
            if all(self._current_data.get(k) is not None for k in sum(data_keys.values(), [])):
                self._current_data.update(
                    {"epochtime": epoch_time, "time": formatted_time})
                self._last_data = self._current_data.copy()
                self._current_data = self.template.copy()

                if self._save_data:
                    self._filebuffer.append(self._last_data)
                    if len(self._filebuffer) > 100:
                        self.save_data()

        except Exception as e:
            print(f"IMU Read Error: {e}")

        finally:
            self.schedule_update()

    def get_last_data(self):
        """Return the last complete data packet"""
        return self._last_data

    def save_data(self):
        """Save the last complete data packet to file"""
        try:
            with open(self._save_path, "a") as f:
                for data in self._filebuffer:
                    f.write(",".join(map(str, data.values())) + "\n")
            self._filebuffer.clear()
        except Exception as e:
            print(f"Error writing to file: {e}")

    def __del__(self):
        """Cleanup resources on object destruction"""
        self.stop()

if __name__ == "__main__":
    imu = WitMotion(save_data=True, save_path="test")
    imu.start()
    try:
        while True:
            print(imu.get_last_data())
            # pass
    except KeyboardInterrupt:
        imu.stop()
        print("IMU stopped.")
