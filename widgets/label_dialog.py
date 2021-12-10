import re

from qtpy import QT_VERSION
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets


import utils


QT5 = QT_VERSION[0] == "5"


# TODO(unknown):
# - Calculate optimal position so as not to go out of screen area.


class LabelQLineEdit(QtWidgets.QLineEdit):
    def setListWidget(self, list_widget):
        self.list_widget = list_widget

    def keyPressEvent(self, e):
        if e.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]:
            self.list_widget.keyPressEvent(e)
        else:
            super(LabelQLineEdit, self).keyPressEvent(e)

class LabelQComboboxEdit(QtWidgets.QComboBox):
    def setListWidget(self, list_widget):
        self.list_widget = list_widget

    def keyPressEvent(self, e):
        if e.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]:
            self.list_widget.keyPressEvent(e)
        else:
            super(LabelQComboboxEdit, self).keyPressEvent(e)

class LabelDialog(QtWidgets.QDialog):
    def __init__(
        self,
        text="位置ID",
        parent=None,
        labels=None,
        sort_labels=True,
        config=None,
        completion="startswith",
        fit_to_content=None,
        flags=None,
        **kwargs,
    ):#调整大小以适合内容

        if fit_to_content is None:
            fit_to_content = {"row": False, "column": True}
        self._fit_to_content = fit_to_content

        super(LabelDialog, self).__init__(parent)
        #QLineEdit单行文字的显示和输入。如账号、密码，等。

        #self.comBoBox = LabelQLineEdit()#
        self.comBoBox = LabelQComboboxEdit()#创建下俩列表框
        self.comBoBox.setEditable(True)#可编辑模式
        self.comBoBox.setPlaceholderText(text)#默认占位符
        self.comBoBox.setValidator(utils.labelValidator())#设置有效编辑
#获得配置文件字典
        labelList = []
        self.label = kwargs["kwargs"]["label"]
        labelList = kwargs["kwargs"]["label"].keys()

        groupId = []
        groupId = kwargs["kwargs"]["group_id"].keys()


        self.comBoBox.addItems(labelList)

        if flags:
            self.comBoBox.textChanged.connect(self.updateFlags)#输入文字过程中响应

        self.comBoBox_group_id = QtWidgets.QComboBox()
        self.comBoBox_group_id.setEditable(True)
        self.comBoBox_group_id.setPlaceholderText("类别ID")
        self.comBoBox_group_id.setValidator(utils.labelValidator())

        self.comBoBox_group_id.addItems(groupId)
        layout = QtWidgets.QVBoxLayout()
      #水平布局方式添加到对话框中
        layout_edit = QtWidgets.QHBoxLayout()
        layout_edit.addWidget(self.comBoBox, 5)
        layout_edit.addWidget(self.comBoBox_group_id, 5)
        layout.addLayout(layout_edit)
        # buttons
        self.buttonBox = bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self,
        )
        bb.button(bb.Ok).setIcon(utils.newIcon("done"))
        bb.button(bb.Cancel).setIcon(utils.newIcon("undo"))
        bb.accepted.connect(self.validate)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)
        # label_list
        self.labelList = QtWidgets.QListWidget()#列表框

        if self._fit_to_content["row"]:#水平滚条
            self.labelList.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOff
            )
            #设置垂直滚动条
        if self._fit_to_content["column"]:
            self.labelList.setVerticalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOff
            )
        self._sort_labels = sort_labels

        if self._sort_labels:
            self.labelList.sortItems()#项目排序
        else:
            self.labelList.setDragDropMode(
                QtWidgets.QAbstractItemView.InternalMove
            )#用于控制视图拖放事件的处理方式
        self.labelList.currentItemChanged.connect(self.labelSelected)#当前项目更改时会发出此信号。当前项目由current指定，这将替换先前的当前项目
        self.labelList.itemDoubleClicked.connect(self.labelDoubleClicked)#双击触发
        self.comBoBox.setListWidget(self.labelList)#赋值给self.listweget

        layout.addWidget(self.labelList)##列表框添加到编辑框中


        # label_flags
        if flags is None:
            flags = {}
        self._flags = flags
        self.flagsLayout = QtWidgets.QVBoxLayout()
        self.resetFlags()
        layout.addItem(self.flagsLayout)
        self.setLayout(layout)#已设置好的布局应用到控件中去.

        # -------------------completion  自动补全-------------------------
        completer = QtWidgets.QCompleter()
        if not QT5 and completion != "startswith":
            completion = "startswith"
        if completion == "startswith":
            completer.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
            # Default settings.
            # completer.setFilterMode(QtCore.Qt.MatchStartsWith)
        elif completion == "contains":
            completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            completer.setFilterMode(QtCore.Qt.MatchContains)
        else:
            raise ValueError("Unsupported completion: {}".format(completion))
        completer.setModel(self.labelList.model())
        self.comBoBox.setCompleter(completer)
#----------------------------------------------------------------------------------
    def addLabelHistory(self, label):

        if self.labelList.findItems(label, QtCore.Qt.MatchExactly):
            return
        self.labelList.addItem(label)
        if self._sort_labels:
            self.labelList.sortItems()

    def labelSelected(self, item):
        self.comBoBox.setCurrentText(item.text())

    def validate(self):
        text = self.comBoBox.currentText()
        if hasattr(text, "strip"):
            text = text.strip()
        else:
            text = text.trimmed()
        if text:
            self.accept()

    def labelDoubleClicked(self, item):
        self.validate()

    def postProcess(self):
        text = self.comBoBox.currentText()
        if hasattr(text, "strip"):
            text = text.strip()
        else:
            text = text.trimmed()#去除了开头和结尾的空白字符串，这里的空白指QChar::isSpace()返回值为true，比如'\t','\n','\v','\f','\r'和' ';
        self.comBoBox.currentText(text)

    def updateFlags(self, label_new):
        # keep state of shared flags 保持共享标志的状态
        flags_old = self.getFlags()

        flags_new = {}
        for pattern, keys in self._flags.items():
            if re.match(pattern, label_new):
                for key in keys:
                    flags_new[key] = flags_old.get(key, False)
        self.setFlags(flags_new)

    def deleteFlags(self):
        for i in reversed(range(self.flagsLayout.count())):
            item = self.flagsLayout.itemAt(i).widget()
            self.flagsLayout.removeWidget(item)
            item.setParent(None)

    def resetFlags(self, label=""):
        flags = {}
        for pattern, keys in self._flags.items():
            if re.match(pattern, label):
                for key in keys:
                    flags[key] = False
        self.setFlags(flags)

    def setFlags(self, flags):
        self.deleteFlags()
        for key in flags:
            item = QtWidgets.QCheckBox(key, self)
            item.setChecked(flags[key])
            self.flagsLayout.addWidget(item)
            item.show()

    def getFlags(self):
        flags = {}
        for i in range(self.flagsLayout.count()):
            item = self.flagsLayout.itemAt(i).widget()
            flags[item.text()] = item.isChecked()
        return flags

    def getGroupId(self):
        group_id = self.comBoBox_group_id.currentText()
        if group_id:
            return group_id
        return None

    def popUp(self, text=None, move=True, flags=None, group_id=None,label_format=False,number = -1):
        if self._fit_to_content["row"]:
            self.labelList.setMinimumHeight(
                self.labelList.sizeHintForRow(0) * self.labelList.count() + 2
            )
        if self._fit_to_content["column"]:
            self.labelList.setMinimumWidth(
                self.labelList.sizeHintForColumn(0) + 2
            )
        # 如果text为None，则self中的前一个标签。编辑保存
        if text is None:
            text = self.comBoBox.currentText()
        if flags:
            self.setFlags(flags)
        else:
            self.resetFlags(text)
        self.comBoBox.setCurrentText(text)
        #self.comBoBox.setSelection(0, len(text))
        if group_id is None:
            #self.comBoBox_group_id.clear()
            pass
        else:
            self.comBoBox_group_id.setCurrentText(str(group_id))
        items = self.labelList.findItems(text, QtCore.Qt.MatchFixedString)
        if items:
            if len(items) != 1:
                print("Label list has duplicate '{}'".format(text))
            self.labelList.setCurrentItem(items[0])
            row = self.labelList.row(items[0])
            self.comBoBox.completer().setCurrentRow(row)
        self.comBoBox.setFocus(4)#QtCore.Qt.PopupFocusReason

        if move:
            self.move(QtGui.QCursor.pos())
        #culane 格式不用跳出对话框
        #label=["left1","left2","right1","right2"]
        if label_format:
            return str(number),None,None
        else:
            if self.exec_():
                return self.comBoBox.currentText(), self.getFlags(), self.getGroupId()
            else:
                return None, None, None

