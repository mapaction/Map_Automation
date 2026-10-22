EXAMPLE PROJECTS FOR TESTING
============================

The example projects (cut-down copies of real Crash Move Folders) are too
large for git, so they are kept on MapAction's Google Drive. Git ignores
everything in this folder except this file.

Downloads
---------

2026-ven-001 (Venezuela, about 165 MB zipped, 410 MB unzipped)
    https://drive.google.com/file/d/1iUS69OUgAX1vLjwRQUhNChAuNPcb4qYh/view?usp=sharing


1) Download
-----------

Download the zip file(s) above and unzip each one into this folder
(cmf_examples). Each zip holds one top-level folder named after the project.

Careful: Windows "Extract All" suggests a folder named after the zip, which
gives a doubled folder (cmf_examples\2026-ven-001\2026-ven-001). Extract to
cmf_examples itself, or move the inner folder up a level.


2) Check the folder structure
-----------------------------

It should look like this (only the main folders are shown):

    Map_Automation\                      (the repository)
      map_automation_pro.ipynb
      map_automation_pro_lib.py
      map_automation_pro_config.py
      cmf_examples\
        README.txt                       (this file)
        2026-ven-001\
          cmf_description.json
          event_description.json
          TEST_ENVIRONMENT.txt
          GIS\
            2_Active_Data\               (the GIS data: 202_admn, 207_carto, ...)
            3_Mapping\
              31_Resources\
              32_Map_Templates\
              33_Map_Projects\           (empty: the script's .aprx outputs)
              34_Map_Products_MapAction\ (empty: the script's JPEG outputs)
            6_Pro_Default_Files\
            7_Python\
              71_Jupyter\
                map_automation\          (empty until step 3)

event_description.json and the GIS folder must be directly inside
2026-ven-001, not one level further down.


3) Set up the symlinks
----------------------

The notebook and its two Python files live at the top of the repository.
Each example project needs links (symlinks) to them in its
GIS\7_Python\71_Jupyter\map_automation folder, so it always runs the
current version.

Creating symlinks on Windows needs Developer Mode turned on:
Settings > System > For developers > Developer Mode.

Then, in PowerShell, from the repository folder (Map_Automation):

    Set-Location cmf_examples\2026-ven-001\GIS\7_Python\71_Jupyter\map_automation
    cmd /c mklink map_automation_pro.ipynb ..\..\..\..\..\..\map_automation_pro.ipynb
    cmd /c mklink map_automation_pro_lib.py ..\..\..\..\..\..\map_automation_pro_lib.py
    cmd /c mklink map_automation_pro_config.py ..\..\..\..\..\..\map_automation_pro_config.py
    Get-ChildItem

(The same three mklink lines work in a Command Prompt, without "cmd /c".
PowerShell's own New-Item -ItemType SymbolicLink needs admin rights, so use
mklink.)

Get-ChildItem should list the three files as links (mode "-a---l").
For another example project, replace 2026-ven-001 with its folder name.

Then run the test as described in the repository's README.md
("Running the notebook").
