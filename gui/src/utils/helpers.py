from PySide6.QtCore import QObject, Signal, QTimer


class Bridge(QObject):
    lastData = Signal(object)

    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll)
        self.timer.start(1000)  # adjust poll rate (ms) as needed

    def poll(self):
        while not self.queue.empty():
            data = self.queue.get()
            self.lastData.emit(data)
