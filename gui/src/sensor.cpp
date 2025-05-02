#include "sensor.h"
#include "ui_sensor.h"
#include "mainwindow.h"
#include "serial/witmotion/witmotion.h"
#include "serial/datatypes.h"

#include <QNetworkInterface>
#include <QUrl>

Sensor::Sensor(MainWindow* mainWindowPtr, QWidget *parent)
    : QWidget{parent}
    , ui(new Ui::Sensor)
    , mainWindow(mainWindowPtr)
{
    ui->setupUi(this);

    // Set Ports info
    ui->gpsSerial->addItem("None");
    ui->imuSerial->addItem("None");
    ui->ethernetPort->addItem("None");
    ui->gpsType->addItem("None");
    ui->imuType->addItem("None");

    ui->gpsType->addItem("2BPro");
    ui->gpsType->addItem("Fusion");
    ui->imuType->addItem("Microstrain CV7");
    ui->imuType->addItem("WitMotion");

    for (const QSerialPortInfo &serialPortInfo : QSerialPortInfo::availablePorts()) {
        ui->gpsSerial->addItem(serialPortInfo.portName());
    }

    for (const QSerialPortInfo &serialPortInfo : QSerialPortInfo::availablePorts()) {
        ui->imuSerial->addItem(serialPortInfo.portName());
    }

    for (const QNetworkInterface &interface : QNetworkInterface::allInterfaces()) {
        if (interface.flags().testFlag(QNetworkInterface::IsUp) &&
            interface.flags().testFlag(QNetworkInterface::IsRunning) &&
            !interface.flags().testFlag(QNetworkInterface::IsLoopBack)) {
            ui->ethernetPort->addItem(interface.humanReadableName());
        }
    }

}

Sensor::~Sensor()
{
    delete ui;
}

void Sensor::on_next_clicked()
{
    ui->stackedDisplay->setCurrentIndex(1);
}

void Sensor::on_prev_clicked()
{
    ui->stackedDisplay->setCurrentIndex(0);
}


void Sensor::on_btnPandarView_clicked()
{
    QProcess pandarviewProcess;
    pandarviewProcess.setWorkingDirectory(mainWindow->pandarview_path);  // set to /home/krupal/Downloads/PandarView2
    qDebug() << mainWindow->password;
    QString command = QString("echo '%1' | sudo -S bash PandarView.sh").arg(mainWindow->password);
    pandarviewProcess.start("bash", QStringList() << "-c" << command);

    if (!pandarviewProcess.waitForStarted())
        qDebug() << "Failed to start the script.";

    if (!pandarviewProcess.waitForFinished())
        qDebug() << "Script didn't finish properly.";

    QString output = pandarviewProcess.readAllStandardOutput();
    QString error = pandarviewProcess.readAllStandardError();
    qDebug() << "Output:" << output;
    qDebug() << "Error:" << error;
}


void Sensor::on_btnLidarStatus_clicked()
{
    QDesktopServices::openUrl(QUrl("http://192.168.1.201"));
}


void Sensor::on_btnPtpd_clicked()
{
    QString ethernetPort = ui->ethernetPort->currentText();

    if (ethernetPort == "None" || ethernetPort.isEmpty()) {
        qDebug() << "Ethernet port not selected.";
        return;
    }

    // Check if ptpd is already running
    QProcess checkProcess;
    checkProcess.start("pgrep", QStringList() << "ptpd");
    checkProcess.waitForFinished();

    QString output = checkProcess.readAllStandardOutput();
    if (!output.trimmed().isEmpty()) {
        qDebug() << "ptpd is already running.";
        ui->btnPtpd->setEnabled(false);
        return;
    }

    // Start ptpd
    QString command = QString("echo '%1' | sudo -S ptpd -M -i %1").arg(mainWindow->password, ethernetPort);
    QProcess::startDetached("/bin/bash", QStringList() << "-c" << command);
    ui->btnPtpd->setEnabled(false);
}


void Sensor::on_btnIPV4_clicked()
{
    QString ethernetPort = ui->ethernetPort->currentText();

    if (ethernetPort == "None" || ethernetPort.isEmpty()) {
        qDebug() << "Ethernet port not selected.";
        return;
    }

    // Check if ifconfig is installed
    QProcess checkIfconfig;
    checkIfconfig.start("which", QStringList() << "ifconfig");
    checkIfconfig.waitForFinished();

    QString path = checkIfconfig.readAllStandardOutput().trimmed();
    if (path.isEmpty()) {
        qDebug() << "ifconfig not installed.";
        return;
    }

    QString command = QString("sudo ifconfig %1 192.168.1.100").arg(ethernetPort);
    QProcess::startDetached("/bin/bash", QStringList() << "-c" << command);
}


void Sensor::on_recordingFolderbtn_clicked()
{
    QDesktopServices::openUrl(mainWindow->recording_path);
}

void Sensor::displayIMUData(IMUData data) const{
    ui->systemTimeIMU->setPlainText(data.getAsString("system_time"));
    ui->TimeIMU->setPlainText(data.getAsString("timestamp"));
    ui->AccX->setPlainText(data.getAsString("accX"));
    ui->AccY->setPlainText(data.getAsString("accY"));
    ui->AccZ->setPlainText(data.getAsString("accZ"));
    ui->gyroX->setPlainText(data.getAsString("gyroX"));
    ui->gyroY->setPlainText(data.getAsString("gyroY"));
    ui->gyroZ->setPlainText(data.getAsString("gyroZ"));
    ui->roll->setPlainText(data.getAsString("roll"));
    ui->pitch->setPlainText(data.getAsString("pitch"));
    ui->yaw->setPlainText(data.getAsString("yaw"));
    ui->quatX->setPlainText(data.getAsString("qX"));
    ui->quatY->setPlainText(data.getAsString("qY"));
    ui->quatZ->setPlainText(data.getAsString("qZ"));
    ui->quatW->setPlainText(data.getAsString("qW"));
}


void Sensor::on_serialConnectionButton_clicked()
{
    QString gpsport = ui->gpsSerial->currentText();
    int gpsbaud = ui->baudGPS->currentText().toInt();
    QString gpstype = ui->gpsType->currentText();

    QString imuport = ui->imuSerial->currentText();
    int imubaud = ui->baudIMU->currentText().toInt();
    QString imutype = ui->imuType->currentText();

    bool save = ui->saveButton->isChecked();
    bool gps = false, imu = false;

    if (gpsport != "None" and gpstype != "None" and gpsbaud != 0){
        gps = true;
        if (gpstype == "Fusion"){

        }
        else if (gpstype == "2BPro"){

        } else {
            qDebug() << "Gps Type not found";
            gps = false;
        }
    }

    if (imuport != "None" and imutype != "None" and imubaud != 0){
        imu = true;
        if (imutype == "WitMotion") {
            imuport = "/dev/" + imuport;

            wit = new WitMotion(imuport, imubaud, save, mainWindow->recording_path, nullptr);

            QThread *imuthread = new QThread(this);
            wit->moveToThread(imuthread);

            connect(imuthread, &QThread::started, wit, &WitMotion::startReading);
            connect(wit, &WitMotion::finished, imuthread, &QThread::quit);
            connect(imuthread, &QThread::finished, wit, &WitMotion::deleteLater);
            connect(imuthread, &QThread::finished, imuthread, &QThread::deleteLater);
            connect(wit, &WitMotion::newData, this, &::Sensor::displayIMUData);

            imuthread->start();
        }

        else if (imutype == "Microstrain CV7"){

        } else {
            qDebug() << "IMU Type not found";
            imu = false;
        }
    }

    if (gps || imu){
        ui->serialConnectionButton->setEnabled(false);
        ui->serialTerminationButton->setEnabled(true);
    }


}


void Sensor::on_serialTerminationButton_clicked()
{
    ui->serialConnectionButton->setEnabled(true);
    ui->serialTerminationButton->setEnabled(false);

    if (imuthread && imuthread->isRunning()) {
        // Gracefully stop the WitMotion object
        QMetaObject::invokeMethod(wit, "stop", Qt::QueuedConnection);

        // Wait for the thread to quit after 'stop' emits 'finished'
        if (!imuthread->wait(3000)) {  // Wait up to 3 seconds
            qWarning() << "IMU thread did not finish in time, forcing termination";
            imuthread->requestInterruption();
            imuthread->terminate();  // only if absolutely necessary
            imuthread->wait();
        }

        wit = nullptr;
        imuthread = nullptr;
    }
}

