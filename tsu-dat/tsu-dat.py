#!/usr/bin/env python

"""The TIRM/PTHA-DAT/DAFT/NANKAI/Tsu-DAT application."""

######
# Terminology:
#   RP     Return Period
#   WH     Wave Height
#   HP     Hazard Point
######


# do this first so we can log import errors
import os
import config as cfg
import log
log = log.Log(cfg.LogFilename, cfg.DefaultLogLevel, append=False)

import sys
import os
import re
import math
import shutil
import time
import subprocess
import ConfigParser
import wx
import wx.html
import webbrowser
import tempfile
import Image
# get pickler, try for 'C' pickler
try:
    import cPickle as pickle
except ImportError:
    import pickle
# get module handling creation of icon image from string data
Imported_PyEmbeddedImage = True
try:
    from wx.lib.embeddedimage import PyEmbeddedImage
except ImportError:
    Imported_PyEmbeddedImage = False

import pyslip
import util
import select_zone
import get_hp_events as ghe
import list_quakes as lq
import multimux as mmx
import polygon
import dataobj
import execute_tail_log as etl


# set platform-dependent sizes
if sys.platform == 'win32':
    CopyrightSize = (800, 415)
    AboutSize = (800, 420)
    SummaryDialogSize = (800, 450)
    GraphSize = (600, 560)
else:
    CopyrightSize = (800, 400)
    AboutSize = (800, 435)
    SummaryDialogSize = (800, 425)
    GraphSize = (600, 515)

# estimate fudge factor (power law exponent)
EstimateFudgeFactor = 2.1

# size of save directory path text box
SavedirSize = (500, -1)

# max difference in RP interpolation indices before warning
MaxNowarnRPRange = 4

# level+point of initial display
InitViewLevel = 3
InitViewLon = 133.9
InitViewLat = -27.4
InitViewPosition = (InitViewLon, InitViewLat)

# the default waveheight delta
DefaultWaveHeightDelta = '0.05'

# flag = True of project is changed and unsaved
DirtyProject = False

# the number of decimal places in a lon/lat display
LonLatPrecision = 3

# the project default save file
# TODO: should be $HOME/.save.tsu-dat - Windows?
DefaultSaveFile = '.save.%s' % cfg.AppNameLower

# the project user save file
ProjectSaveFilename = None

# current project default directory
ProjectDefaultDir = None

# 'save as' dialog wildcard string
SaveAsWildcard = ('%s project (*.%s)|*.%s|All files (*.*)|*.*'
                  % (cfg.AppName, cfg.AppName.lower(),
                     cfg.AppName.lower()))

# AOI polygon dialog wildcard string
LoadAOIWildcard = ('Polygon file (*.csv)|*.csv|'
                   'Polygon file (*.txt)|*.txt|'
                   'All files (*.*)|*.*')

# format mask for generated point files
PointFileMask = 'points_%04d_%d.txt'

# format mask for generated legend files
LegendFileMask = 'legend_%04d_%d.png'

# startup size of the application
DefaultAppSize = (1024, 768)

# startup size of the application
PreferenceSize = (800, 600)

# how close click has to be before point is selected
# the value is distance squared (degrees^2)
PointSelectDelta = 0.025

# unselected point colour (rgb) and size
PointsColour = '#ff0000'
PointsSize = 3

# Selected HP point colour (rgb) and size
SelectHPPointColour = '#0000ff'
SelectHPPointSize = 5

# 'halo' around subfaults in zone
ZoneSelectColour = '#ccccff'
ZoneSelectSize = 7

# selected subfault stuff
SubfaultPointColour = '#0000ff'
SubfaultPointSize = 9

# Polygon point colour (rgba) and size
AOIPolygonColour = '#0000ff'
AOIPolygonSize = 4
AOITooltipText = 'Shows path to the file defining the area of interest'
AOIPolygonWidth = 1

# ID numbers for menuitems
ID_FILE_NEW = 101
ID_FILE_OPEN = 102
ID_FILE_SAVE = 103
ID_FILE_SAVEAS = 104
ID_FILE_EXIT = 109

#ID_EDIT_UNDO = 201
#ID_EDIT_REDO = 202
#ID_EDIT_NEXT = 203
#ID_EDIT_PREV = 204
ID_EDIT_PREFS = 201

ID_HELP_CONTENTS = 301
ID_HELP_COPYRIGHT = 302
ID_HELP_ABOUT = 309

######
# Various GUI layout constants
######

# set various GUI sizes depending on platform
# in an ideal world, we wouldn't have to do this (sigh)
if sys.platform == 'win32':
    # any Win box
    # point size of text in the listctrl
    ListPointSize = 8
    EventListColumnWidths = [40, 60, 35, 35, 40]
    WaveHeightTextSize = (45, 20)
    # combobox size
    CBSize = (95, 27)
elif sys.platform == 'linux2':
    # point size of text in the listctrl
    ListPointSize = 9
    #EventListColumnWidths = [48, 57, 37, 37, 44]
    EventListColumnWidths = [48, 57, 36, 28, 53]
    WaveHeightTextSize = (50, 25)
    # combobox size
    CBSize = (75, 27)
else:
    raise RuntimeError('platform %s is unrecognised' % sys.platform)

# header strings for event list box
#EventListHeaders = ['ID', 'prob', 'wh', 'Mg', 'slip']
EventListHeaders = ['ID', 'prob', 'wh', 'M', 'slip']

# sizes of various spacers
HSpacerSize = 3         # horizontal in application screen
VSpacerSize = 15         # vertical in control pane

# border width when packing GUI elements
PackBorder = 1

ListCtrlSize = (-1, 150)

# height of the buttons
BtnWidth = 80
BtnHeight = 27
BtnSize = (BtnWidth, BtnHeight)

GenerateButtonColour = wx.Colour(255, 192, 128)

# values for the wave height max/min controls
WaveHeightIntegerWidth = 2
WaveHeightFractionWidth = 2

# the minimum allowed tile level to display
MinTileLevel = 1

# size of 'directed' arrowhead
DirectedArrowheadAngle = 0.45       # radians
DirectedArrowheadSize = 0.02
midArrows = False


# text displayed in the ABOUT dialog
AboutHTMLText = """<html>
<body background="%(background)s">
<h2>About %(name)s v%(version)s</h2>
The Tsunami Data Access Tool (Tsu-DAT) is intended for use by the emergency
management community to understand the offshore tsunami hazard for areas of
interest around Australia and to access the large database of tsunami
waveforms to generate the required input to a detailed tsunami impact assessment
for a given community.
<p>
The offshore tsunami hazard and resultant waveforms are a
result of the probabilistic tsunami hazard assessment (PTHA) of Australia.
This assessment modelled thousands of synthetic tsunami to estimate the
likelihood of a tsunami wave of a given amplitude occurring at an offshore
location, defined at the 100 m depth contour. A database of tsunami waveforms
at points along the 100 m depth contour around the Australian coast was created.
Tsu-DAT allows users to search this database and extract tsunami waveforms
for events of interest. These waveforms are in a format that can be used to
drive more detailed models of tsunami inundation and impact for communities of
interest.
<p>
The basic procedure for accessing the database is contained in the
following steps (full instructions in Chapters 4 and 5 of the User Guide):
<ol>
<li>
Choose an offshore location to obtain data for, usually directly
offshore the community of interest.
</li><li>
Define an offshore wave height range or return period. Choosing one field will
populate the other.
</li><li>
Deaggregate the hazard for your chosen return period to choose which source
zone you would like to choose events from.
</li><li>
Choose one or more events from a list that satisfy the above criteria. This step
may take some time (10 minutes to 2 hours) as a considerable volume of data is
analysed.
</li>
</ol>
</body>
</html>
""" % {'name': cfg.AppName, 'version': cfg.AppVersion,
       'background': cfg.TsuDatBackgroundImage}

# text displayed in the COPYRIGHT dialog
CopyrightHTMLText = """<html>
<body background="%(background)s">

<h1>Copyright statement</h1>
<p>
&copy; Commonwealth of Australia 2010<br>
This work is for internal government use only and no part of this product may be
reproduced, distributed or displayed publicly by any process without the joint
permission of Geoscience Australia and the Attorney-General's Department.
<p>
Requests and enquiries should be directed to the
<blockquote>
Chief Executive Officer<br>
Geoscience Australia<br>
GPO Box 378 Canberra ACT 2601
</blockquote>
and the
<blockquote>
Attorney-General's Department<br>
3-5 National Circuit Barton ACT 2600
</blockquote>
Geoscience Australia and the Attorney-General's Department
have tried to make the information in the product as accurate as possible. 
However, it does not guarantee that the information is totally accurate or
complete.  Therefore, you should not solely rely on this information when
making a commercial decision.
</body>
</html>
""" % {'name': cfg.AppName, 'background': cfg.TsuDatBackgroundImage}

GraphHTMLText = """<html>
<body background="%s">
</html>
"""


################################################################################
# This code was generated by img2py.py
# Embed the ICON image here, so we don't need an external *.ico file.
# Icon image inspired by Hokusai's print "The Great Wave off Kanagawa"
# (kanagawa okinami ura) from the "Thirty-Six Views of Mount Fuji" series.
# http://commons.wikimedia.org/wiki/Image:The_Great_Wave_off_Kanagawa.jpg
################################################################################

if Imported_PyEmbeddedImage:
    def getIcon():
        return PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAABHNCSVQICAgIfAhkiAAAE9JJ"
    "REFUeJzdm3mUXFW1h799q25VV1dXekonIZ0AISOBEAmDIkMYxYBMJvDwMTi854CKspZLng8Z"
    "FUUQZHgoD2Jgia6oRAQJyBRkASEJGU1iSNLEdMZO0nN39VDDvWe/P87tqq5Od+gMgI9d63R3"
    "3XuGvX9nn3323ue0GKOqqogIAJ7nEQo5gIAIjkD9tsWUVR5F484VNLZmmDztQhzHJWgCKCCI"
    "gZXOSk6X0/kMn+GZ9DN0dG/H66wl6jTjOj6OOCgQSnmsLapjVbSWazNn09plCJefQTxRYXv0"
    "DAblPfkne979C2+NbGRo8ZFcF7sOJU+ayUA6jcRiIPRPxoBvoKhor1diAQAkEEIV0wsQxxG2"
    "rZvH0NGn0dmVZnPNcsYfM52KyiqMURBwEHpztVPrMNsyjBg1Et/ziBYVk+puZ+uG15g42qDq"
    "oKkMTiSCiIOPDwht3mhCiQn4dPNWbAlr21dza+XtlJgiOiSNimGWzmKezsMXg5PshEgEVOk1"
    "G/1TKGRLn3qSzWY05ITp6uqkOF7Sb9tMJkMq1cmQIeWoQqq7k1gsjgikSPMPXctvnCd5hF/x"
    "R/0jM2UmqzYvZ9zQUbQ1N1F9xDFBP2k6t8+jbEgcUhmIumjAjyCAT0tngu8Pe5In4nODKQYE"
    "QoTw1QdgskxmXftKNO6C4wwOgAHI6ahfTmfDYtqbN1O/Yy3ZbIbWliasWoCq4rouCSlFFByg"
    "uDhOrWzmp9zFp+RTnOacxsP6P/jqM0tmcW/2XqYddRJ36E+Jhobk+olEo2SlEkVJp7N4voJC"
    "yHFwQg4iDo5j6Ii095oiuFqv4W/6OpVSCcC7+i6fHXIJ4tjlpBw4OWXheuLUE9fNhKKVhMMu"
    "ZeUViAi+7yMieHhclLgIV1xEhHM4h7GM5YdyE6v176RJ55gFuDF8IyhkhwhV1aPtKxG6ks14"
    "6WZAiERdwiHBqLJ6/Q6WrdmGOA4h7eBM/4ICJv8k8/g7q9iZ2ZIb42VeZmJ2Ik7Syy3Xnknb"
    "H5KzOqeoRIQT0mM4q2MCpm08JydOpsSUk0w24Rjh3cPamV4+3bZQBjQ2I8wIdstuEJjGdFZs"
    "nI+uexWmHIeMH8eeLYsQx4AUUe5vhGiUHQ1JnBHnMnJXK+3l3VTG6vh80T08k1ic7zgY84mW"
    "+6mIHsZ/xL5NI42B/XH439QjfCV1NU5p8X4DAJr/hP2QFntFWpUt0+GpCh2eKtfh3WWayCS0"
    "d72J/iT9efP3tciE809N/veJ76DtY4aqDhmi6jiqlUPVvPmWep6nvm/UGNXW2ne04e+/1T3r"
    "n9auu36qGotp5rs3aON7T+kf2r9XMF5P30k/qdrRre1+u5ZqacGY13ZeqWpUfWP7t8X0+b13"
    "KQDg/T7b/G06T5/Whxru0FOzY3PPE23o6W+gVz+JnvoW2lWEKqix5sn+/fSfc4P6RlW7U5pN"
    "+5r5x/p83ZmzNNnerunt81W3vKbza+fod+qv0/E6Qc/T81R9VdPRob5vtN0k9Uxzprrq5oC4"
    "179Xt5sdmvJTusgs1s1+rW3TI7C/NxD7BcAN3g0a1Wju+zkL0Ee/hm4clRc0Vy6+RM2sy9X8"
    "4Y9qFi9R45vc7BvfOh8NDXu0Y/FiWz8SUbNosRqjmupOaqa7SbdtXKp7tm7VVq9FWzqb1fiq"
    "fkfStvdV035a55v5OS1ImISO1JE61UxVFD3WHKuNfmOh0L5R43m5wsPmlzrHPK7DzXAdYUZo"
    "QgvVHWOLqGiZliuKVjagn/9TIKiE1Tz0kBpV7brzDq351hd13a/u0ZqtNeqpqlHVdDql7W1t"
    "heqoqo11a3XX84/ZfqIRNUuXWpACsFRtB8Y32rCnTpOtTWo6OgpmUn3VB9IPqKjkeC4xJSpG"
    "NKpRXWjeVuP3Er6lRU1rq5rWdjWtbSrq502nQVkv61nIQiJEeJuFbJGtAJyn5/I1/z+Zf+lQ"
    "LlgCQ5uAkSPR519Ap05FROj2PbZvWkIiUYGTXE20uIK0VrKzbheHjzmWocOPzFlQY5Td215h"
    "2JPzcG+fA5EIumABevzx/drYTDZNyHEJqYHSsgL76HQqL5S8yPM8T5Qo1+v1fEm+yEJdyEly"
    "Ekt1aX6r7OyE4uKc3xDWXqMJwuTgoyhf1i/lNlkFUI9rVx4GTbvsw7o6NOIijvUEnWwGbV3L"
    "yOHVGLcI6ALponyM0iWZQHhr0hXwTQq3ZmuegaIYDOCMRSixLm0yaYUIuJKgrxkd07mQM4Pe"
    "Xa5yL2dhdCHLWAadoHRaYDMZCDl2LKxf0y8Jggq2YD0gdcPot74NIjlEW5ctw1NFFTrbapk0"
    "fiR+xrOWIBC5vilD2hQK5mVTDEuE0YtOsQ+yWZj9WIBRP/u5qvX6Egnr/roupDMQjUAkgkQi"
    "aMSFiIuJwDfkO0xkEuWmlFejL+FEim27RAI6OnLjhAcCoBANQRsbkTFjkO5uVBUBtn9yGs5p"
    "Edym9ZRUHo2T3opxrF+PWMfEESUcO5xwKD/7FhjFUcWcMhk5+nBk/TZk9mzYsQP9619taNKH"
    "BztlTt79dcMQdvuZPDvURjaAA1+Rr7Jdt4MEdYuKrCa4kYE1oAB8Afn61y1yvo8ccQT1JxxL"
    "6ePfprqsmKYdS9i6+ll27tyN6eWWiwjZrEc0PpzyoSMDsQPJxLF1i4vQV36OVFfZxy++GAx6"
    "MA6upSqGATCF43oJo1YLgmU0KACkbhc884z9Mv1MeGc5bY/eQvHQUoxRhlclqC7r5ugjh+CI"
    "5HhXVULhCMXeKmrWvBIoRmAE/YydSGOgtAQuOiVvqJLJ/QtutE8JqIF6EsAm1vQSJqjjRsCY"
    "QQAQ7OwSqH3HxTN44a0ncaQLBytsrCjMezuEUChQ8kD9RcQGQW6ISaOStGx6lbaWOlKpLjAp"
    "MJ4dI5PFnH9i3kTe/wA6GPmNAd+3/fQuvg8Cn2QKJQoRmlktK/IIqEI4DL7//gCoI1C7Ofc9"
    "snERR084jLFHlueiUOPDhNFgjORsmIjgmwAEFFWHUrMLk1yG8X3Sya04YoMt8Xw4YSIMt8kQ"
    "fj+3Jz2x76VgDPgeeH5hSaXAN9yoN5IQiEoXdbzXa/lJYEf60wBVi34mA3V1yJ0/Qb75zZxm"
    "uSURxhwWw8/6BVrq9Nq9JfiR7LIzLLmg36EsDqG2F0g42xBxcgxpkYv/b9Nt2w0bkKMnocuW"
    "9ahT/wCEwxCJQjSKRiIQjVpLXxJHO5NM9aYwjjiVQC2L8nzkZO1rA1RRR5C770bOOQcZNxa5"
    "5WZ07VoESH3hXPS/rizIGPVLAmqUshK3IES1E6pE3CgiTuE7hfQV55OuGGrrbdyIc/LJcOut"
    "VgsHAEFV8Twvt9wsYKClpYzyjmCiP4qxCptkbrDECvtxevVkhZ8xA/nBD+DthVaVAsbbr7qM"
    "8P3foCdt9n7UA1BfoCQYq+87VYhNGEZy8UM0/fuVeXtw54+Ra67ZBwhasOuoKr7vIQrRaBmf"
    "dmYwCkjQxHZZhKOF/YiNiILBNm+GcWMRIFlVQfiSi8jMPJ3wWccSSTUQSmVRBpj97jREXOtl"
    "7c2jhbq1E8oCj66fPlQVx3FoIoq/uJvhN98Oa9fal1OOQ39xH3ruudY+qEJHEhL5jFMPCM0N"
    "tSRKRxIKuez2V/Jc9DRGaZpixnBGdiVhjUEmC+FwLw0wBu7+WW4lR5++jdBdsyiZVkGsbSeh"
    "dBbkfVT/IElEMMZQqd1kJiXgid9YYwXo2jVw8cX7bNvDW6y4lOZtL6LiEKqvYAYP4Qt0Usvm"
    "0IOIE0XDNkGaA0B27kBmz7YrJOQQLk8QNtlAXXqE/uCE7y2IIpRH62k6+hj8X8+BWMyOnM0O"
    "ogclVlJBvPJEdm96iWHVRxDaeTwuEQT4Z+g+lrqXkQm1AAEAKsDjT1gGAHPP12FYWY6hD50U"
    "4sUxdq/7E13DSq12Anje3nX3Ys/6JiUVo6gY9Wm6OjsYXX0SY/QGfAFPk+zSZ1ktX0EI52MB"
    "qdtp7YAj6A2zkIbWA041HzSJlXnimDhdS9dDOm0184c3F9ZTIOvRNy/cw3UsYiM+k80ymbsp"
    "YhgbwrcD8InsHFTTiK+q8sabyJk26amXT8c8fiPSld4/pg+BEezbRERo2LCVYeffiHRnrJiv"
    "vGoNIdgloWZQ7FkWomRCzSg+Ua8cIz2eYEtLvuKD1yOdqUF1esDUI/s+tlPBxglVEw+nY8lj"
    "ZONx2+zll/KVXNc6QoMoEomiEXBDFURCVWg0jESiAQC+n1ei3c2oM6gYaW/KeFYl+xbPg6xv"
    "t55s8Lfnv68W9Ozrscpi9ISxViteXYCkDt0EWSM4dWrezs99DaKDSxPsRfuSR9VGfT2zns7u"
    "UwNyXYrgZLK4jW32QSh0YLwNQGExio4bm+ezqQ3kADXADfdvA/oj3+zzkCX3LghxxbPnglo9"
    "0sYAh4icnBpOGA+A/G4BxCKHJCExKNo7oR6Ek8F7wR6iDiu3mNTV9b8dHiDlp+viS+0AWQ9Z"
    "8q71vT9IUrW7gdH+S9aDtg5IZ9FkNwwtDaLM/edrX2eGOQD0iisQ17Ug3Pw40p05AKn2hysC"
    "AAYovoFE3KbgHIE9LdZQ+4Pb9gZLDthQVI8/Hp0506K8s8HOwH4uAxuj9MlLDTiy2LUcDvVf"
    "grsDmXDY7hhr/mlNwsQJqLt3InRftC9vNr8EQiE47zMggmyqgw3bBr0dqh0FR3piFxn8UbXI"
    "gEWASCQMvrG+iQjMuCC3E/S+w3CgVCChXjAjJ7T8+S2IDox070EdR8j4Ps1dLk2dJXR5Iau2"
    "fZnr9bcFbe++CkgEwg4seTf/fcyYXq+FbCZzUPFKwX4iQWwNWLXrh3LJzqIImTfX4Wyoxa9r"
    "xVlRR2VRCRw3hezbb9B93jQ6r7qQivIMqOI4QnfGoyji5na4dMbDjYRx+hEglfYojofYsh5S"
    "N77BeATHGPSUU3o5koobieR4OmgAWLEil+3R48fnQFCwfj42M5xVpWvuOkpvugunta0QoFdf"
    "xAXcJe/Ai2+TmncTxTEXVUNdc5xxI9P4xjLrhkMDuwEi1NbGOfXiU2lvPZub+CH//dRp1tcI"
    "Dh8GyjrtDxVmhN5aiJw1HYzBLH0EnTga2bQTNm5H5r6GREKgQtoI0b+8me+lutomNsvKkOZm"
    "m1BtbAQgdflZRL53Ba0jj0HVo6KoBYNAZ8qqQUkMMXsvASfscfFVpzP/pRE93AUXDfSAtsIe"
    "ymWOHEFN36OxbCYXe8uVP0KGV8B7O5DG/CwrEM2xBDp3Lpx5ll3fZWVoc7MNUo4aA93dFM17"
    "Hf3rEuI/+Rn1F04gFgpR5NobDfggNdvRsdX5WQw6VifMsfFNzGcEIHkP+CBD9J5xtmxax5hx"
    "x+Q1IJcUveYa5He/KxBYAB02PFgGAR15JPzt9QKVzI8CumULctxx9gjKGATonPMI/ueOJC7d"
    "0JVGiiKoCJLsgpKYdQAdwTOKNrTS+NkHOafuD2SGVPH7V4dy0okHn6LQwB5tfncB4ejQXgD0"
    "BuGxx+DZZxHPHjro6afBzbegbh8fvJfH2mcUcOwJsix4DTnvXCuoKi2/vJfik0twR1aS8pWi"
    "aBi6UtCRgqhLsq2TIVWl6K5mVp3yIO1UctYtn4Qf3X9IvfNUVzPrlj+L+L7R/oxIwb2Bnizs"
    "gcAvwLx5yBVXFMQ+5o0HYNLhwb2DnmO0YG2mM8gTL+HcatN0Zs0aZMqUQflXg2ZL4B8rXuyj"
    "AR8E9WjVww8j119vHwFUJODLM9AbZiKJYrzuDOGQ1Rrvb6uIfOHO3DG8UbWG8hCn6Jqb6kG1"
    "/+tjh7r4vlHT3KLm13MKbpD5FQltv++7umzJc9pW+1tt2TavIC40t92m/gfEY3tro/JhCN/7"
    "hpavqv6eejVHHFEYAN/3C63ZtFLbu7pyAJkTT7TC93O97eAmQ9XzPG2pe+dDBqDnppaqmrZ2"
    "Nc8+m9eGeNw+V1VzxnT7fOpU9VPpQ6+Jwe/uPTV6gKmfg6Dg8JKSEvSSS+CrXwNAfR+teQ/P"
    "93KWUhqbkMChOhTU4zJ3tNeTSnbyWMXLg7sh8oFQzwXnyy5FQiEklcL//jdJNbyGvPGGfTeq"
    "2qbADtmQglHwWxfTunsBn35v8kcIAEEe4uxz0DPOsLdWnltA667dMCK4KNHPBaj9Ibu/+UAK"
    "SKNq6GxaT3HEo6IkyzHVkwZ5S+yDpGgEvnsDvP46ANW3PWpT8wAnn3wQHSsiHvAcIuuAGDAB"
    "x4vjhhzaTRUl8REfgh/wvmwCAs60aeiqVb2uUoKpqYHx4/e+MjeIXlUFx5kNtFDDBhKaYIQc"
    "Rrq1lGxrgmzifMorqj7aJQBWUPENZuVKuPQymDwZpkzBrF6DjB/fb6S4b1IgiyNzUBqhdQnJ"
    "TU8w23sIwSEcN/hDziYWs/9A9ZFrQA8pIMF/gOE4aDxucxP75f3ZmReZg0gzvLAcnfMU8mOo"
    "HfYJxlRdCToW5fOAvaLzkWtADwnkr7L2nAMekPDLEamHp1bA555CFoMuOooxVVcALkZPoEds"
    "EfnX0YCDJasszYg8CjW74dpfQsRHl4Kk7kFxMf5ViFQhuTt4fVNi/+9pK4qDDqvFW+ITfgRk"
    "0mjsJb7DcZyqICOU16yPEQAK7EKA5WUbWQJMuw5O5SJQg3IS9HPB62MDgIhv174KV0sNQ4F1"
    "DOFoyigniuqwfpOn/zJG8ODJA7YxW96hBlgEDGc85RoDqrGZzL3pYwSAAyT4kp5AnAhHUcEd"
    "+gVEKlCdOWCrj9EuoIgsAXkN0RJAMaQRLgfGDtjuYwMA9IDQhMgy7DnCqagmCra9vvR/UPSK"
    "MMh832MAAAAASUVORK5CYII=")

################################################################################
# Override the wx.TextCtrl class to add read-only style and background colour
################################################################################

class ROTextCtrl(wx.TextCtrl):
    """Override the wx.TextCtrl widget to get read-only text control which
    has a distinctive background colour."""

    ControlReadonlyColour = '#ffffcc'

    def __init__(self, parent, value, tooltip='', *args, **kwargs):
        wx.TextCtrl.__init__(self, parent, wx.ID_ANY, value=value,
                             style=wx.TE_READONLY, *args, **kwargs)
        self.SetBackgroundColour(self.ControlReadonlyColour)
        self.SetToolTip(wx.ToolTip(tooltip))

################################################################################
# Override the wx.StaticBox class to show our style
################################################################################

class AppStaticBox(wx.StaticBox):

    def __init__(self, parent, label, *args, **kwargs):
        if label:
            label = '  ' + label + '  '
        wx.StaticBox.__init__(self, parent, wx.ID_ANY, label, *args, **kwargs)

################################################################################
# Window to show WHxRP graph for a Hazard Point
################################################################################

class ShowGraph(wx.Frame):

    class wxHTML(wx.html.HtmlWindow):

        def OnLinkClicked(self, link):
            webbrowser.open(link.GetHref())

    def __init__(self, parent, title, text, size=None):
        style = (wx.DEFAULT_FRAME_STYLE &
                 ~(wx.RESIZE_BOX | wx.MAXIMIZE_BOX |
                   wx.MINIMIZE_BOX | wx.RESIZE_BORDER))
        style |= wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, parent, wx.ID_ANY, title,
                          style=style, size=size)

        html = self.wxHTML(self)
        html.SetPage(text)

        self.CentreOnParent()
        self.Show()

################################################################################
# Window for 'About' & 'Copyright' - HTML
################################################################################

class CopyAboutDlg(wx.Frame):

    class wxHTML(wx.html.HtmlWindow):

        def OnLinkClicked(self, link):
            webbrowser.open(link.GetHref())

    def __init__(self, parent, title, text, size=None):
        style = (wx.DEFAULT_FRAME_STYLE &
                 ~(wx.RESIZE_BOX | wx.MAXIMIZE_BOX |
                   wx.MINIMIZE_BOX | wx.RESIZE_BORDER))
        style |= wx.FRAME_FLOAT_ON_PARENT
#        style = (wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT |
#                    wx.FRAME_TOOL_WINDOW | wx.CAPTION)
        wx.Frame.__init__(self, parent, wx.ID_ANY, title,
                          style=style, size=size)

        html = self.wxHTML(self)
        html.SetPage(text)

        self.CentreOnParent()
        self.Show()

################################################################################
# Dialog to edit preferences.
################################################################################

class Preferences(wx.Dialog):

    def __init__(self, parent, savedir='', *args, **kwargs):
        wx.Dialog.__init__(self, parent, title=cfg.PreferencesTitle,
                           size=PreferenceSize, *args, **kwargs)

        self.SavePath = savedir

        # draw the gui
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.txt_savedir = ROTextCtrl(self, value=savedir, size=SavedirSize)
        self.txt_savedir.SetToolTip(wx.ToolTip('Generated files will go into '
                                               'this directory'))
        self.btn_savedir_browse = wx.Button(self, label='Browse...')
        self.btn_savedir_browse.Bind(wx.EVT_BUTTON, self.onBrowse)

        sb = AppStaticBox(self, 'Save directory')
        hbox = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        hbox.Add(self.txt_savedir, proportion=1,
                 flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)

        hbox.Add(self.btn_savedir_browse,
                 flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)

        vbox.Add(hbox)

        # add buttons
        okButton = wx.Button(self, wx.ID_OK, "&OK")
        okButton.SetDefault()
        okButton.Bind(wx.EVT_BUTTON, self.onOK)
        cancelButton = wx.Button(self, wx.ID_CANCEL, "&Cancel")
        cancelButton.Bind(wx.EVT_BUTTON, self.onCancel)

        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(okButton)
        btnSizer.AddButton(cancelButton)
        btnSizer.Realize()

        vbox.Add(btnSizer, flag=wx.TOP, border=10)

        self.SetSizerAndFit(vbox)

    def onBrowse(self, event):
        while True:
            dlg = wx.DirDialog(self, 'Choose a save directory',
                               style=wx.DD_DEFAULT_STYLE)
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return

            # get the directory path
            dir_path = dlg.GetPath()
            dlg.Destroy()

            # ensure we can create directory (if required) and write into it
            try:
                if not os.path.isdir(dir_path):
                    os.makedirs(dir_path)
                test_file = os.path.join(dir_path, 'test')
                f = open(test_file, 'w')
                f.write('write test\n')
                f.close()
                os.remove(test_file)
            except:
                msg = ("Sorry, I can't create/use that directory, "
                       "please choose another.")
                dlg = wx.MessageDialog(parent=self, message=msg,
                                       caption='Error',
                                       style=wx.OK|wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
                continue

            self.SavePath = dir_path
            self.txt_savedir.SetValue(dir_path)
            return

    def onCancel(self, event):
        self.Close()

    def onOK(self, event):
        self.Close()

################################################################################
# Validator class for 'float' text input
################################################################################

class FloatValidator(wx.PyValidator):
    """A validator class for floating point entry textboxes."""

    AllowedChars = '0123456789.'

    def __init__(self):
        wx.PyValidator.__init__(self)
        self.Bind(wx.EVT_CHAR, self.onChar)

    def Clone(self):
        return FloatValidator()

    def Validate(self, win):
        tc = self.GetWindow()
        val = tc.GetValue()

        try:
            f_val = float(val)
        except ValueError:
            tc.SetBackGroundColour(wx.RED)
            return False

        return True

    def onChar(self, event):
        key = event.GetKeyCode()

        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return

        if chr(key) in FloatValidator.AllowedChars:
            event.Skip()

################################################################################
# The main application frame
################################################################################

class AppFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, size=DefaultAppSize, title=cfg.FrameTitle)
        self.SetMinSize(DefaultAppSize)
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.panel.SetBackgroundColour(wx.WHITE)
        self.panel.ClearBackground()

        # set the application icon
        if Imported_PyEmbeddedImage:
            tsunami = getIcon()
            icon = tsunami.GetIcon()
            self.SetIcon(icon)

        # create all application controls
        self.make_gui(self.panel)

        # and the menus
        self.make_menus()

        # do initialisation stuff - all the application stuff
        self.init()

        # load any user changes to the config
        self.load_config()

        # finally, set up application window position
        self.Centre()

        # check sanity of calculated data structures
        self.testDataSane()

    def testDataSane(self):
        """Run sanity tests on calculated data.

        Check self-consistency of:
            self.subfaultid_2_zonename
            self.zonename_2_subfault_posns
            self.subfaultid_2_position
        """

        for subfaultid in self.subfaultid_2_zonename:
            zonename = self.subfaultid_2_zonename[subfaultid]
            subfault_position = self.subfaultid_2_position[subfaultid]
            if subfault_position not in \
                    self.zonename_2_subfault_posns[zonename]:
                msg = 'Inconsistency for subfaultid %d' % subfaultid
                log(msg)
                raise RuntimeError(msg)

        log('testDataSane: Successful!')

#####
# Build the GUI
#####

    def make_gui_corporate(self, parent):
        """Build the corporate part of the controls part of GUI.

        parent reference to parent object

        Returns a reference to enclosing sizer.
        """

        # get corporate image
        img = wx.Image(cfg.corporate_image, wx.BITMAP_TYPE_ANY)
        ci_gif = img.ConvertToBitmap()

        # create gui objects
        bmp = wx.StaticBitmap(parent, wx.ID_ANY, ci_gif, (0, 0))

        # lay out objects
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(bmp, flag=wx.ALIGN_CENTER)

        return box

    def make_gui_mouse(self, parent):
        """Build the mouse part of the controls part of GUI.

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        # create objects
        txt = wx.StaticText(parent, wx.ID_ANY, 'Lon/Lat:')
        self.mouse_position = ROTextCtrl(parent, '',
                                         tooltip=('Shows the mouse '
                                                  'longitude and latitude '
                                                  'on the map'))

        # lay out the controls
        sb = AppStaticBox(parent, 'Mouse position')
        box = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        box.Add(txt, border=PackBorder, flag=(wx.ALIGN_CENTER_VERTICAL
                                     |wx.ALIGN_RIGHT|wx.LEFT))
        box.Add(self.mouse_position, proportion=1, border=PackBorder,
                flag=wx.RIGHT|wx.TOP|wx.BOTTOM)

        return box

    def make_gui_hazard(self, parent):
        """Build the hazard part of the controls part of GUI.

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        # create objects
        txt = wx.StaticText(parent, wx.ID_ANY, 'Lon/Lat:')
        self.hp_position = ROTextCtrl(parent, '',
                                      tooltip=('Shows the longitude and '
                                               'latitude of the selected '
                                               'hazard point'))

        # lay out objects
        sb = AppStaticBox(parent, 'Hazard point')
        box = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        box.Add(txt, border=PackBorder,
                flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT)
        box.Add(self.hp_position, proportion=1, border=PackBorder,
                flag=wx.RIGHT|wx.TOP|wx.BOTTOM)

        return box

    def make_gui_scenario(self, parent):
        """Build the scenario part of the controls part of GUI.

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        self.float_validator = FloatValidator()
        self.float_validator2 = FloatValidator()

        # create objects
        txt_scenario_label = wx.StaticText(parent, wx.ID_ANY, 'Scenario Name:')
        self.txt_scenario = wx.TextCtrl(parent, wx.ID_ANY, '')
        self.txt_scenario.SetToolTip(wx.ToolTip('Set the scenario name here'))

        txt_rp = wx.StaticText(parent, wx.ID_ANY, 'Return Period:')
        self.rp_cbox = wx.ComboBox(parent, wx.ID_ANY, size=CBSize,
                                   choices=[],
                                   style=(wx.CB_DROPDOWN|wx.CB_READONLY
                                          |wx.BG_STYLE_COLOUR))
        self.rp_cbox.SetToolTip(wx.ToolTip('Select Return Period'))

        stxt_wh = wx.StaticText(parent, wx.ID_ANY, 'Wave Height:')
        self.txt_wh = wx.TextCtrl(parent, wx.ID_ANY, '',
                                  validator=self.float_validator,
                                  size=WaveHeightTextSize,
                                  style=wx.ALIGN_RIGHT)
        self.txt_wh.SetToolTip(wx.ToolTip('Enter the Wave Height'))

        txt_to = wx.StaticText(parent, wx.ID_ANY, u'\u00B1')    # unicode +/-

        self.txt_wh_delta = wx.TextCtrl(parent, wx.ID_ANY, '',
                                        validator=self.float_validator2,
                                        size=WaveHeightTextSize,
                                        style=wx.ALIGN_RIGHT)
        self.txt_wh_delta.SetValue(DefaultWaveHeightDelta)
        self.txt_wh_delta.SetToolTip(wx.ToolTip('Enter the waveheight delta'))

        txt_m = wx.StaticText(parent, wx.ID_ANY, ' m')

        # set event handler when wave height text controls get focus
        self.txt_wh.Bind(wx.EVT_SET_FOCUS, self.onTextCtrlGetsFocus)
        self.txt_wh_delta.Bind(wx.EVT_SET_FOCUS, self.onTextCtrlGetsFocus)

        # lay out objects
        sb = AppStaticBox(parent, 'Offshore hazard')
        box = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        fg = wx.FlexGridSizer(rows=3, cols=2) #, vgap=5)
        wh_box = wx.BoxSizer(wx.HORIZONTAL)
        wh_box.Add(self.txt_wh, flag=wx.ALIGN_CENTER_VERTICAL)
        wh_box.Add(txt_to, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT,
                   border=2)
        wh_box.Add(self.txt_wh_delta, flag=wx.ALIGN_CENTER_VERTICAL)
        wh_box.Add(txt_m, flag=wx.ALIGN_CENTER_VERTICAL)

        fg.Add(txt_scenario_label, border=PackBorder,
               flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        fg.Add(self.txt_scenario, proportion=1, border=PackBorder,
               flag=wx.EXPAND|wx.RIGHT)
        fg.Add(txt_rp, border=PackBorder,
               flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        fg.Add(self.rp_cbox, proportion=1, border=PackBorder,
               flag=wx.EXPAND|wx.RIGHT)
        fg.Add(stxt_wh, border=PackBorder,
               flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        fg.Add(wh_box, border=PackBorder, flag=wx.BOTTOM)
        fg.AddGrowableCol(1, 1)
        box.Add(fg, flag=wx.EXPAND|wx.ALL, proportion=1)

        return box

    def make_gui_aoi(self, parent):
        """Build the area of interest part of the controls part of GUI.

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        global DefaultButtonColour

        # create objects
        txt_file = wx.StaticText(parent, wx.ID_ANY, 'File:')
        self.txt_area_of_interest = ROTextCtrl(parent, '',
                                               tooltip=AOITooltipText)
        self.btn_aoi_import = wx.Button(parent, wx.ID_ANY, 'Import file',
                                        size=BtnSize)
        self.btn_aoi_clear = wx.Button(parent, wx.ID_ANY, 'Clear area',
                                       size=BtnSize)
        self.btn_aoi_edit = wx.Button(parent, wx.ID_ANY,
                                      'Order boundary points',
                                      size=(-1, BtnHeight))
        DefaultButtonColour = self.btn_aoi_edit.GetBackgroundColour()
        self.btn_aoi_edit.Enable(False)

        # lay out the controls
        sb = AppStaticBox(parent, 'Area of interest')
        box = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)

        box1 = wx.BoxSizer(wx.HORIZONTAL)
        box1.Add(txt_file, border=PackBorder,
                 flag=wx.LEFT|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        box1.Add(self.txt_area_of_interest, border=PackBorder, proportion=1,
                 flag=wx.RIGHT|wx.EXPAND)
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        box2.Add(self.btn_aoi_import, border=PackBorder, flag=wx.ALL)
        box2.Add((5,5), proportion=1)
        box2.Add(self.btn_aoi_clear, border=PackBorder, flag=wx.ALL)
        box.Add(box1, border=PackBorder, flag=wx.TOP|wx.EXPAND)
        box.Add((5,5))
        box.Add(box2, flag=wx.EXPAND)
        box3 = wx.BoxSizer(wx.HORIZONTAL)
        box3.Add(self.btn_aoi_edit, border=PackBorder,
                 proportion=0, flag=wx.EXPAND|wx.ALL)
        box.Add((5,5))
        box.Add(box3, flag=wx.EXPAND)

        return box

    def make_gui_zone_faults(self, parent):
        """Build the zone & faults part of the controls part of GUI.

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        # create objects
        txt_zone = wx.StaticText(parent, wx.ID_ANY, 'Zone:')
        self.txt_zone_name = ROTextCtrl(parent, '',
                                        tooltip=('Shows name of the '
                                                 'selected zone'))

        txt_numsf = wx.StaticText(parent, wx.ID_ANY, 'events:')
        self.txt_num_subfaults = ROTextCtrl(parent, '', size=(45,-1),
                                            tooltip=('Shows the number of '
                                                     'subfaults in the '
                                                     'selected zone'))

        self.lst_subfaults = wx.ListCtrl(parent, size=ListCtrlSize,
                                         style=(wx.LC_REPORT|wx.LB_EXTENDED|
                                                wx.LC_VRULES))
        self.lst_subfaults.SetToolTip(wx.ToolTip('Shows the selected '
                                                 'events in the zone'))

        # lay out the objects
        sb = AppStaticBox(parent, 'Zone && events')
        box = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)
        box1 = wx.BoxSizer(wx.HORIZONTAL)
        box1.Add(txt_zone, border=PackBorder,
                 flag=wx.LEFT|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        box1.Add(self.txt_zone_name, border=PackBorder, proportion=1,
                 flag=wx.RIGHT|wx.EXPAND)
        box1.Add(txt_numsf, border=PackBorder,
                 flag=wx.LEFT|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        box1.Add(self.txt_num_subfaults, border=PackBorder, proportion=0,
                 flag=wx.RIGHT|wx.EXPAND)
        box.Add(box1, border=PackBorder, flag=wx.TOP|wx.EXPAND)
        box.Add((5,5))
        box.Add(self.lst_subfaults, border=PackBorder,
                flag=wx.RIGHT|wx.LEFT|wx.BOTTOM|wx.EXPAND)

        # set event handler for list item selection/deselection
        self.lst_subfaults.Bind(wx.EVT_LIST_ITEM_SELECTED,
                                self.displaySubfaults)
        self.lst_subfaults.Bind(wx.EVT_LIST_ITEM_DESELECTED,
                                self.displaySubfaults)
        self.lst_subfaults.Bind(wx.EVT_LIST_COL_CLICK, self.sortEventColumn)

        return box

    def displaySubfaults(self, event):
        """Handle de/selection of subfaults.
        
        We don't care what was added/removed from selection, just get selected
        items and display involved subfaults in own layer.
        """

        # get selected item index numbers
        index = self.lst_subfaults.GetFirstSelected()
        item_ids = [index]
        while item_ids[-1] != -1:
            next = self.lst_subfaults.GetNextSelected(index)
            item_ids.append(next)
            index = next
        item_ids = item_ids[:-1]    # remove '-1' final entry

        # convert to event ID list
        event_ids = []
        for item in item_ids:
            event_ids.append(int(self.lst_subfaults.GetItemText(item)))

        # convert to set of subfaults
        subfaults = []
        for e_id in event_ids:
            subfaults.extend(self.eventid_2_subfaults[e_id])

        subfaults = set(subfaults)

        # convert subfault IDs to positions
        positions = [self.subfaultid_2_position[s] for s in subfaults]

        # display selected zone
        if self.selected_subfaults_layer:
            self.pyslip.deleteLayer(self.selected_subfaults_layer)
        self.selected_subfaults_layer = \
            self.pyslip.addMonoPointLayer(positions,
                                          colour=SubfaultPointColour,
                                          size=SubfaultPointSize,
                                          name='selected zone')
        self.pyslip.placeLayerAfterLayer(self.selected_subfaults_layer,
                                         self.selected_zone_layer)

    def sortEventColumn(self, event):
        """Sort the event data by clicked column.

        Tricky point:
            We must maintain selected events.
        """

        # get column index we want to sort on (0, 1, ...)
        col = event.GetColumn()
        if col < 0:         # just in case
            return

        # get indices of selected events
        item_ids = []
        index = self.lst_subfaults.GetFirstSelected()
        item_ids.append(index)
        while item_ids[-1] != -1:
            next = self.lst_subfaults.GetNextSelected(index)
            item_ids.append(next)
            index = next
        item_ids = item_ids[:-1]

        # convert to event ID list
        event_ids = []
        for item in item_ids:
            event_ids.append(self.lst_subfaults.GetItemText(item))

        # check column - same as last time?
        if col == self.events_last_sort_col:
            self.events_last_sort_order = not self.events_last_sort_order
        else:
            self.events_last_sort_order = False
            self.events_last_sort_col = col

        # sort the events data by that column
        self.events.sort(key=lambda x: float(x[col]),
                         reverse=self.events_last_sort_order)
        self.fillEventsListCtrl(self.events)

        # select events that were selected before
        for id in event_ids:
            index = self.lst_subfaults.FindItem(-1, id)
            self.lst_subfaults.Select(index)

    def make_gui_generate(self, parent):
        """Build the 'generate' part of the controls part of GUI.

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        # create objects
        self.btn_generate = wx.Button(parent, wx.ID_ANY, 'Generate',
                                      size=BtnSize)
        self.btn_generate.SetBackgroundColour(GenerateButtonColour)
        self.btn_generate.ClearBackground()
        self.btn_generate.Refresh() 

        return self.btn_generate

    def make_gui_view(self, parent):
        """Build the map view widget

        parent  reference to the widget parent

        Returns the static box sizer.
        """

        # create gui objects
        sb = AppStaticBox(parent, '')
        self.pyslip = pyslip.pySlip(parent, tile_dir=cfg.TilesDirectory,
                                    min_level=MinTileLevel)

        # lay out objects
        box = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        box.Add(self.pyslip, proportion=1, border=1, flag=wx.EXPAND)

        return box

    def make_gui_controls(self, parent):
        """Build the 'controls' part of the GUI

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        # all controls in vertical box sizer
        controls = wx.BoxSizer(wx.VERTICAL)

        # corporate area
        corp_box = self.make_gui_corporate(parent)
        controls.Add(corp_box, proportion=0, flag=wx.EXPAND|wx.ALL)

        # add the mouse position feedback stuff
        mouse = self.make_gui_mouse(parent)
        controls.Add(mouse, proportion=0, flag=wx.EXPAND|wx.ALL)

        # stretchable spacer
        controls.AddStretchSpacer()

        # hazard point meta-data
        hazard = self.make_gui_hazard(parent)
        controls.Add(hazard, proportion=0, flag=wx.EXPAND|wx.ALL)

        # vertical spacer
        controls.AddSpacer(VSpacerSize)

        # scenario information
        scenario = self.make_gui_scenario(parent)
        controls.Add(scenario, proportion=0, flag=wx.EXPAND|wx.ALL)

        # another vertical spacer
        controls.AddSpacer(VSpacerSize)

        # area-of-interest
        aoi = self.make_gui_aoi(parent)
        controls.Add(aoi, proportion=0, flag=wx.EXPAND|wx.ALL)

        # another vertical spacer
        controls.AddSpacer(VSpacerSize)

        # zone and faults
        zandf = self.make_gui_zone_faults(parent)
        controls.Add(zandf, proportion=0, flag=wx.EXPAND|wx.ALL)

        # another vertical spacer
        controls.AddSpacer(VSpacerSize)

        # zone and faults
        generate = self.make_gui_generate(parent)
        controls.Add(generate, proportion=0, flag=wx.EXPAND|wx.ALL)

        return controls

    def make_gui(self, parent):
        """Create application GUI."""

        # start application layout
        all_display = wx.BoxSizer(wx.HORIZONTAL)
        parent.SetSizer(all_display)

        # put map view in left of horizontal box
        sl_box = self.make_gui_view(parent)
        all_display.Add(sl_box, proportion=1, border=1, flag=wx.EXPAND)

        # small spacer here - separate view and controls
        all_display.AddSpacer(HSpacerSize)

        # add controls in right of spacer
        controls = self.make_gui_controls(parent)
        all_display.Add(controls, proportion=0, border=1, flag=wx.EXPAND)

        parent.SetSizerAndFit(all_display)

        # a Statusbar in the bottom of the window
        self.status_bar = self.CreateStatusBar()

    def make_menus(self):
        """Create the application menubar."""

        # the parent menubar
        menuBar = wx.MenuBar()

        # put File menu on master
        filemenu= wx.Menu()
#        filemenu.Append(ID_FILE_NEW, '&New Project\tCtrl+N',
#                        ' Start a new project')
#        filemenu.Append(ID_FILE_OPEN, '&Open Project ...\tCtrl+O',
#                        ' Open an existing project')
#        filemenu.AppendSeparator()
#        filemenu.Append(ID_FILE_SAVE, '&Save\tCtrl+S',
#                        ' Save the current project')
#        filemenu.Append(ID_FILE_SAVEAS, 'Save &As ...',
#                        ' Save the current project under a new name')
#        filemenu.AppendSeparator()
        filemenu.Append(ID_FILE_EXIT, 'E&xit',
                        ' Exit the application')
        menuBar.Append(filemenu,'&File')

        # bind File items to code
        self.Bind(wx.EVT_MENU, self.onFileNew, id=ID_FILE_NEW)
        self.Bind(wx.EVT_MENU, self.onFileOpen, id=ID_FILE_OPEN)
        self.Bind(wx.EVT_MENU, self.onFileSave, id=ID_FILE_SAVE)
        self.Bind(wx.EVT_MENU, self.onFileSaveAs, id=ID_FILE_SAVEAS)
        self.Bind(wx.EVT_MENU, self.onExit, id=ID_FILE_EXIT)

        # put Edit menu on master
        editmenu= wx.Menu()
        editmenu.Append(ID_EDIT_PREFS, 'Preferences ...',
                        '  Edit the %s application preferences'
                        % cfg.AppName)
        menuBar.Append(editmenu,'&Edit')

        # bind Edit items to code
        self.Bind(wx.EVT_MENU, self.onEditPrefs, id=ID_EDIT_PREFS)

        # put Help menu on master
        helpmenu= wx.Menu()
        helpmenu.Append(ID_HELP_CONTENTS, '&User Guide ...\tF1',
                        ' View the user guide for %s' % cfg.AppName)
        helpmenu.Append(ID_HELP_COPYRIGHT, '&Copyright ...',
                        ' Show %s copyright' % cfg.AppName)
        helpmenu.AppendSeparator()
        helpmenu.Append(ID_HELP_ABOUT, '&About %s ...' % cfg.AppName,
                        ' Information about %s' % cfg.AppName)
        menuBar.Append(helpmenu,'&Help')

        # bind Help items to code
        self.Bind(wx.EVT_MENU, self.onHelpContents, id=ID_HELP_CONTENTS)
        self.Bind(wx.EVT_MENU, self.onHelpCopyright, id=ID_HELP_COPYRIGHT)
        self.Bind(wx.EVT_MENU, self.onHelpAbout, id=ID_HELP_ABOUT)

        # finally attach menubar to frame
        self.SetMenuBar(menuBar)

    def init(self):
        # the project file
        self.project_file = None

        # set callbacks from pyslip
        self.pyslip.setMousePositionCallback(self.showMousePosition)

        # set initial view position
        self.pyslip.gotoLevelAndPosition(InitViewLevel, InitViewPosition)

        # populate Return Period combobox from ReturnPeriodsFile
        self.populate_rp_combobox()

        # get the data mapping a zone subfault ID to zone name, etc.
        self.loadSubfaultData()
        self.loadEvent2SubfaultData()

        # get hazard point data, show it
        self.hp_points = util.readPointsFile(cfg.HazardPointsFile)
        self.hp_points_data = [[x[0], x[1]] for x in self.hp_points]
        self.hp_points = [(x[0], x[1], int(x[2])) for x in self.hp_points]
        self.hp_layer_id = self.pyslip.addMonoPointLayer(self.hp_points_data,
                                                         colour=PointsColour,
                                                         size=PointsSize,
                                                         name='hazard points')

        # set callback for selecting a point (left or right click)
        self.pyslip.setLayerPointSelectCallback(self.hp_layer_id,
                                                PointSelectDelta,
                                                self.HazardPointSelected)
        self.pyslip.setLayerPointRightSelectCallback(self.hp_layer_id,
                                                     PointSelectDelta,
                                                     self.HazardPointRightSelected)

        # set handlers for all CHANGE events from controls
        self.rp_cbox.Bind(wx.EVT_COMBOBOX, self.changeRP)
        self.txt_wh.Bind(wx.EVT_TEXT, self.changeWH)
        self.txt_wh_delta.Bind(wx.EVT_TEXT, self.changeWH)
        self.btn_aoi_import.Bind(wx.EVT_BUTTON, self.btn_AOI_import)
        self.btn_aoi_clear.Bind(wx.EVT_BUTTON, self.btn_AOI_clear)
        self.btn_aoi_edit.Bind(wx.EVT_BUTTON, self.btn_AOI_edit)
        self.btn_generate.Bind(wx.EVT_BUTTON, self.onGenerate)

        # set handler for CLOSE event
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # set various state variables
        self.hp_lon = None                  # flag to show HP selected
        self.hp_lat = None
        self.hp_selected_id = None          # ID of selected HP

        self.RP_WH_last_changed = None
        self.aoi_polygon = None             # flag to show AOI selected
        self.wh_value = None                # flag to show WH selected
        self.wh_delta_value = None
        self.timer = None

        self.selected_hp_layer = None           # layer for selected HP
        self.selected_zone_layer = None         # layer for selected zone
        self.selected_subfaults_layer = None    # layer for selected subfaults
        self.aoi_layer = None                   # layer to show AOI
        self.deag_layer = None                  # the deag layer
        self.deag_label_layer = None            # the deag legend layer

        self.events = None                  # event data
        self.events_last_sort_col = None
        self.events_last_sort_order = None

        self.AOI_filename = None
        self.hp_inside_bb = None            # list of HP inside AOI
        self.edit_state = False             # BP edit flag
        self.text_layer = None

        # force pyslip initialisation
        self.pyslip.onResize()

    def populate_rp_combobox(self):
        """Populate the Return Period combobox.

        self.rp_cbox is the combobox to populate.
        """

        fd = open(cfg.ReturnPeriodsFile, 'r')
        lines = fd.readlines()
        fd.close()

        for line in lines:
            line = line.strip()
            self.rp_cbox.Append(line)

#####
# Handlers for control events
#####

    def changeRP(self, event=None):
        """Set state so that RP takes precedence in HP-RP-WH update."""

        self.RP_WH_last_changed = 'RP'
        self.update_HP_RP_WH()

    def changeWH(self, event=None):
        """Set state so that WH takes precedence in HP-RP-WH update."""

        self.RP_WH_last_changed = 'WH'
        self.update_HP_RP_WH()

    def update_HP_RP_WH(self, event=None):
        """Given some change event, update RP and WH sensibly.

        Update RP and HP depending on circumstances.  The state variable
        RP_WH_last_changed tells us which of RP/WH was changed last, so
        take the last changed variable and compute the other.
        """

        # now decide what to do
        if self.hp_lon:                 # if HP set
            if self.RP_WH_last_changed == 'RP':
                # if RP was changed, update WH
                rp_value = self.rp_cbox.GetValue()
                if rp_value:
                    (rp_value, _) = rp_value.split(' ')
                    rp_value = int(rp_value)
                    wh = self.get_WH_from_RP_HP(rp_value,
                                                (self.hp_lon, self.hp_lat))
                    self.txt_wh.ChangeValue('%1.2f' % wh)
                    self.txt_wh_delta.ChangeValue(DefaultWaveHeightDelta)
            elif self.RP_WH_last_changed == 'WH':
                # if WH was changed, update RP
                wh_value = self.txt_wh.GetValue()
                try:
                    wh_value = float(wh_value)
                except ValueError:
                    wh_value = None

                wh_delta_value = self.txt_wh_delta.GetValue()
                try:
                    wh_delta_value = float(wh_delta_value)
                except ValueError:
                    wh_delta_value = 0.0

                if wh_value:
                    rp = self.get_RP_from_WH_HP(wh_value, wh_delta_value,
                                                (self.hp_lon, self.hp_lat))
                    rp_str = '%d years' % rp
                    self.rp_cbox.SetStringSelection(rp_str)
                    self.Refresh()
            self.deleteDeagLayer()
            self.loadDeagLayer()
        else:
            self.deleteDeagLayer()

        # update the WH tooltip text
        self.wh_value = self.txt_wh.GetValue()
        try:
            self.wh_value = float(self.wh_value)
        except ValueError:
            self.wh_value = 0

        self.wh_delta_value = self.txt_wh_delta.GetValue()
        try:
            self.wh_delta_value = float(self.wh_delta_value)
        except ValueError:
            self.wh_delta_value = 0

        if self.wh_value is None:
            self.txt_wh.SetToolTip(wx.ToolTip('Enter the Wave Height'))
        else:
            min_ht = max(0.0, self.wh_value-self.wh_delta_value)
            max_ht = min(10.0, self.wh_value+self.wh_delta_value)
            self.txt_wh.SetToolTip(wx.ToolTip('Wave height range is %.2f to '
                                              '%.2f m'
                                              % (min_ht, max_ht)))

        self.clearZoneEvents()

    def btn_AOI_import(self, event):
        """Display AOI polygon from user file."""

        global ProjectDefaultDir

        default_dir = ProjectDefaultDir
        if default_dir is None:
            default_dir = os.getcwd()

        dlg = wx.FileDialog(self, message='Load area of interest ...',
                            defaultDir=default_dir,
                            defaultFile='', wildcard=LoadAOIWildcard,
                            style=wx.OPEN)
        self.AOI_filename = None
        if dlg.ShowModal() == wx.ID_OK:
            self.AOI_filename = dlg.GetPath()
            ProjectDefaultDir = dlg.GetDirectory()
            basename = os.path.basename(self.AOI_filename)

            # if there is a current AOI shown, remove it
            if self.aoi_layer:
                self.btn_AOI_clear()

            # load AOI polygon from 'self.AOI_filename'
            try:
                fd = open(self.AOI_filename, 'r')
                lines = fd.readlines()
                fd.close()
            except IOError, e:
                try:
                    (err, _) = str(e).split(':', 1)
                except:
                    err = str(e)
                msg = "Can't open file '%s': %s" % (self.AOI_filename, err)
                self.error(msg)

            # create AOI layer - check we have lon+lat, not easting+northing
            self.aoi_polygon = []
            repat = re.compile(',| +')      # split on one ',' or multiple space
            for (i, oline) in enumerate(lines):
                line = oline.strip()
                if not line or line[0] == '#':
                    continue
                fields = repat.split(line)
                if len(fields) < 2:
                    msg = ("File '%s' has a bad format on line %d: %s"
                           % (basename, i+1, oline))
                    self.error(msg)
                    dlg.Destroy()
                    return
                try:
                    lon = float(fields[0])
                    lat = float(fields[1])
                except ValueError:
                    msg = ("File '%s' has a bad format on line %d: %s"
                           % (basename, i+1, oline))
                    self.error(msg)
                    dlg.Destroy()
                    return
                if lon > 360.0 or lat > 90.0:
                    msg = ('Looks like that file has eastings and northings. '
                           'You can only import files containing '
                           'longitude and latitude.')
                    self.error(msg)
                    return
                self.aoi_polygon.append((float(fields[0]), float(fields[1])))

            # ensure polygon is closed
            if  self.aoi_polygon[0] != self.aoi_polygon[-1]:
                self.aoi_polygon.append(self.aoi_polygon[0])

            # add arrow to each vector to make directed polygon
            self.aoi_polygon = self.makeDirectedPolygon(self.aoi_polygon)

            self.aoi_layer = \
                    self.pyslip.addMonoPolygonLayer([self.aoi_polygon],
                                                    map_relative=True,
                                                    colour=AOIPolygonColour,
                                                    size=AOIPolygonWidth,
                                                    closed=True,
                                                    filled=False,
                                                    name='AOI')

            self.txt_area_of_interest.SetValue(basename)
            tt = wx.ToolTip('File is %s' % self.AOI_filename)
            self.txt_area_of_interest.SetToolTip(tt)

            # zoom to centre of AOI polygon at appropriate zoom level
            (w, e, s, n) = self.getPointsExtent(self.aoi_polygon)

            centre_lon = (e + w)/2
            centre_lat = (n + s)/2
            lon_extent = (e - w)
            lat_extent = (n - s)

            self.pyslip.zoomToArea((centre_lon, centre_lat),
                                   (lon_extent, lat_extent))
        else:
            return

        # enable the EDIT button
        self.btn_aoi_edit.Enable(True)

        dlg.Destroy()

        self.clearZoneEvents()
        self.btn_AOI_edit()

        # check HP inside AOI
        self.check_hp_in_aoi()


    def btn_AOI_edit(self, event=None):
        """User pressed the 'order boundary points' button."""

        # user (or code) cancels edit?
        if self.edit_state:
            self.edit_state = False
            self.btn_aoi_edit.SetLabel('Order boundary points')
            self.btn_aoi_edit.SetBackgroundColour(DefaultButtonColour)
            self.btn_aoi_edit.ClearBackground()
            self.btn_aoi_edit.Refresh() 
            self.pyslip.setLayerPointSelectCallback(self.hp_layer_id,
                                                    PointSelectDelta,
                                                    self.HazardPointSelected)
            return

        # otherwise we are now editing
        self.edit_state = True
        self.btn_aoi_edit.SetLabel('End ordering')
        self.btn_aoi_edit.SetBackgroundColour(wx.RED)
        self.btn_aoi_edit.ClearBackground()
        self.btn_aoi_edit.Refresh() 

        if self.text_layer:
            self.pyslip.deleteLayer(self.text_layer)
            self.text_layer = None

        msg = ("You must select the 'first' boundary point inside the "
               "bounding box.  The remaining points will be automatically "
               "ordered and should increase in number as they follow "
               "the directed seaward boundary.")
        dlg = wx.MessageDialog(parent=self, message=msg, caption='Information',
                               style=wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

        # get HPs inside the bounding polygon
        self.hp_inside_bb = []
        for hp in self.hp_points:
            (x, y, id) = hp
            if polygon.point_in_poly(x, y, self.aoi_polygon):
                self.hp_inside_bb.append((id, x, y))

        # now look for Bounded HP selections - change selection callback
        self.pyslip.setLayerPointSelectCallback(self.hp_layer_id,
                                                PointSelectDelta,
                                                self.BoundaryPointSelected)

    def BoundaryPointSelected(self, id, point=None):
        """User clicked on hazard point during boundary edit.
        
        id     ID of layer click was on (can ignore this)
        point  (lon,lat) of clicked point, or None if click off point

        We ignore clicks on HPs *not* inside AOI.
        """

        if point:
            (lon, lat) = point
            # get HP index number
            hp_selected_id = None
            for (hp_id, hp_lon, hp_lat) in self.hp_inside_bb:
                if lon == hp_lon and lat == hp_lat:
                    hp_selected_id = int(hp_id)
                    break

            if hp_selected_id is None:
                return          # not a point in the AOI

            # create generator of 'next' point closest to chosen
            closest_point = self.sort_by_distance(lon, lat, self.hp_inside_bb)

            # create a text layer dataset
            text_data = []
            for (i, point) in enumerate(closest_point):
                (x, y) = point
                text = '%d' % (i+1)
                text_data.append((x, y, text))

            # add attribute dictionary and create text layer
            d = {'placement': 'tl', 'offset': 3}
            self.text_layer = \
                    self.pyslip.addTextLayer(text_data, map_relative=True,
                                             name='<text_layer>', attributes=d)

    def sort_by_distance(self, lon, lat, points):
        """Sort list of points by distance from a given point in list.

        lon     longitude of first point in list
        lat     latitude of first point in list
        points  list of (id, x, y) of boundary points

        The point (lon, lat) is expected to be in 'points'.

        Returns a list of [(lon, lat), (lon, lat), ...] where item 0 is the
        given initial point, and the following points are the closest to the
        first point, closest to the second point, and so on.
        """

        # convert 'points' list to just [(lon,lat), ...]
        points = [(x[1],x[2]) for x in points]

        # start the result list
        result = []

        current = (lon, lat)
        while points:
            result.append(current)

            # remove 'current' from 'points' list
            points.remove(current)
            if len(points) < 1:
                break

            # figure out which point in 'points' is closest to last result.
            # leave 'index' as the index of closest point
            index = None
            distance = 9999999999.
            (old_x, old_y) = current
            for (i, pt) in enumerate(points):
                (new_x, new_y) = pt
                dist_square = ((new_x-old_x)*(new_x-old_x) +
                               (new_y-old_y)*(new_y-old_y))
                if dist_square < distance:
                    index = i
                    distance = dist_square

            # prepare to return the next closest
            current = points[index]

        # exit edit mode
        self.btn_AOI_edit()

        return result

    def makeDirectedPolygon(self, poly):
        """Convert simple polygon into directed polygon."""

        last_posn = poly[0]
        result = [last_posn]

        for posn in poly[1:]:
            result.extend(self.makeArrowhead(last_posn, posn))
            last_posn = posn

        return result

    def makeArrowhead(self, tail, head):
        """Create list of vectors to draw arrowhead.

        tail  location of tail of vector
        head  location of head of vector
        """

        (tail_x, tail_y) = tail
        (head_x, head_y) = head

        dx = (head_x - tail_x)
        dy = (head_y - tail_y)

        length = math.sqrt(dx*dx + dy*dy)
        sin_theta = dx / length
        cos_theta = dy / length

        l_tan_phi = DirectedArrowheadSize*math.tan(DirectedArrowheadAngle)

        result = []

        if midArrows:
            curr_x = tail_x+dx/2
            curr_y = tail_y+dy/2
        else:
            curr_x = head_x
            curr_y = head_y

        result.append((curr_x, curr_y))

        rtip_x = (curr_x - DirectedArrowheadSize*sin_theta +
                  l_tan_phi*cos_theta)
        rtip_y = (curr_y - DirectedArrowheadSize*cos_theta -
                  l_tan_phi*sin_theta/2)
        result.append((rtip_x, rtip_y))

        ltip_x = (curr_x - DirectedArrowheadSize*sin_theta -
                  l_tan_phi*cos_theta)
        ltip_y = (curr_y - DirectedArrowheadSize*cos_theta +
                  l_tan_phi*sin_theta/2)
        result.append((ltip_x, ltip_y))
        result.append((curr_x, curr_y))
        if midArrows:
            result.append((head_x, head_y))

        return result

    def btn_AOI_clear(self, event=None):
        """Handle 'clear AOI' button."""

        if self.aoi_layer:
            self.pyslip.deleteLayer(self.aoi_layer)
            self.aoi_layer = None
            self.txt_area_of_interest.Clear()
            tt = wx.ToolTip(AOITooltipText)
            self.txt_area_of_interest.SetToolTip(tt)

        if self.text_layer:
            self.pyslip.deleteLayer(self.text_layer)
            self.text_layer = None
            self.btn_aoi_edit.Enable(False)
            
        self.aoi_polygon = None

        self.clearZoneEvents()

    def change_rb_hazard(self, event):
        """Get an event when state of rb_hazard is 'selected'."""

        log("'hazard' radiobutton selected")

    def change_rb_historical(self, event):
        """Get an event when state of rb_historical is 'selected'."""

        log("'historical' radiobutton selected")

    def clearZoneEvents(self):
        """Clear all entries in 'zone & events' widget.

        Also remove any selected subfaults, reset sort state variables, etc.
        """

        self.txt_zone_name.Clear()
        self.txt_num_subfaults.Clear()
        self.lst_subfaults.ClearAll()
        if self.selected_subfaults_layer:
            self.pyslip.deleteLayer(self.selected_subfaults_layer)
            self.selected_subfaults_layer = None
        if self.selected_zone_layer:
            self.pyslip.deleteLayer(self.selected_zone_layer)
            self.selected_zone_layer = None

        self.events_last_sort_col = None
        self.events_last_sort_order = None

######
# Various 'worker' routines.
######

    def saveState(self, filename=None):
        """Save application state to a given filename.

        filename  path to file to save to

        If filename not provided, use the default path.
        """

        log('saveState: filename=%s' % filename)

        if filename is None:
            filename = DefaultSaveFile

        # open pickle file
        fd = open(filename, 'w')
        p = pickle.Pickler(fd)

        # write state data to pickle
        p.dump(self.project_file)
        p.dump(self.txt_scenario.GetValue())
        p.dump(self.txt_wh.GetValue())
        p.dump(self.txt_wh_delta.GetValue())
        p.dump(self.rp_cbox.GetValue())
        p.dump(self.hp_points_data)

        p.dump(self.hp_lon)
        p.dump(self.hp_lat)

        p.dump(self.txt_area_of_interest.GetValue())
        p.dump(self.AOI_filename)
        p.dump(self.aoi_polygon)

        # close pickle, finished
        fd.close()

    def restoreState(self, filename=None):
        """Restore application state from file.

        filename  path to save file
        """

        log('restoreState: filename=%s' % filename)

        if filename is None:
            filename = DefaultSaveFile

        # open pickle file
        fd = open(filename, 'r')
        p = pickle.Unpickler(fd)

        # restore global variables
        self.project_file = p.load()
        self.txt_scenario.SetValue(p.load())
        self.txt_wh.SetValue(p.load())
        self.txt_wh_delta.SetValue(p.load())
        self.rp_cbox.SetValue(p.load())
        self.hp_points_data = p.load()
        self.pyslip.deleteLayer(self.hp_layer_id)
        self.hp_layer_id = \
                self.pyslip.addMonoPointLayer(self.hp_points_data,
                                              colour=PointsColour,
                                              size=PointsSize,
                                              name='hazard points')
        self.pyslip.setLayerPointSelectCallback(self.hp_layer_id,
                                                PointSelectDelta,
                                                self.HazardPointSelected)

        self.hp_lon = p.load()
        self.hp_lat = p.load()
        if self.hp_lon:
            self.hp_position.SetValue('%.3f / %.3f'
                                      % (self.hp_lon, self.hp_lat))
            self.deleteHPSelectedLayer()
            self.selected_hp_layer = \
                self.pyslip.addMonoPointLayer(((self.hp_lon, self.hp_lat),),
                                              colour=SelectHPPointColour,
                                              size=SelectHPPointSize,
                                              name='selected HP')

        self.txt_area_of_interest.SetValue(p.load())
        self.AOI_filename = p.load()
        self.aoi_polygon = p.load()
        self.pyslip.deleteLayer(self.aoi_layer)
        self.aoi_layer = \
                self.pyslip.addMonoPolygonLayer([self.aoi_polygon],
                                                map_relative=True,
                                                colour=AOIPolygonColour,
                                                size=AOIPolygonWidth,
                                                closed=True,
                                                filled=False,
                                                name='AOI')
        tt = wx.ToolTip('File is %s' % self.AOI_filename)
        self.txt_area_of_interest.SetToolTip(tt)

        fd.close()

    def showMousePosition(self, posn):
        """Show mouse geo position in controls.

        posn  tuple (lon, lat), float values
        """

        posn_str = ''
        if self.pyslip.isPositionOnMap(posn):
            (lon, lat) = posn
            posn_str = '%.*f / %.*f' % (LonLatPrecision, lon,
                                        LonLatPrecision, lat)

        self.mouse_position.SetValue(posn_str)

        # for Windows, action from pyslip means it gets focus
        if sys.platform == 'win32':
            self.pyslip.SetFocus()

    def HazardPointSelected(self, id, point=None):
        """Callback for hazard *point* selection.

        id        ID of layer of interest
        point     tuple (lon,lat) of point position
                  (None if click off point)

        Returns True if display was changed.

        Side effect is to display point lon/lat in text control.
        Side effect is to display selected HP in new layer.
        Side effect is to display deag source layer in map.
        """

        # whatever, deselect selected HP and deag layers
        self.deleteHPSelectedLayer()
        self.deleteDeagLayer()
        self.hp_selected_id = None

        # display HP position
        if point:
            # remember selected HP data
            (lon, lat) = point
            posn_str = '%.*f / %.*f' % (LonLatPrecision, lon,
                                        LonLatPrecision, lat)
            self.hp_position.SetValue(posn_str)
            self.hp_lon = lon
            self.hp_lat = lat

            (lon, lat) = point
            # get HP index number
            # TODO? could speed up with (lon, lat)->index dictionary
            for (hp_lon, hp_lat, hp_id) in self.hp_points:
                if lon == hp_lon and lat == hp_lat:
                    self.hp_selected_id = int(hp_id)
                    break

            self.loadHPSelectedLayer((lon, lat))

            # check that HP inside AOI
            self.check_hp_in_aoi()
        else:
            # no selection
            self.hp_position.SetValue('')
            self.hp_lon = None
            self.hp_lat = None

        # see if setting HP will update RP or WH
        self.update_HP_RP_WH()

        return True

    def HazardPointRightSelected(self, id, point=None):
        """Callback for hazard *point* right selection.

        id        ID of layer of interest
        point     tuple (lon,lat) of point position
                  (None if click off point)

        Side effect is to display HP_WH_RP graph in child window.
        """

        # display HP WHxRP graph
        if point:
            # get graph filename
            (lon, lat) = point
            lon = '%.3f' % lon
            lat = '%.3f' % lat
            filename = cfg.WHvRPHazardGraphFilemask % (lon, lat)
            filepath = os.path.join(cfg.WHvRPHazardGraphDir, filename)
            graph = ShowGraph(self, 'Wave height against Return Period',
                              GraphHTMLText % filepath, size=GraphSize)
            graph.Show()


    def loadHPSelectedLayer(self, posn):
        """Load the layer showing selected HP.

        posn  (lon, lat) tuple for position of selected HP
        """

        self.selected_hp_layer = \
            self.pyslip.addMonoPointLayer((posn,),
                                          colour=SelectHPPointColour,
                                          size=SelectHPPointSize,
                                          name='selected HP')

    def deleteHPSelectedLayer(self):
        """Delete the layer showing selected HP.
        """

        if self.selected_hp_layer:
            self.pyslip.deleteLayer(self.selected_hp_layer)
            self.selected_hp_layer = None

    def loadDeagLayer(self):
        """Load the deag layer.

        Only loads the deag layer if the RP value is set and there is a
        selected hazard point.

        Deag data is a file of: 'lon lat colour id'

        Updates self.deag_layer and self.deag_label_layer.
        """

        # get RP value
        rp_value = self.rp_cbox.GetValue()
        if rp_value and self.hp_selected_id:
            # get numeric RP value - split off 'years'
            (rp_value, _) = rp_value.split(' ')
            rp_value = int(rp_value)

            # get file in DeagPointsDirectory
            filename = PointFileMask % (self.hp_selected_id, rp_value)
            filepath = os.path.join(cfg.DeagPointsDirectory, filename)
            try:
                fd = open(filepath, 'r')
                lines = fd.readlines()
                fd.close()
            except IOError, e:
                msg = "Can't read file '%s': %s" % (filepath, str(e))
                raise RuntimeError(msg)

            data = []
            for line in lines:
                line = line.strip()
                (lon, lat, col, id) = line.split(' ')
                data.append((float(lon), float(lat), col, int(id)))

            self.deag_layer = self.pyslip.addPointLayer(data, colour=None,
                                                        size=PointsSize,
                                                        name='deag points')

            # register a box select callback for deag zone layer
            self.pyslip.setBoxSelectCallback(self.deag_layer, self.onZoneSelect)

            # get label file in DeagPointsDirectory
            filename = LegendFileMask % (self.hp_selected_id, rp_value)
            filepath = os.path.join(cfg.DeagPointsDirectory, filename)
            data = [(2, 2, filepath, 'se')]
            self.deag_label_layer = \
                    self.pyslip.addImageLayer(data, map_relative=False,
                                              name='deag legend')

    def deleteDeagLayer(self):
        """Delete the deag layer.

        Deletes self.deag_layer and self.deag_label_layer.
        """

        if self.deag_layer:
            # deregister a box select callback for deag zones
            self.pyslip.setBoxSelectCallback(self.deag_layer, None)

            self.pyslip.deleteLayer(self.deag_layer)
            self.deag_layer = None

        if self.deag_label_layer:
            self.pyslip.deleteLayer(self.deag_label_layer)
            self.deag_label_layer = None

    def onZoneSelect(self, id, points):
        """Zone select callback function.

        id      is the ID of the layer the selection was made in
        points  is a list of tuple (lon, lat) of selected points

        Decide if user has selected one source zone or many.  If more than one
        then user must choose in dialog.  Update zone name text control, etc.

        Returns True if display should be redrawn.
        """

        # see what zones contain the selected points
        zone_list = []
        for (x, y, id) in points:
            zone = self.subfaultid_2_zonename[id]
            if zone not in zone_list:
                zone_list.append(zone)

        # if more than one zone user must choose
        if len(zone_list) > 1:
            dlg = select_zone.SelectZone(self, zone_list)
            dlg.ShowModal()
            selected_zone = dlg.choice
            dlg.Destroy()
            if selected_zone is None:
                return False

            zone_list = [selected_zone]
        zone_name = zone_list[0]

        # update zone/subfault details
        self.txt_zone_name.SetValue(zone_name)

        # hourglass the cursor
        wx.BeginBusyCursor()
        wx.Yield()

        # get list of *all* subfaults in zone
        points = self.zonename_2_subfault_posns[zone_name]

        # populate the events grid and number-of-events box
        wh = float(self.txt_wh.GetValue())
        wh_delta = float(self.txt_wh_delta.GetValue())
        min_height = wh - wh_delta
        max_height = wh + wh_delta
        self.events = ghe.get_hp_events(self.hp_selected_id,
                                        min_height, max_height, zone_name)
        self.txt_num_subfaults.ChangeValue('%d' % len(self.events))

        self.fillEventsListCtrl(self.events)

        self.events_last_sort_col = 0
        self.events_last_sort_order = False

        # remove any subfault selection
        if self.selected_subfaults_layer:
            self.pyslip.deleteLayer(self.selected_subfaults_layer)
            self.selected_subfaults_layer = None

        # create selected zone layer
        if self.selected_zone_layer:
            self.pyslip.deleteLayer(self.selected_zone_layer)
        self.selected_zone_layer = \
            self.pyslip.addMonoPointLayer(points,
                                          colour=ZoneSelectColour,
                                          size=ZoneSelectSize,
                                          name='selected zone')
        self.pyslip.placeLayerAfterLayer(self.selected_zone_layer,
                                         self.deag_layer)

        # un-hourglass the cursor
        wx.EndBusyCursor()
        wx.Yield()

        return True

    def fillEventsListCtrl(self, events):
        """Populate the event list control.

        events  list of tuples [(...), ...]
        """

        # populate the event listctrl
        self.lst_subfaults.ClearAll()
        for (i, h) in enumerate(EventListHeaders):
            self.lst_subfaults.InsertColumn(i, h)
        for (i, e) in enumerate(events):
            index = self.lst_subfaults.InsertStringItem(sys.maxint, e[0])
            for (ii, ee) in enumerate(e[1:]):
                self.lst_subfaults.SetStringItem(index, ii+1, ee)
                font = self.lst_subfaults.GetItemFont(index)
                font.SetPointSize(ListPointSize)
                self.lst_subfaults.SetItemFont(index, font)
        for (i, w) in enumerate(EventListColumnWidths):
            self.lst_subfaults.SetColumnWidth(i, w)

######
# Menu event handlers
######

    def onFileNew(self, event):
        wx.MessageBox('File | New - not yet implemented', 'Sorry',
                      wx.OK | wx.ICON_EXCLAMATION)

    def onFileOpen(self, event):
        """Load project from a save file."""

        global ProjectDefaultDir

        default_dir = ProjectDefaultDir
        if default_dir is None:
            default_dir = os.getcwd()

        dlg = wx.FileDialog(self, message='Open project ...',
                            defaultDir=default_dir,
                            defaultFile='', wildcard=SaveAsWildcard,
                            style=wx.OPEN)
        filename = None
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            ProjectDefaultDir = dlg.GetDirectory()
            self.restoreState(filename)
        dlg.Destroy()

    def onFileSave(self, event):
        """Save project in previously defined project file.

        If no previously defined save file, becomes 'save as' and we
        remember the project pathname.
        """

        global ProjectSaveFilename

        if ProjectSaveFilename is None:
            ProjectSaveFilename = self.onFileSaveAs()
        else:
            self.saveState(ProjectSaveFilename)

    def onFileSaveAs(self, event=None):
        """Save project in a new file.

        Returns path to saved file.
        """

        global ProjectDefaultDir

        default_dir = ProjectDefaultDir
        if default_dir is None:
            default_dir = os.getcwd()

        dlg = wx.FileDialog(self, message='Save project as ...',
                            defaultDir=default_dir,
                            defaultFile='', wildcard=SaveAsWildcard,
                            style=wx.SAVE)
        filename = None
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            if not filename.endswith('.' + cfg.AppName.lower()):
                filename += '.' + cfg.AppName.lower()
            ProjectDefaultDir = dlg.GetDirectory()
            self.saveState(filename)

        dlg.Destroy()

        return filename

    def onExit(self, event):
        self.Close(True)

    def onEditPrefs(self, event):
        PreferencesDlg = Preferences(self, cfg.GenSaveDir)
        PreferencesDlg.ShowModal()
        cfg.GenSaveDir = PreferencesDlg.SavePath
        PreferencesDlg.Destroy()

    def onHelpContents(self, event):
        try:
            if sys.platform == 'win32':
                os.startfile(cfg.UserGuideFile)
            else:
                subprocess.Popen(['xdg-open', cfg.UserGuideFile])
        except:
            self.error('To view the User Guide you must have installed '
                       'a viewer for PDF  files.\n\n'
                       'You can get one from www.adobe.com.')

    def onHelpCopyright(self, event):
        CopyrightDlg = CopyAboutDlg(self, cfg.CopyrightTitle, CopyrightHTMLText,
                                    size=CopyrightSize)
        CopyrightDlg.Show()

    def onHelpAbout(self, event):
        aboutDlg = CopyAboutDlg(self, cfg.AboutTitle, AboutHTMLText,
                                size=AboutSize)
        aboutDlg.Show()

######
# GUI event handlers
######

    def onClose(self, event):
        """Handle the CLOSE event.

        Save state that needs saving.  Don't prompt user to save, just write
        to a default state file.
        """

        # save project, if necessary
        if DirtyProject:
            self.saveState(DefaultSaveFile)

        # save user-changeable config
        self.saveState()

        # let wxPython handle the event
        event.Skip()

    def onTextCtrlGetsFocus(self, event):
        """Set text in object as 'all selected'."""

        obj = event.GetEventObject()
        #obj.SetValue('')
        #obj.SetInsertionPoint(0)
        obj.SelectAll()

    def onGenerate(self, event):
        """Handle pressing the 'Generate' button."""

        # check the scenario name
        msg = ''
        scenario_name = self.txt_scenario.GetValue()
        if not scenario_name:
            msg += 'You must set a scenario name.\n'

        # check we have selected an HP
        if not self.hp_lon:
            msg += 'You must select a hazard point.\n'

        # check we have done the WH
        wave_height = self.txt_wh.GetValue()
        wave_height_delta = self.txt_wh_delta.GetValue()
        if not wave_height or not wave_height_delta:
            msg += 'You must select a wave height and delta.\n'

        # check bounding box chosen
        bbox_file = self.txt_area_of_interest.GetValue()
        if not bbox_file and not self.aoi_polygon:
            msg += 'You must select an area of interest.\n'

        # check bounding box chosen self.hp_inside_bb
        if not self.hp_inside_bb:
            msg += 'You must order points inside the area of interest.\n'

        # check user has selected quakes
        num_q_selected = self.lst_subfaults.GetSelectedItemCount()
        if num_q_selected < 1:
            msg += 'You must select a fault and one or more events.\n'

        # check that ANUGA is around
        try:
            import anuga.shallow_water.data_manager
        except ImportError, e:
            log('Import error: %s' % str(e))
            msg += 'You have not installed ANUGA correctly.\n'

        if msg:
            self.error(msg)
            return

        # get selected items - [<eventID>, <eventID>, ...]
        selected_events = []
        item = -1
        while True:
            item = self.lst_subfaults.GetNextSelected(item)
            if item < 0:
                break
            data = self.lst_subfaults.GetItemText(item)
            selected_events.append(int(data))

        ######
        # OK, do generation
        ######

        self.btn_generate.SetLabel('Generating...')
        wx.BeginBusyCursor()
        self.Disable()
        wx.Yield()

        self.warn('Estimating completion time...')

        # get hazard point index
        hp_id = self.hp_selected_id

        # get wave height max and min
        wh = float(self.txt_wh.GetValue())
        wh_delta = float(self.txt_wh_delta.GetValue())

        # start the generation process
        max_wh = wh + wh_delta
        min_wh = wh - wh_delta

        min_wh = max(min_wh, 0.0)       # limit wave height to [0.0, 10.0]
        max_wh = min(max_wh, 10.0)

        # prepare various file pathnames
        results_dir = cfg.ResultsDirMask % (hp_id, min_wh, max_wh)
        base_dir = os.path.join(cfg.GenSaveDir, scenario_name)
        gen_dir = os.path.join(base_dir, results_dir)
        boundaries_dir = os.path.join(base_dir, 'boundaries')

        shutil.rmtree(gen_dir, ignore_errors=True)
        try:
            os.makedirs(gen_dir)
        except OSError, e:
            self.error('Error making directory:\n%s\n%s'
                       % (gen_dir, str(e)))
            wx.EndBusyCursor()
            self.Enable()
            self.btn_generate.SetLabel('Generate')
            return

        faultxy_filename = os.path.join(gen_dir, cfg.FaultXYFilename)
        quakeprob_filename = os.path.join(gen_dir, cfg.QuakeProbFilename)

        # get path to and check existence of data files
        msg = ''
        hazard_file = os.path.join(cfg.TFilesDirectory,
                                   'T-%05d' % self.hp_selected_id)
        if not os.path.isfile(hazard_file):
            msg += "Hazard file %s doesn't exist!?" % hazard_file
        invall_file = os.path.join(cfg.MultimuxDirectory, cfg.InvallFilename)
        if not os.path.isfile(invall_file):
                        msg += "Invall file %s doesn't exist!?" % invall_file

        if msg:
            self.error(msg)
            wx.EndBusyCursor()
            self.Enable()
            self.btn_generate.SetLabel('Generate')
            return

        # now actually get quake data
        try:
            lq.list_quakes(hp_id, min_wh, max_wh, invall_file,
                           hazard_file, faultxy_filename, quakeprob_filename)
        except RuntimeError, msg:
            wx.EndBusyCursor()
            self.Enable()
            self.btn_generate.SetLabel('Generate')
            self.error('Error in list_quakes(): %s' % msg)
            return

        try:
            for event_id in selected_events:
                mmx.multimux(event_id, base_dir)
        except RuntimeError, msg:
            wx.EndBusyCursor()
            self.Enable()
            self.btn_generate.SetLabel('Generate')
            self.error('Error in multimux(): %s' % msg)
            return

        # create urs_order.csv containing HPs inside bounding box
        urs_order_file = os.path.join(boundaries_dir, 'urs_order.csv')
        fd = open(urs_order_file, 'w')
        fd.write('index,longitude,latitude\n')
        for bbhp in self.hp_inside_bb:
            fd.write('%d,%f,%f\n' % bbhp)
        fd.close()

        # copy required files to 'gen_dir'
        shutil.copy('run_build.py', gen_dir)
        shutil.copy('config.py', gen_dir)
        shutil.copy('build_urs_boundary.py', gen_dir)

        self.warn('Files created in directory: %s' % cfg.GenSaveDir)

        # estimate completion time
        estimated_time = \
                self.estimate_generate_time(num_q_selected, selected_events,
                                            scenario_name)

        ######
        # Present summary to user
        ######

        msg = ['Scenario: %s' % scenario_name,
               'Hazard Point: %.3f / %.3f' % (self.hp_lon, self.hp_lat),
               'Return period: %s' % self.rp_cbox.GetValue(),
               'Wave height: %sm +/- %sm'
                   % (self.txt_wh.GetValue(), self.txt_wh_delta.GetValue()),
               'Boundary file: %s' % self.txt_area_of_interest.GetValue(),
               'Zone: %s' % self.txt_zone_name.GetValue(),
               'Number of selected events: %d' % num_q_selected,
               '',
               'This might take %s to finish, but could take '
               'longer on slower hardware.' % estimated_time,
               '',
               'Do you want to continue?']
        msg = '\n'.join(msg)
        log('Generate Summary:\n' + msg)
        dlg = wx.MessageDialog(parent=self, message=msg, caption='Summary',
                               style=wx.OK|wx.CANCEL|wx.ICON_INFORMATION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result != wx.ID_OK:
            wx.EndBusyCursor()
            self.Enable()
            self.btn_generate.SetLabel('Generate')
            log('Generate cancelled')
            return
        log('Generate continuing ...')

        # run the generate process as a subprocess
        here = os.getcwd()
        log_filename = os.path.join(gen_dir, 'build_urs_boundary.log')
        try:
            os.remove(log_filename)
        except OSError:
            pass

        # figure out full mux directory path (required for Windows)
        mux_dir = os.path.abspath(cfg.MuxDirectory)

        # now move to generating output directory        
        os.chdir(gen_dir)

        cmd = ['python', 'run_build.py', log_filename, scenario_name,
               cfg.GenSaveDir, cfg.AppName, mux_dir, cfg.EventFile]
        str_selected_events = [str(x) for x in selected_events]
        cmd.extend(str_selected_events)
        dlg = etl.ExecuteAndTailLogfile(self, cmd,
                                        log_filename, 'Generating data ...')
        dlg.ShowModal()
        returncode = dlg.returncode
        dlg.Destroy()

        os.chdir(here)

        # now split the fault.xy file that was generated
        wx.Yield()
        self.splitFaultXY(faultxy_filename, boundaries_dir, selected_events)

        # cursor back to normal
        wx.EndBusyCursor()
        self.Enable()
        self.btn_generate.SetLabel('Generate')

        log('Generate finished!')

######
# Utility routines
######

    def estimate_generate_time(self, num_subfaults, selected_events,
                               scenario_name):
        """Estimate generation time.

        num_subfaults    numer of subfaults
        selected_events  list of selected event IDs
        scenario_name    name of scenario

        Return estimated time string.
        """

        max_sources = 0

        for ev_id in selected_events:
            # form pathname of multimux file - get # of sources
            mux_filename = os.path.join(cfg.GenSaveDir, scenario_name,
                                        'boundaries', str(ev_id), cfg.EventFile)
            f = open(mux_filename, 'r')
            line = f.readline()
            f.close()
            num_sources = int(line.strip())
            max_sources = max(max_sources, num_sources)

        # get estimated completion time in seconds
        result = int((num_subfaults+max_sources)**EstimateFudgeFactor)
        if result < 120:
            result = 120

        # convert integer minutes to hours, days and minutes
        mins = int(float(result) / 60 + 0.5)
        hours = int(float(result) / (60*60) + 0.5)
        days = int(float(result) / (24*60*60) + 0.5)

        if days > 0:
            if hours >= 12:
                days += 1
            result = '%d day%s' % (days, 's' if days > 1 else '')
        elif hours > 0:
            if mins >= 30:
                hours += 1
            result = '%d hour%s' % (hours, 's' if hours > 1 else '')
        else:
            result = '%d minute%s' % (mins, 's' if mins > 1 else '')

        return result


    def splitFaultXY(self, fault_xy_file, boundaries_dir, event_list):
        """Split generated fault.xy file into boundaries/<ID>/event_<ID>.xy.

        fault_xy_file   path to generated fault.xy file
        boundaries_dir  path to 'boundaries' directory
        event_list      list of event IDs used to generate fault.xy
        """

        # read the fault.xy file into memory
        f = open(fault_xy_file, 'r')
        fxy_lines = f.readlines()
        f.close()

        fxy_header = fxy_lines[0]
        split_lines = []
        for l in fxy_lines[1:]:
            l = l.strip()
            split_lines.append(l.split(','))

        # for each eventID, get subfaults and strip lines into split file
        for id in event_list:
            # make the split file
            split_file = os.path.join(boundaries_dir, str(id),
                                      'event_%05d.xy' % id)
            sf = open(split_file, 'w')
            sf.write(fxy_header)

            subfaults = self.eventid_2_subfaults[id]
            for sl in split_lines:
                (lon, lat, quake_id, subfault_id) = sl
                quake_id = int(quake_id)
                if quake_id == id:
                    sf.write('%s,%s,%d,%s\n'
                             % (lon, lat, quake_id, subfault_id))
            sf.close()

    def get_WH_from_RP_HP(self, rp, hp):
        """Get waveheight given return period and hazard point.

        rp   is the return period
        hp   is a hazard point position tuple (lon, lat)

        Return the appropriate waveheight for rp and hp by grovelling
        in the 'WaveAmplitudeFile' file.
        """

        # get contents of file
        fd = open(cfg.WaveAmplitudeFile, 'r')
        lines = fd.readlines()
        fd.close()

        repat = re.compile(' +')

        # get possible return periods from first line
        hdr = lines[0].strip()
        periods = repat.split(hdr)
        periods = [int(float(x)) for x in periods]

        # figure out index into 'periods' for given RP
        try:
            rp_index = periods.index(rp)
        except ValueError:
            msg = ("RP '%d' not found in line 1 of file '%s'"
                   % (rp, cfg.WaveAmplitudeFile))
            raise RuntimeError(msg)

        # unpack the hp position tuple
        (hp_lon, hp_lat) = hp

        # look through lines after header for line matching hp tuple
        for l in lines[1:]:
            l = l.strip()
            fields = repat.split(l)
            lon = float(fields[0])
            lat = float(fields[1])
            if lon == hp_lon and lat == hp_lat:
                return float(fields[rp_index+3])

        msg = ("HP (%.3f,%.3f) not found in file '%s'"
               % (hp_lon, hp_lat, cfg.WaveAmplitudeFile))
        raise RuntimeError(msg)

    def get_RP_from_WH_HP(self, wh, wh_delta, hp):
        """Get return period given wave height and hazard point.

        wh        is the wave height
        wh_delta  is the WH delat from the textbox
        hp        is a hazard point position tuple (lon, lat)

        Return an 'appropriate' return period for wh and hp by grovelling
        in 'WaveAmplitudeFile' file.  The return period appropriateness
        is up for discussion!
        """

        # get contents of file
        fd = open(cfg.WaveAmplitudeFile, 'r')
        lines = fd.readlines()
        fd.close()

        repat = re.compile(' +')

        # get possible return periods from first line
        hdr = lines[0].strip()
        periods = repat.split(hdr)
        periods = [int(float(x)) for x in periods]

        # unpack the hp position tuple
        (hp_lon, hp_lat) = hp

        # look through lines after header for line matching hp tuple
        lon = None
        for l in lines[1:]:
            l = l.strip()
            fields = repat.split(l)
            lon = float(fields[0])
            lat = float(fields[1])
            if lon == hp_lon and lat == hp_lat:
                break

        if lon is None:
            msg = ("HP (%.3f,%.3f) not found in file '%s'"
                   % (hp_lon, hp_lat, cfg.WaveAmplitudeFile))
            raise RuntimeError(msg)

        # we have line matching HP - get list of waveheights
        wh_list = [float(x) for x in fields[3:]]

        # now get max and min RP given wh+delta and wh-delta
        # NOTE: these min/max are indices into periods (and wh)
        min_rp = self.nearest_interpolate_index(wh_list, wh-wh_delta)
        max_rp = self.nearest_interpolate_index(wh_list, wh+wh_delta)

        # now decide which RP in range [min_rp, max_rp] we will use
        if min_rp == max_rp:
            # no-brainer
            return periods[min_rp]

        if (max_rp - min_rp) <= MaxNowarnRPRange:
            return periods[(max_rp + min_rp) // 2]

        # RP range is 'big', warn user
        result = periods[(max_rp + min_rp) // 2]
        self.warn('Valid Return Periods for the waveheights given are in the '
                  'range %s to %s years: choosing %d.'
                  % (periods[min_rp], periods[max_rp], result))

        return result

    def nearest_interpolate_index(self, values, value):
        """Get index of closest value in list matching value.

        values  list of monotonically increasing values
        value   value of interest

        Return index of value in values matching value of interest.
        """

        # ensure list is monotonically increasing
        values.sort()

        # handle values outside range in values
        if value <= values[0]:
            return 0
        if value >= values[-1]:
            return len(values) - 1

        for i in range(len(values)-1):
            if values[i] <= value <= values[i+1]:
                return i

        msg = ("Problem in nearest_interpolate_index():\n"
               "Value %d, list=%s\n"
               "Didn't get interpolation termination!?"
               % (value, str(values)))
        raise RuntimeError(msg)

    def loadEvent2SubfaultData(self):
        """Load dictionary that maps eventID -> subfaultID iterable.

        Creates: eventid_2_subfaults    {<eventID>: (subfaultID, ...), ...}
        """

        # get data from file
        fd = open(cfg.EventTFile, 'r')
        lines = fd.readlines()
        fd.close()

        # trash the first line
        lines = lines[1:]

        # load into dictionary
        self.eventid_2_subfaults = {}
        repat = re.compile(' +')        # split on one or more spaces
        for (i, l) in enumerate(lines):
            l = l.strip()
            (_, _, _, _, _, subfaults) = repat.split(l, maxsplit=5)
            subfaults = repat.split(subfaults)
            self.eventid_2_subfaults[i] = map(int, subfaults)

    def loadSubfaultData(self):
        """Load dictionaries that maps subfault ID to zone name, etc.

        Creates:
        subfaultid_2_zonename      {<subfaultID>: <zonename>, ...}
        zonename_2_subfault_posns  {<zonename>: [(lon,lat), ...], ...}
        subfaultid_2_position      {<subfaultID>: (lon,lat), ...}
        """

        # create empty dictionaries
        self.subfaultid_2_zonename = {}
        self.zonename_2_subfault_posns = {}
        self.subfaultid_2_position = {}

        # get data from file
        fd = open(cfg.SubfaultIdZoneFile, 'r')
        lines = fd.readlines()
        fd.close()

        # read data lines, creating dictionaries
        for line in lines:
            line = line.strip()
            if not line or line[0] == '#':
                continue

            (lon, lat, subfaultid, zonename) = line.split(' ', 3)
            lon = float(lon)
            lat = float(lat)
            subfaultid = int(subfaultid)

            self.subfaultid_2_zonename[subfaultid] = zonename

            val = self.zonename_2_subfault_posns.get(zonename, [])
            val.append((lon,lat))
            self.zonename_2_subfault_posns[zonename] = val

            self.subfaultid_2_position[subfaultid] = (lon, lat)

    def get_home_path(self):
        """Get the path to the defined home directory.

        Returns a string containing the path to the user's HOME directory.

        Works on both Linux and Windows.
        """

        if sys.platform == 'win32':
            drive = os.environ['HOMEDRIVE']
            path = os.environ['HOMEPATH']
            path = os.path.join(drive, path)
        elif sys.platform == 'linux2':
            path = os.environ['HOME']
        else:       # assume UNIX, whatever
            path = os.environ['HOME']

        return path

    def getPointsExtent(self, points):
        """Get geo extent of a set of points.

        points  a list of (lon, lat) tuples

        Returns a tuple (w, e, s, n) of limits.
        """

        w = 361.
        e = -361.
        s = 91.0
        n = -91.0

        for p in points:
            (lon, lat) = p
            w = min(w, lon)
            e = max(e, lon)
            s = min(s, lat)
            n = max(n, lat)

        return (w, e, s, n)

######
# Load config settings.
#
# Base config values come from the "import config" import.
# Values in the saved config overwrite the imported attributes.
######

    def load_config(self):
        """Load config settings from default file, overwrite cfg.attibutes."""

        try:
            fd = open(cfg.CfgSaveFile, 'r')
        except IOError:
            return

        config = ConfigParser.RawConfigParser()
        config.read(cfg.CfgSaveFile)

        cfg.GenSaveDir = config.get('Config', 'GenSaveDir')
        log('load_config: cfg.GenSaveDir=%s' % cfg.GenSaveDir)

        fd.close()

######
# Check if Hazard Point is within Area Of Interest
######

    def check_hp_in_aoi(self):
        """Check that the HP is inside the AOI.

        If HP and AOI defined and HP not in AOI, warn user.

        The HP (self.hp_lon, self.hp_lat) may not be set.
        The AOI (self.aoi_polygon) may not be set.
        """

        if self.hp_lon and self.aoi_polygon:
            if not polygon.point_in_poly(self.hp_lon, self.hp_lat,
                                         self.aoi_polygon):
                msg = ['The hazard point you have selected is not '
                       'inside the area of interest bounding polygon.',
                       '',
                       'It is recommended that the selected hazard point '
                       'lie within the area of interest bounding polygon.']
                msg = '\n'.join(msg)
                self.info(msg)

######
# Display error/warning messages
######

    def warn(self, msg):
        """Warn user about something.

        msg  warning message
        """

        # set message into status bar
        self.status_bar.SetStatusText(msg)
        self.status_bar.SetBackgroundColour(wx.RED)
        self.status_bar.Refresh()

        # remove warning after a time
        self.timer = wx.Timer(self, wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.unshade)
        self.timer.Start(1000)

    def unshade(self, event):
        """Timer handler to remove status bar warning."""

        self.status_bar.SetBackgroundColour(wx.WHITE)
        self.status_bar.Refresh()

        self.timer = wx.Timer(self, wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.unwarn)
        self.timer.Start(10000)

    def unwarn(self, event):
        """Timer handler to remove status bar warning."""

        self.status_bar.SetBackgroundColour(wx.WHITE)
        self.status_bar.SetStatusText('')
        self.status_bar.Refresh()
        self.Bind(wx.EVT_TIMER, None)
        self.timer = None


    def error(self, msg):
        """Tell user about an error.

        msg  error message
        """

        log.critical('ERROR displayed:\n\n%s\n' % msg)

        dlg = wx.MessageDialog(parent=self, message=msg, caption='Error',
                               style=wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def info(self, msg):
        """Tell user something.

        msg  message
        """

        dlg = wx.MessageDialog(parent=self, message=msg, caption='Information',
                               style=wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def log_stack(self):
        """Dump traceback-style info to the log."""

        log('\n' + ''.join(traceback.format_list(traceback.extract_stack())))

################################################################################
# Start the application.
################################################################################

if __name__ == '__main__':
    import sys
    import time
    import traceback

    # our own handler for uncaught exceptions
    def excepthook(type, value, tb):
        msg = '\n' + '=' * 80
        msg += '\nUncaught exception:\n'
        msg += ''.join(traceback.format_exception(type, value, tb))
        msg += '=' * 80 + '\n'

        log.critical('\n' + msg)
        print msg
        time.sleep(0.5)
        sys.exit(1)

    # plug our handler into the python system
    sys.excepthook = excepthook

    # start wxPython app
    app = wx.App()
    AppFrame().Show()
    app.MainLoop()

