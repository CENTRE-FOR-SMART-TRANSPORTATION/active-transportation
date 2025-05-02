#ifndef WITMOTION_H
#define WITMOTION_H

#include "src/serial/datatypes.h"
#include <QObject>
#include <QTextStream>
#include <QFile>
#include <QSocketNotifier>
#include <QMutex>
#include <deque>


class WitMotion : public QObject
{
    Q_OBJECT

public:
    explicit WitMotion(const QString &port, int baudRate, bool saveData, const QString &saveDir, QObject *parent = nullptr);
    ~WitMotion();

public slots:
    void startReading();
    void stop();
    void handleSerialData();
    void processTempData();

signals:
    void newData(const IMUData &data);
    void finished();

private:
    QString port_;
    int baudRate_;
    bool saveData_;
    QString savePath_;
    QFile saveFile_;
    QTextStream stream_;

    int fd = -1;
    QSocketNotifier *socketNotifier_ = nullptr;

    std::deque<IMUData> data_buffer_;
    IMUData lastData;
    QMutex mutex_;

    void writeDataIfNeeded(const IMUData &data);
};

#endif // WITMOTION_H
