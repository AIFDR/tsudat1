#!/usr/bin/env python

"""A class to execute a standalone process and 'tail' a logfile for viewing."""


import os
import subprocess
import time
import wx


class ExecuteAndTailLogfile(wx.Dialog):
    """A dialog to execute a command and tail a produced logfile."""

    def __init__(self, parent, cmd, logfile, title, *args, **kwargs):
        """Execute a command as a subprocess and tail a file.

        parent   reference to parent widget
        cmd      a string or list of strings defining the command to execute
                 (see subprocess.Popen() documentation)
        logfile  path to the logfile to monitor
        title    title string for dialog window
        env      if supplied, the environment to pass to the subprocess

        Waits until the subprocess finishes, then enables the 'OK' button.
        """

        if kwargs.has_key('style'):
            del kwargs['style']
        kwargs['style'] = wx.CAPTION |  wx.CLIP_CHILDREN
        wx.Dialog.__init__(self, parent, title=title, *args, **kwargs)

        # draw the gui
        self.txt_log = wx.TextCtrl(self, size=(800,400), style=wx.TE_MULTILINE)
        self.btn_ok = wx.Button(self, label='OK')
        self.btn_ok.Bind(wx.EVT_BUTTON, self.onOk)
        self.btn_ok.Enable(False)

        sb = wx.StaticBox(self,  wx.ID_ANY, label='')
        hbox = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)
        hbox.Add(self.txt_log, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        hbox.Add(self.btn_ok, flag=wx.ALIGN_RIGHT|wx.ALL, border=5)

        self.SetSizerAndFit(hbox)
        self.Show()
        wx.Yield()

        self.cmd = cmd
        self.logfile = logfile

        # start subprocess - the stdout/stderr redirection ignores any prints
        p = subprocess.Popen(self.cmd)
#        p = subprocess.Popen(self.cmd, stdout=subprocess.PIPE,
#                             stderr=subprocess.PIPE)

        # wait until logfile is produced
        file_size = 0
        while True:
            try:
                fd = open(self.logfile)
            except IOError:
                time.sleep(0.1)
            else:
                break

        wx.Yield()

        # read logfile, copy to TextCtrl
        while p.poll() is None:
            time.sleep(0.01)
            size = os.stat(self.logfile).st_size
            if size > file_size:
                lines = fd.read(size - file_size).strip()
                lines = lines.split('\n')
                for line in lines:
                    if '|' in line:
                        (_, line) = line.split('|', 1)
                    self.txt_log.AppendText(line+'\n')
                file_size = size
            wx.Yield()

        self.returncode = p.returncode

        self.btn_ok.Enable(True)
        self.btn_ok.Refresh()

    def onOk(self, event=None):
        self.Hide()

################################################################################

if __name__ == '__main__':
    import sys

    class MyFrame(wx.Frame):
        """ We simply derive a new class of Frame. """
        def __init__(self, parent, title):
            wx.Frame.__init__(self, parent, title=title, size=(200,100))
            self.button = wx.Button(self, label='Run Test')
            self.button.Bind(wx.EVT_BUTTON, self.onButton)
            self.Show(True)

        def onButton(self, event):
            cmd = './test.sh'
            logfile = 'xyzzy'
            try:
                os.remove(logfile)
            except OSError:
                pass
            pdlg = ExecuteAndTailLogfile(self, cmd, logfile, 'Generating...')
            pdlg.ShowModal()
            pdlg.Destroy()

    app = wx.App(False)
    frame = MyFrame(None, 'Test window')
    app.MainLoop()

