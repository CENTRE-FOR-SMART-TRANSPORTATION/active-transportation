#pragma once

#include <QThread>
#include <QSerialPort>
#include <QMutex>

class SerialThread : public QThread {
    Q_OBJECT

public:
    explicit SerialThread(QObject *parent = nullptr);
    virtual ~SerialThread();

    void startSerialDataThread(const QString &port, qint32 baud);
    void stopSerialThread();
    void write(const QByteArray &data);

protected:
    virtual void handleLine(const QString &line) = 0;
    void run() override;

private:
    QString m_port;
    qint32 m_baud;
    bool m_stop;
    QSerialPort serial_;
    QMutex m_mutex;

    bool getStopFlag();
    void setStopFlag(bool state);
};
