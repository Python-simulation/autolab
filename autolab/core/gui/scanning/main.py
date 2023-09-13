# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 22:08:29 2019

@author: qchat
"""
from PyQt5 import QtWidgets, uic
import os

from .config import ConfigManager
from .figure import FigureManager
from .parameter import ParameterManager
from .recipe import RecipeManager
from .scan import ScanManager
from .data import DataManager
from .scanrange import RangeManager

class Scanner(QtWidgets.QMainWindow):

    def __init__(self,mainGui):

        self.mainGui = mainGui

        # Configuration of the window
        QtWidgets.QMainWindow.__init__(self)
        ui_path = os.path.join(os.path.dirname(__file__),'interface.ui')
        uic.loadUi(ui_path,self)
        self.setWindowTitle(f"AUTOLAB Scanner")
        self.splitter.setSizes([500, 700])  # Set the width of the two main widgets
        # self.splitter_recipe.setSizes([80, 223, 80])  # set the height of the three recipe widgets

        # OPTIMIZE: temporary untill begin and end are functionnal
        self.splitter_recipe.setChildrenCollapsible(True)
        self.splitter_recipe.setSizes([0, 483, 0])  # set the height of the three recipe widgets

        # Loading of the different centers
        self.configManager = ConfigManager(self)
        self.figureManager = FigureManager(self)
        self.parameterManager = ParameterManager(self)
        self.recipeManager_begin = RecipeManager(self, self.tree_layout_begin)
        # self.recipeManager_begin.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.recipeManager = RecipeManager(self, self.tree_layout)
        self.recipeManager_end = RecipeManager(self, self.tree_layout_end)
        # self.recipeManager_end.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.scanManager = ScanManager(self)
        self.dataManager = DataManager(self)
        self.rangeManager = RangeManager(self)

        self.setAcceptDrops(True)

    def dropEvent(self, event):
        """ Set parameter if drop compatible variable onto scanner (excluding recipe area) """
        if hasattr(event.source(), "last_drag"):
            gui = event.source().gui
            variable = event.source().last_drag
            if variable and variable.parameter_allowed:
                gui.setScanParameter(variable)
        else:
            filename = event.mimeData().urls()[0].toLocalFile()
            self.configManager.import_configPars(filename)

    def dragEnterEvent(self, event):
        """ Only accept config file (url) and parameter from controlcenter """
        if event.mimeData().hasUrls() or (
                hasattr(event.source(), "last_drag") and (hasattr(event.source().last_drag, "parameter_allowed") and event.source().last_drag.parameter_allowed)):
            event.accept()
        else:
            event.ignore()

    def closeEvent(self,event):

        """ This function does some steps before the window is really killed """
        # Stop ongoing scan
        if self.scanManager.isStarted() :
            self.scanManager.stop()

        # Stop datamanager timer
        self.dataManager.timer.stop()

        # Delete reference of this window in the control center
        self.mainGui.clearScanner()



    def setLineEditBackground(self,obj,state):

        """ Function used to set the background color of a QLineEdit widget,
        based on its editing state """

        if state == 'synced' :
            color='#D2FFD2' # vert
        if state == 'edited' :
            color='#FFE5AE' # orange

        obj.setStyleSheet("QLineEdit:enabled {background-color: %s; font-size: 9pt}"%color)





def cleanString(name):

    """ This function clears the given name from special characters """

    for character in '*."/\[]:;|, ' :
        name = name.replace(character,'')
    return name
