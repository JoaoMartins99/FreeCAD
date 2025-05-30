# ***************************************************************************
# *   (c) 2009 Yorik van Havre <yorik@uncreated.net>                        *
# *   (c) 2010 Ken Cline <cline@frii.com>                                   *
# *   (c) 2019 Eliud Cabrera Castillo <e.cabrera-castillo@tum.de>           *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************
"""Provides the base classes for newer Draft Gui Commands."""
## @package gui_base
# \ingroup draftguitools
# \brief Provides the base classes for newer Draft Gui Commands.

## \addtogroup draftguitools
# @{
import FreeCAD as App
import FreeCADGui as Gui
from draftguitools import gui_trackers as trackers
from draftutils import gui_utils
from draftutils import params
from draftutils import todo
from draftutils.messages import _toolmsg, _log


class GuiCommandSimplest:
    """Simplest base class for GuiCommands.

    This class only sets up the command name and the document object
    to use for the command.
    When it is executed, it logs the command name to the log file,
    and prints the command name to the console.

    It implements the `IsActive` method, which must return `True`
    when the command should be available.
    It should return `True` when there is an active document,
    otherwise the command (button or menu) should be disabled.

    This class is meant to be inherited by other GuiCommand classes
    to quickly log the command name, and set the correct document object.

    Parameter
    ---------
    name: str, optional
        It defaults to `'None'`.
        The name of the action that is being run,
        for example, `'Heal'`, `'Flip dimensions'`,
        `'Line'`, `'Circle'`, etc.

    Attributes
    ----------
    featureName: str
        This is the command name, which is assigned by `name`.

    doc: App::Document
        This attribute should be used by functions to make sure
        that the operations are performed in the correct document
        and not in other documents.
    """

    def __init__(self, name="None"):
        self.doc = None
        self.featureName = name

    def IsActive(self):
        """Return True when this command should be available."""
        return bool(App.activeDocument())

    def Activated(self):
        """Execute when the command is called.

        Log the command name to the log file and console.
        Also update the `doc` attribute.
        """
        self.doc = App.activeDocument()
        _toolmsg("{}".format(16*"-"))
        _toolmsg("GuiCommand: {}".format(self.featureName))


class GuiCommandNeedsSelection(GuiCommandSimplest):
    """Base class for GuiCommands that need a selection to be available.

    It re-implements the `IsActive` method to return `True`
    when there is both an active document and an active selection.

    It inherits `GuiCommandSimplest` to set up the document
    and other behavior. See this class for more information.
    """

    def IsActive(self):
        """Return True when this command should be available."""
        return bool(Gui.Selection.getSelection())


class GuiCommandBase:
    """Generic class that is the basis of all Gui commands.

    This class should eventually replace `DraftTools.DraftTool`,
    once all functionality in that class is merged here.

    Attributes
    ----------
    commit_list : list of 2-element tuples
        Each tuple is made of a string, and a list of strings.
        ::
            commit_list = [(string1, list1), (string2, list2), ...]

        The string is a simple header, for example, a command name,
        that indicates what is being executed.

        Each string in the list of strings represents a Python instruction
        which will be executed in a delayed fashion
        by `todo.ToDo.delayCommit()`
        ::
            list1 = ["a = FreeCAD.Vector()",
                     "pl = FreeCAD.Placement()",
                     "Draft.autogroup(obj)"]

            commit_list = [("Something", list1)]

        This is used when the 3D view has event callbacks that crash
        Coin3D.
        If this is not needed, those commands could be called in the
        body of the command without problem.
        ::
            >>> a = FreeCAD.Vector()
            >>> pl = FreeCAD.Placement()
            >>> Draft.autogroup(obj)
    """

    def __init__(self, name="None"):
        App.activeDraftCommand = None
        self.call = None
        self.commit_list = []
        self.doc = None
        self.featureName = name
        self.planetrack = None
        self.view = None

    def IsActive(self):
        """Return True when this command should be available."""
        return bool(gui_utils.get_3d_view())

    def Activated(self):
        self.doc = App.ActiveDocument
        if not self.doc:
            self.finish()
            return

        App.activeDraftCommand = self
        self.view = gui_utils.get_3d_view()

        if params.get_param("showPlaneTracker"):
            self.planetrack = trackers.PlaneTracker()

        _toolmsg("{}".format(16*"-"))
        _toolmsg("GuiCommand: {}".format(self.featureName))

    def finish(self):
        """Terminate the active command by committing the list of commands.

        It also perform some other tasks like terminating
        the plane tracker and the snapper.
        """
        App.activeDraftCommand = None
        if self.planetrack:
            self.planetrack.finalize()
        self.planetrack = None
        if hasattr(Gui, "Snapper"):
            Gui.Snapper.off()
        if self.call:
            try:
                self.view.removeEventCallback("SoEvent", self.call)
            except RuntimeError:
                # the view has been deleted already
                pass
        self.call = None
        if self.commit_list:
            todo.ToDo.delayCommit(self.commit_list)
        self.commit_list = []

    def commit(self, name, func):
        """Store actions to be committed to the document.

        Parameters
        ----------
        name : str
            A string that indicates what is being committed.

        func : list of strings
            Each element of the list should be a Python command
            that will be executed.
        """
        self.commit_list.append((name, func))

## @}
