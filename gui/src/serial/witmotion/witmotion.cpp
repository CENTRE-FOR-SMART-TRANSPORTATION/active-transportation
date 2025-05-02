#include "witmotion.h"
#include "../../thirdparty/witmotion/wit_c_sdk.h"
#include "../../thirdparty/witmotion/REG.h"
#include "../../thirdparty/witmotion/serial.h"
#include <QDateTime>
#include <QDebug>


static std::map<int, WitMotion*> g_instances;
static thread_local WitMotion *t_currentInstance = nullptr;

WitMotion::WitMotion(const QString &port, int baudRate, bool saveData, const QString &saveDir, QObject *parent)
    : QObject(parent), port_(port), baudRate_(baudRate), saveData_(saveData)
{
    QString filename =  saveDir + "/WitMotion_0.csv";
    int count = 0;
    while (QFile::exists(filename)) {
        filename =  saveDir + QString("/WitMotion_%1.csv").arg(count++);
    }
    savePath_ = filename;

    if (saveData_)
    {
        saveFile_.setFileName(savePath_);
        if (saveFile_.open(QIODevice::WriteOnly | QIODevice::Text))
        {
            stream_.setDevice(&saveFile_);
            stream_ << IMUData::fieldOrder().join(',') << "\n";
        }
        else
        {
            qWarning("Failed to open file for saving data.");
            saveData_ = false;
        }
    }

    g_instances[fd] = this;

}

WitMotion::~WitMotion()
{
    stop();
    if (saveFile_.isOpen())
        saveFile_.close();
}

void WitMotion::startReading()
{
    const char *dev = port_.toUtf8().constData();

    WitInit(WIT_PROTOCOL_NORMAL, 0x50);
    WitRegisterCallBack([](uint32_t uiReg, uint32_t uiRegNum) {
        WitMotion* instance = t_currentInstance;
        if (!instance) return;
        {
            IMUData temp;

            for (uint32_t i = 0; i < uiRegNum; ++i)
            {
                switch (uiReg)
                {
                case MS:
                {
                    int YY = sReg[YYMM] & 0xff;
                    int Mo = (sReg[YYMM] & 0xff00) >> 8;
                    int DD = sReg[DDHH] & 0xff;
                    int HH = (sReg[DDHH] & 0xff00) >> 8;
                    int Mi = sReg[MMSS] & 0xff;
                    int SS = (sReg[MMSS] & 0xff00) >> 8;
                    int Ms = sReg[MS];
                    QString timestamp = QString::asprintf("%02d-%02d-%02dT%02d:%02d:%02d.%03dZ",
                                                          YY, Mo, DD, HH, Mi, SS, Ms);
                    temp.set("timestamp", timestamp);
                    temp.set("system_time", QDateTime::currentDateTimeUtc().toString("yyyy-MM-ddTHH:mm:ss.zzzZ"));
                }
                break;

                case AZ:
                    for (int j = 0; j < 3; j++)
                        temp.set(QString("acc%1").arg(QChar('X' + j)),
                                 QString::number(sReg[AX + j] / 32768.0f * 16.0f, 'f', 4));
                    break;

                case GZ:
                    for (int j = 0; j < 3; j++)
                        temp.set(QString("gyro%1").arg(QChar('X' + j)),
                                 QString::number(sReg[GX + j] / 32768.0f * 2000.0f, 'f', 4));
                    break;

                case Yaw:
                    for (int j = 0; j < 3; j++)
                        temp.set(QStringList{"roll", "pitch", "yaw"}[j],
                                 QString::number(sReg[Roll + j] / 32768.0f * 180.0f, 'f', 4));
                    break;

                case q3:
                {
                    const char* axisLabels = "XYZW";
                    for (int j = 0; j < 4; j++) {
                        temp.set(QString("q%1").arg(axisLabels[j]),
                                 QString::number(sReg[q0 + j] / 32768.0f, 'f', 4));
                    }
                    break;
                }


                default:
                    break;
                }
                uiReg++;
            }

            {
                QMutexLocker lock(&instance->mutex_);
                instance->data_buffer_.push_back(temp);
            }


            QMetaObject::invokeMethod(instance, "processTempData", Qt::QueuedConnection);
        }
    });

    fd = serial_open(dev, baudRate_);
    if (fd < 0)
    {
        qWarning() << "Could not open" << dev << "with baud" << baudRate_;
        emit finished();
        return;
    }

    socketNotifier_ = new QSocketNotifier(fd, QSocketNotifier::Read, this);
    connect(socketNotifier_, &QSocketNotifier::activated, this, &WitMotion::handleSerialData);
}

void WitMotion::stop()
{
    if (socketNotifier_)
    {
        socketNotifier_->setEnabled(false);
        socketNotifier_->deleteLater();
        socketNotifier_ = nullptr;
    }

    if (fd >= 0)
    {
        serial_close(fd);
        fd = -1;
    }

    emit finished();
}

void WitMotion::handleSerialData()
{
    unsigned char c;
    while (serial_read_data(fd, &c, 1)) {
        t_currentInstance = this;  // Set the thread-local instance
        WitSerialDataIn(c);
    }
}

void WitMotion::processTempData()
{
    IMUData temp;
    {
        QMutexLocker lock(&mutex_);
        if (data_buffer_.empty())
            return;
        temp = data_buffer_.front();
        data_buffer_.pop_front();
    }

    lastData.add(temp);

    if (lastData.full())
    {
        emit newData(lastData);
        writeDataIfNeeded(lastData);
        lastData.clear();
    }
}

void WitMotion::writeDataIfNeeded(const IMUData &data)
{
    if (saveData_ && saveFile_.isOpen())
    {
        stream_ << data.toCSVRow() << "\n";
        stream_.flush();
    }
}
