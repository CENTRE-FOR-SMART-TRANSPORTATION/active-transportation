#include "serialthread.h"
#include <QDebug>

SerialThread::SerialThread(QObject *parent) : QThread(parent), m_stop(false) {}

SerialThread::~SerialThread() {
    stopSerialThread();
}

void SerialThread::startSerialDataThread(const QString &port, qint32 baud) {
    m_port = port;
    m_baud = baud;
    m_stop = false;
    start();
}

void SerialThread::stopSerialThread() {
    setStopFlag(true);
    wait();
}

bool SerialThread::getStopFlag() {
    QMutexLocker locker(&m_mutex);
    return m_stop;
}

void SerialThread::setStopFlag(bool state) {
    QMutexLocker locker(&m_mutex);
    m_stop = state;
}

void SerialThread::write(const QByteArray &data) {
    if (serial_.isOpen())
        serial_.write(data);
}

void SerialThread::run() {
    serial_.setPortName(m_port);
    serial_.setBaudRate(m_baud);
    serial_.setDataBits(QSerialPort::Data8);
    serial_.setParity(QSerialPort::NoParity);
    serial_.setStopBits(QSerialPort::OneStop);
    serial_.setFlowControl(QSerialPort::NoFlowControl);

    if (!serial_.open(QIODevice::ReadWrite)) {
        qWarning() << "Failed to open serial port:" << m_port;
        return;
    }

    while (!getStopFlag()) {
        if (serial_.waitForReadyRead(100)) {
            while (serial_.canReadLine()) {
                QString line = QString::fromLocal8Bit(serial_.readLine()).trimmed();
                if (!line.isEmpty())
                    handleLine(line);
            }
        }
    }

    serial_.close();
}
