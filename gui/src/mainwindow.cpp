#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QSettings>
#include <QLineEdit>

QString MainWindow::pandarview_path = "/home/Downloads/PandarView2";
QString MainWindow::recording_path = "/home/Desktop/AT";
QString MainWindow::password = "";

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    MainWindow::loadSettings();

}

MainWindow::~MainWindow()
{
    delete ui;
}


void MainWindow::loadSettings() {
    QSettings settings("AT", "ATgui");
    pandarview_path = settings.value("pandarview_path", "/home/Downloads/PandarView2").toString();
    recording_path = settings.value("recording_path", "/home/Desktop/AT").toString();
    password = settings.value("password", "").toString();
}

void MainWindow::saveSettings() {
    QSettings settings("AT", "ATgui");
    settings.setValue("pandarview_path", pandarview_path);
    settings.setValue("recording_path", recording_path);
    settings.setValue("password", password);
}

void MainWindow::on_tabWindow_tabCloseRequested(int index)
{
    QMessageBox::StandardButton reply = QMessageBox::question(this, "Confirmation Close Tab", "Are you sure you want to close this tab");
    if (reply == QMessageBox::Yes){
        ui->tabWindow->removeTab(index);
    }
}

void MainWindow::on_addSensor_clicked()
{
    Sensor *sensorTab = new Sensor(this);
    ui->tabWindow->addTab(sensorTab, QString("GPS %0").arg(ui->tabWindow->count() + 1));
    ui->tabWindow->setCurrentIndex(ui->tabWindow->count() - 1);
}

void MainWindow::on_actionQuit_triggered()
{
    QCoreApplication::quit();
}


void MainWindow::on_actionAbout_triggered()
{
    QMessageBox::about(this, "Active Transportation Recording", "This is a GUI Program to record GPS and IMU data with ease.\n Currently running version 1.0.0.\n Credits: Krupal Shah, Jaspreet Singh Chhabra");
}


void MainWindow::on_actionPandarView_Path_triggered()
{
    QString dir = QFileDialog::getExistingDirectory(this, tr("Select PandarView Directory"));

    if (!dir.isEmpty()) {
        MainWindow::pandarview_path = dir;
        qDebug() << "PandarView path set to:" << pandarview_path;
        MainWindow::saveSettings();
    }
}



void MainWindow::on_actionRecording_Path_triggered()
{
    QString dir = QFileDialog::getExistingDirectory(this, tr("Select Recording Directory"));

    if (!dir.isEmpty()) {
        MainWindow::recording_path = dir;
        qDebug() << "Recording path set to:" << recording_path;
        MainWindow::saveSettings();
    }
}


void MainWindow::on_actionSet_Password_triggered()
{
    bool ok;
    QString password = QInputDialog::getText(
        this,
        "Authentication",
        "Enter your password:",
        QLineEdit::Password,
        "",
        &ok
        );

    if (ok && !password.isEmpty()) {
        qDebug() << "Password entered:" << password;
    } else {
        qDebug() << "Password input cancelled or empty.";
    }

    MainWindow::password = password;
    qDebug() << "Password entered:" << MainWindow::password;
    MainWindow::saveSettings();
}

