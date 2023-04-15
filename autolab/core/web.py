# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 17:11:57 2019

@author: qchat
"""

import webbrowser
import socket
import os
import inspect


def report():
    webbrowser.open('https://github.com/qcha41/autolab/issues')

def doc(online="default"):
    """ By default try to open the online doc and if no internet connection, open the local pdf documentation.
    Can open online or offline documentation by using True or False."""

    if online == "default":
        if has_internet():
            webbrowser.open('https://autolab.readthedocs.io')
        else:
            doc_offline()
    elif online is True:
        webbrowser.open('https://autolab.readthedocs.io')
    elif online is False:
        doc_offline()

def doc_offline():
    dirname = os.path.dirname(os.path.abspath(inspect.stack()[0][1]))
    filename = os.path.join(dirname, "../autolab.pdf")
    if os.path.exists(filename):
        print("Openning local pdf documentation")
        os.startfile(filename)
    else:
        print("No local pdf documentation found at {filename}")

def has_internet():
    """ https://stackoverflow.com/questions/20913411/test-if-an-internet-connection-is-present-in-python#20913928 """
    try:
        # see if we can resolve the host name -- tells us if there is
        # a DNS listening
        host = socket.gethostbyname("one.one.one.one")
        # connect to the host -- tells us if the host is actually reachable
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except Exception:
        pass # we ignore any errors, returning False

    print("No internet connection found")
    return False
