import os
import sys
import mscl
import datetime
import threading
from queue import Queue
import datatypes as dt


class Microstrain():

    def __init__(self, imu_port, baud_rate=115200, save_data=False, save_path=None):
        super().__init__()

        self.running = False
        self.connection = None
        self.node = None
        self.imu_port = imu_port
        self.baud_rate = baud_rate

        self.template = {**dt.time_template, **dt.imu_template}
        self._raw_data = {}
        self._current_data = self.template.copy()
        self._save_data = save_data
        self._save_path = os.path.join(
            save_path, f"microstrain_data_{imu_port[-1:]}.csv") if save_path else None
        self._raw_data_buffer = Queue()
        self._filebuffer = Queue()

        self._save_thread = None
        self._parse_thread = None
        self.raw_data_thread = None

        if self._save_data and self._save_path:
            try:
                if not os.path.exists(save_path):
                    os.mkdir(save_path)
                with open(self._save_path, "w") as f:
                    f.write(",".join(self._current_data.keys()) + "\n")
            except Exception as e:
                print(f"Error opening file for writing: {e}")
                self._save_data = False

    def start(self):
        # Attempt to establish a connection to the Microstrain device
        try:
            self.connection = mscl.Connection.Serial(
                self.imu_port, self.baud_rate)
            self.node = mscl.InertialNode(self.connection)
            print("Connected to Microstrain device.")

            if not self.node.isDataStreamEnabled(mscl.MipTypes.CLASS_AHRS_IMU):
                self.enable_data_streams()

            self.running = True
            self.raw_data_thread = threading.Thread(
                target=self.start_data_streaming)
            self.raw_data_thread.start()

            self._parse_thread = threading.Thread(
                target=self.parse_sensor_data)
            self._parse_thread.start()

            if self._save_data:
                self._save_thread = threading.Thread(
                    target=self.save_data_thread)
                self._save_thread.start()
        except mscl.Error as e:
            print(f"Error connecting to Microstrain device: {e}")
            sys.exit(1)

    def stop(self):
        # Stop the data stream and close the connection
        self.running = False

        if isinstance(self.raw_data_thread, threading.Thread) and self.raw_data_thread.is_alive():
            self.raw_data_thread.join()

        if isinstance(self._parse_thread, threading.Thread) and self._parse_thread.is_alive():
            self._parse_thread.join()

        if isinstance(self._save_thread, threading.Thread) and self._save_thread.is_alive():
            self._save_thread.join()

        if isinstance(self.connection, mscl.Connection):
            try:
                self.connection.disconnect()
                print("Connection closed.")
            except mscl.Error as e:
                print(f"Error closing connection: {e}")

        if self._save_data:
            self.save_data()

    def __del__(self):
        self.stop()

    def enable_data_streams(self):
        # Enable data streams based on the device's capabilities
        try:
            if self.node.features().supportsCategory(mscl.MipTypes.CLASS_AHRS_IMU):
                self.node.enableDataStream(mscl.MipTypes.CLASS_AHRS_IMU)

            if self.node.features().supportsCategory(mscl.MipTypes.CLASS_ESTFILTER):
                self.node.enableDataStream(mscl.MipTypes.CLASS_ESTFILTER)

            if self.node.features().supportsCategory(mscl.MipTypes.CLASS_GNSS):
                self.node.enableDataStream(mscl.MipTypes.CLASS_GNSS)
        except mscl.Error as e:
            print(f"Error enabling data streams: {e}")
            sys.exit(1)

    def start_data_streaming(self):
        # Continuously read data packets from the device
        try:
            while self.running:
                packets = self.node.getDataPackets(500)
                for packet in packets:
                    """
                    timeInfo_tow_ahrsImu: 199.586000 
                    scaledAccelX: 0.026692 scaledAccelY: 0.009321 scaledAccelZ: -0.999889 
                    roll: -0.010865 pitch: 0.023428 yaw: -1.357981 
                    orientQuaternion: [0.778182,0.00312887,0.012527,-0.627906] 
                    scaledGyroX: -0.001219 scaledGyroY: 0.000571 scaledGyroZ: 0.000751
                    """
                    now = datetime.datetime.now()
                    epoch_time = now.timestamp() * 1000
                    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")

                    self._raw_data.update(
                        {"systemepoch": epoch_time, "systemtime": formatted_time})

                    for dataPoint in packet.data():
                        self._raw_data[dataPoint.channelName(
                        )] = dataPoint.as_string()

                    # Add the raw data to the queue
                    self._raw_data_buffer.put(self._raw_data.copy())
                    self._raw_data.clear()
        except mscl.Error as e:
            print(f"Error reading data: {e}")
            sys.exit(1)

    def parse_sensor_data(self):
        # Compute imutime
        while self.running:
            try:
                if not self._raw_data_buffer.empty():
                    raw_data = self._raw_data_buffer.get(timeout=1)

                    # Direct field mappings
                    self._current_data.update({
                        "systemtime": raw_data.get("systemtime"),
                        "systemepoch": raw_data.get("systemepoch"),
                        "imutime": raw_data.get("timeInfo_tow_ahrsImu"),
                        "roll": raw_data.get("roll"),
                        "pitch": raw_data.get("pitch"),
                        "yaw": raw_data.get("yaw"),
                        "accX": raw_data.get("scaledAccelX"),
                        "accY": raw_data.get("scaledAccelY"),
                        "accZ": raw_data.get("scaledAccelZ"),
                        "gyroX": raw_data.get("scaledGyroX"),
                        "gyroY": raw_data.get("scaledGyroY"),
                        "gyroZ": raw_data.get("scaledGyroZ"),
                        # "qX": quat_list[0],
                        # "qY": quat_list[1],
                        # "qZ": quat_list[2],
                        # "qW": quat_list[3],
                    })

                    quat = raw_data.get("orientQuaternion")
                    if isinstance(quat, str) and quat.startswith("[") and quat.endswith("]"):
                        try:
                            q_vals = [float(x.strip())
                                      for x in quat[1:-1].split(",")]
                            if len(q_vals) == 4:
                                self._current_data["qX"], self._current_data[
                                    "qY"], self._current_data["qZ"], self._current_data["qW"] = q_vals
                        except ValueError:
                            print("Invalid quaternion format")

                    # Add the current data to the file buffer
                    if all(self._current_data.get(k) is not None for k in self._current_data.keys()):
                        self._current_data = {k: str(v) if isinstance(
                            v, (int, float)) else v for k, v in self._current_data.items()}

                        if self._save_data:
                            self._filebuffer.put(self._current_data.copy())

                    self._current_data = self.template.copy()

            except Exception as e:
                print(f"Error parsing data: {e}")

    def save_data_thread(self):
        while self.running:
            try:
                if not self._filebuffer.empty():
                    # Wait for data to be available and get it
                    data = self._filebuffer.get(timeout=1)
                    with open(self._save_path, "a") as f:
                        f.write(",".join(data.values()) + "\n")
            except Exception as e:
                print(f"Error writing to file: {e}")

    def save_data(self):
        try:
            with open(self._save_path, "a") as f:
                for data in self._filebuffer:
                    f.write(",".join(data.values()) + "\n")
            self._filebuffer.clear()
        except Exception as e:
            print(f"Error writing to file: {e}")


if __name__ == "__main__":
    imu = Microstrain(imu_port="/dev/ttyACM1", baud_rate=115200,
                      save_data=True, save_path="test")
    imu.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        imu.stop()
    except Exception as e:
        print(f"Unexpected error: {e}")
        imu.stop()
