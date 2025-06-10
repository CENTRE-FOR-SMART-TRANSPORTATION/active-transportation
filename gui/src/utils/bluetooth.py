from PySide6.QtCore import QObject, Signal, Slot, Qt
from PySide6.QtGui import QColor
from PySide6.QtBluetooth import (
    QBluetoothAddress, QBluetoothDeviceDiscoveryAgent, QBluetoothDeviceInfo,
    QBluetoothLocalDevice, QBluetoothServiceDiscoveryAgent, QBluetoothServiceInfo,
    QBluetoothSocket
)
from multiprocessing import Queue


class Bluetooth(QObject):
    deviceFound = Signal(str, QColor)  # Emits device label and color based on pairing status
    scanFinished = Signal()
    connectionStatus = Signal(str)
    dataReceived = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.local_device = QBluetoothLocalDevice()
        self.device_agent = QBluetoothDeviceDiscoveryAgent()
        self.service_agent = None
        self.socket = None
        self.current_service_info = None
        self.devices = {}  # {address_str: QBluetoothDeviceInfo}
        self.raw_queue = Queue()

        self.device_agent.deviceDiscovered.connect(self._on_device_discovered)
        #self.device_agent.finished.connect(lambda: self.scanFinished.emit())
        self.device_agent.finished.connect(
            lambda: self.connectionStatus.emit("Scan Finished"))

    def scan(self):
        self.devices.clear()
        self.device_agent.start()

    @Slot(QBluetoothDeviceInfo)
    def _on_device_discovered(self, info: QBluetoothDeviceInfo):
        address = info.address().toString()
        name = info.name() or "(unknown)"
        label = f"{address} {name}"
        self.devices[address] = info
        pairing = self.local_device.pairingStatus(info.address())
        color = QColor(Qt.green if pairing in (
            QBluetoothLocalDevice.Paired, QBluetoothLocalDevice.AuthorizedPaired) else Qt.black)
        self.deviceFound.emit(label, color)

    def discover_services(self, address_str: str):
        if address_str not in self.devices:
            self.connectionStatus.emit("Device not found")
            return

        local_device = QBluetoothLocalDevice()
        adapter_address = QBluetoothAddress(local_device.address())
        address = QBluetoothAddress(address_str)
        self.service_agent = QBluetoothServiceDiscoveryAgent(adapter_address)
        self.service_agent.setRemoteAddress(address)
        self.service_agent.serviceDiscovered.connect(self._on_service_discovered)
        self.service_agent.finished.connect(self._on_service_discovery_finished)
        self.service_agent.start()
        self.connectionStatus.emit(f"Searching services on {address_str}...")

    @Slot(QBluetoothServiceInfo)
    def _on_service_discovered(self, info: QBluetoothServiceInfo):
        if info.serviceName():
            self.current_service_info = info
            print('hiii', info.serviceName())

    @Slot()
    def _on_service_discovery_finished(self):
        if not self.current_service_info:
            self.connectionStatus.emit("No valid service found")
            return

        self.socket = QBluetoothSocket(QBluetoothServiceInfo.RfcommProtocol)
        self.socket.connected.connect(lambda: self.connectionStatus.emit("Connected"))
        self.socket.readyRead.connect(self._read_socket_data)
        # self.socket.errorOccurred.connect(lambda err: self.connectionStatus.emit(
        #     f"Socket error: {self.socket.errorString()}"))
        self.socket.errorOccurred.connect(lambda err: print(f"Socket error: {self.socket.errorString()}"))

        self.socket.connectToService(self.current_service_info)

    @Slot()
    def _read_socket_data(self):
        set_ = True
        while self.socket and self.socket.canReadLine():
            try:
                if set_:
                    while True:
                        q = self.socket.read(1)
                        if not q:
                            return  # No data, exit or wait for next readyRead signal
                        if q[0] == b'U':  # sync byte found
                            set_ = False
                            break
                packet = self.socket.read(11)
                if len(packet) > 10:
                    self.raw_queue.put(packet.data())
                else:
                    print("Incomplete packet, resetting sync...")
                    set_ = True  # always reset to look for sync again

            except Exception as e:
                print(f"Socket Read Error: {e}")
                set_ = True  # Reset sync on error

    def disconnect(self):
        if self.socket:
            self.socket.disconnectFromService()
            self.socket.deleteLater()
            self.socket = None
            self.connectionStatus.emit("Disconnected")

    def connect(self, address_str: str):
        self.discover_services(address_str)