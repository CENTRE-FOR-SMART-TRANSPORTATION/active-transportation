import struct
import serial
import threading
import numpy as np
import datetime

# Data structure template
template = {
    "Time": None,
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
                self.current_data["AccX"] = accel[0]
                self.current_data["AccY"] = accel[1]
                self.current_data["AccZ"] = accel[2]

            if gyro is not None:
                gyro = gyro.tolist()
                self.current_data["GyroX"] = gyro[0]
                self.current_data["GyroY"] = gyro[1]
                self.current_data["GyroZ"] = gyro[2]

            if angle is not None:
                angle = angle.tolist()
                self.current_data["Roll"] = angle[0]
                self.current_data["Pitch"] = angle[1]
                self.current_data["Original Yaw"] = angle[2]
                self.current_data["Yaw"] = (angle[2] + 360) % 360

            if None not in self.current_data.values():
                self.last_data = self.current_data.copy()
                self.current_data = template.copy()

        except Exception as e:
            print(f"IMU Read Error: {e}")

        finally:
            self.schedule_update()