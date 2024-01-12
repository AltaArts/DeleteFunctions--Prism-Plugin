# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.
####################################################
#
#           DeleteAction Plugin for Prism2
#
#                 Joshua Breckeen
#                    Alta Arts
#                josh@alta-arts.com
#
####################################################


import os
import ntpath
import subprocess
import json
import shutil
from datetime import datetime


try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_DeleteAction_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.pluginDir = os.path.dirname(os.path.dirname(__file__))
        self.settingsFile = os.path.join(self.pluginDir, "DeleteAction_Config.json")

        self.loadedPlugins = []
        self.delDirectory = None

        #   Callbacks                                           #   TODO    Doesn't seem to be a callback for the Project Chooser
        self.core.registerCallback("projectBrowserContextMenuRequested", self.projectBrowserContextMenuRequested, plugin=self)      

        self.core.registerCallback("openPBFileContextMenu", self.deleteSceneFile, plugin=self)




        # self.core.registerCallback("openPBShotDepartmentContextMenu", self.deleteSceneEntity, plugin=self)
        self.core.registerCallback("openPBShotTaskContextMenu", self.deleteShotTask, plugin=self)





        self.core.registerCallback("productSelectorContextMenuRequested", self.productSelectorContextMenuRequested, plugin=self)        
        # self.core.registerCallback("mediaPlayerContextMenuRequested", self.mediaPlayerContextMenuRequested, plugin=self)        
        # self.core.registerCallback("textureLibraryTextureContextMenuRequested", self.textureLibraryTextureContextMenuRequested, plugin=self)
        self.core.registerCallback("userSettings_loadUI", self.userSettings_loadUI, plugin=self)
        # self.core.registerCallback("onUserSettingsSave", self.onUserSettingsSave, plugin=self)


    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True


    #   Called with Callback
    @err_catcher(name=__name__)                                                         #   TODO MAKE ERROR CHECKING
    def userSettings_loadUI(self, origin):  # ADDING "Delete Action" TO USER SETTINGS

        self.getLoadedPlugins()

        # Create a Widget
        origin.w_deleteMenu = QWidget()
        origin.lo_deleteMenu = QVBoxLayout(origin.w_deleteMenu)

        # Add a new box for Delete Temp Directory
        self.gb_deleteDirectory = QGroupBox("Prism Delete Holding Directory")  # TODO: Better name
        self.lo_deleteDirectory = QVBoxLayout()

        # Add a grid layout for the top section
        self.lo_topSection = QGridLayout()

        # Create a read-only QLineEdit
        self.e_deleteDir = QLineEdit()
        self.e_deleteDir.setReadOnly(True)

        # Create a button with "..." on the right side
        self.but_fileDialogue = QPushButton("...")

        # Add widgets to the top section grid layout
        self.lo_topSection.addWidget(self.e_deleteDir, 0, 0)
        self.lo_topSection.addWidget(self.but_fileDialogue, 0, 1)

        # Add the top section grid layout to the QVBoxLayout
        self.lo_deleteDirectory.addLayout(self.lo_topSection)

        # Add a spacer to separate the top and bottom sections
        self.vertSpacer1 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.lo_deleteDirectory.addItem(self.vertSpacer1)

        # Add a box for "Number of Hours to keep files before permanent deletion"
        self.lo_hoursBox = QGridLayout()

        self.l_hours = QLabel("Number of Hours to keep files before permanent deletion")
        self.spb_hours = QSpinBox()
                                                                                            #   TODO   ADD TIP FOR NEVER DELETE

        self.hotzSpacer1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Add widgets to the hours box
        self.lo_hoursBox.addWidget(self.l_hours, 0, 0)
        self.lo_hoursBox.addWidget(self.spb_hours, 0, 1)
        self.lo_hoursBox.addItem(self.hotzSpacer1, 0, 2)

        # Add the hours box layout to the QVBoxLayout
        self.lo_deleteDirectory.addLayout(self.lo_hoursBox)

        # Add the table directly to the layout
        self.table_delItems = QTableWidget()
        self.table_delItems.setColumnCount(3)  # Set the number of columns
        self.table_delItems.setHorizontalHeaderLabels(["Project", "File", "Deleted"])  # Set column headers

        self.table_delItems.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Set column widths
        self.table_delItems.setColumnWidth(0, 200)  # Project column
        # self.table_delItems.setColumnWidth(1, -1)  # File column (stretch to fill)
        self.table_delItems.setColumnWidth(2, 150)  # Deleted column

        # Set column stretch
        self.table_delItems.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # File column (stretch to fill)

        # Set column alignments
        self.table_delItems.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)  # Project column (left-align)
        self.table_delItems.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)  # File column (center-align)
        self.table_delItems.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)  # Deleted column (right-align)

        self.lo_deleteDirectory.addWidget(self.table_delItems)

        # Add a box for buttons at the bottom
        self.lo_buttonBox = QHBoxLayout()

        # Create buttons
        self.but_openDir = QPushButton("Open in Explorer")
        self.but_refreshList = QPushButton("Resync List")
        self.but_undoLast = QPushButton("Undo Last Delete")
        self.but_purgeSelected = QPushButton("Purge Selected")
        self.but_purgeAll = QPushButton("Purge All")

        # Add buttons to the button box layout
        self.lo_buttonBox.addWidget(self.but_openDir)
        self.lo_buttonBox.addWidget(self.but_refreshList)
        self.lo_buttonBox.addWidget(self.but_undoLast)
        self.lo_buttonBox.addWidget(self.but_purgeSelected)
        self.lo_buttonBox.addWidget(self.but_purgeAll)

        # Add the button box layout to the QVBoxLayout
        self.lo_deleteDirectory.addLayout(self.lo_buttonBox)


        # Set the layout for the QGroupBox
        self.gb_deleteDirectory.setLayout(self.lo_deleteDirectory)

        # Add the QGroupBox to the main layout
        origin.lo_deleteMenu.addWidget(self.gb_deleteDirectory)

        # Add Tab to User Settings
        origin.addTab(origin.w_deleteMenu, "Delete Action")

        self.connections()
        self.loadSettings()


    @err_catcher(name=__name__)
    def connections(self):

        self.but_fileDialogue.clicked.connect(lambda: self.openExplorer(set=True))
        self.but_openDir.clicked.connect(lambda: self.openExplorer(set=False))
        self.but_refreshList.clicked.connect(lambda: self.refreshList())
        self.but_undoLast.clicked.connect(lambda: self.undoLast())
        self.but_purgeSelected.clicked.connect(lambda: self.purgeFiles(mode="single"))
        self.but_purgeAll.clicked.connect(lambda: self.purgeFiles(mode="all"))


    @err_catcher(name=__name__)
    def openExplorer(self, set=False):
        #   Gets default path for dialogue
        path = self.pluginDir

        #   Sets location to open Dialogue if exists        
        if self.e_deleteDir.text() != "":
            path = self.e_deleteDir.text()
  
        path = path.replace("/", "\\")

        #   If set True then opens selectable Dialogue
        if set == True:
            windowTitle = "Select Directory to hold Deleted Files"
            newDir = QFileDialog.getExistingDirectory(None, windowTitle, path)
            newDir = newDir.replace("/", "\\")
            self.delDirectory = newDir
            self.e_deleteDir.setText(self.delDirectory)
            self.saveSettings()

        #   If set not True, then just opens file explorer
        else:
            cmd = "explorer " + path
            subprocess.Popen(cmd)


    #   Check Loaded Plugins
    @err_catcher(name=__name__)
    def getLoadedPlugins(self):

        pluginNames = ["Standalone",
                       "Libraries",
                       "USD"
                       ]
        
        for plugin in pluginNames:
            pluginName = self.core.plugins.getPlugin(plugin)
            if pluginName is not None:
                self.loadedPlugins.append(plugin)


    #   Load Settings from json
    @err_catcher(name=__name__)
    def loadSettings(self):
        try:
            with open(self.settingsFile, "r") as json_file:
                data = json.load(json_file)
                self.delDirectory = data.get("Delete Directory")
                try:
                    self.e_deleteDir.setText(self.delDirectory)
                except:
                    pass

                # Check if "Items" key exists in the loaded data
                if "Items" in data:
                    self.delFileInfoList = data["Items"]
                    try:
                        # Clear the existing rows in the table
                        self.table_delItems.setRowCount(0)

                        # Populate the table with data from self.delFileInfoList
                        for item in self.delFileInfoList:
                            rowPosition = self.table_delItems.rowCount()
                            self.table_delItems.insertRow(rowPosition)

                            # Assuming "Project", "File", and "Deleted" keys exist in each item
                            self.table_delItems.setItem(rowPosition, 0, QTableWidgetItem(item["Project"]))
                            self.table_delItems.setItem(rowPosition, 1, QTableWidgetItem(item["File"]))
                            self.table_delItems.setItem(rowPosition, 2, QTableWidgetItem(item["Deleted"]))
                    except:
                        pass

        except FileNotFoundError:
            # Create the settings file if it doesn't exist
            with open(self.settingsFile, "w") as json_file:
                json.dump({}, json_file)


    #   Save Settings to json
    @err_catcher(name=__name__)
    def saveSettings(self):

        # Save both dictionaries
        with open(self.settingsFile, "w") as json_file:
            json.dump({"Delete Directory": self.delDirectory,
                       "Items": self.delFileInfoList},
                       json_file,
                       indent=4
                       )



    #   Called with Callback - Project Browser
    @err_catcher(name=__name__)                                         #   TODO  There is no Callback for Project Browser RCL Menu
    def projectBrowserContextMenuRequested(self, origin, menu):

        pass


    #   Called with Callback - SceneFiles Browser
    @err_catcher(name=__name__)
    def deleteSceneFile(self, origin, rcmenu, filePath):
        self.menuContext = "Scene Files"
        fileData = None

        self.loadSettings()

        #   Retrieves File Info from Core
        try:
            fileData = self.core.getScenefileData(filePath)
            sourceDir, fileData["sourceFilename"] = ntpath.split(fileData["filename"])

        except Exception as e:
            msg = f"Error opening Config File {str(e)}"
            self.core.popup(msg)

        #   Retrieves File Info from Project Config
        try:
            pData = self.core.getConfig(config="project", dft=3)        
            projectName = pData["globals"]["project_name"]

        except Exception as e:
            msg = f"Error opening Config File {str(e)}"
            self.core.popup(msg)

        #   Adds Right Click Item
        if os.path.isfile(fileData["filename"]):

            #   Version to delete
            delItem = delItemName = fileData["version"]

            sendToAct = QAction("Delete Version", rcmenu)
            sendToAct.triggered.connect(lambda: self.deleteAction(delItem, delItemName, sourceDir, projectName))
            rcmenu.addAction(sendToAct)
            

    @err_catcher(name=__name__)
    def deleteShotTask(self, origin, rcmenu, pos):
        self.menuContext = "Scene Entity"
        fileData = None

        self.loadSettings()


        try:
            pData = self.core.getConfig(config="project", dft=3)        
            projectName = pData["globals"]["project_name"]

        except Exception as e:
            msg = f"Error opening Config File {str(e)}"
            self.core.popup(msg)


        entity = self.core.pb.sceneBrowser.getCurrentEntity()
        if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
            return

        curDep = self.core.pb.sceneBrowser.getCurrentDepartment()

        if curDep:
            deptPath = self.core.getEntityPath(entity=entity, step=curDep)
        else:
            return
        
        self.core.popup(f"entity:  {entity}")                                      #    TESTING

        delItemName = taskName = pos.data()
        delItem = os.path.join(deptPath, taskName)
        sourceDir = deptPath
        
        sendToAct = QAction(f"Delete Task: {taskName}", rcmenu)
        sendToAct.triggered.connect(lambda: self.deleteAction(delItem, delItemName, sourceDir, projectName))
        rcmenu.addAction(sendToAct)


    #   Called with Callback - Product Browser
    @err_catcher(name=__name__)
    def productSelectorContextMenuRequested(self, origin, viewUi, pos, rcmenu):
        version = origin.getCurrentVersion()
        if not version:
            return

        self.menuContext = "Product Files:"
        self.singleFileMode = True
        fileData = None

        try:
            #   Gets Source Path from Last Column
            row = viewUi.rowAt(pos.y())
            numCols = viewUi.columnCount()
            if row >= 0:
                sourcePath = viewUi.item(row, numCols - 1).text()

            #   Retrieves File Info        
            infoFolder = self.core.products.getVersionInfoPathFromProductFilepath(sourcePath)
            infoPath = self.core.getVersioninfoPath(infoFolder)
            fileData = self.core.getConfig(configPath=infoPath)

            fileData["sourcePath"] = sourcePath
            fileData["sourceDir"], fileData["sourceFilename"] = ntpath.split(sourcePath)
            fileData["extension"] = os.path.splitext(fileData["sourceFilename"])[1]

            #   Adds Right Click Item
            if os.path.exists(sourcePath):
                sendToAct = QAction("Export to Dir...", viewUi)
                sendToAct.triggered.connect(lambda: self.sendToDialogue())
                rcmenu.addAction(sendToAct)

            #   Sends File Info to get sorted
            self.loadCoreData(fileData)

        except:
            return



    @err_catcher(name=__name__)                             #   TODO MAKE SURE DIRS EXIST -- Maybe do not show the Delete option if not.
    def deleteAction(self, delItem, delItemName, sourceDir, projectName):

        currentTime = datetime.now()
        timestamp = currentTime.strftime("%m/%d/%y %H:%M")

        deleteList = []

        if self.menuContext == "Scene Files":
            for file in os.listdir(sourceDir):
                if delItem in file:
                    deleteList.append(file)

            questionText = f"Are you sure you want to Delete:\n\nVersion {delItem}"
            result = self.core.popupQuestion(questionText, title="Delete Files")

            if result == "Yes":
                for file in deleteList:
                    try:
                        sourceFilePath = os.path.join(sourceDir, file)
                        destFilePath = os.path.join(self.delDirectory, file)

                        # Create a dictionary for the current file
                        fileInfo = {
                            "Project": projectName,
                            "File": file,
                            "Deleted": timestamp
                            }
                        
                        self.delFileInfoList.append(fileInfo)

                        shutil.move(sourceFilePath, destFilePath)

                    except OSError as e:
                        self.core.popup(f"Unable to Delete files:  {e}")


        elif self.menuContext == "Scene Entity":
            deleteList.append(delItem)

            questionText = f"Are you sure you want to Delete:\n\nTask {delItemName}"
            result = self.core.popupQuestion(questionText, title="Delete Task")

            if result == "Yes":
                try:
                    sourcePath = delItem
                    destPath = self.delDirectory

                    # Create a dictionary for the current file
                    fileInfo = {
                        "Project": projectName,
                        "Task": delItem,
                        "Deleted": timestamp
                        }
                    
                    self.delFileInfoList.append(fileInfo)

                    shutil.move(delItem, self.delDirectory)

                except OSError as e:
                    self.core.popup(f"Unable to Delete files:  {e}")



        self.saveSettings()
        self.core.pb.refreshUI()





    @err_catcher(name=__name__)                             #   TODO MAKE SURE DIRS EXIST -- Maybe do not show the Delete option if not.
    def purgeFiles(self, mode=None):

        if mode == "all":
            questionText = f"Are you sure you want to Permanently Delete all Items?\n\nThis is not Reversable."
            result = self.core.popupQuestion(questionText, title="Permanently Delete Files")

            if result == "Yes":
                for fileName in os.listdir(self.delDirectory):
                    filePath = os.path.join(self.delDirectory, fileName)

                    if os.path.exists(filePath):
                        os.remove(filePath)

                self.delFileInfoList = []
                self.saveSettings()
            else:
                return

        elif mode == "single":
            questionText = f"Are you sure you want to Permanently Delete the Selected Items?\n\nThis is not Reversable."
            result = self.core.popupQuestion(questionText, title="Permanently Delete Files")

            if result == "Yes":
                # Deleting selected files in the table
                selectedRows = set(index.row() for index in self.table_delItems.selectionModel().selectedIndexes())

                for row in selectedRows:
                    fileName = self.table_delItems.item(row, 1).text()

                    # Remove the selected entry from the list of dictionaries
                    self.delFileInfoList = [item for item in self.delFileInfoList if item["File"] != fileName]

                    # Add your logic to delete the file or perform any other action
                    filePath = os.path.join(self.delDirectory, fileName)
                    if os.path.exists(filePath):
                        os.remove(filePath)

                self.saveSettings()
        else:
            return

        self.refreshList()


    @err_catcher(name=__name__)                 #   TODO    MAKE UNDO
    def undoLast(self):

        pass



    @err_catcher(name=__name__)                     #   TODO ENSURE SYNC BETWEEN DIR AND LIST
    def refreshList(self):

        self.table_delItems.clearContents()
        self.loadSettings()
        self.table_delItems.viewport().update()