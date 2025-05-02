#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QFileDialog>
#include <QInputDialog>
#include "sensor.h"

QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();
    static QString pandarview_path;
    static QString recording_path;
    static QString password;

    static void loadSettings();
    static void saveSettings();

private slots:
    void on_addSensor_clicked();
    void on_tabWindow_tabCloseRequested(int index);
    void on_actionQuit_triggered();
    void on_actionAbout_triggered();
    void on_actionPandarView_Path_triggered();

    void on_actionRecording_Path_triggered();

    void on_actionSet_Password_triggered();

private:
    Ui::MainWindow *ui;
};
#endif // MAINWINDOW_H
