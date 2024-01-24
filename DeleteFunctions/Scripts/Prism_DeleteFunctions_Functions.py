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


import os                                                           #   TODO    CLEANUP
import ntpath
import subprocess
import json
import shutil
import re
import threading
import time
import logging
from datetime import datetime, timedelta
from functools import partial


try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher

# from PrismDeleteUtils.PrismWaitingIcon import PrismWaitingIcon            #   TODO


logger = logging.getLogger(__name__)


class Prism_DeleteFunctions_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.pluginDir = os.path.dirname(os.path.dirname(__file__))
        self.settingsFile = os.path.join(self.pluginDir, "DeleteFunctions_Config.json")

        self.loadedPlugins = []                                 #   NEEDED ???
        self.delDirectory = None
        self.deleteActive = False
        self.delFileInfoList = []

        self.loadSettings()

        #   Creates autoPurger timer instance
        if self.core.appPlugin.pluginName == "Standalone":
            self.autoPurger = AutoPurger(self.core, self.settingsFile, self.delDirectory)
            self.updateAutoPurger(mode="launch")



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

        #   TODO    GET MORE INFO FOR LIBRARY ITEMS
        self.core.registerCallback("textureLibraryTextureContextMenuRequested", self.deleteLibraryItem, plugin=self)
        
        self.core.registerCallback("userSettings_loadUI", self.userSettings_loadUI, plugin=self)
        self.core.registerCallback("onUserSettingsSave", self.saveSettings, plugin=self)


    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True


    @err_catcher(name=__name__)
    def isDeleteActive(self):
        if os.path.exists(self.delDirectory) and self.deleteActive:
            return True
        else:
            return False


    #   Check Loaded Plugins
    @err_catcher(name=__name__)                                     #   TODO    NEEDED ???
    def getLoadedPlugins(self):
        logger.debug("Getting Loaded Plugins")

        pluginNames = ["Standalone",
                       "Libraries",
                       "USD"
                       ]
        
        for plugin in pluginNames:
            pluginName = self.core.plugins.getPlugin(plugin)
            if pluginName is not None:
                self.loadedPlugins.append(plugin)


    #   Called with Callback
    @err_catcher(name=__name__)
    def userSettings_loadUI(self, origin):  # ADDING "Delete Functions" TO USER SETTINGS

        logger.debug("Loading DeleteFunctions Menu")

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
        self.spb_hours.setRange(0, 720)
        tip = ("Time period in hours to keep the Deleted files in the Delete Dir\n"
               "before being automatically purged.\n"
               "\n"
               "Setting Zero will mean Deleted Files will be held indefinitly."
               )
        self.spb_hours.setToolTip(tip)

        self.hotzSpacer1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Create widgets for the additional items
        self.l_tempDirSizeLabel = QLabel("Delete folder centents: ")
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
        self.table_delItems.setColumnWidth(0, 150)      # Project column
        self.table_delItems.setColumnWidth(1, 150)      # Type column
        # self.table_delItems.setColumnWidth(1, -1)     # File column (stretch to fill)
        self.table_delItems.setColumnWidth(3, 150)      # Deleted column

        # Set column stretch
        self.table_delItems.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # File column (stretch to fill)

        # Set column alignments
        self.table_delItems.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)  # Project column (left-align)
        self.table_delItems.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)  # Type column (center-align)
        self.table_delItems.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)  # File column (center-align)
        self.table_delItems.horizontalHeaderItem(3).setTextAlignment(Qt.AlignLeft)  # Deleted column (right-align)

        #   Hides UID Column
        self.table_delItems.setColumnHidden(4, True)



        # Set items to be read-only                                                         #   TODO READONLY NOT WORKING
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

        self.lo_deleteDirectory.addLayout(self.lo_buttonBox)
        self.gb_deleteDirectory.setLayout(self.lo_deleteDirectory)
        origin.lo_deleteMenu.addWidget(self.gb_deleteDirectory)

        # Add Tab to User Settings
        origin.addTab(origin.w_deleteMenu, "Delete Functions")

        self.connections()
        self.loadSettings()
        self.calcDelDirSize()


    @err_catcher(name=__name__)
    def configureUI(self):
        #   Configures menu items enabled based on Delete Active
        try:
            self.deleteActive = self.chb_usedelete.isChecked()
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

            logger.debug(f"DeleteActive = {enabled}")
        except:
            pass
        

    @err_catcher(name=__name__)
    def connections(self):

        self.chb_usedelete.toggled.connect(lambda: self.configureUI())
        self.but_fileDialogue.clicked.connect(lambda: self.openExplorer(set=True))
        self.but_openDir.clicked.connect(lambda: self.openExplorer(set=False))
        self.spb_hours.editingFinished.connect(lambda: self.updateAutoPurger())
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

            logger.debug("Delete Directory Selected")
            self.saveSettings()

        #   If set not True, then just opens file explorer
        else:
            cmd = "explorer " + path
            subprocess.Popen(cmd)


    #   Load Settings from json
    @err_catcher(name=__name__)
    def loadSettings(self):
        logger.debug("Loading Settings.")

        try:
            with open(self.settingsFile, "r") as json_file:
                data = json.load(json_file)

                self.deleteActive = data["Delete Active"]
                self.updateInterval = data["UpdateInterval"]
                self.delDirectory = data.get("Delete Directory")

                try:
                    self.chb_usedelete.setChecked(self.deleteActive)
                    self.e_deleteDir.setText(self.delDirectory)
                    self.spb_hours.setValue(self.updateInterval)
                except:
                    pass

                # Check if "Items" key exists in the loaded data
                if "Items" in data:
                    self.delFileInfoList = data["Items"]
                    try:
                        # Clear the existing rows in the table
                        self.table_delItems.setRowCount(0)

                        #   Temporalily disable sorting to load table correctly
                        self.table_delItems.setSortingEnabled(False)

                        # Populate the table with data from delFileInfoList
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

        # Create the settings file if it doesn't exist
        except FileNotFoundError:
            logger.debug("Settings file does not exist. Creating New.")
            self.createSettings()

        #   Delete and Create Corrupt Settings File
        except:
            logger.warning("ERROR: Settings file currupt.  Removing existing file.")
            self.core.popup("Error Opening Config File.\n\n"
                            "Reverting to defaults"
                            )
            os.remove(self.settingsFile)

            self.createSettings()


    #   Save Settings to json
    @err_catcher(name=__name__)
    def createSettings(self):

        self.deleteActive = False
        self.updateInterval = 0
        self.delDirectory = ""
        self.delFileInfoList = []

        logger.debug("Created settings file.")
        self.saveSettings()


    #   Save Settings to json
    @err_catcher(name=__name__)
    def saveSettings(self, origin=None):
        try:
            self.updateInterval = self.spb_hours.value()
        except:
            pass

        try:
            # Save settings to Plugin Settings File
            with open(self.settingsFile, "w") as json_file:
                json.dump({"Delete Active": self.deleteActive,
                        "UpdateInterval": self.updateInterval,
                            "Delete Directory": self.delDirectory,
                            "Items": self.delFileInfoList},
                            json_file,
                            indent=4
                            )
        
            logger.debug("Saved settings file.")
            self.loadSettings()

        except Exception as e:
            logger.warning(f"ERROR: Unable to save Settings file:  {e}")


    # Launches and updates AutoPurger
    @err_catcher(name=__name__)
    def updateAutoPurger(self, mode="refresh"):

        if mode == "launch":
            if self.autoPurger.isRunning():
                return
        #   Used when the duration is changed
        if mode ==  "refresh":
            logger.debug("Stopping AutoPurger")
            self.autoPurger.stop()
            self.updateInterval = self.spb_hours.value()

        #   If interval is Zero, the autoPurge is not used
        if self.updateInterval >0:
            logger.debug("Starting AutoPurger")
            self.autoPurger.run(self.updateInterval)
        else:
            logger.info("AutoPurger Disabled")

        self.saveSettings()




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

            logger.debug("Loading Scene Data")

            try:
                #   Retrieves File Info from Core
                sceneData = self.core.getScenefileData(filePath)
                sourceDir, sourceFilename = ntpath.split(sceneData["filename"])

                projectName = self.core.projectName

                if sceneData["type"] == "shot":
                    sequence = sceneData["sequence"]
                    shot = sceneData["shot"]
                    entity = f"{sequence}_{shot}"
                else:
                    entity = sceneData["asset"]

                department = sceneData["department"]
                task = sceneData["task"]
                version = sceneData["version"]

                #   Creates deleteList from items in Dir
                deleteList = []
                for file in os.listdir(sourceDir):
                    if version in file:
                        item = {"location": version, "path": os.path.normpath(os.path.join(sourceDir, file))}
                        deleteList.append(item)

                questionText = (f"Are you sure you want to Delete:\n\n"
                                f"Version: {version}"
                                )
                windowTitle = f"Delete {version}"                                       #   TODO

                #   Builds delEntityData to be passed to deleteAction
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
            
            except Exception as e:
                msg = f"Cannot delete {delEntityData['delItemName']}\n\n{str(e)}"
                self.core.popup(msg)
                logger.wraning(f"ERROR:  Cannot delete {delEntityData['delItemName']}. {e}")


    @err_catcher(name=__name__)
    def deleteShotDepartment(self, origin, rcmenu, pos):
        self.menuContext = "Shot Dept"
        self.loadSettings()

        if self.isDeleteActive():
            try:
                if pos.data() == None:
                    return
                
                #   Gets data from Core
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

                #   Creates deleteList from folder
                delItem = {"location": shot, "path": deptDir}
                deleteList = []
                deleteList.append(delItem)

                questionText = (f"Are you sure you want to Delete:\n\n"
                                f"Shot Department: {deptName}"
                                )
                windowTitle = f"Delete {deptName}"                                       #   TODO

                #   Builds delEntityData to be passed to deleteAction
                delEntityData = {}
                delEntityData["projectName"] = projectName
                delEntityData["delItemName"] = f"{sequence}_{shot}_{deptNameFull}"
                delEntityData["deleteList"] = deleteList
                delEntityData["questText"] = questionText
                delEntityData["questTitle"] = windowTitle

                #   Adds Right Click Item
                deleteAct = QAction(f"Delete Dept: {deptNameFull}", rcmenu)
                deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
                rcmenu.addAction(deleteAct)

            except Exception as e:
                msg = f"Cannot delete {delEntityData['delItemName']}\n\n{str(e)}"
                self.core.popup(msg)
                logger.wraning(f"ERROR:  Cannot delete {delEntityData['delItemName']}. {e}")


    @err_catcher(name=__name__)
    def deleteShotTask(self, origin, rcmenu, pos):

        self.menuContext = "Shot Task"
        self.loadSettings()

        if self.isDeleteActive():
            try:
                if pos.data() == None:
                    return
                
                #   Gets data from Core
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

                #   Builds delEntityData to be passed to deleteAction
                delEntityData = {}
                delEntityData["projectName"] = projectName
                delEntityData["delItemName"] = f"{sequence}_{shot}_{curDep}_{taskName}"
                delEntityData["deleteList"] = deleteList
                delEntityData["questText"] = questionText
                delEntityData["questTitle"] = windowTitle

                #   Adds Right Click Item
                deleteAct = QAction(f"Delete Task: {taskName}", rcmenu)
                deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
                rcmenu.addAction(deleteAct)

            except Exception as e:
                msg = f"Cannot delete {delEntityData['delItemName']}\n\n{str(e)}"
                self.core.popup(msg)
                logger.wraning(f"ERROR:  Cannot delete {delEntityData['delItemName']}. {e}")


    @err_catcher(name=__name__)
    def deleteAssetDepartment(self, origin, rcmenu, pos):

        self.menuContext = "Asset Dept"
        self.loadSettings()

        if self.isDeleteActive():
            try:
                if pos.data() == None:
                    return
                
                #   Gets data from Core
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

                #   Builds delEntityData to be passed to deleteAction
                delEntityData = {}
                delEntityData["projectName"] = projectName
                delEntityData["delItemName"] = f"{asset}_{deptNameFull}"
                delEntityData["deleteList"] = deleteList
                delEntityData["questText"] = questionText
                delEntityData["questTitle"] = windowTitle

                #   Adds Right Click Item
                deleteAct = QAction(f"Delete Dept: {deptNameFull}", rcmenu)
                deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
                rcmenu.addAction(deleteAct)

            except Exception as e:
                msg = f"Cannot delete {delEntityData['delItemName']}\n\n{str(e)}"
                self.core.popup(msg)
                logger.wraning(f"ERROR:  Cannot delete {delEntityData['delItemName']}. {e}")


    @err_catcher(name=__name__)
    def deleteAssetTask(self, origin, rcmenu, pos):

        self.menuContext = "Asset Task"
        self.loadSettings()

        if self.isDeleteActive():
            try:
                if pos.data() == None:
                    return
                
                #   Gets data from Core
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

                #   Builds delEntityData to be passed to deleteAction
                delEntityData = {}
                delEntityData["projectName"] = projectName
                delEntityData["delItemName"] = f"{asset}_{curDep}_{taskName}"
                delEntityData["deleteList"] = deleteList
                delEntityData["questText"] = questionText
                delEntityData["questTitle"] = windowTitle

                #   Adds Right Click Item
                deleteAct = QAction(f"Delete Task: {taskName}", rcmenu)
                deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
                rcmenu.addAction(deleteAct)

            except Exception as e:
                msg = f"Cannot delete {delEntityData['delItemName']}\n\n{str(e)}"
                self.core.popup(msg)
                logger.wraning(f"ERROR:  Cannot delete {delEntityData['delItemName']}. {e}")


    #   Called with Callback - Product Browser
    @err_catcher(name=__name__)
    def deleteProduct(self, origin, viewUi, pos, rcmenu):

        self.menuContext = "Product"
        self.loadSettings()

        if self.isDeleteActive():
            try:
                version = origin.getCurrentVersion()
                if not version:
                    return

                #   Checks which Table was called
                if viewUi == origin.tw_identifier:
                    listType = "identifier"
                elif viewUi == origin.tw_versions:
                    listType = "version"

                if listType == "identifier":
                    #   Retrieves Product Data
                    item = origin.tw_identifier.itemAt(pos)
                    prodData = item.data(0, Qt.UserRole)

                elif listType == "version":
                    #   Gets Source Path from Last Column - Assuming path is always last Column
                    row = viewUi.rowAt(pos.y())
                    numCols = viewUi.columnCount()
                    if row >= 0:
                        sourcePath = viewUi.item(row, numCols - 1).text()
                    #   Retrieves File Info        
                    infoFolder = self.core.products.getVersionInfoPathFromProductFilepath(sourcePath)
                    infoPath = self.core.getVersioninfoPath(infoFolder)
                    prodData = self.core.getConfig(configPath=infoPath)

                    #   Retrieves Product Data
                    data = origin.getCurrentProduct()

                    version = prodData["version"]
                    prodData["path"] = os.path.join(data["path"], version)


                prodData["project_name"] = self.core.projectName

                product = prodData["product"]
                path = prodData["path"]

                if prodData["type"] == "asset":
                    asset = prodData["asset"]
                    entity = f"{asset}_{product}"
                else:
                    sequence = prodData["sequence"]
                    shot = prodData["shot"]
                    entity = f"{sequence}_{shot}_{product}"


                deleteList = []
            #   Retrieves Locations Data
                saveLocs = origin.core.paths.getExportProductBasePaths()

            #   Constructs deleteList with Location Names and Paths
                for loc in saveLocs:
                    newPath = self.core.convertPath(path, target=loc)
                    if os.path.exists(newPath):
                        locItem = {"location": loc, "path": newPath}
                        deleteList.append(locItem)

                #   Builds delEntityData to be passed to deleteAction
                delEntityData = {}
                delEntityData["projectName"] = prodData["project_name"]
                delEntityData["deleteList"] = deleteList

                if listType == "identifier":
                    questionText = f"Are you sure you want to Delete:\n\nProduct: {product}"
                    windowTitle = f"Delete Product {product}"

                    delEntityData["delItemName"] = entity
                    delEntityData["questText"] = questionText
                    delEntityData["questTitle"] = windowTitle

                    #   Add Command to Right-click Menu
                    deleteAct = QAction(f"Delete {product}", viewUi)
                    deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
                    rcmenu.addAction(deleteAct)

                elif listType == "version":
                    questionText = f"Are you sure you want to Delete:\n\nProduct Version: {version}"
                    windowTitle = f"Delete Product Version {version}"

                    delEntityData["delItemName"] = f"{entity}_{version}"
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

            except Exception as e:
                msg = f"Cannot delete {delEntityData['delItemName']}\n\n{str(e)}"
                self.core.popup(msg)
                logger.wraning(f"ERROR:  Cannot delete {delEntityData['delItemName']}. {e}")


    @err_catcher(name=__name__)
    def deleteMedia(self, origin, rcmenu, lw, item, path):
        if not item:
            return
        
        self.loadSettings()
        self.menuContext = "Media"

        if self.deleteActive:
            try:
                #   From where right-click originated
                if lw == origin.tw_identifier:
                    itemName = item.text(0)
                else:
                    itemName = item.text()

                entity = origin.getCurrentEntity()

                if not entity:
                    return
                
                #   Obtaining data based on where right-click originated
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

            except Exception as e:
                msg = f"Cannot delete {delEntityData['delItemName']}\n\n{str(e)}"
                self.core.popup(msg)
                logger.wraning(f"ERROR:  Cannot delete {delEntityData['delItemName']}. {e}")


    @err_catcher(name=__name__)                                             #   TODO MORE INFO FOR LIBRARY ITEMS
    def deleteLibraryItem(self, origin, menu):

        if not type(origin).__name__ == "TextureWidget":
            return
        
        self.menuContext = "Library Item"
        self.loadSettings()

        if self.deleteActive:
            try:

                # self.core.popup(f"accessibleName: {origin.accessibleName()}")                       #   BLANK
                # self.core.popup(f"data:  {origin.data}")                                            #   RETURNS FILEPATH UNDER "filepath": ....
                # self.core.popup(f"devType:  {origin.devType()}")                                    #   RETURNS 1
                # self.core.popup(f"existsOnDisk:  {origin.existsOnDisk()}")                          #   RETURNS TRUE
                # self.core.popup(f"getPaths:  {origin.getPaths()}")                                  #   RETURNS FILEPATH
                # self.core.popup(f"getTextureDisplayName:  {origin.getTextureDisplayName()}")        #   RETURNS FILENAME
                # self.core.popup(f"objectName:  {origin.objectName()}")                              #   RETURNS "texture"
                # self.core.popup(f"path:  {origin.path}")                                            #   RETURNS PATH
                # self.core.popup(f"paths:  {origin.paths}")                                          #   RETURNS NONE
                # self.core.popup(f"pos:  {origin.pos()}")                                            #   RETURNS A POSITION
                # self.core.popup(f"refreshUi:  {origin.refreshUi()}")                                #   REFRESHES


                deleteList = []

                projectName = self.core.projectName
                # filename = origin.getTextureDisplayName()
                filePath = origin.path
                filename = os.path.basename(filePath)
                fileDir = os.path.basename(os.path.dirname(filePath))

                #   Constructs deleteList with Location Names and Paths
                locItem = {"location": fileDir, "path": filePath}
                deleteList.append(locItem)



                questionText = (f"Are you sure you want to Delete Library Item:\n\n"
                                f"{filename}"
                                )
                windowTitle = f"Delete Library Item"                                       #   TODO

                #   Builds delEntityData to be passed to deleteAction
                delEntityData = {}
                delEntityData["projectName"] = projectName
                delEntityData["delItemName"] = f"{projectName}_{filename}"
                delEntityData["deleteList"] = deleteList
                delEntityData["questText"] = questionText
                delEntityData["questTitle"] = windowTitle

                #   Adds Right Click Item
                deleteAct = QAction("Delete Item", menu)
                deleteAct.triggered.connect(lambda: self.deleteAction(delEntityData))
                menu.addAction(deleteAct)

            except Exception as e:
                msg = f"Cannot delete {delEntityData['delItemName']}\n\n{str(e)}"
                self.core.popup(msg)
                logger.wraning(f"ERROR:  Cannot delete {delEntityData['delItemName']}. {e}")


    #   Used to Remove Item from Specific Location
    @err_catcher(name=__name__)
    def removeAction(self, delEntityData, loc):
        logger.debug("Reformatting Delete Data for Remove Action")

        #   Alters Data to reflect location
        delEntityData["deleteList"] = [item for item in delEntityData["deleteList"] if item["location"] == loc["location"]]
        delEntityData["delItemName"] = f"{delEntityData['delItemName']} ({loc['location']})"
        delEntityData["questText"] = delEntityData["questText"].replace("Delete", "Remove")
        delEntityData["questTitle"] = delEntityData["questTitle"].replace("Delete", "Remove")
        
        self.deleteAction(delEntityData)


    @err_catcher(name=__name__)
    def deleteAction(self, delEntityData):

        projectName = delEntityData["projectName"]      #   PROJECT NAME
        delItemName = delEntityData["delItemName"]      #   ENTITY NAME
        deleteList = delEntityData["deleteList"]        #   ITEMS IN DIR TO MOVE
        questTitle = delEntityData["questTitle"]        #   FOR QUESTION POPUP
        questText = delEntityData["questText"]          #   FOR QUESTION POPUP

        # self.core.popup(f"deleteList: {deleteList}")                                      #    TESTING

        #   Make timestamp
        currentTime = datetime.now()
        timestamp = currentTime.strftime("%m/%d/%y %H:%M")

        #   Asks Popup Question
        result = self.core.popupQuestion(questText, title=questTitle)

        if result == "Yes":
            logger.debug(f"Deleting: {delItemName}")

            try:
                #   Temp disable Media Player to allow for deletion
                if self.menuContext == "Media":
                    viewOrigState = self.mediaViewer.state
                    self.mediaViewer.state = "disabled"
                    self.mediaViewer.updatePreview()

                origLocList = []
                destDir, delItemName = self.ensureDirName(delItemName)

                #   For cases that just delete files in a Dir
                if self.menuContext in ["Scene Files", "Library Item"]:
                    for item in deleteList:
                        #   Make dict with location details
                        sourceItem = item["path"]
                        destItem = os.path.join(destDir, item["location"])
                        subDir = os.path.join(destDir, item["location"])

                        # self.core.popup(f"from: {sourceItem} to {destItem}")                                      #    TESTING

                        if not os.path.exists(subDir):
                            os.mkdir(subDir)
                        shutil.move(sourceItem, destItem)
                        origLocList.append(item)

                else:
                    #   For cases that delete an entire Dir
                    for item in deleteList:
                        sourceItem = item["path"]
                        destItem = os.path.join(destDir, item["location"])

                        # self.core.popup(f"from: {sourceItem} to {destItem}")                                      #    TESTING

                        shutil.move(sourceItem, destItem)                               #   TODO DO I NEED MKDIR HERE ???
                        origLocList.append(item)

                #   Makes item dict to be saved in "Items" in settingsFile
                fileInfo = {
                    "Project": projectName,
                    "Type": self.menuContext,
                    "Entity": delItemName,
                    "Deleted": timestamp,
                    "UID": self.generateUID(),
                    "OriginalLocation": origLocList,
                    "DeletedLocation": destDir,
                    }
                
                self.delFileInfoList.append(fileInfo)

                #   Restore Media Player to orignal state
                if self.menuContext == "Media":
                    self.mediaViewer.state = viewOrigState
                    self.mediaViewer.updatePreview()

                logger.debug(f"SUCCESS: {delItemName} deleted")
                self.saveSettings()
                #   Refresh ProjectBrowser
                self.core.pb.refreshUI()

            except Exception as e:
                if self.menuContext == "Product":
                    self.core.popup(f"Unable to Delete: {delItemName}\n\nTry closing the Viewer Window\n\nError:\n\n{e}")
                    logger.warning(f"ERROR: Unable to Delete: {delItemName}\n\nTry closing the Viewer Window\n\nError:\n\n{e}")


                elif self.menuContext == "Media":
                    self.core.popup(f"Unable to Delete: {delItemName}\n\nTry disabling the Media Viewer\n\nError:\n\n{e}")
                    logger.warning(f"ERROR: Unable to Delete: {delItemName}\n\nTry disabling the Media Viewer\n\nError:\n\n{e}")

                else:
                    self.core.popup(f"Unable to Delete: {delItemName}\n\n{e}")
                    logger.warning(f"ERROR: Unable to Delete: {delItemName}\n\n{e}")

                # shutil.rmtree(subDir)                                                         #   TODO DELTE DIR IF FAIL
    

    @err_catcher(name=__name__)                 #   TODO MAKE SURE DIRS EXIST -- Maybe do not show the Delete option if not.
    def purgeFiles(self, mode=None):

        #   Purges all items
        if mode == "all":
            logger.debug("Purging All Files")
            questionText = f"Are you sure you want to Permanently Delete all Items?\n\nThis is not Reversable."
            result = self.core.popupQuestion(questionText, title="Permanently Delete Files")

            if result == "Yes":
                try:
                    # Iterate over all files and subdirectories in the given directory
                    for root, dirs, files in os.walk(self.delDirectory, topdown=False):
                        for file in files:
                            file_path = os.path.join(root, file)
                            os.remove(file_path)

                        for dir_name in dirs:
                            dir_path = os.path.join(root, dir_name)
                            shutil.rmtree(dir_path)

                    #   Clear list
                    self.delFileInfoList = []
                    logger.debug("SUCCESS:  Purged All Files")
                    self.saveSettings()
                    self.refreshList()

                except Exception as e:
                    logger.warning(f"ERROR: Unable to Purge Files.  {e}")
            else:
                return
            

            #   TODO
            
            # self.waitingCircle = PrismWaitingCircleManager()
            # self.waitingCircle.start()      #   TESTING FOR WAITING CIRCLE
            # time.sleep(5)                   #   TESTING
            # self.waitingCircle.stop()       #   TESTING



        #   Purges selected item
        elif mode == "single":
            selectedRow = self.table_delItems.currentRow()
            #   Return if no row selected
            if selectedRow == -1:
                return

            questionText = f"Are you sure you want to Permanently Delete the Selected Item?\n\nThis is not Reversible."
            result = self.core.popupQuestion(questionText, title="Permanently Delete Files")

            if result == "Yes":
                try:
                    # Deleting selected files in the table
                    selectedUID = self.table_delItems.item(selectedRow, 4).text()

                    # Find the dictionary in the list with the matching UID
                    purgeItem = self.getItemFromUID(selectedUID)
                    logger.debug(f"Purging {purgeItem['Entity']}")

                    if purgeItem:
                        itemPath = purgeItem["DeletedLocation"]
                        if os.path.exists(itemPath):
                            shutil.rmtree(itemPath)

                        # Remove the matched item from the list
                        self.delFileInfoList.remove(purgeItem)

                        logger.debug(f"SUCCESS: Purged {purgeItem['Entity']}")
                        self.saveSettings()
                        self.refreshList()

                except Exception as e:
                    logger.warning(f"ERROR: Unable to Purge {purgeItem['Entity']}.  {e}")

            else:
                return


    @err_catcher(name=__name__)                             #   TODO MORE ROBUST FILE CHECKING BEFORE DELETE
    def restoreSelected(self):                              #   TODO ADD EXECEPTIONS

        selectedRow = self.table_delItems.currentRow()
        #   Return if no row selected
        if selectedRow == -1:
            return

        questionText = (f"Are you sure you want to Restore the selected Entity to the original location?\n\n"
                        "The restore may overwrite any files with the same name as the deleted files."                  #   TODO TEXT ABOUT RESTORE.
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
                logger.debug(f"Restoring {restoreEntity['Entity']}")
                try:
                    #   For case where restoring files to a Dir
                    if restoreEntity["Type"] in ["Scene Files", "Library Item"]:                  #   TODO CLEANUP
                        for origItem in origList:
                            origLocName = origItem["location"]
                            origLocPath = origItem["path"]
                            origLocDir = os.path.dirname(origLocPath)
                            delLocBase = restoreEntity["DeletedLocation"]
                            delLocation = os.path.join(delLocBase, origLocName)
                            
                            if not os.path.exists(origLocDir):
                                os.mkdir(origLocDir)
                            
                            for item in os.listdir(delLocation):
                                delItemPath = os.path.join(delLocation, item)
                                origItemPath = os.path.join(origLocDir, item)

                                #   If file exists it will abort
                                if os.path.isfile(origItemPath):
                                    logger.debug(f"Unable to Restore--Item already exists:  {restoreEntity['Entity']}")
                                    title = "Unable to Restore"
                                    text = (f"{restoreEntity['Type']}: {item}\n\n"
                                            "already exists in Restore Location."                   #   TODO
                                            )
                                    self.core.popup(text=text, title=title)
                                    return

                            for item in os.listdir(delLocation):
                                delItemPath = os.path.join(delLocation, item)
                                origItemPath = os.path.join(origLocDir, item)                           
                                try:
                                    shutil.move(delItemPath, origLocDir)
                                except Exception as e:
                                    self.core.popup(f"{e}")                         #   TODO
                                    logger.debug(f"Restore Error: {e}")

                    else:
                        #   For case that resore entire Dir
                        for origItem in origList:
                            origLocName = origItem["location"]
                            origLocPath = origItem["path"]
                            delLocBase = restoreEntity["DeletedLocation"]
                            delLocation = os.path.join(delLocBase, origLocName)

                            if not os.path.exists(origLocPath):
                                os.mkdir(origLocPath)
                            
                            for item in os.listdir(delLocation):
                                delItemPath = os.path.join(delLocation, item)
                                origItemPath = os.path.join(origLocPath, item)

                                #   If file exists it will abort
                                if os.path.exists(origItemPath):
                                    logger.debug(f"Unable to Restore--Item already exists:  {restoreEntity['Entity']}")
                                    title = "Unable to Restore"
                                    text = (f"{restoreEntity['Type']}\n\n"
                                            "already exists in Restore Location."                   #   TODO
                                            )
                                    self.core.popup(text=text, title=title)
                                    return
                                try:
                                    shutil.move(delItemPath, origLocPath)
                                except Exception as e:
                                    self.core.popup(f"{e}")                             #   TODO
                                    logger.debug(f"Restore Error: {e}")

                    #   Remove item from table
                    self.table_delItems.removeRow(selectedRow)

                    # Remove the matched item from the list
                    self.delFileInfoList.remove(restoreEntity)

                    if os.path.exists(delLocBase):
                        shutil.rmtree(delLocBase)

                    logger.debug(f"SUCCESS: Restored {restoreEntity['Entity']}")
                    self.saveSettings()
                    self.calcDelDirSize()
                    self.core.pb.refreshUI()

                except Exception as e:
                    logger.warning(f"ERROR: Unable to Restore: {e}")
            else:
                pass


    @err_catcher(name=__name__)
    def generateUID(self):
        #   Generate UID using current datetime to the nearest tenth of a second
        currentDatetime = datetime.now()
        UID = currentDatetime.strftime("%m%d%y%H%M%S") + str(currentDatetime.microsecond // 100000)

        logger.debug("Creating UID")

        return UID


    @err_catcher(name=__name__)
    def ensureDirName(self, delItemName):

        #   Checks if Dir name already exists, and will append _# if it does
        destDir = os.path.join(self.delDirectory, delItemName)

        if not os.path.exists(destDir):
            os.mkdir(destDir)
            logger.debug(f"Creating Deleted Item: {delItemName}")
        else:
            #   Checks if an appened deleted item already exists
            match = re.match(r"_(\d+)$", destDir)
            if match:
                baseDir = match.group(1)
            else:
                baseDir = destDir

            #   Appends suffix
            newSuffix = 0
            while os.path.exists(destDir):
                newSuffix += 1
                destDir = f"{baseDir}_{newSuffix}"

            delItemName = f"{delItemName}_{newSuffix}"
            os.mkdir(destDir)

            logger.debug(f"Item already exists in Delete Dir.  Creating duplicate: {delItemName}")

        return destDir, delItemName
    

    @err_catcher(name=__name__)
    def getItemFromUID(self, UID): 
        #   Returns full item details from matching UID
        try:  
            selectedItem = next((item for item in self.delFileInfoList if item["UID"] == UID), None)
            return selectedItem
        except:
            return None
    

    @err_catcher(name=__name__)                 #   TODO ENSURE SYNC BETWEEN DIR AND LIST and MAYBE READ CURRENT FILES IN DIR
    def refreshList(self):
        #   To resync table in menu
        self.table_delItems.clearContents()
        self.loadSettings()
        self.calcDelDirSize()
        self.table_delItems.viewport().update()
        logger.debug("Delete Dir List Refreshed")


    @err_catcher(name=__name__)
    def calcDelDirSize(self):
        totalSize = 0
        try:
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
        except:
            pass


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




class AutoPurger(object):

    timerRunning = False

    def __init__(self, core, settingsFile, delDirectory):
        super().__init__()

        self.core = core
        #   Timer for directory check
        self.timer = QTimer()
        self.timer.timeout.connect(self.checkDir)

        #   Interval for AutoPurger to check DeleteDir for purge items.
        #   This is NOT the duration to keep the items before purging
        self.dirCheckInterval = 600  # seconds  (10 mins)
        
        self.settingsFile = settingsFile
        self.delDirectory = delDirectory

        #   Stops timer thread when Prism is quitting
        QCoreApplication.instance().aboutToQuit.connect(self.stop)


    def checkDir(self):
        logger.info(f"AutoPurge--Checking directory: {self.delDirectory}")

        #   Calculates cutoff time based on interval and present time
        delTimeCutoff_str = self.getDelTimeCutoff()
        logger.debug(f"Files older than {delTimeCutoff_str} will be purged.")

        #   Deletes the deleted files
        self.executePurge(delTimeCutoff_str)

        # Schedule the next check only if the timer hasn't been started by another instance
        if not AutoPurger.timerRunning:
            logger.debug(f"Next AutoPurge check in {self.dirCheckInterval / 60} mins.")
            self.timer.start(self.dirCheckInterval * 1000)  # Convert seconds to milliseconds
            AutoPurger.timerRunning = True


    def getDelTimeCutoff(self):
        #   Returns the date/time based on the hours interval selected in the menu
        currentDateTime = datetime.now()
        delTimeCutoff = currentDateTime - timedelta(hours=self.deleteInterval)
        delTimeCutoff_str = delTimeCutoff.strftime('%m/%d/%y %H:%M')

        return delTimeCutoff_str


    def executePurge(self, delTimeCutoff_str):
        #   Opens settingsFile
        with open(self.settingsFile, 'r') as file:
            data = json.load(file)

        itemsList = data.get("Items", [])

        #   Retrieves item deleted times
        itemsToDelete = []
        for item in itemsList:
            deletedTime_str = item.get("Deleted", "")

            # Convert the "Deleted" date strings to datetime
            delTimeCutoff = datetime.strptime(delTimeCutoff_str, '%m/%d/%y %H:%M')
            deletedTime = datetime.strptime(deletedTime_str, '%m/%d/%y %H:%M')

            # Check if the item's "Deleted" date is less than delTimeCutoff
            if deletedTime < delTimeCutoff:
                itemsToDelete.append(item)

        for item in itemsToDelete:
            try:
                #   Delete matching items
                logger.debug(f"Purging: {item['DeletedLocation']}")
                shutil.rmtree(item['DeletedLocation'])
                logger.info(f"SUCCESS: Purged {item['DeletedLocation']}")

                # Remove the deleted item from the data dictionary
                itemsList.remove(item)

            except Exception as e:
                logger.warning(f"Unable to purge: {item['DeletedLocation']}")
                logger.warning(e)

        # Save the updated data back to the settings file
        data["Items"] = itemsList
        with open(self.settingsFile, 'w') as file:
            json.dump(data, file, indent=4)


    def run(self, interval):
        self.deleteInterval = interval
        logger.info("Starting AutoPurge Timer")
        logger.info(f"AutoPurge Interval: {interval}")
        logger.info(f"Deleted files older than {interval}hrs will be purged")

        self.checkDir()


    def isRunning(self):
        return self.timer.isActive()


    def stop(self):
        self.timer.stop()
