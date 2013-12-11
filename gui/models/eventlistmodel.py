# encoding: utf-8
'''
@author:     Jose Emilio Romero Lopez

@copyright:  2013 organization_name. All rights reserved.

@license:    LGPL

@contact:    jemromerol@gmail.com

  This file is part of AMPAPicker.

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Lesser General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from PySide import QtCore
from PySide import QtGui
from gui.models import eventcommands as commands
from picking import record
import datetime


class EventListModel(QtCore.QAbstractTableModel):
    """A Table Model class to handle a list of seismic events.
    """

    emptyList = QtCore.Signal(bool)
    eventCreated = QtCore.Signal(record.Event)
    eventDeleted = QtCore.Signal(record.Event)
    eventModified = QtCore.Signal(record.Event)
    detectionPerformed = QtCore.Signal()

    def __init__(self, record, header):
        QtCore.QAbstractTableModel.__init__(self)
        self.record = record
        self._header = header
        self.empty = (len(self.record.events) != 0)
        self.command_stack = QtGui.QUndoStack(self)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.record.events)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self._header)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        attr_name = self._header[index.column()]
        data = self.record.events[index.row()].__getattribute__(attr_name)
        if attr_name == 'time':
            return str(datetime.timedelta(seconds=data / self.record.fs))
        if attr_name == 'cf_value':
            return "%.3f" % data
        return "%s" % data

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._header[section].replace('_', ' ').title()
        return None

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        self.command_stack.push(commands.SortEventList(self,
                                                       self._header[column],
                                                       order))
        self.layoutChanged.emit()

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            params = {self._header[index.column()]: value}
            self.command_stack.push(commands.EditEvent(self, self.record.events[index.row()],
                                                       **params))
            self.dataChanged.emit(index, index)
            return True
        return False

    def editEvent(self, event, **kwargs):
        row = self.record.events.index(event)
        self.command_stack.push(commands.EditEvent(self, event, **kwargs))
        # notify update of edited arguments
        for arg_name in kwargs.keys():
            for col, col_name in enumerate(self._header):
                if arg_name == col_name:
                    index = self.createIndex(row, col)
                    self.dataChanged.emit(index, index)
                break
        self.layoutChanged.emit()

    def flags(self, index):
        attr_name = self._header[index.column()]
        if attr_name in ['time', 'cf_value', 'mode', 'method']:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        return (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable |
                QtCore.Qt.ItemIsEnabled)

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        if row < 0 or row > len(self.record.events):
            return
        self.beginRemoveRows(parent, row, row + count - 1)
        while count != 0:
            self.command_stack.push(commands.DeleteEvent(self,
                                                         self.record.events[row]))
            count -= 1
        self._setEmpty()
        self.endRemoveRows()

    def addEvent(self, event):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.record.events),
                             len(self.record.events))
        self.command_stack.push(commands.AppendEvent(self, event))
        self._setEmpty()
        self.endInsertRows()

    def detectEvents(self, alg, **kwargs):
        self.modelAboutToBeReset.emit()
        self.command_stack.push(commands.DetectEvents(self, alg, **kwargs))
        self.modelReset.emit()

    def clearEvents(self):
        self.modelAboutToBeReset.emit()
        self.command_stack.push(commands.ClearEventList(self))
        self.modelReset.emit()

    def _setEmpty(self):
        empty = (len(self.record.events) != 0)
        if self.empty != empty:
            self.empty = empty
            self.emptyList.emit(empty)

    def updateList(self):
        self.modelAboutToBeReset.emit()
        self._setEmpty()
        self.modelReset.emit()

