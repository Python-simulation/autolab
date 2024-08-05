# -*- coding: utf-8 -*-
"""
Created on Tue Mar 28 14:48:14 2017

@author: Quentin Chateiller
quentin.chateiller@c2n.upsaclay.fr


"""
#from threading import Event, Thread

#started = Event()

#def gui() :
#
#    if started.is_set():
#        print("Gui already running")
#    else :
#        t=AppThread()
#        t.start()


def gui():
    """ Open the Autolab GUI """
    _start('gui')


def plotter(var = None):
    """ Open the Autolab Plotter with optional variable capture """
    _start('plotter', var=var)


def monitor(var):
    """ Open the Autolab Monitor for variable var """
    _start('monitor', var=var)


def slider(var):
    """ Open a slider for variable var """
    _start('slider', var=var)


def add_device(name: str = ''):
    """ Open the utility to add a device or modify the given device name """
    _start('add_device', var=name)


def about():
    """ Open the about window """
    _start('about')


def variables_menu():
    """ Open the variables menu """
    _start('variables_menu')


def _start(gui: str, **kwargs):
    """ Open the Autolab GUI if gui='gui', the Plotter if gui='plotter'
    or the Monitor if gui='monitor' """

    import os
    from ..config import get_GUI_config
    GUI_config = get_GUI_config()
    if GUI_config['QT_API'] != 'default':
        os.environ['QT_API'] = str(GUI_config['QT_API'])
    try:
        import pyqtgraph as pg
        from qtpy import QtWidgets
    except ModuleNotFoundError as e:
        print(f"""Can't use GUI, package(s) missing: {e}
Need to install pyqtgraph, qtpy, and one of PyQt5, PySide2, PyQt6 or PySide6.

Using pip:
pip install pyqtgraph
pip install qtpy
pip install PyQt5
pip install PySide2
pip install PyQt6
pip install PySide6

Using anaconda:
conda install pyqtgraph
conda install qtpy
conda install pyqt
conda install -c conda-forge pyside2
no PyQt6 anaconda version available
conda install -c conda-forge pyside6
""")
    else:
        background = GUI_config['image_background']
        foreground = GUI_config['image_foreground']
        pg.setConfigOptions(background=background, foreground=foreground)
        pg.setConfigOption('imageAxisOrder', 'row-major')

        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])

        if GUI_config['font_size'] != 'default':
            font = app.font()
            font.setPointSize(int(GUI_config['font_size']))
            app.setFont(font)

        var = kwargs.get('var')

        if gui == 'gui':
            from .controlcenter.main import ControlCenter
            gui = ControlCenter()
            gui.initialize()
            gui.show()
        elif gui == 'plotter':
            from .GUI_instances import openPlotter
            openPlotter(variable=var)
        elif gui == 'monitor':
            from .GUI_instances import openMonitor
            openMonitor(var)
        elif gui == 'slider':
            from .GUI_instances import openSlider
            openSlider(var)
        elif gui == 'add_device':
            from .GUI_instances import openAddDevice
            openAddDevice(name=var)
        elif gui == 'about':
            from .GUI_instances import openAbout
            openAbout()
        elif gui == 'variables_menu':
            from .GUI_instances import openVariablesMenu
            openVariablesMenu()
        else:
            raise ValueError("gui accept either 'main', 'plotter', 'monitor'," \
                             "'slider, add_device', 'about' or 'variables_menu'" \
                             f". Given {gui}")

        app.exec()


#class AppThread(Thread):
#
#    def __init__(self):
#
#        Thread.__init__(self)
#
#    def run(self):
#
#        started.set()
#
#        _run()
#
#        started.clear()
#
