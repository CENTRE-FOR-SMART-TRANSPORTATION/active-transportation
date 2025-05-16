import time
from PySide6.QtCore import QThread, Signal, Slot, QObject
from ublox import Ublox
from microstrain import Microstrain
import serial
from queue import Queue, Empty
import threading

BUFFER = Queue()


class SerialReader(QObject):
    data_received = Signal(str)  # Signal to emit received data

    def __init__(self, port, baud_rate, save_path=None):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.running = True
        self.data_queue = Queue()  # Queue to store received data
        self.save_path = save_path

        # Start a separate thread for saving data
        self.save_thread = threading.Thread(target=self.save_data)
        self.save_thread.start()

    def start_reading(self):
        try:
            with serial.Serial(self.port, self.baud_rate, timeout=1) as ser:
                print(f"Connected to {self.port} at {self.baud_rate} baud.")
                while self.running:
                    if ser.in_waiting > 0:
                        data = ser.read()
                        self.data_queue.put(data)  # Emit the received data
        except serial.SerialException as e:
            print(f"Error: {e}")

    def stop(self):
        self.running = False
        self.save_thread.join()

    def save_data(self):
        while self.running or not self.data_queue.empty():
            try:
                # Wait for data in the queue
                data = self.data_queue.get(timeout=1)
                with open(self.save_path, "a") as f:
                    f.write(data)  # Save data to file
            except Empty:
                continue


def main():
    gps_thread = QThread()
    gps = Ublox(gps_port="/dev/ttyACM1", fusion=False,
                save_data=True, save_path="test1")
    gps.moveToThread(gps_thread)
    gps_thread.started.connect(gps.start)
    gps_thread.start()

    imu_thread = QThread()
    imu = Microstrain(imu_port="/dev/ttyACM0", baud_rate=115200,
                      save_data=True, save_path="test1")
    imu.moveToThread(imu_thread)
    imu_thread.started.connect(imu.start)
    imu_thread.start()
    try:
        while True:
            # print(gps.get_last_data())
            print(imu.get_last_data())

            time.sleep(1)
    except KeyboardInterrupt:
        gps.stop()
        imu.stop()

    except Exception as e:
        print(f"Unexpected error: {e}")
        gps.stop()
        imu.stop()


if __name__ == "__main__":
    main()
