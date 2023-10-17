# -*- coding: utf-8 -*-
"""
Created on Oct 2022

@author: jonathan based on qchat
"""
from PyQt5 import QtCore, QtWidgets, uic, QtGui
import os

from .figure import FigureManager
from .data import DataManager
from .thread import ThreadManager
from .treewidgets import TreeWidgetItemModule

from ... import devices
from ... import config


class MyQTreeWidget(QtWidgets.QTreeWidget):

    reorderSignal = QtCore.pyqtSignal(object)

    def __init__(self,parent, plotter):
        self.plotter = plotter
        QtWidgets.QTreeWidget.__init__(self,parent)

        self.setAcceptDrops(True)

    def dropEvent(self, event):

        """ This function is used to add a plugin to the plotter """

        variable = event.source().last_drag
        if type(variable) == str:
            self.plotter.addPlugin(variable)
        self.setGraphicsEffect(None)

    def dragEnterEvent(self, event):

        if (event.source() is self) or (
                hasattr(event.source(), "last_drag") and type(event.source().last_drag) is str):
            event.accept()
            shadow = QtWidgets.QGraphicsDropShadowEffect(blurRadius=25, xOffset=3, yOffset=3)
            self.setGraphicsEffect(shadow)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setGraphicsEffect(None)


class Plotter(QtWidgets.QMainWindow):

    def __init__(self,mainGui):

        self.active = False
        self.mainGui = mainGui
        self.all_plugin_dict = dict()
        self.active_plugin_dict = dict()

        # Configuration of the window
        QtWidgets.QMainWindow.__init__(self)
        ui_path = os.path.join(os.path.dirname(__file__),'interface.ui')
        uic.loadUi(ui_path,self)
        self.setWindowTitle("AUTOLAB Plotter")

        # Loading of the different centers
        self.figureManager = FigureManager(self)
        self.dataManager = DataManager(self)

        self.threadManager = ThreadManager(self)
        self.threadModuleDict = {}
        self.threadItemDict = {}

        # Save button
        self.save_pushButton.clicked.connect(self.dataManager.saveButtonClicked)
        self.save_pushButton.setEnabled(False)

        # Clear button
        self.clear_pushButton.clicked.connect(self.dataManager.clear)
        self.clear_all_pushButton.clicked.connect(self.dataManager.clear_all)
        self.clear_pushButton.setEnabled(False)
        self.clear_all_pushButton.setEnabled(False)

        # Open button
        self.openButton.clicked.connect(self.dataManager.importActionClicked)

        # comboBox with data id
        self.data_comboBox.activated['QString'].connect(self.dataManager.data_comboBoxClicked)

        # Number of traces
        self.nbTraces_lineEdit.setText(f'{self.figureManager.nbtraces:g}')
        self.nbTraces_lineEdit.returnPressed.connect(self.nbTracesChanged)
        self.nbTraces_lineEdit.textEdited.connect(lambda : self.setLineEditBackground(self.nbTraces_lineEdit,'edited'))
        self.setLineEditBackground(self.nbTraces_lineEdit,'synced')

        for axe in ['x','y'] :
            getattr(self,f'logScale_{axe}_checkBox').stateChanged.connect(lambda b, axe=axe:self.logScaleChanged(axe))
            getattr(self,f'variable_{axe}_comboBox').currentIndexChanged.connect(self.variableChanged)
            getattr(self,f'autoscale_{axe}_checkBox').stateChanged.connect(lambda b, axe=axe:self.figureManager.autoscaleChanged(axe))
            getattr(self,f'autoscale_{axe}_checkBox').setChecked(True)

        self.device_lineEdit.setText(f'{self.dataManager.deviceValue}')
        self.device_lineEdit.returnPressed.connect(self.deviceChanged)
        self.device_lineEdit.textEdited.connect(lambda : self.setLineEditBackground(self.device_lineEdit,'edited'))
        self.setLineEditBackground(self.device_lineEdit,'synced')

        # Plot button
        self.plotDataButton.clicked.connect(self.refreshPlotData)

        # Timer
        self.timer_time = 0.5  # This plotter is not meant for fast plotting like the monitor, be aware it may crash with too high refreshing rate
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(int(self.timer_time*1000)) # ms
        self.timer.timeout.connect(self.autoRefreshPlotData)

        self.auto_plotDataButton.clicked.connect(self.autoRefreshChanged)
        self.overwriteDataButton.clicked.connect(self.overwriteDataChanged)

        # Delay
        self.delay_lineEdit.setText(str(self.timer_time))
        self.delay_lineEdit.returnPressed.connect(self.delayChanged)
        self.delay_lineEdit.textEdited.connect(lambda : self.setLineEditBackground(self.delay_lineEdit,'edited'))
        self.setLineEditBackground(self.delay_lineEdit,'synced')

        self.setAcceptDrops(True)

        self.processPlugin()

        timerPlugin = QtCore.QTimer(self)
        timerPlugin.setInterval(50) # ms
        timerPlugin.timeout.connect(self.timerAction)
        timerPlugin.start()

    def timerAction(self):

        """ This function checks if a module has been loaded and put to the queue. If so, associate item and module """

        threadItemDictTemp = self.threadItemDict.copy()
        threadModuleDictTemp = self.threadModuleDict.copy()

        for item_id in threadModuleDictTemp.keys():

            item = threadItemDictTemp[item_id]
            module = threadModuleDictTemp[item_id]

            self.associate(item, module)
            item.setExpanded(True)

            self.threadItemDict.pop(item_id)
            self.threadModuleDict.pop(item_id)

    def itemClicked(self,item):

        """ Function called when a normal click has been detected in the tree.
            Check the association if it is a main item """

        if item.parent() is None and item.loaded is False and id(item) not in self.threadItemDict.keys():
            self.threadManager.start(item,'load')  # load device and add it to queue for timer to associate it later (doesn't block gui while device is openning)

    def rightClick(self,position):

        """ Function called when a right click has been detected in the tree """

        item = self.tree.itemAt(position)
        if hasattr(item,'menu') :
            item.menu(position)

    def processPlugin(self):

        # Create frame
        self.frame = QtWidgets.QFrame()
        self.splitter_2.insertWidget(1, self.frame)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        layout = QtWidgets.QVBoxLayout(self.frame)

        label = QtWidgets.QLabel('Plugin:',self.frame)
        layout.addWidget(label)
        font = QtGui.QFont()
        font.setBold(True)
        label.setFont(font)

        # Tree widget configuration
        self.tree = MyQTreeWidget(self.frame, self)
        layout.addWidget(self.tree)
        self.tree.setHeaderLabels(['Plugin','Type','Actions','Values',''])
        self.tree.header().setDefaultAlignment(QtCore.Qt.AlignCenter)
        self.tree.header().resizeSection(0, 170)
        self.tree.header().hideSection(1)
        self.tree.header().resizeSection(2, 50)
        self.tree.header().resizeSection(3, 70)
        self.tree.header().resizeSection(4, 15)
        self.tree.header().setStretchLastSection(False)
        self.tree.setAlternatingRowColors(True)

        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.itemClicked.connect(self.itemClicked)
        self.tree.customContextMenuRequested.connect(self.rightClick)

        plotter_config = config.load_config("plotter")

        if 'plugin' in plotter_config.sections() and len(plotter_config['plugin']) != 0:
            self.splitter_2.setSizes([200,300,80,80])
            for plugin_nickname in plotter_config['plugin'].keys() :
                plugin_name = plotter_config['plugin'][plugin_nickname]
                self.addPlugin(plugin_name, plugin_nickname)
        else:
            self.splitter.setSizes([400,40])
            self.splitter_2.setSizes([200,80,80,80])


    def addPlugin(self, plugin_name, plugin_nickname=None):

        if plugin_nickname is None:
            plugin_nickname = plugin_name

        if plugin_name in devices.list_devices():
            plugin_nickname = self.getUniqueName(plugin_nickname)
            item = TreeWidgetItemModule(self.tree,plugin_name,plugin_nickname,self)
            item.setBackground(0, QtGui.QColor('#9EB7F5'))  # blue

            self.itemClicked(item)
        else:
            self.statusBar.showMessage(f"Error: plugin {plugin_name} not found in devices_config.ini",5000)

    def associate(self, item, module):

        plugin_nickname = item.nickname
        item.load(module)
        self.active_plugin_dict[plugin_nickname] = module
        self.all_plugin_dict[plugin_nickname] = module

        try:
            data = self.dataManager.getLastSelectedDataset().data
            data = data[[self.figureManager.getLabel("x"),self.figureManager.getLabel("y")]].copy()
            module.instance.refresh(data)
        except Exception:
            pass

    def getUniqueName(self,basename):
        """ This function adds a number next to basename in case this basename is already taken """
        names = self.all_plugin_dict.keys()
        name = basename

        compt = 0
        while True :
            if name in names :
                compt += 1
                name = basename+'_'+str(compt)
            else :
                break
        return name

    def dropEvent(self, event):
        """ Import data from filenames dropped """
        filenames = [e.toLocalFile() for e in event.mimeData().urls()]
        self.dataManager.importAction(filenames)

        qwidget_children = self.findChildren(QtWidgets.QWidget)
        for widget in qwidget_children:
            widget.setGraphicsEffect(None)

    def dragEnterEvent(self, event):
        """ Check that drop filenames """
        # only accept if there is at least one filename in the dropped filenames -> refuse folders
        if event.mimeData().hasUrls() and any([os.path.isfile(e.toLocalFile()) for e in event.mimeData().urls()]):
            event.accept()

            qwidget_children = self.findChildren(QtWidgets.QWidget)
            for widget in qwidget_children:
                shadow = QtWidgets.QGraphicsColorizeEffect()
                shadow.setColor(QtGui.QColor(20,20,20))
                shadow.setStrength(1)
                widget.setGraphicsEffect(shadow)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        qwidget_children = self.findChildren(QtWidgets.QWidget)
        for widget in qwidget_children:
            widget.setGraphicsEffect(None)

    def plugin_refresh(self):
        if self.active_plugin_dict:
            self.clearStatusBar()
            if hasattr(self.dataManager.getLastSelectedDataset(),"data"):
                data = self.dataManager.getLastSelectedDataset().data
                data = data[[self.figureManager.getLabel("x"),self.figureManager.getLabel("y")]].copy()
            else:
                data = None

            for module in self.active_plugin_dict.values():
                if hasattr(module.instance, "refresh"):
                    try:
                        module.instance.refresh(data)
                    except Exception as error:
                        self.statusBar.showMessage(f"Error in plugin {module.name}: '{error}'",5000)

    def overwriteDataChanged(self):
        """ Set overwrite name for data import """

        self.dataManager.setOverwriteData(self.overwriteDataButton.isChecked())

    def autoRefreshChanged(self):
        """ Set if auto refresh call for device data """

        if self.auto_plotDataButton.isChecked():
            self.timer.start()
        else:
            self.timer.stop()

    def autoRefreshPlotData(self):
        """ Function that refresh plot every timer interval """
        # OPTIMIZE: timer should not call a heavy function, idealy just take data to plot
        self.refreshPlotData()

    def refreshPlotData(self):
        """ This function get the last dataset data and display it onto the Plotter GUI """

        deviceValue = self.dataManager.getDeviceValue()

        try:
            deviceVariable = self.dataManager.getDeviceName(deviceValue)
            dataset = self.dataManager.importDeviceData(deviceVariable)
            data_name = dataset.name
            self.figureManager.start(dataset)
            self.statusBar.showMessage(f"Display the data: '{data_name}'",5000)
        except Exception as error:
            self.statusBar.showMessage(f"Can't refresh data: {error}",10000)

    def deviceChanged(self):
        """ This function start the update of the target value in the data manager
        when a changed has been detected """

        # Send the new value
        try:
            value = str(self.device_lineEdit.text())
            self.dataManager.setDeviceValue(value)
        except Exception as er:
            self.statusBar.showMessage(f"ERROR Can't change device variable: {er}", 10000)
        else:
            # Rewrite the GUI with the current value
            self.updateDeviceValueGui()

    def updateDeviceValueGui(self):
        """ This function ask the current value of the target value in the data
        manager, and then update the GUI """

        value = self.dataManager.getDeviceValue()
        self.device_lineEdit.setText(f'{value}')
        self.setLineEditBackground(self.device_lineEdit,'synced')

    def logScaleChanged(self,axe):
        """ This function is called when the log scale state is changed in the GUI. """

        state = getattr(self,f'logScale_{axe}_checkBox').isChecked()
        self.figureManager.setLogScale(axe,state)
        self.figureManager.redraw()

    def variableChanged(self,index):
        """ This function is called when the displayed result has been changed in
        the combo box. It proceeds to the change. """

        self.figureManager.clearData()

        if self.variable_x_comboBox.currentIndex() != -1 and self.variable_y_comboBox.currentIndex() != -1 :
            self.figureManager.reloadData()

    def nbTracesChanged(self):
        """ This function is called when the number of traces displayed has been changed
        in the GUI. It proceeds to the change and update the plot. """

        value = self.nbTraces_lineEdit.text()

        check = False
        try:
            value = int(float(value))
            assert value > 0
            self.figureManager.nbtraces = value
            check = True
        except:
            pass

        self.nbTraces_lineEdit.setText(f'{self.figureManager.nbtraces:g}')
        self.setLineEditBackground(self.nbTraces_lineEdit,'synced')

        if check is True and self.variable_y_comboBox.currentIndex() != -1 :
            self.figureManager.reloadData()


    def closeEvent(self,event):
        """ This function does some steps before the window is really killed """

        # Delete reference of this window in the control center
        self.timer.stop()
        self.mainGui.clearPlotter()


    def setLineEditBackground(self,obj,state):

        """ Function used to set the background color of a QLineEdit widget,
        based on its editing state """

        if state == 'synced' :
            color='#D2FFD2' # vert
        if state == 'edited' :
            color='#FFE5AE' # orange

        # if "QLineEdit".lower() in str(obj).lower():
        obj.setStyleSheet("QLineEdit:enabled {background-color: %s; font-size: 9pt}"%color)
        # elif "QSpinBox".lower() in str(obj).lower():
        #     obj.setStyleSheet("QSpinBox {background-color : %s}"%color)
        # else:
        #     print(str(obj), "Not implemented")

    def clearStatusBar(self):
        self.statusBar.showMessage('')


    def delayChanged(self):
        """ This function start the update of the delay in the thread manager
        when a changed has been detected """

        # Send the new value
        try :
            value = float(self.delay_lineEdit.text())
            assert value >= 0
            self.timer_time = value
        except :
            pass

        # Rewrite the GUI with the current value
        self.updateDelayGui()


    def updateDelayGui(self):
        """ This function ask the current value of the delay in the data
        manager, and then update the GUI """

        value = self.timer_time
        self.delay_lineEdit.setText(f'{value:g}')
        self.timer.setInterval(int(value*1000))  # ms
        self.setLineEditBackground(self.delay_lineEdit,'synced')


    def setStatus(self,message, timeout=0):

        """ Modify the message displayed in the status bar """

        self.statusBar.showMessage(message, msecs=timeout)


    def clearStatus(self):

        """ Erase the message displayed in the status bar """

        self.setStatus('')

def cleanString(name):

    """ This function clears the given name from special characters """

    for character in '*."/\[]:;|, ' :
        name = name.replace(character,'')
    return name
