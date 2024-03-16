# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 22:08:29 2019

@author: qchat
"""
import os
import sys
from collections import OrderedDict

from qtpy import QtWidgets, QtCore, uic, QtGui

from .config import ConfigManager
from .figure import FigureManager
from .parameter import ParameterManager
from .recipe import RecipeManager
from .scan import ScanManager
from .data import DataManager
from ..icons import icons
from ...config import get_GUI_config


class Scanner(QtWidgets.QMainWindow):

    def __init__(self, mainGui: QtWidgets.QMainWindow):

        self.mainGui = mainGui

        GUI_config = get_GUI_config()
        if GUI_config['font_size'] != 'default':
            self._font_size = int(GUI_config['font_size'])
        else:
            self._font_size = QtWidgets.QApplication.instance().font().pointSize()

        # Configuration of the window
        QtWidgets.QMainWindow.__init__(self)
        ui_path = os.path.join(os.path.dirname(__file__), 'interface.ui')
        uic.loadUi(ui_path, self)
        self.setWindowTitle("AUTOLAB Scanner")
        self.setWindowIcon(QtGui.QIcon(icons['scanner']))
        self.splitter.setSizes([500, 700])  # Set the width of the two main widgets
        self.setAcceptDrops(True)
        self.recipeDict = {}

        # Loading of the different centers
        self.figureManager = FigureManager(self)
        self.scanManager = ScanManager(self)
        self.dataManager = DataManager(self)
        self.configManager = ConfigManager(self)

        self.configManager.addRecipe("recipe")  # add one recipe by default
        self.configManager.undoClicked() # avoid false history
        self.setStatus("")
        self.addRecipe_pushButton.clicked.connect(lambda: self.configManager.addRecipe("recipe"))

        self.selectRecipe_comboBox.activated.connect(self._updateSelectParameter)

    def _addRecipe(self, recipe_name: str):
        """ Adds recipe to managers. Called by configManager """
        self._update_recipe_combobox()  # recreate all and display first index
        self.selectRecipe_comboBox.setCurrentIndex(self.selectRecipe_comboBox.count()-1)  # display last index

        self.recipeDict[recipe_name] = {}  # order of creation matter
        self.recipeDict[recipe_name]['recipeManager'] = RecipeManager(self, recipe_name)
        self.recipeDict[recipe_name]['parameterManager'] = OrderedDict()

        for parameter in self.configManager.parameterList(recipe_name):
            self._addParameter(recipe_name, parameter['name'])

    def _removeRecipe(self, recipe_name: str):  # order of creation matter
        """ Removes recipe from managers. Called by configManager and self """
        test = self.recipeDict.pop(recipe_name)
        test['recipeManager']._removeWidget()
        self._update_recipe_combobox()
        self._updateSelectParameter()

    def _activateRecipe(self, recipe_name: str, state: bool):
        """ Activates/Deactivates an existing recipe. Called by configManager and recipeManager """
        active = bool(state)
        self._update_recipe_combobox()
        self.recipeDict[recipe_name]['recipeManager']._activateTree(active)

    def _update_recipe_combobox(self):
        """ Shows recipe combobox if multi recipes else hide """
        prev_index = self.selectRecipe_comboBox.currentIndex()

        self.selectRecipe_comboBox.clear()
        self.selectRecipe_comboBox.addItems(self.configManager.recipeNameList())

        new_index = min(prev_index, self.selectRecipe_comboBox.count()-1)
        self.selectRecipe_comboBox.setCurrentIndex(new_index)

        dataSet_id = len(self.configManager.recipeNameList())
        if dataSet_id > 1:
            self.selectRecipe_comboBox.show()
        else:
            self.selectRecipe_comboBox.hide()

    def _clearRecipe(self):
        """ Clears recipes from managers. Called by configManager """
        for recipe_name in list(self.recipeDict.keys()):
            self._removeRecipe(recipe_name)

    def _addParameter(self, recipe_name: str, param_name: str):
        """ Adds parameter to managers. Called by configManager and self """
        new_ParameterManager = ParameterManager(self, recipe_name, param_name)
        self.recipeDict[recipe_name]['parameterManager'][param_name] = new_ParameterManager

        layoutAll = self.recipeDict[recipe_name]['recipeManager']._layoutAll
        layoutAll.insertWidget(len(layoutAll)-1, new_ParameterManager.mainFrame)

        self._updateSelectParameter()
        self.selectParameter_comboBox.setCurrentIndex(self.selectParameter_comboBox.count()-1)

    def _removeParameter(self, recipe_name: str, param_name: str):
        """ Removes parameter from managers. Called by configManager """
        test = self.recipeDict[recipe_name]['parameterManager'].pop(param_name)
        test._removeWidget()

        self._updateSelectParameter()

    def _updateSelectParameter(self):
        """ Updates selectParameter_comboBox. Called by configManager and self """
        recipe_name = self.selectRecipe_comboBox.currentText()

        prev_index = self.selectParameter_comboBox.currentIndex()
        if prev_index == -1: prev_index = 0

        self.selectParameter_comboBox.clear()
        if recipe_name != "":
            self.selectParameter_comboBox.addItems(self.configManager.parameterNameList(recipe_name))
            self.selectParameter_comboBox.setCurrentIndex(prev_index)

        if self.selectParameter_comboBox.currentText() == "":
            self.selectParameter_comboBox.setCurrentIndex(self.selectParameter_comboBox.count()-1)

        #Shows parameter combobox if multi parameters else hide
        if recipe_name != "" and len(self.configManager.parameterList(recipe_name)) > 1:
            self.selectParameter_comboBox.show()
        else:
            self.selectParameter_comboBox.hide()

    def dropEvent(self, event):
        """ Imports config file if event has url of a file """
        filename = event.mimeData().urls()[0].toLocalFile()
        self.configManager.import_configPars(filename)

        qwidget_children = self.findChildren(QtWidgets.QWidget)
        for widget in qwidget_children:
            widget.setGraphicsEffect(None)

    def dragEnterEvent(self, event):
        """ Only accept config file (url) """
        if event.mimeData().hasUrls():
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

    def closeEvent(self, event):
        """ Does some steps before the window is really killed """
        # Stop ongoing scan
        if self.scanManager.isStarted():
            self.scanManager.stop()

        # Stop datamanager timer
        self.dataManager.timer.stop()

        # Delete reference of this window in the control center
        self.mainGui.clearScanner()

        for recipe in self.recipeDict.values():
            for parameterManager in recipe['parameterManager'].values():
                parameterManager.close()

        self.figureManager.close()

        for children in self.findChildren(
                QtWidgets.QWidget, options=QtCore.Qt.FindDirectChildrenOnly):
            children.deleteLater()

        super().closeEvent(event)

    def setStatus(self, message: str, timeout: int = 0, stdout: bool = True):
        """ Modifies displayed message in status bar and adds error message to logger """
        self.statusBar.showMessage(message, timeout)
        if not stdout: print(message, file=sys.stderr)

    def setLineEditBackground(self, obj, state: str):
        """ Sets background color of a QLineEdit widget based on its editing state """
        if state == 'synced': color='#D2FFD2' # vert
        if state == 'edited': color='#FFE5AE' # orange

        obj.setStyleSheet(
            "QLineEdit:enabled {background-color: %s; font-size: %ipt}" % (
                color, self._font_size+1))
