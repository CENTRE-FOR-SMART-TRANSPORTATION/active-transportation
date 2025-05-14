# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QTabWidget, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1440, 920)
        MainWindow.setMinimumSize(QSize(0, 0))
        self.actionQuit = QAction(MainWindow)
        self.actionQuit.setObjectName(u"actionQuit")
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.actionPandarView_Path = QAction(MainWindow)
        self.actionPandarView_Path.setObjectName(u"actionPandarView_Path")
        self.actionRecording_Path = QAction(MainWindow)
        self.actionRecording_Path.setObjectName(u"actionRecording_Path")
        self.actionSet_Password = QAction(MainWindow)
        self.actionSet_Password.setObjectName(u"actionSet_Password")
        self.actionNTRIP_Configuration = QAction(MainWindow)
        self.actionNTRIP_Configuration.setObjectName(u"actionNTRIP_Configuration")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.tabWindow = QTabWidget(self.centralwidget)
        self.tabWindow.setObjectName(u"tabWindow")
        self.tabWindow.setGeometry(QRect(0, 0, 1440, 920))
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tabWindow.sizePolicy().hasHeightForWidth())
        self.tabWindow.setSizePolicy(sizePolicy)
        self.tabWindow.setMinimumSize(QSize(0, 0))
        self.tabWindow.setTabsClosable(True)
        self.tabWindow.setMovable(True)
        self.addSensor = QPushButton(self.centralwidget)
        self.addSensor.setObjectName(u"addSensor")
        self.addSensor.setGeometry(QRect(1330, 0, 105, 29))
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1440, 22))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuAbout = QMenu(self.menubar)
        self.menuAbout.setObjectName(u"menuAbout")
        self.menuSettings = QMenu(self.menubar)
        self.menuSettings.setObjectName(u"menuSettings")
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuAbout.menuAction())
        self.menuFile.addAction(self.actionQuit)
        self.menuAbout.addAction(self.actionAbout)
        self.menuSettings.addSeparator()
        self.menuSettings.addAction(self.actionPandarView_Path)
        self.menuSettings.addAction(self.actionRecording_Path)
        self.menuSettings.addAction(self.actionSet_Password)
        self.menuSettings.addAction(self.actionNTRIP_Configuration)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Starrtracker", None))
        self.actionQuit.setText(QCoreApplication.translate("MainWindow", u"Quit", None))
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.actionPandarView_Path.setText(QCoreApplication.translate("MainWindow", u"PandarView Path", None))
        self.actionRecording_Path.setText(QCoreApplication.translate("MainWindow", u"Recording Path", None))
        self.actionSet_Password.setText(QCoreApplication.translate("MainWindow", u"Set Password", None))
        self.actionNTRIP_Configuration.setText(QCoreApplication.translate("MainWindow", u"NTRIP Configuration", None))
        self.addSensor.setText(QCoreApplication.translate("MainWindow", u"Add Sensor", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuAbout.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
        self.menuSettings.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
    # retranslateUi

