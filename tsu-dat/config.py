#!/usr/bin/env python

"""
Tsu-DAT configuration.
"""


import os
import sys

import log

# used?
PrintLog = True

# the application name(s) and version
AppName = 'Tsu-DAT'
AppNameLower = AppName.lower()
AppVersion = '1.0'

# log details
LogFilename = '%s.log' % AppNameLower
DefaultLogLevel = log.Log.DEBUG

# set data base directory for each particular platform
if sys.platform == 'win32':
    (drive, _) = os.path.splitdrive(sys.path[0])
    AppBase = '%s\\' % drive
    DefaultConfigSaveDir = r'C:\\'
    GenSaveDir = r'C:\temp'

    # set PATH to find *.pyd files
    os.environ['PYTHONPATH'] = os.path.join(AppBase,
                                            r'Python25\Lib\site-packages')
    os.environ['PATH'] = (os.path.join(AppBase, 'Python25') + ';' +
                          os.path.join(AppBase, r'MinGW\bin') + ';' +
                          os.path.join(AppBase, r'netcdf4\bin') + ';' +
                          os.path.join(AppBase, r'netcdf4n') + ';' +
                          os.environ['PATH'])
else:
    # we assume a linux box
    hostname = os.uname()[1]
    if hostname == 'PC-32572':
        # my personal linux box
        AppBase = '/mnt/tsu-dat'
    else:
        curr_dir = os.getcwd()
        curr_dir = os.path.dirname(curr_dir)
        AppBase = os.path.dirname(curr_dir)
    DefaultConfigSaveDir = '/tmp'
    GenSaveDir = '/tmp'

    # set PATH to find *.pyd files
    PythonPath = os.path.join(AppBase, 'Python25/Lib/site-packages')
    os.environ['PYTHONPATH'] = PythonPath
    os.environ['PATH'] = PythonPath + ':' + os.environ['PATH']

# various identifying strings
FrameTitle = ('%s v%s' % (AppName, AppVersion))
CopyrightTitle = ('%s v%s Copyright Statement' % (AppName, AppVersion))
AboutTitle = ('About %s v%s' % (AppName, AppVersion))
PreferencesTitle = ('%s v%s Preferences' % (AppName, AppVersion))

# base of everything related to data and code
DataBase = os.path.join(AppBase, 'Tsu-DAT_Data')
Code = os.path.join(AppBase, 'Tsu-DAT', 'tsu-dat')
CodeGraphics = os.path.join(Code, 'graphics')

# define paths to the save config file
CfgSaveFile = os.path.join(DataBase, '.%s' % AppNameLower)

# define paths to all required files/directories
quake_base = os.path.join(DataBase, 'earthquake_data')

MultimuxDirectory = os.path.join(quake_base, 'multimux')
MuxDirectory = os.path.join(quake_base, 'mux')
TFilesDirectory = os.path.join(quake_base, 'Tfiles')
DeagPointsDirectory = os.path.join(DataBase, 'deag_points')
TilesDirectory = os.path.join(DataBase, 'tiles.PUBLISH')
HazardPointsFile = os.path.join(DataBase, 'hazard.points')
ReturnPeriodsFile = os.path.join(DataBase, 'return_periods.txt')
WaveAmplitudeFile = os.path.join(quake_base, 'hazmap_files', 'hazard_maps',
                                 'o_amp_green')
SubfaultIdZoneFile = os.path.join(DataBase, 'subfaults.txt')
EventID2ZoneFile = os.path.join(MultimuxDirectory, 'fault_list_extra.txt')
EventTFile = os.path.join(TFilesDirectory, 'T-00000')

FaultNameFilename = 'fault_list.txt'
EventFile = 'event.lst'

WHvRPHazardGraphDir = os.path.join(DataBase, 'wh_rp_hazard_graphs')
WHvRPHazardGraphFilemask = '%s_%s.png'

corporate_image = os.path.join(CodeGraphics, 'corporate.gif')
TsuDatBackgroundImage = os.path.join(CodeGraphics, 'tsu-dat.png')

# mask for results directory name
ResultsDirMask = 'Results_Australia_%d_%.2f_%.2f'

# names of data files
InvallFilename = 'i_invall'

# various generated filenames
FaultXYFilename = 'fault.xy'
QuakeProbFilename = 'quake_prob.txt'

# path to the user guide
UserGuideFile = os.path.join(AppBase, 'Tsu-DAT_User_Guide.pdf')

# set up log file
HomeDir = os.path.expanduser('~')
LogPath = os.path.join(HomeDir, LogFilename)
log = log.Log(LogPath, DefaultLogLevel, append=False)

# log some values here - debug
log('')
log('AppBase=%s' % AppBase)
log('DefaultConfigSaveDir=%s' % DefaultConfigSaveDir)
log('GenSaveDir=%s' % GenSaveDir)
log('PYTHONPATH=%s' % os.getenv('PYTHONPATH'))
log('PATH=%s' % os.getenv('PATH'))
log('MultimuxDirectory=%s' % MultimuxDirectory)
log('MuxDirectory=%s' % MuxDirectory)
log('TFilesDirectory=%s' % TFilesDirectory)
log('DeagPointsDirectory=%s' % DeagPointsDirectory)
log('TilesDirectory=%s' % TilesDirectory)
log('HazardPointsFile=%s' % HazardPointsFile)
log('ReturnPeriodsFile=%s' % ReturnPeriodsFile)
log('WaveAmplitudeFile=%s' % WaveAmplitudeFile)
log('SubfaultIdZoneFile=%s' % SubfaultIdZoneFile)
log('EventID2ZoneFile=%s' % EventID2ZoneFile)
log('EventTFile=%s' % EventTFile)
log('')

