# **DeleteFunctions plugin for Prism Pipeline 2**
A plugin to be used with version 2 of Prism Pipeline 

Prism automates and simplifies the workflow of animation and VFX projects.

You can find more information on the website:

https://prism-pipeline.com/


## **Plugin Usage**

DeleteFunctions adds the ability to delete project items throughout the Prism2 UI.  This plugin allows deletion of Scene Files, Products, Departments, Tasks, Versions, Media, and Library items without using Windows File Explorer.  This plugin also adds Restore functions to un-delete items if needed.

The delete functions are in the right-click menu of most types of items.  If an item exists in multiple locations, such as a global version and a local version, a user has the option to delete the entire version, or just remove from a specific location.  

![Delete Task](https://github.com/AltaArts/DeleteFunctions--Prism-Plugin/assets/86539171/4219e882-c4f4-45b5-b627-c473a469acf7) ![RemoveMenu](https://github.com/AltaArts/DeleteFunctions--Prism-Plugin/assets/86539171/758b77af-6519-4b7e-a5e3-28bcf47bca18)




A new menu tab called Delete Functions will be added to the User Settings.  In this menu a user has the ability to enable/disable the delete functions globally.  A directory needs to be selected to hold the deleted items until purging.  If the folder is unavailable, the delete functions will be disabled to prevent deleting to a unreachable location.

![Prism-DeleteMenu](https://github.com/AltaArts/DeleteFunctions--Prism-Plugin/assets/86539171/71ae8313-5735-4423-8c16-ee49339d65ae)

Deleted files will be moved to the user-selected holding directory to allow for restoring the deleted files if needed.  Deleting subsequent files with the same name is possible (ie deleting v0002, creating a new v0002, and then deleting that).  The files with the same name will be renamed with a suffix, but the restore function will place them back to the original location with the original name.  If a file with the same name exists in the original location, the file will NOT be overwritten and the restore will abort.

Deleted files in the holding directory can be periodically purged based on a duration specifies in the use Settings, or manual purged at any time.  If the hours timer is set to Zero, the autopurging will be disabled and deleted files held until manual deletion.

. 




## **Installation**

This plugin is for Windows only, as Prism2 only supports Windows at this time.

You can either download the latest stable release version from: [Latest Release](https://github.com/AltaArts/DeleteFunctions--Prism-Plugin/releases/latest)

or download the current code zip file from the green "Code" button above or on [Github](https://github.com/JBreckeen/DeleteFunctions--Prism-Plugin/tree/main)

Copy the directory named "DeleteFunctions" to a directory of your choice, or a Prism2 plugin directory.

Prism's default plugin directories are: *{installation path}\Plugins\Apps* and *{installation Path}\Plugins\Custom*.

It is suggested to have all custom plugins in a seperate folder suchs as: *{drive}\ProgramData\Prism2\plugins\CustomPlugins*

You can add the additional plugin search paths in Prism2 settings.  Go to Settings->Plugins and click the gear icon.  This opens a dialogue and you may add additional search paths at the bottom.

Once added, you can either restart Prism2, or select the "Add existing plugin" (plus icon) and navigate to where you saved the DeleteFunctions folder.


## **Issues / Suggestions**

For any bug reports or suggestions, please add to the GitHub repo.
