import os
import sys
import mscl
import time
import datetime
import threading
from queue import Queue, Empty
import src.serial.datatypes as dt
from PySide6.QtCore import QObject, QThread


class Microstrain(QObject):
    def __init__(self, **kwargs):
        super().__init__()
        self.imu_port = kwargs.get("imu_port", "/dev/ttyACM0")
        self.baud_rate = kwargs.get("baud_rate", 115200)
        self.save_data = kwargs.get("save_data", False)
        self.save_path = kwargs.get("save_path", None)
        self.imu_queue = kwargs.get("imu_queue", None)
        self.imu_error_queue = kwargs.get("imu_error_queue", None)
        self.display_timer = kwargs.get("display_timer", 1)


        self.running = False
        self.connection = None
        self.node = None

        self.template = {**dt.time_template, **dt.imu_template}
        self._raw_data = {}
        self._current_data = self.template.copy()
        self._last_data = self.template.copy()
        if self.save_data:
            base_dir = self.save_path or "."
            base_filename = f"microstrain_data"
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
                if self.imu_error_queue is not None:
                    self.imu_error_queue.put(
                        f"Error opening file for writing: {e}")
            
        self.start()

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
            self._raw_data_thread = threading.Thread(
                target=self._start_data_streaming)
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
                    self.imu_queue.put(self._last_data)
                    time.sleep(self.display_timer)


        except mscl.Error as e:
            print(f"Error connecting to Microstrain device: {e}")
            if self.imu_error_queue is not None:
                self.imu_error_queue.put(
                    f"Error connecting to Microstrain device: {e}")
            sys.exit(1)

    def stop(self):
        # Stop the data stream and close the connection
        self.running = False

        if isinstance(self._raw_data_thread, threading.Thread) and self._raw_data_thread.is_alive():
            self._raw_data_thread.join()

        if isinstance(self._parse_thread, threading.Thread) and self._parse_thread.is_alive():
            self._parse_thread.join()

        if isinstance(self.connection, mscl.Connection):
            try:
                self.connection.disconnect()
                
                print("Connection closed.")
            except mscl.Error as e:
                print(f"Error closing connection: {e}")

        if isinstance(self._save_thread, threading.Thread) and self._save_thread.is_alive():
            self._save_thread.join()

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
            if self.imu_error_queue is not None:
                self.imu_error_queue.put(
                    f"Error enabling data streams: {e}")
            sys.exit(1)

    def _start_data_streaming(self):
        # Continuously read data packets from the device
        try:
            while self.running:
                packets = self.node.getDataPackets(500, 100)
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
                    self._rawbuffer.put(self._raw_data.copy())
                    self._raw_data.clear()
                time.sleep(0.005)
        except mscl.Error as e:
            print(f"Error reading data: {e}")
            if self.imu_error_queue is not None:
                self.imu_error_queue.put(
                    f"Error reading data: {e}")
            sys.exit(1)

    def _parse_sensor_data(self):
        # Compute imutime
        while self.running:
            try:
                if not self._rawbuffer.empty():
                    raw_data = self._rawbuffer.get(timeout=1)

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

                        if self.save_data:
                            self._filebuffer.put(self._current_data.copy())

                        self._last_data = self._current_data.copy()

                    self._current_data = self.template.copy()

            except Exception as e:
                print(f"Error parsing data: {e}")
                if self.imu_error_queue is not None:
                    self.imu_error_queue.put(
                        f"Error parsing data: {e}")

    def get_last_data(self):
        """Return the last complete data packet"""
        # self.lastData.emit(self._last_data)
        return self._last_data

    def _save_data_thread(self):
        with open(self.save_path, "a", buffering=1) as f:
            data_batch = []  # List to collect data packets
            while self.running:
                try:
                    data = self._filebuffer.get(timeout=1)
                    # Collect data in the batch
                    data_batch.append(",".join(data.values()))

                    # Check if we have collected 100 data packets
                    if len(data_batch) >= 100:
                        # Write the batch to the file
                        f.write("\n".join(data_batch) + "\n")
                        data_batch.clear()  # Clear the batch after writing
                except Exception as e:
                    print(f"Error writing to file: {e}")
                    if self.imu_error_queue is not None:
                        self.imu_error_queue.put(
                            f"Error writing to file: {e}")
                except Empty:
                    continue

            # Write any remaining data in the batch when the thread stops
            if data_batch:
                f.write("\n".join(data_batch) + "\n")



if __name__ == "__main__":
    imu_thread = QThread()
    imu = Microstrain(imu_port="/dev/ttyACM0", baud_rate=115200,
                      save_data=True, save_path="test")
    imu.moveToThread(imu_thread)
    imu_thread.started.connect(imu.start)
    imu_thread.start()
    try:
        while True:
            print(imu.get_last_data())
            time.sleep(1)
    except KeyboardInterrupt:
        imu.stop()
    except Exception as e:
        print(f"Unexpected error: {e}")
        imu.stop()
