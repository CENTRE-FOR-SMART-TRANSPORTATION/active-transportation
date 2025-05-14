from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtBluetooth import (
    QBluetoothLocalDevice, QBluetoothDeviceDiscoveryAgent,
    QBluetoothDeviceInfo, QBluetoothAddress, QBluetoothSocket,
    QBluetoothServiceDiscoveryAgent, QBluetoothServiceInfo
)


class Bluetooth(QObject):
    dataReceived = Signal(str)
    connectionStatus = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.local_device = QBluetoothLocalDevice()
        self.discovery_agent = QBluetoothDeviceDiscoveryAgent()
        self.discovery_agent.deviceDiscovered.connect(
            self._on_device_discovered)
        self.discovery_agent.finished.connect(
            lambda: self.connectionStatus.emit("Scan Finished"))

        self.service_agent = None
        self.socket = None
        self.available_devices = {}  # {address: {'name': name, 'info': QBluetoothDeviceInfo}}

        self.connected_service_info = None

    def scan(self):
        self.available_devices.clear()
        self.discovery_agent.start()

    @Slot(QBluetoothDeviceInfo)
    def _on_device_discovered(self, info: QBluetoothDeviceInfo):
        address = info.address().toString()
        name = info.name()
        self.available_devices[address] = {'name': name, 'info': info}

    def connect(self, address_str: str):
        if address_str not in self.available_devices:
            self.connectionStatus.emit(f"Device {address_str} not found")
            return

        address = QBluetoothAddress(address_str)
        self.service_agent = QBluetoothServiceDiscoveryAgent(address)
        self.service_agent.serviceDiscovered.connect(
            self._on_service_discovered)
        self.service_agent.finished.connect(
            self._on_service_discovery_finished)
        self.service_agent.start()
        self.connectionStatus.emit(f"Searching services on {address_str}...")

    @Slot(QBluetoothServiceInfo)
    def _on_service_discovered(self, service_info: QBluetoothServiceInfo):
        if service_info.serviceName():  # Pick the first valid service
            self.connected_service_info = service_info

    @Slot()
    def _on_service_discovery_finished(self):
        if not self.connected_service_info:
            self.connectionStatus.emit("No valid service found")
            return

        self.socket = QBluetoothSocket(QBluetoothServiceInfo.RfcommProtocol)
        self.socket.connected.connect(
            lambda: self.connectionStatus.emit("Connected"))
        self.socket.readyRead.connect(self._read_socket_data)
        self.socket.errorOccurred.connect(lambda err: self.connectionStatus.emit(
            f"Socket error: {self.socket.errorString()}"))

        self.socket.connectToService(self.connected_service_info)

    @Slot()
    def _read_socket_data(self):
        while self.socket and self.socket.canReadLine():
            raw = self.socket.readLine().data()
            try:
                decoded = raw.decode("utf-8", errors="replace").strip()
                self.dataReceived.emit(decoded)
            except Exception as e:
                self.dataReceived.emit(f"Decode error: {e}")

    def disconnect(self):
        if self.socket:
            self.socket.disconnectFromService()
            self.socket.deleteLater()
            self.socket = None
            self.connectionStatus.emit("Disconnected")
