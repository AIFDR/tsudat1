#!/usr/bin/env python

"""The TIRM/PTHA-DAT/DAFT/NANKAI/Tsu-DAT application.

Run this bit of the generate code as a separate process.

Usage: python run_build.py <event1> <event2> ...
"""


import os
import time


LogFD = None
LogFilename = None


def log(msg):
    global LogFD

    if not LogFD:
        LogFD = open(LogFilename, 'w')

    LogFD.write(msg+'\n')
    LogFD.flush()


def run_build(log_filename, ScenarioName, GenSaveDir, AppLongName,
              MuxDirectory, EventFile, selected_events):
    """Run build_urs_boundary.py for each selected event.

    log_filename     path to the log file to generate/monitor
    ScenarioName     the scenario name
    GenSaveDir       path to the generated data save directory
    AppLongName      the application long form string
    MuxDirectory     path to the MUX directory
    EventFile        path to the event file
    selected_events  a list of event IDs (strings)
    """

    global LogFilename

    LogFilename = log_filename

    # now run build_urs_boundary for each event ID
    for event_id in selected_events:
        log('Handling event ID %d' % event_id)

        # get paths
        event_folder = os.path.join(GenSaveDir, ScenarioName,
                                    'boundaries', str(event_id))

        # now run the build
        import build_urs_boundary as bub

        log('Running build_urs_boundary() for event %d' % event_id)
        bub.log = log
        bub.build_urs_boundary(EventFile,
                               os.path.join(event_folder, ScenarioName),
                               True, event_folder, MuxDirectory,
                               '../boundaries/urs_order.csv', ScenarioName)

        del bub

    log('Generation is finished')
    log('*' * 80)
    log('*' * 80)

if __name__ == '__main__':
    import sys

    # get all selected events from command line
    LogFilename = sys.argv[1]
    ScenarioName = sys.argv[2]
    GenSaveDir =  sys.argv[3]
    AppLongName = sys.argv[4]
    MuxDirectory = sys.argv[5]
    EventFile = sys.argv[6]
    selected_events = sys.argv[7:]
    selected_events = [int(x) for x in selected_events]

    log('Generation logfile is: %s' % LogFilename)

    run_build(LogFilename, ScenarioName, GenSaveDir, AppLongName,
              MuxDirectory, EventFile, selected_events)
