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
import threading
import time
from datetime import datetime
from functools import partial


try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher

# from PrismDeleteUtils.PrismWaitingIcon import PrismWaitingIcon


class Prism_DeleteFunctions_Functions(object):                      #   TODO    ADD DEBUG STATEMENTS
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        # self.waitingCircle = PrismWaitingCircleManager()

        self.pluginDir = os.path.dirname(os.path.dirname(__file__))
        self.settingsFile = os.path.join(self.pluginDir, "DeleteFunctions_Config.json")

        self.loadedPlugins = []
        self.delDirectory = None
        self.deleteActive = False

        #   Callbacks                                           #   TODO    Doesn't seem to be a callback for the Project Chooser
        # self.core.registerCallback("projectBrowserContextMenuRequested", self.projectBrowserContextMenuRequested, plugin=self)      
                                                                #   TODO    DELETE ENTITY
        # self.core.registerCallback("sceneBrowserContextMenuRequested", self.deleteEntity, plugin=self)


        self.core.registerCallback("openPBFileContextMenu", self.deleteSceneFile, plugin=self)
        self.core.registerCallback("openPBShotDepartmentContextMenu", self.deleteShotDepartment, plugin=self)
        self.core.registerCallback("openPBShotTaskContextMenu", self.deleteShotTask, plugin=self)
        self.core.registerCallback("openPBAssetDepartmentContextMenu", self.deleteAssetDepartment, plugin=self)
        self.core.registerCallback("openPBAssetTaskContextMenu", self.deleteAssetTask, plugin=self)
        self.core.registerCallback("productSelectorContextMenuRequested", self.deleteProduct, plugin=self)  


        self.core.registerCallback("openPBListContextMenu", self.deleteMedia, plugin=self)        



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
               "Setting Zero will mean Deleted Files will be held indefinitly."
               )
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
        self.table_delItems.setColumnCount(5)  # Set the number of columns
        self.table_delItems.setHorizontalHeaderLabels(["Project", "Type", "Entity", "Deleted"])  # Set column headers

        # # Set column widths
        self.table_delItems.setColumnWidth(0, 150)  # Project column
        self.table_delItems.setColumnWidth(1, 150)  # Project column
        # self.table_delItems.setColumnWidth(1, -1)  # File column (stretch to fill)
        self.table_delItems.setColumnWidth(3, 150)  # Deleted column

        # Set column stretch
        self.table_delItems.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # File column (stretch to fill)

        # Set column alignments
        self.table_delItems.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)  # Project column (left-align)
        self.table_delItems.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)  # File column (center-align)
        self.table_delItems.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)  # File column (center-align)
        self.table_delItems.horizontalHeaderItem(3).setTextAlignment(Qt.AlignLeft)  # Deleted column (right-align)

        #   Hides UID Column
        self.table_delItems.setColumnHidden(4, True)

        # Set items to be read-only                                     #   TODO READONLY NOT WORKING
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

        self.table_delItems.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_delItems.setSelectionMode(QAbstractItemView.SingleSelection)

        self.lo_deleteDirectory.addWidget(self.table_delItems)

        # Add a box for buttons at the bottom
        self.lo_buttonBox = QHBoxLayout()

        # Create buttons
        self.but_openDir = QPushButton("Open in Explorer")
        tip = "Opens Explorer to Delete Dir."
        self.but_openDir.setToolTip(tip)

        self.but_refreshList = QPushButton("ReSync List")
        tip = ("ReSyncs deleted item list to Delete Dir current contents.\n\n"
               "This may be required when files are manually changed in the Delete Dir."
                )
        self.but_refreshList.setToolTip(tip)

        self.but_undoLast = QPushButton("Restore Selected")
        tip = "Restore selected items to their orginal location."
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
        self.but_undoLast.clicked.connect(lambda: self.restoreSelected())
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
    @err_catcher(name=__name__)                                     #   NEEDED ???
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

                        #   Temporalily disable sorting for table load
                        self.table_delItems.setSortingEnabled(False)

                        # Populate the table with data from self.delFileInfoList
                        for item in self.delFileInfoList:
                            rowPosition = self.table_delItems.rowCount()
                            self.table_delItems.insertRow(rowPosition)

                            self.table_delItems.setItem(rowPosition, 0, QTableWidgetItem(item["Project"]))
                            self.table_delItems.setItem(rowPosition, 1, QTableWidgetItem(item["Type"]))
                            self.table_delItems.setItem(rowPosition, 2, QTableWidgetItem(item["Entity"]))
                            self.table_delItems.setItem(rowPosition, 3, QTableWidgetItem(item["Deleted"]))
                            #   Loads the data even though column is hidden from theUI
                            self.table_delItems.setItem(rowPosition, 4, QTableWidgetItem(item["UID"]))

                        # Reset Table Sorting Behavior
                        self.table_delItems.setSortingEnabled(True)
                        self.table_delItems.sortByColumn(3, Qt.DescendingOrder)  # Default sorting by "Deleted" column, descending order

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
        
        self.loadSettings()


    @err_catcher(name=__name__)
    def configureUI(self):
        
        try:
            self.deleteActive = self.chb_usedelete.isChecked()              #   TODO MAKE SURE THIS IS WORKING CORRECTLY
            enabled = self.deleteActive
            dirExists = os.path.exists(self.delDirectory)
            active = enabled and dirExists

            self.l_delDirText.setEnabled(enabled)
            self.e_deleteDir.setEnabled(enabled)
            self.but_fileDialogue.setEnabled(enabled)
            self.l_hours.setEnabled(active)
            self.spb_hours.setEnabled(active)
            self.l_tempDirSizeLabel.setEnabled(active)
            self.e_tempDirSize.setEnabled(active)
            if enabled and not dirExists:
                #   If Delete Dir is does not exist
                self.table_delItems.setRowCount(10)
                # Add message to Table
                self.table_delItems.setItem(5, 1, QTableWidgetItem("DELETE DIRECTORY"))
                self.table_delItems.setItem(5, 2, QTableWidgetItem("DOES NOT EXIST."))
                self.table_delItems.setEnabled(False)
            else:
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






    ##########  THIS IS FOR THE PROJECT PICKER   ###################
    # #   Called with Callback - Project Browser
    # @err_catcher(name=__name__)                                 #   TODO  There is no Callback for Project Browser RCL Menu
    # def projectBrowserContextMenuRequested(self, origin, menu):

    #     pass


    #   Called with Callback - SceneFiles Browser                                   #   TODO    DELETE ENTITY
    # @err_catcher(name=__name__)
    # def deleteEntity(self, origin, menuType, menu):

    #     self.core.popup("HERE!")                                      #    TESTING






    #   Called with Callback - SceneFiles Browser
    @err_catcher(name=__name__)
    def deleteSceneFile(self, origin, rcmenu, filePath):

        self.menuContext = "Scene Files"
        self.loadSettings()

        if self.isDeleteActive() and os.path.isfile(filePath):
            #   Retrieves File Info from Core
            try:
                sceneData = self.core.getScenefileData(filePath)
                sourceDir, sourceFilename = ntpath.split(sceneData["filename"])

            except Exception as e:
                msg = f"Error opening Config File {str(e)}"
                self.core.popup(msg)

            projectName = self.core.projectName

            if sceneData["type"] == "shot":
                entity = sceneData["shot"]
            else:
                entity = sceneData["asset"]

            department = sceneData["department"]
            task = sceneData["task"]
            version = sceneData["version"]

            deleteList = []

            for file in os.listdir(sourceDir):
                if version in file:
                    item = {"location": version, "path": os.path.normpath(os.path.join(sourceDir, file))}
                    deleteList.append(item)

            questionText = (f"Are you sure you want to Delete:\n\n"
                            f"Version: {version}"
                            )
            windowTitle = f"Delete {version}"                                       #   TODO

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["delItemName"] = f"{entity}_{department}_{task}_{version}"
            delEntityData["deleteList"] = deleteList
            delEntityData["questText"] = questionText
            delEntityData["questTitle"] = windowTitle

            #   Adds Right Click Item
            deleteAct = QAction("Delete Version", rcmenu)
            deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(deleteAct)
            

    @err_catcher(name=__name__)
    def deleteShotDepartment(self, origin, rcmenu, pos):

        self.menuContext = "Shot Dept"
        self.loadSettings()

        if self.isDeleteActive():
            if pos.data() == None:
                return
            
            deptNameFull = pos.data()
            projectName = self.core.projectName
            entity = origin.getCurrentEntity()

            if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
                return

            sequence = entity["sequence"]
            shot = entity["shot"]

            deptName = origin.getCurrentDepartment()
            if deptName:
                deptDir = self.core.getEntityPath(entity=entity, step=deptName)
            else:
                return

            delItem = {"location": shot, "path": deptDir}
            deleteList = []
            deleteList.append(delItem)

            questionText = (f"Are you sure you want to Delete:\n\n"
                            f"Shot Department: {deptName}"
                            )
            windowTitle = f"Delete {deptName}"                                       #   TODO

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["delItemName"] = f"{sequence}_{shot}_{deptNameFull}"
            delEntityData["deleteList"] = deleteList
            delEntityData["questText"] = questionText
            delEntityData["questTitle"] = windowTitle

            deleteAct = QAction(f"Delete Dept: {deptNameFull}", rcmenu)
            deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(deleteAct)


    @err_catcher(name=__name__)
    def deleteShotTask(self, origin, rcmenu, pos):

        self.menuContext = "Shot Task"
        self.loadSettings()

        if self.isDeleteActive():

            if pos.data() == None:
                return
            
            taskName = pos.data()
            projectName = self.core.projectName

            entity = origin.getCurrentEntity()
            if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
                return

            sequence = entity["sequence"]
            shot = entity["shot"]

            curDep = origin.getCurrentDepartment()
            if curDep:
                deptDir = self.core.getEntityPath(entity=entity, step=curDep)
            else:
                return
            taskDir = os.path.join(deptDir, taskName)

            delItem = {"location": f"{shot}_{curDep}", "path": taskDir}
            deleteList = []
            deleteList.append(delItem)


            questionText = (f"Are you sure you want to Delete:\n\n"
                            f"Shot Task: {taskName}"
                            )
            windowTitle = f"Delete {taskName}"                                       #   TODO

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["delItemName"] = f"{sequence}_{shot}_{curDep}_{taskName}"
            delEntityData["deleteList"] = deleteList
            delEntityData["questText"] = questionText
            delEntityData["questTitle"] = windowTitle

            deleteAct = QAction(f"Delete Task: {taskName}", rcmenu)
            deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(deleteAct)



    @err_catcher(name=__name__)
    def deleteAssetDepartment(self, origin, rcmenu, pos):

        self.menuContext = "Asset Dept"
        self.loadSettings()

        if self.isDeleteActive():
            if pos.data() == None:
                return
            
            deptNameFull = pos.data()
            projectName = self.core.projectName

            entity = origin.getCurrentEntity()
            if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
                return

            asset = entity["asset"]

            deptName = origin.getCurrentDepartment()
            if deptName:
                deptDir = self.core.getEntityPath(entity=entity, step=deptName)
            else:
                return

            delItem = {"location": asset, "path": deptDir}
            deleteList = []
            deleteList.append(delItem)

            questionText = (f"Are you sure you want to Delete:\n\n"
                            f"Asset Department: {deptName}"
                            )
            windowTitle = f"Delete {deptName}"                                       #   TODO

            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["delItemName"] = f"{asset}_{deptNameFull}"
            delEntityData["deleteList"] = deleteList
            delEntityData["questText"] = questionText
            delEntityData["questTitle"] = windowTitle

            deleteAct = QAction(f"Delete Dept: {deptNameFull}", rcmenu)
            deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(deleteAct)


    @err_catcher(name=__name__)
    def deleteAssetTask(self, origin, rcmenu, pos):

        self.menuContext = "Asset Task"
        self.loadSettings()

        if self.isDeleteActive():

            if pos.data() == None:
                return
            
            taskName = pos.data()


            projectName = self.core.projectName

            entity = origin.getCurrentEntity()
            if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
                return

            asset = entity["asset"]

            curDep = origin.getCurrentDepartment()
            if curDep:
                deptDir = self.core.getEntityPath(entity=entity, step=curDep)
            else:
                return
            
            taskDir = os.path.join(deptDir, taskName)

            delItem = {"location": f"{asset}_{curDep}", "path": taskDir}
            deleteList = []
            deleteList.append(delItem)


            questionText = (f"Are you sure you want to Delete:\n\n"
                            f"Shot Task: {taskName}"
                            )
            windowTitle = f"Delete {taskName}"                                       #   TODO

            #   Populate Data to be Passed to deleteAction()
            delEntityData = {}
            delEntityData["projectName"] = projectName
            delEntityData["delItemName"] = f"{asset}_{curDep}_{taskName}"
            delEntityData["deleteList"] = deleteList
            delEntityData["questText"] = questionText
            delEntityData["questTitle"] = windowTitle


            deleteAct = QAction(f"Delete Task: {taskName}", rcmenu)
            deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(deleteAct)
            


    #   Called with Callback - Product Browser
    @err_catcher(name=__name__)
    def deleteProduct(self, origin, viewUi, pos, rcmenu):             #   TODO CLEANUP

        self.menuContext = "Product"
        self.loadSettings()

        if self.isDeleteActive():
            version = origin.getCurrentVersion()
            if not version:
                return

            if viewUi == origin.tw_identifier:
                listType = "identifier"
            elif viewUi == origin.tw_versions:
                listType = "version"

            deleteList = []

            #   Case 1 - Product Indentifier
            if listType == "identifier":
                item = origin.tw_identifier.itemAt(pos)
                #   Retrieves Product Data
                prodData = item.data(0, Qt.UserRole)
                product = prodData["product"]

                if prodData["type"] == "asset":
                    asset = prodData["asset"]
                    delItemName = f"{asset}_{product}"
                else:
                    sequence = prodData["sequence"]
                    shot = prodData["shot"]
                    delItemName = f"{sequence}_{shot}_{product}"

                #   Retrieves Locations Data
                saveLocs = origin.core.paths.getExportProductBasePaths()

                #   Combine Dicts to correlate Location Name and Path
                for loc in prodData["locations"]:
                    for location, pathStart in saveLocs.items():
                        if loc.startswith(pathStart):
                            deleteList.append({
                                "location": location,
                                "path": loc
                            })
                            break

                questionText = f"Are you sure you want to Delete:\n\nProduct: {product}"
                windowTitle = f"Delete Product {product}"

                #   Populate Data to be Passed to deleteAction()
                delEntityData = {}
                delEntityData["projectName"] = prodData["project_name"]
                delEntityData["delItemName"] = delItemName
                delEntityData["deleteList"] = deleteList
                delEntityData["questText"] = questionText
                delEntityData["questTitle"] = windowTitle

                #   Add Command to Right-click Menu
                deleteAct = QAction(f"Delete {product}", viewUi)
                deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
                rcmenu.addAction(deleteAct)


            #   Case 2 - Product Version
            elif listType == "version":
                #   Retreives Product Data
                data = origin.getCurrentProduct()
                paths = data["paths"]
                
                #   Gets Source Path from Last Column - Assuming path is always last Column
                row = viewUi.rowAt(pos.y())
                numCols = viewUi.columnCount()
                if row >= 0:
                    sourcePath = viewUi.item(row, numCols - 1).text()
                #   Retrieves File Info        
                infoFolder = self.core.products.getVersionInfoPathFromProductFilepath(sourcePath)
                infoPath = self.core.getVersioninfoPath(infoFolder)
                prodData = self.core.getConfig(configPath=infoPath)

                version = prodData["version"]
                product = prodData["product"]


                if prodData["type"] == "asset":
                    asset = prodData["asset"]
                    delItemName = f"{asset}_{product}_{version}"
                else:
                    sequence = prodData["sequence"]
                    shot = prodData["shot"]
                    delItemName = f"{sequence}_{shot}_{product}_{version}"

                #   Retrieves Locations Data
                saveLocs = origin.core.paths.getExportProductBasePaths()

                #   Combine Dicts to correlate Location Name and Path
                locsList = []
                for loc in data["locations"]:
                    for location, pathStart in saveLocs.items():
                        if loc.startswith(pathStart):
                            locsList.append({
                                "location": location,
                                "path": os.path.join(loc, version)
                            })
                            break

                #   Adds Version to deleteList if present in Location Dirs
                for loc in locsList:
                    if os.path.exists(loc["path"]):
                        deleteList.append(loc)                  

                questionText = f"Are you sure you want to Delete:\n\nProduct Version: {version}"
                windowTitle = f"Delete Product Version {version}"

                delEntityData = {}
                delEntityData["projectName"] = prodData["project_name"]
                delEntityData["delItemName"] = delItemName
                delEntityData["deleteList"] = deleteList
                delEntityData["questText"] = questionText
                delEntityData["questTitle"] = windowTitle

                #   Adds right-click Item
                deleteAct = QAction(f"Delete Version {version}", viewUi)
                deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
                rcmenu.addAction(deleteAct)

                #   If there are multiple locations, will add Remove Menu
                if len(deleteList) > 1:
                    removeMenu = QMenu(f"Remove Verion {version} from", viewUi)

                    #   Adds Remove Menu items for each location
                    for loc in deleteList:
                        removeFromAct = QAction(loc["location"], viewUi)
                        removeFromAct.triggered.connect(partial(self.removeAction, delEntityData, loc))
                        removeMenu.addAction(removeFromAct)

                    rcmenu.addMenu(removeMenu)



    @err_catcher(name=__name__)
    def deleteMedia(self, origin, rcmenu, lw, item, path):

        if not item:
            return
        
        self.menuContext = "Media"
        self.loadSettings()

        self.mediaViewer = origin.w_preview.mediaPlayer

        if lw == origin.tw_identifier:
            itemName = item.text(0)
        else:
            itemName = item.text()

        entity = origin.getCurrentEntity()

        if not entity:
            return

        if lw == origin.tw_identifier:
            listType = "identifier"
            if itemName:
                data = item.data(0, Qt.UserRole)

        elif lw == origin.lw_version:
            listType = "version"
            if itemName:
                data = item.data(Qt.UserRole)
            else:
                identifier = origin.getCurrentIdentifier()
                if not identifier:
                    return

        identifier = data["identifier"]

        if data["type"] == "asset":
            asset = data["asset"]
            entity = f"{asset}_{identifier}"
        else:
            sequence = data["sequence"]
            shot = data["shot"]
            entity = f"{sequence}_{shot}_{identifier}"

        deleteList = []
        path = data["path"]

        #   Retrieves Locations Data
        saveLocs = origin.core.paths.getExportProductBasePaths()
    
        #   Constructs deleteList with Location Names and Paths
        for loc in saveLocs:
            newPath = self.core.convertPath(path, target=loc)
            if os.path.exists(newPath):
                locItem = {"location": loc, "path": newPath}
                deleteList.append(locItem)

        delEntityData = {}
        delEntityData["projectName"] = data["project_name"]
        delEntityData["deleteList"] = deleteList

        #   Case 1 - Media Indentifier
        if listType == "identifier":

            questionText = f"Are you sure you want to Delete:\n\nMedia Identifier: {identifier}\n\n"
            windowTitle = f"Delete Media: {identifier}"

            #   Populate Data to be Passed to deleteAction()
            delEntityData["delItemName"] = entity
            delEntityData["questText"] = questionText
            delEntityData["questTitle"] = windowTitle

            #   Add Command to Right-click Menu
            deleteAct = QAction(f"Delete {identifier}", rcmenu)
            deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(deleteAct)

        #   Case 2 - Media Version
        elif listType == "version":

            version = data["version"]

            questionText = f"Are you sure you want to Delete:\n\nMedia Version: {version}"
            windowTitle = f"Delete Media Version: {version}"

            delEntityData["delItemName"] = f"{entity}_{version}"
            delEntityData["questText"] = questionText
            delEntityData["questTitle"] = windowTitle

            #   Adds right-click Item
            deleteAct = QAction(f"Delete Version {version}", rcmenu)
            deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
            rcmenu.addAction(deleteAct)

            #   If there are multiple locations, will add Remove Menu
            if len(deleteList) > 1:
                removeMenu = QMenu(f"Remove Verion {version} from", rcmenu)

                #   Adds Remove Menu items for each location
                for loc in deleteList:
                    removeFromAct = QAction(loc["location"], rcmenu)
                    removeFromAct.triggered.connect(partial(self.removeAction, delEntityData, loc))
                    removeMenu.addAction(removeFromAct)

                rcmenu.addMenu(removeMenu)


    #   Used to Remove Item from Specific Location
    @err_catcher(name=__name__)
    def removeAction(self, delEntityData, loc):
        #   Alters Data to reflect location
        delEntityData["deleteList"] = [item for item in delEntityData["deleteList"] if item["location"] == loc["location"]]
        delEntityData["delItemName"] = f"{delEntityData['delItemName']} ({loc['location']})"
        
        self.deleteAction(delEntityData)


    @err_catcher(name=__name__)
    def deleteAction(self, delEntityData):

        projectName = delEntityData["projectName"]      #   PROJECT NAME
        delItemName = delEntityData["delItemName"]      #   ENTITY NAME
        deleteList = delEntityData["deleteList"]        #   ITEMS IN DIR TO MOVE
        questTitle = delEntityData["questTitle"]        #   
        questText = delEntityData["questText"]          #   FOR QUESTION POPUP

        # self.core.popup(f"deleteList: {deleteList}")                                      #    TESTING

        currentTime = datetime.now()
        timestamp = currentTime.strftime("%m/%d/%y %H:%M")

        result = self.core.popupQuestion(questText, title=questTitle)

        if result == "Yes":
            try:
                if self.menuContext == "Media":
                    viewOrigState = self.mediaViewer.state
                    self.mediaViewer.state = "disabled"
                    self.mediaViewer.updatePreview()

                origLocList = []
                destDir, delItemName = self.ensureDirName(delItemName)

                if self.menuContext == "Scene Files":

                    for item in deleteList:
                        sourceItem = item["path"]
                        destItem = os.path.join(destDir, item["location"])
                        subDir = os.path.join(destDir, item["location"])

                        # self.core.popup(f"from: {sourceItem} to {destItem}")                                      #    TESTING

                        if not os.path.exists(subDir):
                            os.mkdir(subDir)
                        shutil.move(sourceItem, destItem)
                        origLocList.append(item)

                else:
                    for item in deleteList:
                        sourceItem = item["path"]
                        destItem = os.path.join(destDir, item["location"])

                        # self.core.popup(f"from: {sourceItem} to {destItem}")                                      #    TESTING

                        shutil.move(sourceItem, destItem)                               #   TODO DO I NEED MKDIR HERE
                        origLocList.append(item)

                fileInfo = {                                                            #   TODO CHECK IF ALL NEEDED
                    "Project": projectName,
                    "Type": self.menuContext,
                    "Entity": delItemName,
                    "Deleted": timestamp,
                    "UID": self.generateUID(),
                    "OriginalLocation": origLocList,
                    "DeletedLocation": destDir,
                    }
                
                self.delFileInfoList.append(fileInfo)

                if self.menuContext == "Media":
                    self.mediaViewer.state = viewOrigState
                    self.mediaViewer.updatePreview()

                self.saveSettings()
                self.core.pb.refreshUI()

            except Exception as e:
                if self.menuContext == "Product":
                    self.core.popup(f"Unable to Delete: {delItemName}\n\nTry closing the Viewer Window\n\nError:\n\n{e}")                 #   TODO    ADD DEBUG

                elif self.menuContext == "Media":
                    self.core.popup(f"Unable to Delete: {delItemName}\n\nTry disabling the Media Viewer\n\nError:\n\n{e}")                 #   TODO    ADD DEBUG

                else:
                    self.core.popup(f"Unable to Delete: {delItemName}\n\n{e}")                 #   TODO    ADD DEBUG

                # shutil.rmtree(subDir)                                                         #   TODO DELTE DIR IF FAIL
    

    @err_catcher(name=__name__)
    def generateUID(self):
        #   Generate UId using current datetime to the nearest tenth of a second
        currentDatetime = datetime.now()
        UID = currentDatetime.strftime("%m%d%y%H%M%S") + str(currentDatetime.microsecond // 100000)
        return UID


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
    

    @err_catcher(name=__name__)                 #   TODO MAKE SURE DIRS EXIST -- Maybe do not show the Delete option if not.
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
            
            # self.waitingCircle.start()      #   TESTING FOR WAITING CIRCLE
            # time.sleep(5)                   #   TESTING
            # self.waitingCircle.stop()       #   TESTING

            
        elif mode == "single":
            selectedRow = self.table_delItems.currentRow()
            #   Return if no row selected
            if selectedRow == -1:
                return

            questionText = f"Are you sure you want to Permanently Delete the Selected Item?\n\nThis is not Reversible."
            result = self.core.popupQuestion(questionText, title="Permanently Delete Files")

            if result == "Yes":
                # Deleting selected files in the table
                selectedUID = self.table_delItems.item(selectedRow, 4).text()

                # Find the dictionary in the list with the matching UID
                purgeItem = self.getItemFromUID(selectedUID)

                if purgeItem:
                    itemPath = purgeItem["DeletedLocation"]
                    if os.path.exists(itemPath):
                        shutil.rmtree(itemPath)

                    # Remove the matched item from the list
                    self.delFileInfoList.remove(purgeItem)

                    self.saveSettings()
                    self.refreshList()

            else:
                return

        self.refreshList()


    @err_catcher(name=__name__)
    def getItemFromUID(self, UID): 
        try:  
            selectedItem = next((item for item in self.delFileInfoList if item["UID"] == UID), None)
            return selectedItem
        except:
            return None
    

    @err_catcher(name=__name__)                             #   TODO MORE ROBUST FILE CHECKING BEFORE DELETE
    def restoreSelected(self):

        selectedRow = self.table_delItems.currentRow()
        #   Return if no row selected
        if selectedRow == -1:
            return

        questionText = (f"Are you sure you want to Restore the selected Entity to the original location?\n\n"
                        "The restore will overwrite any files with the same name as the deleted files."
                        )
        title = "Restore Entity"
        result = self.core.popupQuestion(questionText, title=title)

        if result == "Yes":
            # Retrieving UID from hidden table column
            selectedUID = self.table_delItems.item(selectedRow, 4).text()

            # Find the dictionary in the list with the matching UID
            restoreEntity = self.getItemFromUID(selectedUID)
            origList = restoreEntity["OriginalLocation"]

            if restoreEntity:
                if restoreEntity["Type"] == "Scene Files":                  #   TODO CLEANUP

                    for origItem in origList:
                        origLocName = origItem["location"]
                        origLocPath = origItem["path"]
                        origLocDir = os.path.dirname(origLocPath)
                        delLocBase = restoreEntity["DeletedLocation"]
                        delLocation = os.path.join(delLocBase, origLocName)
                        
                        if not os.path.exists(origLocDir):
                            os.mkdir(origLocDir)
                        
                        for item in os.listdir(delLocation):
                            itemPath = os.path.join(delLocation, item)
                            shutil.move(itemPath, origLocDir)

                else:
                    for origItem in origList:
                        origLocName = origItem["location"]
                        origLocPath = origItem["path"]
                        delLocBase = restoreEntity["DeletedLocation"]
                        delLocation = os.path.join(delLocBase, origLocName)

                        if not os.path.exists(origLocPath):
                            os.mkdir(origLocPath)
                        
                        for item in os.listdir(delLocation):
                            sourceDir = os.path.join(delLocation, item)
                            shutil.move(sourceDir, origLocPath)



                self.table_delItems.removeRow(selectedRow)

                # Remove the matched item from the list
                self.delFileInfoList.remove(restoreEntity)

                if os.path.exists(delLocBase):
                    shutil.rmtree(delLocBase)




                self.saveSettings()
                self.calcDelDirSize()
                self.core.pb.refreshUI()
            else:
                pass


    @err_catcher(name=__name__)                 #   TODO ENSURE SYNC BETWEEN DIR AND LIST and MAYBE READ CURRENT FILES IN DIR
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


######  TODO


# class PrismWaitingCircleManager(object):
#     def __init__(self):
#         self.prismWaitingIcon = PrismWaitingIcon()
#         self.showWaitingCircleFlag = False

#     def show(self):
#         self.prismWaitingIcon.showWaitingIcon()
#         print("started")                            #   TESTING
#         self.showWaitingCircleFlag = True

#     def hide(self):
#         self.prismWaitingIcon.hideWaitingIcon()
#         print("stopped")                            #   TESTING
#         self.showWaitingCircleFlag = False

#     def start(self):
#         self.show()
#         self.prismWaitingIcon.show()

#     def stop(self):
#         self.hide()
#         self.prismWaitingIcon.hide()






