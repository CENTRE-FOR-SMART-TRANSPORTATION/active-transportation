#ifndef SENSOR_H
#define SENSOR_H

#include "src/serial/witmotion/witmotion.h"
#include <QWidget>
#include <QSerialPort>
#include <QVariant>
#include <QtCore>
#include <QtGui>
#include <QtQuick>
#include <QSerialPortInfo>
#include <QMessageBox>
#include <QTextStream>
#include <QDebug>
#include <QQmlContext>
#include <QQuickWidget>

QT_BEGIN_NAMESPACE
namespace Ui { class Sensor; }
QT_END_NAMESPACE

class MainWindow;

class Sensor : public QWidget
{
    Q_OBJECT

    private slots:
        void on_prev_clicked();
        void on_next_clicked();
        void on_btnPandarView_clicked();
        void on_btnLidarStatus_clicked();
        void on_btnPtpd_clicked();
        void on_btnIPV4_clicked();
        void on_recordingFolderbtn_clicked();
        void on_serialConnectionButton_clicked();
        void on_serialTerminationButton_clicked();

    public:
        explicit Sensor(MainWindow* mainWindowPtr, QWidget *parent = nullptr);
        ~Sensor();

    private:
        WitMotion *wit;
        Ui::Sensor *ui;
        MainWindow *mainWindow;
        QThread* imuthread = new QThread;
        void displayIMUData(IMUData data) const;
};

#endif // SENSOR_H
