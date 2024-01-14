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
#           DeleteFunctions Plugin for Prism2
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
import re
from datetime import datetime
import time


try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_DeleteFunctions_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.pluginDir = os.path.dirname(os.path.dirname(__file__))
        self.settingsFile = os.path.join(self.pluginDir, "DeleteFunctions_Config.json")

        self.loadedPlugins = []
        self.delDirectory = None
        self.deleteActive = False

        #   Callbacks                                           #   TODO    Doesn't seem to be a callback for the Project Chooser
        self.core.registerCallback("projectBrowserContextMenuRequested", self.projectBrowserContextMenuRequested, plugin=self)      

        self.core.registerCallback("openPBFileContextMenu", self.deleteSceneFile, plugin=self)


        self.core.registerCallback("openPBShotDepartmentContextMenu", self.deleteShotDepartment, plugin=self)
        self.core.registerCallback("openPBShotTaskContextMenu", self.deleteShotTask, plugin=self)

        self.core.registerCallback("openPBAssetDepartmentContextMenu", self.deleteAssetDepartment, plugin=self)
        self.core.registerCallback("openPBAssetTaskContextMenu", self.deleteAssetTask, plugin=self)



        self.core.registerCallback("productSelectorContextMenuRequested", self.productSelectorContextMenuRequested, plugin=self)        
        # self.core.registerCallback("mediaPlayerContextMenuRequested", self.mediaPlayerContextMenuRequested, plugin=self)        
        # self.core.registerCallback("textureLibraryTextureContextMenuRequested", self.textureLibraryTextureContextMenuRequested, plugin=self)
        self.core.registerCallback("userSettings_loadUI", self.userSettings_loadUI, plugin=self)
        self.core.registerCallback("onUserSettingsSave", self.saveSettings, plugin=self)


    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True


    #   Called with Callback
    @err_catcher(name=__name__)
    def userSettings_loadUI(self, origin):  # ADDING "Delete Functions" TO USER SETTINGS

        self.getLoadedPlugins()

        # Create a Widget
        origin.w_deleteMenu = QWidget()
        origin.lo_deleteMenu = QVBoxLayout(origin.w_deleteMenu)

        # Add a new box for Delete Temp Directory
        self.gb_deleteDirectory = QGroupBox()
        self.lo_deleteDirectory = QVBoxLayout()

        # Add a grid layout for the top section
        self.lo_useDeleteBox = QGridLayout()

        self.chb_usedelete = QCheckBox()
        self.chb_usedelete.setText("Enable Delete Functions")
        tip = ("Enables delete functions in right-click menus throughout the Project Browser\n"
            "Deleted items will be held in the Deleted Dir for the time period specified below."
            )
        self.chb_usedelete.setToolTip(tip)

        self.lo_useDeleteBox.addWidget(self.chb_usedelete, 0, 0)
        self.lo_deleteDirectory.addLayout(self.lo_useDeleteBox)

        # Add a spacer to separate the top and bottom sections
        self.vertSpacer1 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.lo_deleteDirectory.addItem(self.vertSpacer1)

        self.lo_deleteDir = QGridLayout()

        self.l_delDirText = QLabel("Directory for Deleted Items.")
        self.hotzSpacer0 = QSpacerItem(60, 20, QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Create a read-only QLineEdit
        self.e_deleteDir = QLineEdit()
        self.e_deleteDir.setReadOnly(True)
        tip = ("Directory to hold Deleted items.  If the Directory cannot be found,\n"
               "the Delete Functions will not be available."
            )
        self.e_deleteDir.setToolTip(tip)

        self.but_fileDialogue = QPushButton("...")
        tip = "Opens Directory Selection Dialogue."
        self.but_fileDialogue.setToolTip(tip)

        self.lo_deleteDir.addWidget(self.l_delDirText, 0, 0)
        self.lo_deleteDir.addItem(self.hotzSpacer0, 0, 1)
        self.lo_deleteDir.addWidget(self.e_deleteDir, 0, 2)
        self.lo_deleteDir.addWidget(self.but_fileDialogue, 0, 3)

        # Add the top section grid layout to the QVBoxLayout
        self.lo_deleteDirectory.addLayout(self.lo_deleteDir)

        # Add a box for "Number of Hours to keep files before permanent deletion"
        self.lo_hoursBox = QGridLayout()

        self.l_hours = QLabel("Hours to Keep Deleted Files before Purging")
        self.spb_hours = QSpinBox()
        tip = ("Time period in hours to keep the Deleted files in the Delete Dir\n"
               "before being automatically purged.\n"
               "\n"
               "Setting Zero will mean Deleted Files will be held indefinitly.")
        self.spb_hours.setToolTip(tip)

        self.hotzSpacer1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Create widgets for the additional items
        self.l_tempDirSizeLabel = QLabel("Delete folder size: ")                  #   TODO    CHANGE TITLE
        self.e_tempDirSize = QLineEdit()
        self.e_tempDirSize.setReadOnly(True)
        self.e_tempDirSize.setFixedWidth(100)  # Set the width
        tip = "Current size of deleted files held in Delete Dir."
        self.e_tempDirSize.setToolTip(tip)

        # Add widgets to the hours box
        self.lo_hoursBox.addWidget(self.l_hours, 0, 0)
        self.lo_hoursBox.addWidget(self.spb_hours, 0, 1)
        self.lo_hoursBox.addItem(self.hotzSpacer1, 0, 2)
        self.lo_hoursBox.addWidget(self.l_tempDirSizeLabel, 0, 3)
        self.lo_hoursBox.addWidget(self.e_tempDirSize, 0, 4)

        # Add the hours box layout to the QVBoxLayout
        self.lo_deleteDirectory.addLayout(self.lo_hoursBox)

        # Add the table directly to the layout
        self.table_delItems = QTableWidget()
        self.table_delItems.setColumnCount(4)  # Set the number of columns
        self.table_delItems.setHorizontalHeaderLabels(["Project", "Type", "Entity", "Deleted"])  # Set column headers

        self.table_delItems.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Set sorting behavior
        self.table_delItems.setSortingEnabled(True)
        self.table_delItems.sortByColumn(3, Qt.DescendingOrder)  # Default sorting by "Deleted" column, descending order

        # Set column widths
        self.table_delItems.setColumnWidth(0, 150)  # Project column
        self.table_delItems.setColumnWidth(1, 150)  # Project column
        # self.table_delItems.setColumnWidth(1, -1)  # File column (stretch to fill)
        self.table_delItems.setColumnWidth(3, 150)  # Deleted column

        # Set column stretch
        # self.table_delItems.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # File column (stretch to fill)
        self.table_delItems.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # File column (stretch to fill)

        # Set column alignments
        self.table_delItems.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)  # Project column (left-align)
        self.table_delItems.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)  # File column (center-align)
        self.table_delItems.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)  # File column (center-align)
        self.table_delItems.horizontalHeaderItem(3).setTextAlignment(Qt.AlignLeft)  # Deleted column (right-align)

        # Set items to be read-only                                                                                     #   TODO NOT WORKING               
        for row in range(self.table_delItems.rowCount()):
            for col in range(self.table_delItems.columnCount()):
                item = QTableWidgetItem()
                item.setReadOnly(True)
                # item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Make the item read-only
                self.table_delItems.setItem(row, col, item)

        tip = ("Deleted files currently in Delete Dir.  These files will be automatically\n"
               "purged based on time set above.\n"
               "\n"
               "Deleted files may be purged using buttons below."
                )
        self.table_delItems.setToolTip(tip)

        self.lo_deleteDirectory.addWidget(self.table_delItems)

        # Add a box for buttons at the bottom
        self.lo_buttonBox = QHBoxLayout()

        # Create buttons
        self.but_openDir = QPushButton("Open in Explorer")
        tip = "Opens Explorer to Delete Dir."
        self.but_openDir.setToolTip(tip)

        self.but_refreshList = QPushButton("ReSync List")
        tip = "ReSyncs deleted item list to Delete Dir current contents."
        self.but_refreshList.setToolTip(tip)

        self.but_undoLast = QPushButton("Undo Last Delete")
        tip = "Will restore last deleted items to their orginal location."
        self.but_undoLast.setToolTip(tip)

        self.but_purgeSelected = QPushButton("Purge Selected")
        tip = "Permantly delete selected files from Delete Dir."
        self.but_purgeSelected.setToolTip(tip)

        self.but_purgeAll = QPushButton("Purge All")
        tip = "Permantly delete all files from Delete Dir."
        self.but_purgeAll.setToolTip(tip)

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
        origin.addTab(origin.w_deleteMenu, "Delete Functions")

        self.connections()
        self.loadSettings()
        self.calcDelDirSize()
        self.configureUI()


    @err_catcher(name=__name__)
    def connections(self):

        self.chb_usedelete.toggled.connect(lambda: self.configureUI())
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

                if "Delete Active" in data:
                    self.deleteActive = data["Delete Active"]

                self.delDirectory = data.get("Delete Directory")
                try:
                    self.e_deleteDir.setText(self.delDirectory)
                    self.chb_usedelete.setChecked(self.deleteActive)
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
                            self.table_delItems.setItem(rowPosition, 1, QTableWidgetItem(item["Type"]))
                            self.table_delItems.setItem(rowPosition, 2, QTableWidgetItem(item["Entity"]))
                            self.table_delItems.setItem(rowPosition, 3, QTableWidgetItem(item["Deleted"]))
                    except:
                        pass

            self.configureUI()

        except FileNotFoundError:
            # Create the settings file if it doesn't exist
            with open(self.settingsFile, "w") as json_file:
                json.dump({}, json_file)


    #   Save Settings to json
    @err_catcher(name=__name__)
    def saveSettings(self, origin=None):

        # Save settings to Plugin Settings File
        with open(self.settingsFile, "w") as json_file:
            json.dump({"Delete Active": self.deleteActive,
                        "Delete Directory": self.delDirectory,
                        "Items": self.delFileInfoList},
                        json_file,
                        indent=4
                        )
        

    @err_catcher(name=__name__)
    def configureUI(self):

        try:
            self.deleteActive = self.chb_usedelete.isChecked()
            active = self.deleteActive

            self.e_deleteDir.setEnabled(active)
            self.but_fileDialogue.setEnabled(active)
            self.l_hours.setEnabled(active)
            self.spb_hours.setEnabled(active)
            self.l_tempDirSizeLabel.setEnabled(active)
            self.e_tempDirSize.setEnabled(active)
            self.table_delItems.setEnabled(active)
            self.but_openDir.setEnabled(active)
            self.but_refreshList.setEnabled(active)
            self.but_undoLast.setEnabled(active)
            self.but_purgeSelected.setEnabled(active)
            self.but_purgeAll.setEnabled(active)
        except:
            pass

        
    @err_catcher(name=__name__)
    def isDeleteActive(self):

        if os.path.exists(self.delDirectory) and self.deleteActive:
            return True
        else:
            return False


    #   Called with Callback - Project Browser
    @err_catcher(name=__name__)                                         #   TODO  There is no Callback for Project Browser RCL Menu
    def projectBrowserContextMenuRequested(self, origin, menu):

        pass


    #   Called with Callback - SceneFiles Browser
    @err_catcher(name=__name__)
    def deleteSceneFile(self, origin, rcmenu, filePath):

        self.loadSettings()

        if self.isDeleteActive() and os.path.isfile(filePath):

            self.menuContext = "Scene Files"

            #   Retrieves File Info from Core
            try:
                sceneData = self.core.getScenefileData(filePath)
                sourceDir, sourceFilename = ntpath.split(sceneData["filename"])
                version = sceneData["version"]

            except Exception as e:
                msg = f"Error opening Config File {str(e)}"
                self.core.popup(msg)

            projectName = self.core.projectName

            deleteList = []
            for file in os.listdir(sourceDir):
                if version in file:
                    deleteList.append(file)

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["sourceDir"] = sourceDir
            delEntityData["delItem"] = version
            delEntityData["delItemName"] = sourceFilename
            delEntityData["deleteList"] = deleteList

            #   Adds Right Click Item
            sendToAct = QAction("Delete Version", rcmenu)
            sendToAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(sendToAct)
            

    @err_catcher(name=__name__)
    def deleteShotDepartment(self, origin, rcmenu, pos):

        self.loadSettings()

        if self.isDeleteActive():

            if pos.data() == None:
                return
            
            deptNameFull = pos.data()

            self.menuContext = "Shot Dept"

            projectName = self.core.projectName

            entity = self.core.pb.sceneBrowser.getCurrentEntity()
            if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
                return

            sequence = entity["sequence"]
            shot = entity["shot"]

            deptName = self.core.pb.sceneBrowser.getCurrentDepartment()
            if deptName:
                deptDir = self.core.getEntityPath(entity=entity, step=deptName)
            else:
                return

            deleteList = []
            for file in os.listdir(deptDir):
                deleteList.append(file)

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["sourceDir"] = deptDir
            delEntityData["delItem"] = deptNameFull
            delEntityData["delItemName"] = f"{sequence}_{shot}_{deptNameFull}"
            delEntityData["deleteList"] = deleteList

            sendToAct = QAction(f"Delete Dept: {deptNameFull}", rcmenu)
            sendToAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(sendToAct)


    @err_catcher(name=__name__)
    def deleteShotTask(self, origin, rcmenu, pos):

        self.loadSettings()

        if self.isDeleteActive():

            if pos.data() == None:
                return
            
            taskName = pos.data()

            self.menuContext = "Shot Task"

            projectName = self.core.projectName

            entity = self.core.pb.sceneBrowser.getCurrentEntity()
            if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
                return

            sequence = entity["sequence"]
            shot = entity["shot"]

            curDep = self.core.pb.sceneBrowser.getCurrentDepartment()
            if curDep:
                deptPath = self.core.getEntityPath(entity=entity, step=curDep)
            else:
                return

            taskDir = os.path.join(deptPath, taskName)

            deleteList = []
            for file in os.listdir(taskDir):
                deleteList.append(file)

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["sourceDir"] = taskDir
            delEntityData["delItem"] = taskName
            delEntityData["delItemName"] = f"{sequence}_{shot}_{curDep}_{taskName}"
            delEntityData["deleteList"] = deleteList

            sendToAct = QAction(f"Delete Task: {taskName}", rcmenu)
            sendToAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(sendToAct)



    @err_catcher(name=__name__)
    def deleteAssetDepartment(self, origin, rcmenu, pos):

        self.loadSettings()

        if self.isDeleteActive():

            if pos.data() == None:
                return
            
            deptNameFull = pos.data()

            self.menuContext = "Asset Dept"

            projectName = self.core.projectName

            entity = self.core.pb.sceneBrowser.getCurrentEntity()
            if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
                return

            asset = entity["asset"]

            deptName = self.core.pb.sceneBrowser.getCurrentDepartment()
            if deptName:
                deptDir = self.core.getEntityPath(entity=entity, step=deptName)
            else:
                return

            deleteList = []
            for file in os.listdir(deptDir):
                deleteList.append(file)

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["sourceDir"] = deptDir
            delEntityData["delItem"] = deptNameFull
            delEntityData["delItemName"] = f"{asset}_{deptNameFull}"
            delEntityData["deleteList"] = deleteList

            sendToAct = QAction(f"Delete Dept: {deptNameFull}", rcmenu)
            sendToAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(sendToAct)


    @err_catcher(name=__name__)
    def deleteAssetTask(self, origin, rcmenu, pos):

        self.loadSettings()

        if self.isDeleteActive():

            if pos.data() == None:
                return
            
            taskName = pos.data()

            self.menuContext = "Asset Task"

            projectName = self.core.projectName

            entity = self.core.pb.sceneBrowser.getCurrentEntity()
            if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
                return

            asset = entity["asset"]

            curDep = self.core.pb.sceneBrowser.getCurrentDepartment()
            if curDep:
                deptPath = self.core.getEntityPath(entity=entity, step=curDep)
            else:
                return

            taskDir = os.path.join(deptPath, taskName)

            deleteList = []
            for file in os.listdir(taskDir):
                deleteList.append(file)

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["sourceDir"] = taskDir
            delEntityData["delItem"] = taskName
            delEntityData["delItemName"] = f"{asset}_{taskName}"
            delEntityData["deleteList"] = deleteList

            sendToAct = QAction(f"Delete Task: {taskName}", rcmenu)
            sendToAct.triggered.connect(lambda: self.deleteAction(delEntityData))
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



    @err_catcher(name=__name__)
    def deleteAction(self, delEntityData):

        projectName = delEntityData["projectName"]      #   PROJECT NAME
        sourceDir = delEntityData["sourceDir"]          #   SOURCE DIRECTORY
        delItem = delEntityData["delItem"]              #   NAME FOR QUESTION
        delItemName = delEntityData["delItemName"]      #   ENTITY NAME
        deleteList = delEntityData["deleteList"]        #   ITEMS IN DIR TO COPY

        currentTime = datetime.now()
        timestamp = currentTime.strftime("%m/%d/%y %H:%M")

        if self.menuContext == "Scene Files":
            questionText = f"Are you sure you want to Delete:\n\nVersion: {delItem}"
            windowTitle = "Delete Files"

        elif self.menuContext in ["Shot Dept", "Asset Dept"]:
            questionText = f"Are you sure you want to Delete:\n\nDept: {delItem}"
            windowTitle = "Delete Department"

        elif self.menuContext in ["Shot Task", "Asset Task"]:
            questionText = f"Are you sure you want to Delete:\n\nTask: {delItem}"
            windowTitle = "Delete Task"

        result = self.core.popupQuestion(questionText, title=windowTitle)

        if result == "Yes":
            destDir, delItemName = self.ensureDirName(delItemName)

            for file in deleteList:
                sourceFile = os.path.join(sourceDir, file)
                destFile = os.path.join(destDir, file)
                shutil.move(sourceFile, destFile)

            fileInfo = {
                "Project": projectName,
                "Type": self.menuContext,
                "Entity": delItemName,
                "Deleted": timestamp,
                "Original Location": sourceDir,
                "Deleted Location": destDir
                }
            
            self.delFileInfoList.append(fileInfo)

            if self.menuContext in ["Shot Dept", "Shot Task"]:
                shutil.rmtree(sourceDir)

        self.saveSettings()
        self.core.pb.refreshUI()
    

    @err_catcher(name=__name__)
    def ensureDirName(self, delItemName):

        destDir = os.path.join(self.delDirectory, delItemName)

        if not os.path.exists(destDir):
            os.mkdir(destDir)
        else:
            match = re.match(r"_(\d+)$", destDir)
            if match:
                baseDir = match.group(1)
            else:
                baseDir = destDir

            newSuffix = 0
            while os.path.exists(destDir):
                newSuffix += 1
                destDir = f"{baseDir}_{newSuffix}"

            delItemName = f"{delItemName}_{newSuffix}"
            os.mkdir(destDir)

        return destDir, delItemName


    @err_catcher(name=__name__)                             #   TODO MAKE SURE DIRS EXIST -- Maybe do not show the Delete option if not.
    def purgeFiles(self, mode=None):

        if mode == "all":
            questionText = f"Are you sure you want to Permanently Delete all Items?\n\nThis is not Reversable."
            result = self.core.popupQuestion(questionText, title="Permanently Delete Files")

            if result == "Yes":
                # Iterate over all files and subdirectories in the given directory
                for root, dirs, files in os.walk(self.delDirectory, topdown=False):
                    for file in files:
                        file_path = os.path.join(root, file)
                        os.remove(file_path)

                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        shutil.rmtree(dir_path)

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
                    entity = self.table_delItems.item(row, 2).text()

                    # Remove the selected entry from the list of dictionaries
                    self.delFileInfoList = [item for item in self.delFileInfoList if item["Entity"] != entity]

                    # Add your logic to delete the file or perform any other action
                    itemPath = os.path.join(self.delDirectory, entity)
                    if os.path.exists(itemPath):
                        shutil.rmtree(itemPath)

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
        self.calcDelDirSize()
        self.table_delItems.viewport().update()


    @err_catcher(name=__name__)
    def calcDelDirSize(self):
        totalSize = 0

        for dirpath, dirnames, filenames in os.walk(self.delDirectory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                totalSize += os.path.getsize(filepath)

        # Convert bytes to appropriate unit and round to the nearest tenth
        if totalSize < 1024 * 1024:
            delDirSize = round(totalSize / 1024*2, 1)
            unit = "KB"
        elif totalSize >= 1024**3:
            delDirSize = round(totalSize / (1024**3), 1)
            unit = "GB"
        else:
            delDirSize = round(totalSize / (1024 * 1024), 1)
            unit = "MB"

        delDirSizeStr = f"{delDirSize} {unit}"

        self.e_tempDirSize.setText(delDirSizeStr)









