#!/usr/bin/env python

"""
A dialog allowing user to select one of many zone names.
"""


import wx


# sizes of various bits and pieces
DialogSize = (220, 100)
ListBoxSize = (220, 100)
ButtonSize = (75, 27)


################################################################################
# A simple custom dialog that allows the user to select one of many zone names.
#
# Used:
#     zone_list = ['Alaska', 'Yap']
#     dlg = SelectZone(self, zone_list)
#     selected_zone = dlg.choice
#     dlg.Destroy()
#     if selected_zone:
#         # user *did* select a zone
################################################################################

class SelectZone(wx.Dialog):
    """A simple dialog that allows the user to select one of many zone names.

    Used:
        zone_list = ['Alaska', 'Yap']
        dlg = SelectZone(self, zone_list)
        selected_zone = dlg.choice
        dlg.Destroy()
        if selected_zone:
            # user *did* select a zone
    """

    def __init__(self, parent, zone_list=None):
        """Initialize the dialog.

        parent  reference to parent object
        zone_list  a list of zone names

        Sets self.choice to user selection, or None if no selection.
        """

        wx.Dialog.__init__(self, parent, id=wx.ID_ANY,
                           title='Choose a zone')

        vbox = wx.BoxSizer(wx.VERTICAL)
        txt = wx.StaticText(self, wx.ID_ANY,
                            'You selected more than one zone.\n'
                            'Please choose one:')
        self.list = wx.ListBox(self, wx.ID_ANY, size=ListBoxSize,
                               choices=zone_list)
        self.btnOK = wx.Button(self, wx.ID_ANY, size=ButtonSize, label='OK')
        self.btnOK.Disable()
        self.btnCANCEL = wx.Button(self, wx.ID_ANY, size=ButtonSize,
                                   label='Cancel')

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btnCANCEL, proportion=0, border=5,
                 flag=wx.ALL|wx.ALIGN_RIGHT)
        hbox.Add(self.btnOK, proportion=0, border=5, flag=wx.ALL|wx.ALIGN_RIGHT)

        vbox.Add(txt, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.list, proportion=1, flag=wx.ALL, border=5)
        vbox.Add(hbox, proportion=0, flag=wx.ALL|wx.ALIGN_RIGHT, border=0)

        self.SetSizer(vbox)
        self.Fit()

        self.choice = None

        self.list.Bind(wx.EVT_LISTBOX, self.onListChoice)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.onListDClick)
        self.btnOK.Bind(wx.EVT_BUTTON, self.onOK)
        self.btnCANCEL.Bind(wx.EVT_BUTTON, self.onCANCEL)

    def onListChoice(self, event):
        self.choice = self.list.GetStringSelection()
        self.btnOK.Enable()

    def onListDClick(self, event):
        self.choice = self.list.GetStringSelection()
        self.Close()

    def onOK(self, event):
        self.Close()

    def onCANCEL(self, event):
        self.choice = None
        self.Close()


if __name__ == '__main__':

    class MyFrame(wx.Frame):
        def __init__(self, parent, id, title):
            wx.Frame.__init__(self, parent, id, title)
            panel = wx.Panel(self, -1)
            wx.Button(panel, 1, 'Show SelectZone Dialog', (50,50))
            self.Bind(wx.EVT_BUTTON, self.OnShowCustomDialog)

        def OnShowCustomDialog(self, event):
            zones = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta',
                     'Eta', 'Theta']
            dia = SelectZone(self, zones)
            val = dia.ShowModal()
            print('.choice=%s' % dia.choice)
            dia.Destroy()

    class MyApp(wx.App):
        def OnInit(self):
            frame = MyFrame(None, -1, 'select_zone.py')
            frame.Show(True)
            frame.Centre()
            return True

    app = MyApp(0)
    app.MainLoop()
