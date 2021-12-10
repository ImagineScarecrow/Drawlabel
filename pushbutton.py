import os
import os.path as osp
import math
import imgviz
from PIL import Image
import io
import shutil
import functools
from PyQt5 import QtCore
# from qtpy.QtCore import Qt
# from PyQt5.QtGui import QPixmap
# from PyQt5.QtWidgets import QFileDialog
from PyQt5 import QtWidgets,QtGui
from qtpy.QtCore import Qt
from shape import Shape
from widgets import Canvas
from widgets import LabelDialog
from utils import qt
from utils import image
from label_file import LabelFile,LabelFileError,LabelFileFormat
from widgets import ZoomWidget
from widgets import LabelListWidget
from widgets import LabelListWidgetItem
from widgets import UniqueLabelQListWidget
from widgets import ToolBar


LABEL_COLORMAP = imgviz.label_colormap()

FORMAT_JSON = "JSON"
FORMAT_CULANE= "CULANE"

class PushButton(QtWidgets.QMainWindow):
    print("hellow")
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2
    def __init__(self,config=None):
        # if config is None:
        #     config =get_config()
        self._config = config
        self.label_file_format = LabelFileFormat.JSON
        super().__init__()
        output_dir = None
        self.output_dir = output_dir
        self.__version__="DrawLabel_v0.6"
        self.setWindowTitle(self.__version__)
        # 线段颜色默认值设
        self.linecolor=[0,255,0,128]
        self.fillcolor=[0,255,0,0]
        self.selec_line=[255,255,255,255]
        self.select_fill=[0,255,0,255]
        self.file_line=[0,255,0,255]
        self.vertex_fill = [0, 255, 0, 255]
        self.hvertex_fill=[255,255,255,255]
        point_size = 8
        #置线段颜色
        Shape.line_color = QtGui.QColor(*self.linecolor)
        Shape.fill_color = QtGui.QColor(*self.fillcolor)
        Shape.select_line_color = QtGui.QColor(*self.selec_line)
        Shape.select_fill_color = QtGui.QColor(*self.select_fill)
        Shape.vertex_fill_color = QtGui.QColor(*self.vertex_fill)
        Shape.hvertex_fill_color = QtGui.QColor(*self.hvertex_fill)
        #点的尺寸
        Shape.point_size = point_size
#-----------------------------------------------------------------------------------
        self.dirty = False#标注内容改变标志

        self._noSelectionSlot = False

        self._copied_shapes = None
        self.discard = True
        self.deleFile = None#存储被删除的路径名
        self.originfile=None
        self.deleteFlag = False
        self.currentFile = None
        self.number = 0
        self.backupImgFIle = []#保存被删掉的文件路径
        self.backupJsonFIle = []
        self.backupTxtFile = []
        self.saveRevocationFile = None#存储撤销的文件
# --------------创建右边的两个窗口 label fileList 双击打开车道线类型设置窗口---------------------
        # 标完线双击后出现的标签设置窗口
        self.labelDialog = LabelDialog(parent=self,kwargs=self._config)


#LabelList
        self.labelList = LabelListWidget()
        self.lastOpenDir = None

        self.labelList.itemDoubleClicked.connect(self.editLabel)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemChanged.connect(self.labelItemChanged)
        self.labelList.itemDropped.connect(self.labelOrderChanged)

        self.uniqLabelList = UniqueLabelQListWidget()

        self.label_dock = QtWidgets.QDockWidget("标签列表", self)
        self.label_dock.setObjectName(u"Label List")
        self.label_dock.setWidget(self.labelList)

#fiList
        #fileList 中的file search
        self.fileSearch = QtWidgets.QLineEdit()
        self.fileSearch.setPlaceholderText("搜索文件")
        self.fileSearch.textChanged.connect(self.fileSearchChanged)#文本改变触发

        self.button = QtWidgets.QPushButton("跳转")
        self.button.clicked.connect(self.buttonClick)
        self.button.setToolTip("跳到最近标注的文件")
        self.fileEdit = QtWidgets.QLineEdit()
        self.fileEdit.setPlaceholderText("当前位置")
        #self.fileEdit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(r"\d*")))#"[0-9]+$"

        self.fileEdit.editingFinished.connect(self.skipfile)
        self.fileListWidget = QtWidgets.QListWidget()#一个基于条目的接口，用于从列表中添加或删除条目
        self.fileListWidget.itemSelectionChanged.connect(
            self.fileSelectionChanged
        )#鼠标点击item时触发，同时画面会到相应图片上
        # 显示进度

        self.Nimage = 0#计数已标注的文件
        self.saveComFile=[]#保存已标注的文件路径

        vlayout = QtWidgets.QHBoxLayout()
        vlayout.addWidget(self.fileSearch,4)

        vlayout.addWidget(self.fileEdit,5)
        vlayout.addWidget(self.button,1)
        fileListLayout = QtWidgets.QVBoxLayout()
        fileListLayout.setContentsMargins(0, 0, 0, 0)#四个参数分别为：左、上、右、下的边距。设置布局的边距
        fileListLayout.setSpacing(0)#表示各个控件之间的上下间距
        fileListLayout.addItem(vlayout)
        fileListLayout.addWidget(self.fileListWidget)
        self.file_dock = QtWidgets.QDockWidget("文件列表", self)
        self.file_dock.setObjectName(u"Files")
        fileListWidget = QtWidgets.QWidget()
        fileListWidget.setLayout(fileListLayout)
        self.file_dock.setWidget(fileListWidget)

        self.combobox = QtWidgets.QComboBox()
        self.combobox.setToolTip("标注工具")
        # ---这一段是实现图片缩放的代码，在action中设置了相应的触发事件 zoom开头的函数都是---------------------
        self.zoomWidget = ZoomWidget()
        self.setAcceptDrops(True)#告诉系统该窗口可受拖放事件
#= self.labelList.canvas
        self.canvas = Canvas(
            epsilon=10,
            double_click="close",
            num_backups=10,
        )
        self.canvas.zoomRequest.connect(self.zoomRequest)#缩放后需要canvas重新加载图片
        self.canvas.last_point.connect(self.removeSelectedPoint)
        scrollArea = QtWidgets.QScrollArea()#创建滚动显示区域
        scrollArea.setWidget(self.canvas)#将设置好的幕布嵌入到滚动显示区域
        scrollArea.setWidgetResizable(True)#让滚动区域中的内容的左右随着窗口自适应，上下内容超出屏幕，出现滚动。
        #垂直与水平)滚动条样式
        self.scrollBars = {
            Qt.Vertical: scrollArea.verticalScrollBar(),
            Qt.Horizontal: scrollArea.horizontalScrollBar(),
        }

        self.canvas.scrollRequest.connect(self.scrollRequest)

        self.canvas.newShape.connect(self.newShape)

        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)#列表框选择其他item
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)#画图的时候发送信号，禁止其他模式触发
        self.setCentralWidget(scrollArea)

        self.addDockWidget(Qt.RightDockWidgetArea, self.label_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_dock)


# ---这边是创建按键和对应触发事件的代码左边和上边的菜单栏按键全部在这里实现-------------------------------------
        action = functools.partial(qt.newAction, self)
        opendir = action(
            "打开文件夹",
            self.openDirDialog,
            None,
            "open",
            "打开文件夹",
        )
        open = action(
            "打开文件",
            self.openFile,
            None,
            "open",
            "打开文件",
        )
        openNextImg=action(
            "下一张",
            self.openNextImg,
            "D",
            "下一张",
            enabled=False,
        )
        openPrevImg = action(
            "上一张",
            self.openPrevImg,
            "A",
            "上一张",
            enabled=False,
        )
        save = action(
            "保存",
            self.saveFile,
            "Ctrl+s",
            "save",
            "Ctrl+s 保存",
            enabled=False,
        )
        saveAuto = action(
            text="自动保存",
            slot=lambda x: self.actions.saveAuto.setChecked(x),
            icon="None",
            checkable=True,
            enabled=True,
        )
        saveAuto.setChecked(False)
        changeOutputDir = action(
            "更改保存路径",
            slot=self.changeOutputDirDialog,
            icon=None,
        )
        #用lambda的好处是可以任意的往槽函数里面传递参数
        createLineStripMode = action(
            "创建折线",
            lambda: self.toggleDrawMode(False, createMode="linestrip"),
            "R",
            tip="R 创建折线",
            enabled=True,
        )
        createRectangleMode = action(
            text="创建矩形",
            slot = lambda:self.toggleDrawMode(False,createMode="rectangle"),
            shortcut="W",
            icon = None,
            tip = "W 画矩形",
        )
        editMode = action(
            "退出标注",
            self.setEditMode,
            shortcut="F",
            icon=None,
            tip="F 退出标注",
            enabled=True,
        )
        edit = action(
            text = "编辑标签",
            slot = self.editLabel,
            shortcut=None,
            icon = None,
            tip = "修改选定多边形的标签",
            enabled=False,
        )
        delete = action(
            text = "删除标签",
            slot = self.deleteSelectedShape,
            shortcut=("delete","Q"),
            icon=None,
            tip="delete/Q 删除标签",
            enabled=False,
        )
        deleteImage = action(
            text = "删除图片",
            slot = self.deleteImgFile,
            shortcut = "S",
            icon = "dddd",
            tip = "删除图片 S",
            enabled = False,
        )
        revocationFile = action(
            text = "撤销删除图片",
            slot = self.revocationDelete,
            shortcut = "G",
            icon = " ",
            tip = "撤回刚才删除的图片和标签文件 G",
            enabled=False,
        )
        fitWindow = action(
            text = "适应窗口",
            slot = self.setFitWindow,
            shortcut = None,
            icon = None,
            tip = "图像调整为适应窗口大小",
            checkable=True,
            enabled=False,
        )
        undoLastPoint = action(
            text = "撤销最后的控制点",
            slot = self.canvas.undoLastPoint,
            shortcut="Ctrl+Z",
            icon = " ",
            tip = "在标注时可撤销上一次标注的点 Ctrl+Z",
            enabled=False,
        )

        undo = action(
            text = "撤销删除点和线",
            slot = self.undoShapeEdit,
            shortcut = "ctrl+z",
            icon = " ",
            tip = "撤回刚才删除的标签 撤回线ctrl+zz 撤回点ctrl+z",
            enabled=False,
        )

        save_format = action(
            text = "JSON",
            slot = self.change_format,
            shortcut = None,
            icon = None,
            tip = "改变标签保存格式",
            enabled = False,
        )
        HelpMessage1 = action(
            text = "help",
            slot = self.HelpFunction,
            shortcut = None,
            icon = None,
            tip = "help",
            enabled = True,
        )
        # removePoint = action(
        #     text="删除点",
        #     slot=self.removeSelectedPoint,
        #     shortcut=("x","backspace"),
        #     icon=None,
        #     tip="删除选中的坐标点",
        #     enabled=False,
        # )

        #创建列表框Item
        Item = ["创建矩形","创建折线","退出标注","删除"]
        self.combobox.addItems(Item)
        self.combobox.setToolTip("标注工具")
        deleteIndex = self.combobox.model().index(3, 0)
        self.combobox.model().setData(deleteIndex, 0, Qt.UserRole - 1)

        #activated 再选中时激活
        #当用户选中一个下拉选项时发射该信号
        self.combobox.activated.connect(self.ComBoxSelectionChange)
        #将下来框添加到actions中
        combobox = QtWidgets.QWidgetAction(self)
        combobox.setDefaultWidget(self.combobox)


        zoom = QtWidgets.QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            self.tr(
                "Zoom in or out of the image. Also accessible with "
                "{} and {} from the canvas."
            ).format(
                qt.fmtShortcut(
                    "{},{}".format("Ctrl++", "Ctrl--")
                ),
                qt.fmtShortcut(self.tr("Ctrl+Wheel")),
            )
        )
        self.zoomWidget.setEnabled(False)
        self.zoomMode = self.FIT_WINDOW
        #fitWindow.setChecked(Qt.Checked)
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            #加载文件时，设置为1，比例为100%。
            self.MANUAL_ZOOM: lambda: 1,
        }

        # 存储操作以供进一步处理
        self.actions = qt.struct(
            open = open,
            opendir=opendir,
            openPrevImg=openPrevImg,
            openNextImg=openNextImg,
            save=save,
            saveAuto=saveAuto,
            changeOutputDir=changeOutputDir,
            createLineStripMode=createLineStripMode,
            createRectangleMode=createRectangleMode,
            editMode=editMode,
            edit=edit,
            delete=delete,
            fitWindow=fitWindow,
            tool=(),
            combobox= combobox,
            deleteImage = deleteImage,
            revocationFile=revocationFile,
            undoLastPoint=undoLastPoint,
            save_format = save_format,
            #HelpMessage = HelpMessage,
            HelpMessage1=HelpMessage1,
            #removePoint = removePoint,
            undo = undo,
            menu=(
                createLineStripMode,
                createRectangleMode,
                editMode,
                  ),
        )
        #self.canvas.vertexSelected.connect(self.actions.removePoint.setEnabled) #点删除功能
        self.tools = self.toolbar("Tools")

        self.menus =qt.struct(
            file = self.menu("文件"),
            edit=self.menu('编辑'),
            view=self.menu('视图'),
            help = self.menu('Help')
        )
        qt.addActions(
            self.menus.help,
            (HelpMessage1,),
        )
        qt.addActions(
            self.menus.file,
            (
                open,
                opendir,
                openNextImg,
                openPrevImg,
                save,
                saveAuto,
                changeOutputDir,
                editMode,
                undo,
            ),
        )
        qt.addActions(
            self.menus.view,
            (
                self.label_dock.toggleViewAction(),
                self.file_dock.toggleViewAction(),
            ),
        )
        self.actions.tool = (
            open,
            opendir,
            openPrevImg,
            openNextImg,
            save,
            fitWindow,
            deleteImage,
            revocationFile,
            undo,
            #removePoint,
            #undo,
            undoLastPoint,
            save_format,
            combobox,
        )

        #它可以用来设置并动态改变设备的状态栏显示特性。
        self.statusBar().showMessage("%s started." % 'label')
        self.statusBar().show()
        # Application state.应用程序状态。
        self.image = QtGui.QImage()#QImage类主要用于I/O和直接逐像素访问、操作
        self.imagePath = None
        self.recentFiles = []
        self.maxRecent = 7
        self.otherData = None
        self.zoom_level = 100
        self.fit_window = False
        self.zoom_values = {}  # key=filename, value=(zoom_mode, zoom_value)
        self.scroll_values = {
            Qt.Horizontal: {},
            Qt.Vertical: {},
        }  # key=filename, value=scroll_value
        filename=None
        if filename is not None and osp.isdir(filename):
            self.importDirImages(filename, load=False)
        else:
            self.filename = filename

        #恢复应用程序设置。
        self.settings = QtCore.QSettings("labelme", "labelme")#Qsettings 就是提供了一种方便的方法来存储和恢复应用程序的
        #FIXME: QSettings.value can return None on PyQt4

        size = self.settings.value("window/size", QtCore.QSize(1000, 800))#600,500使用整数点精度定义二维对象的大小
        position = self.settings.value("window/position", QtCore.QPoint(0, 0))
        self.resize(size)
        self.move(position)
        self.restoreState(
            self.settings.value("window/state", QtCore.QByteArray())
        )
        #由于加载文件可能需要一些时间，请确保它在后台运行。
        if self.filename is not None:
            self.queueEvent(functools.partial(self.loadFile, self.filename))

        # Callbacks:更新图像大小
        self.zoomWidget.valueChanged.connect(self.paintCanvas)
        # 将设置好的按键/控件添加到tool/menu中
        self.populateModeActions()
        self.canvas.rightClick.connect(lambda:self.toggleDrawMode(True))
        self.canvas.deleteLabel.connect(self.deleteSelectedShape)
#--------------------------------这一部分是各种函数的实现-----------------------------------
    def HelpFunction(self):
        self.labelDialog = LabelDialog(parent=self,kwargs=self._config)
        self.HelpMessage = QtWidgets.QMessageBox.about(self,'快捷键说明',
                                 " 1、 上一页：A\n"
                                 " 2、 下一页：D\n"
                                 " 3、 矩形框：W\n"
                                 " 4、 折线：  R\n"
                                 " 5、 退出标注：F\n"
                                 " 6、 保存：Ctrl+S\n"
                                 " 7、 撤销删除图片:G\n"
                                 " 8、 删除标签：Q/Delete\n"
                                 " 9、 删除未保存的标签：esc\n"
                                 "10、删除点：shift+鼠标左键\n"
                                 "11、图片缩放：Ctrl+鼠标滚轴\n"                
                                 "12、撤销最近标注的点：Ctrl+Z\n"
                                 "13、撤销删除点和线：Ctrl+z+z\n")
        # self.HelpMessage.setText(
        #                          )



    def undoShapeEdit(self):
        self.number -= 1
        self.canvas.restoreShape()
        self.labelList.clear()
        self.loadShapes(self.canvas.shapes)
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)
        self.setDirty()

    def removeSelectedPoint(self):
        # self.canvas.removeSelectedPoint()
        # self.canvas.update()
        if not self.canvas.hShape.points:
            self.canvas.deleteShape(self.canvas.hShape)
            self.remLabels([self.canvas.hShape])
            self.setDirty()
            if self.noShapes():
                self.dirty = False
        #self.setDirty()

    def revocationDelete(self):
        home_path= os.getcwd()#获得当前目录绝对路径
        if self.lastOpenDir:
            dirs = osp.split(self.lastOpenDir)[-1]
            recycle_bin_name = dirs + "_" + "recycle_bin"#回收箱文件夹名
            recycle_bin = osp.join(home_path,recycle_bin_name)#回收箱路径

            if self.backupImgFIle:
                self.saveRevocationFile = self.backupImgFIle.pop()
                without_path_img_file = osp.basename(self.saveRevocationFile)#文件名
                oldFilePath = osp.dirname(self.saveRevocationFile)
                if osp.exists(recycle_bin):
                    img_file = osp.join(recycle_bin,without_path_img_file)#文件绝对路径
                    label_file = osp.splitext(img_file)[0]+ self._config["fileType"]["__TXT_SUFFIX__"]

                    if osp.exists(img_file):

                        shutil.move(img_file, oldFilePath)

                    if osp.exists(label_file):
                        shutil.move(label_file,oldFilePath)

                    self.importDirImages(oldFilePath,revocationFlag=True)
                    #print("img number{}".format(len(self.backupImgFIle)))
                    if len(self.backupImgFIle) ==0:
                        self.actions.revocationFile.setEnabled(False)
                else:
                    self.errorMessage("文件路径错误","请检查回收文件{}是否与可执行文件处于同一路径下".format(recycle_bin_name))

    def deleteImgFile(self):
        self.actions.revocationFile.setEnabled(True)
        self.actions.undo.setEnabled(False)

        if self.deleFile :
            #self.saveRevocationFile = self.deleFile
            # self.discard=False#不触发保存弹窗

            if self.imageList:
                #将图片和标签文件移到回收站
                #移除图片文件
                self.dirty = False
                # 处理回收站路径
                dirs = osp.split(self.lastOpenDir)[-1]
                recycle_bin = dirs + "_" + "recycle_bin"
                current_work_dir = os.getcwd()
                recycle_bin = osp.join(current_work_dir, recycle_bin)
                if not osp.exists(recycle_bin):
                    os.mkdir(recycle_bin)

                if not osp.exists(osp.join(recycle_bin,osp.basename(self.deleFile))):
                    shutil.move(self.deleFile, recycle_bin)
                    self.backupImgFIle.append(self.deleFile)#存储被移除的图片路径
                elif self.deleFile:
                    os.remove(self.deleFile)
                #移除标签文件
                json_label = osp.splitext(self.deleFile)[0] + ".json"
                line_txt_label = osp.splitext(self.deleFile)[0] +  self._config["fileType"]["__TXT_SUFFIX__"]
                if osp.exists(json_label):
                    shutil.move(json_label, recycle_bin)
                    self.backupJsonFIle.append(json_label)
                if osp.exists(line_txt_label):
                    shutil.move(line_txt_label, recycle_bin)
                    self.backupTxtFile.append(line_txt_label)

                row = self.fileListWidget.currentRow()
                self.fileListWidget.takeItem(row)

                curNumber = self.imageList.index((self.deleFile)) + 1
                image_num = len(self.imageList)
                self.fileEdit.setText("{}/{}  {}".format(curNumber, image_num, osp.basename(self.deleFile)))

        else:
            self.errorMessage("警告"," 请先加载图片")

    def change_format(self):
        #改变标注模式
        if not self.mayContinue():
            return
        if self.label_file_format == LabelFileFormat.JSON:
            self.canvas.createMode = "linestrip"
            self.set_format(FORMAT_CULANE)
        elif self.label_file_format == LabelFileFormat.CULANE:
            self.set_format(FORMAT_JSON)
        else:
            raise ValueError('Unknown label file format.')
        self.loadFile(self.currentFile,changeFlage=True,openNextFlag=True)

    def set_format(self, save_format):
        #设置标注模式
        if save_format == FORMAT_JSON:
            self.actions.save_format.setText("JSON")
            #self.actions.save_format.setIcon(qt.newAction("format_voc"))
            self.label_file_format = LabelFileFormat.JSON
            LabelFile.suffix = ".json"

        elif save_format == FORMAT_CULANE:
            self.actions.save_format.setText("CULANE")
            #self.actions.save_format.setIcon(qt.newAction(""))
            self.label_file_format = LabelFileFormat.CULANE
            LabelFile.suffix =  self._config["fileType"]["__TXT_SUFFIX__"]



    def ComBoxSelectionChange(self,i):
        #标注工具下拉框
        if self.combobox.currentText() =="创建矩形":
            self.toggleDrawMode(False, createMode="rectangle")
        elif self.combobox.currentText() =="创建折线":
            self.toggleDrawMode(False, createMode="linestrip")
        elif self.combobox.currentText() =="退出标注":
            self.setEditMode()
        else:
            self.deleteSelectedShape()

    def editLabel(self, item=None):

        if item and not isinstance(item, LabelListWidgetItem):
            raise TypeError("item必须是LabelListWidgetItem类型")
        if not self.canvas.editing():
            return
        if not item:
            item = self.currentItem()
        if item is None:
            return
        shape = item.shape()
        if shape is None:
            return
        text, flags, group_id = self.labelDialog.popUp(
            text=shape.label,
            flags=shape.flags,
            group_id=shape.group_id,
        )
        if text is None:
            return
        if not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._config["validate_label"]
                ),
            )
            return
        shape.label = text
        shape.flags = flags
        shape.group_id = group_id

        self._update_shape_color(shape)
        if shape.group_id is None:
            item.setText(
                '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                    shape.label, *shape.fill_color.getRgb()[:3]
                )
            )
        else:
            item.setText("{} ({})".format(shape.label, shape.group_id))
        self.setDirty()
        if not self.uniqLabelList.findItemsByLabel(shape.label):
            item = QtWidgets.QListWidgetItem()
            item.setData(Qt.UserRole, shape.label)
            self.uniqLabelList.addItem(item)

    def setFitWindow(self, value=True):
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def deleteSelectedShape(self):
        # yes, no = QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        # msg = self.tr(
        #     "即将永久删除标签 {}确定继续吗？"
        # ).format(len(self.canvas.selectedShapes))
        # if yes == QtWidgets.QMessageBox.warning(
        #     self, self.tr("Attention"), msg, yes | no, yes
        # ):

        self.number -= 1#删除后标签的需要要减一 不然会一直加上去
        self.remLabels(self.canvas.deleteSelected())
        self.setDirty()
        self.actions.delete.setEnabled(False)
        deleteIndex = self.combobox.model().index(3, 0)
        self.combobox.model().setData(deleteIndex, 0, Qt.UserRole - 1)
        self.deleteFlag = False
        deleteIndex = self.combobox.model().index(3, 0)
        self.combobox.model().setData(deleteIndex, 0, Qt.UserRole - 1)

        # print(self.labelList.model().rowCount())
        if self.labelList.model().rowCount() == 0:
            self.dirty = False  # 没有标签 就不需要跳出保存标签提示

            deleteFile = osp.splitext(self.deleFile)[0] + ".json"
            if self.label_file_format == LabelFileFormat.CULANE:
                deleteFile = osp.splitext(self.deleFile)[0] +  self._config["fileType"]["__TXT_SUFFIX__"]

            if osp.exists(deleteFile):
                os.remove(deleteFile)

                deleteFile = osp.basename(deleteFile).split('.')[0]
                self.saveComFile.remove(deleteFile)
                self.saveComFile.sort()

                item = self.fileListWidget.currentItem()

                item.setCheckState(Qt.Unchecked)
                self.Nimage -= 1
                if self.saveComFile:
                    # endFIle = osp.split(self.saveComFile[-1])[1].replace(".json",osp.splitext(self.originfile)[1])
                    endFIle = self.saveComFile[-1] + osp.splitext(self.originfile)[1]
                else:
                    endFIle = " "

    def noShapes(self):
        return not len(self.labelList)

    def remLabels(self, shapes):
        for shape in shapes:
            item = self.labelList.findItemByShape(shape)
            self.labelList.removeItem(item)

    def setEditMode(self):
        self.toggleDrawMode(True)

#开始标注
    def toggleDrawMode(self, edit=True, createMode="linestrip"):
        self.canvas.setEditing(edit)#
        self.canvas.createMode = createMode#字符串赋值给这个变量同时还会检查是否符合要求
        if edit:
            self.actions.createLineStripMode.setEnabled(True)
            self.actions.createRectangleMode.setEnabled(True)

            #开启矩形标注
            LineStripindex = self.combobox.model().index(0, 0)
            self.combobox.model().setData(LineStripindex, -1, Qt.UserRole - 1)
            #开启折线标注
            RecTangleindex = self.combobox.model().index(1, 0)
            self.combobox.model().setData(RecTangleindex, -1, Qt.UserRole - 1)
            # 清除缓存
            self.canvas.current = None
            self.canvas.drawingPolygon.emit(False)
            self.canvas.repaint()
        else:
            if createMode == "linestrip":
                # 清除缓存
                self.canvas.current = None
                self.canvas.drawingPolygon.emit(False)

                self.actions.createLineStripMode.setEnabled(False)#被选中了就不能再点击了
                self.actions.createRectangleMode.setEnabled(True)

                #关掉折线标注框
                index = self.combobox.model().index(1, 0)
                self.combobox.model().setData(index, 0, Qt.UserRole - 1)
                #开启矩形标注
                LineStripindex = self.combobox.model().index(0, 0)
                self.combobox.model().setData(LineStripindex, -1, Qt.UserRole - 1)

                self.canvas.repaint()
            elif createMode == "rectangle":
                if self.label_file_format==LabelFileFormat.CULANE:
                    self.errorMessage("警告","culane 格式只支持折线标注")
                    self.canvas.setEditing(True)
                    # 清除缓存
                    self.canvas.current = None
                    self.canvas.drawingPolygon.emit(False)
                    # 开启折线标注
                    RecTangleindex = self.combobox.model().index(1, 0)
                    self.combobox.model().setData(RecTangleindex, -1, Qt.UserRole - 1)
                    self.actions.createLineStripMode.setEnabled(True)
                else:
                    # 清除缓存
                    self.canvas.current = None
                    self.canvas.drawingPolygon.emit(False)

                    self.actions.createRectangleMode.setEnabled(False)
                    self.actions.createLineStripMode.setEnabled(True)
                    # 关掉矩形标注框
                    index = self.combobox.model().index(0, 0)
                    self.combobox.model().setData(index, 0, Qt.UserRole - 1)
                    # 开启折线标注
                    RecTangleindex = self.combobox.model().index(1, 0)
                    self.combobox.model().setData(RecTangleindex, -1, Qt.UserRole - 1)

                    self.canvas.repaint()
            else:
                raise ValueError("不支持createMode: %s" % createMode)

        self.actions.editMode.setEnabled(not edit)#变成可编辑模式

    def changeOutputDirDialog(self, _value=False):
        default_output_dir = self.output_dir
        if default_output_dir is None and self.filename:
            default_output_dir = osp.dirname(self.filename)
        if default_output_dir is None:
            default_output_dir = self.currentPath()

        output_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "%s - 选择标签保存路径" % 'mylabel',
            default_output_dir,
            QtWidgets.QFileDialog.ShowDirsOnly
            | QtWidgets.QFileDialog.DontResolveSymlinks,
        )
        output_dir = str(output_dir)

        if not output_dir:
            return

        self.output_dir = output_dir

        self.statusBar().showMessage(
            "%s . 注释将被保存/载入 %s"
            % ("更改标签路径", self.output_dir)
        )
        self.statusBar().show()

        current_filename = self.filename
        self.Nimage=0#将json文件数目清0
        self.saveComFile.clear()
        self.importDirImages(self.lastOpenDir, load=False)

        if current_filename in self.imageList:
            # 保留当前选定的文件
            self.fileListWidget.setCurrentRow(
                self.imageList.index(current_filename)
            )
            self.fileListWidget.repaint()

    def saveFile(self, _value=False):
        assert not self.image.isNull(), "无法保存空的图片"
        self._saveFile(self.saveFileDialog())

#弹出选择路径对话框
    def saveFileDialog(self):
        if self.label_file_format == LabelFileFormat.CULANE:
            suffix = self._config["fileType"]["__TXT_SUFFIX__"]
        else:
            suffix = ".json"

        caption = "label-选择文件夹"
        filters = "Label files (*%s)" % suffix
        if self.output_dir:
            dlg = QtWidgets.QFileDialog(
                self, caption, self.output_dir, filters
            )
        else:
            dlg = QtWidgets.QFileDialog(
                self, caption, self.currentPath(), filters
            )
        dlg.setDefaultSuffix(suffix[1:])
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)#设置接受模式
        dlg.setOption(QtWidgets.QFileDialog.DontConfirmOverwrite, False)
        dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, False)
        basename = osp.basename(osp.splitext(self.filename)[0])
        if self.output_dir:
            default_labelfile_name = osp.join(
                self.output_dir, basename + suffix
            )
        else:
            default_labelfile_name = osp.join(
                self.currentPath(), basename + suffix
            )
        filename = dlg.getSaveFileName(
            self,
            "选择文件",
            default_labelfile_name,
            "Label files (*%s)" % suffix,
        )
        if isinstance(filename, tuple):
            filename, _ = filename
        return filename

    def currentPath(self):
        return osp.dirname(str(self.filename)) if self.filename else "."

    def _saveFile(self, filename):
        if filename and self.saveLabels(filename):
            self.setClean()


    def saveLabels(self, filename):
        lf = LabelFile(txt_suffix=self._config["fileType"]["__TXT_SUFFIX__"])

        def format_shape(s):
            if s.label in self._config["label"]:
                s.label = self._config["label"][s.label]
            if s.group_id in self._config["group_id"]:
                s.group_id = self._config["group_id"][s.group_id]
            data = s.other_data.copy()
            data.update(
                dict(
                    label=s.label,#s.label,#
                    points=[(p.x(), p.y()) for p in s.points],
                    group_id=s.group_id,
                    shape_type=s.shape_type,
                    flags=s.flags,
                )
            )
            return data
        shapes = [format_shape(item.shape()) for item in self.labelList]

        try:
            imagePath = osp.relpath(self.imagePath, osp.dirname(filename))
            imageData = None
            if osp.dirname(filename) and not osp.exists(osp.dirname(filename)):
                os.makedirs(osp.dirname(filename))
            lf.save(
                filename=filename,
                shapes=shapes,
                imagePath=imagePath,
                imageData=imageData,
                imageHeight=self.image.height(),
                imageWidth=self.image.width(),
                otherData=self.otherData,
                label_file_format = self.label_file_format,
            )

            self.labelFile = lf
            items = self.fileListWidget.findItems(
                self.imagePath, Qt.MatchExactly
            )
            if len(items) > 0:
                if len(items) != 1:
                    raise RuntimeError("There are duplicate files.")
                items[0].setCheckState(Qt.Checked)
                if self.output_dir:
                    path = osp.split(self.imagePath)[-1]
                    path = osp.splitext(path)[0]+'.json'
                    imagePath_json = osp.join(self.output_dir,path)
                else:
                    imagePath_json = osp.splitext(self.imagePath)[0] + ".json"

                imagePath_json = osp.basename(imagePath_json).strip(".json")
                if imagePath_json not in self.saveComFile:
                    #print("image",imagePath_json)
                    self.saveComFile.append(imagePath_json)
                    self.saveComFile.sort()
                    self.Nimage += 1
                    currnetFile = osp.split(self.imagePath)

            # 禁用允许下一个和上一个图像继续
            # self.filename = filename
            return True
        except LabelFileError as e:
            self.errorMessage(
                self.tr("Error saving label data"), self.tr("<b>%s</b>") % e
            )
            return False

    def openPrevImg(self, _value=False):
        if not self.mayContinue():
            return
        #清除缓存
        self.canvas.current = None
        self.canvas.drawingPolygon.emit(False)
        self.canvas.update()

        if len(self.imageList) <= 0:
            return

        if self.filename is None:
            return

        currIndex = self.imageList.index(self.filename)
        if currIndex - 1 >= 0:
            filename = self.imageList[currIndex - 1]
            if filename:
                self.loadFile(filename)

#弹出是否保存消息框
    def mayContinue(self):
        if not self.dirty:
            return True
        mb = QtWidgets.QMessageBox
        msg = self.tr('未保存，是否保存到 "{}" ?').format(
            self.filename
        )
        answer = mb.question(
            self,
            "是否保存？",
            msg,
            mb.Save | mb.Discard | mb.Cancel,
            mb.Save,
        )
        if answer == mb.Discard:
            self.actions.delete.setEnabled(False)
            self.deleteFlag = False
            deleteIndex = self.combobox.model().index(3,0)
            self.combobox.model().setData(deleteIndex,0,Qt.UserRole - 1)

            self.discard = False
            return True
        elif answer == mb.Save:
            self.saveFile()
            return True
        else:  # answer == mb.Cancel
            self.actions.delete.setEnabled(False)
            self.deleteFlag = False
            deleteIndex = self.combobox.model().index(3,0)
            self.combobox.model().setData(deleteIndex,0,Qt.UserRole - 1)
            return False

    def openFile(self, _value=False):
        self.actions.openNextImg.setEnabled(False)
        self.actions.openPrevImg.setEnabled(False)
        self.actions.deleteImage.setEnabled(False)
        #self.actions.deleteImage.setEnabled(False)

        if not self.mayContinue():
            return
        path = osp.dirname(str(self.filename)) if self.filename else "."
        formats = [
            "*.{}".format(fmt.data().decode())
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        if self.label_file_format == FORMAT_CULANE:
            LabelFile.suffix= self._config["fileType"]["__TXT_SUFFIX__"]
        else:
            LabelFile.suffix = ".json"
        filters = "Image & Label files (%s)" % " ".join(
            formats + ["*%s" % LabelFile.suffix]
        )
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "%s - 选择图片或标签文件" % "label",
            path,
            filters,
        )
        filename, _ = filename
        filename = str(filename)
        self.lastOpenDir = filename
        if filename:
            self.loadFile(filename,openNextFlag=True)
        # self.statusBar().showMessage(
        #     self.tr("%s . Annotations will be saved/loaded in %s")
        #     % ("Change Annotations Dir", self.output_dir)
        # )
        # self.statusBar().show()
        #
        # current_filename = self.filename
        # self.importDirImages(self.lastOpenDir, load=False)
        #
        # if current_filename in self.imageList:
        #     self.fileListWidget.setCurrentRow(
        #      opp   self.imageList.index(current_filename)
        #     )
        #     self.fileListWidget.repaint()

    def scaleFitWidth(self):
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def scaleFitWindow(self):
        """计算出像素图大小以适合主部件。."""
        e = 2.0  #这样就不会生成滚动条。
        w1 = self.centralWidget().width() - e#中央控件的宽-2这样就不满足滚动条的生成条件了
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # 根据像素图的宽高比计算一个新的比例值。
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def queueEvent(self, function):
        QtCore.QTimer.singleShot(0, function)

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            qt.addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName("%sToolBar" % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            qt.addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar

    def populateModeActions(self):
        tool,menu = self.actions.tool,self.actions.menu
        self.tools.clear()
        self.menus.edit.clear()
        actions = (
            #self.actions.createMode,
            self.actions.createLineStripMode,
            self.actions.createRectangleMode,
            self.actions.editMode,
            self.actions.delete,
            #self.actions.removePoint,
        )
        qt.addActions(self.tools, tool)#左边工具栏
        qt.addActions(self.menus.edit,actions)

    #更新图像大小的时候被调用，比例设置为原来的60%
    def paintCanvas(self):
        assert not self.image.isNull(), "无法绘制 没有图像"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def resizeEvent(self, event):
        if (
            self.canvas
            and not self.image.isNull()
            and self.zoomMode != self.MANUAL_ZOOM
        ):
            self.adjustScale()
        super(PushButton, self).resizeEvent(event)

#将原来放大的图像调整为合适比例
    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        value = int(100 * value)
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)

    @property
    def imageList(self):
        lst = []
        for i in range(self.fileListWidget.count()):
            item = self.fileListWidget.item(i)
            lst.append(item.text())
        return lst

    def openNextImg(self, _value=False, load=True,revocationFlags = False):
        if not self.mayContinue():
            return
        #清除缓存
        self.canvas.current = None
        self.canvas.drawingPolygon.emit(False)
        self.canvas.update()

        Nimage = len(self.imageList)
        if Nimage <= 0:#判断下有没有文件
            return

        if revocationFlags:
            if self.saveRevocationFile and load:
                self.loadFile(self.saveRevocationFile, openNextFlag=True)
                self.saveRevocationFile = None
        else:
            filename = None
            if self.filename is None:
                filename = self.imageList[0]
            else:
                currIndex = self.imageList.index(self.filename)
                if currIndex + 1 < len(self.imageList):
                    filename = self.imageList[currIndex + 1]
                else:
                    filename = self.imageList[-1]

            self.filename = filename

            if self.filename and load:
                self.loadFile(self.filename,openNextFlag=True)

    def show_annotation_from_file(self,file_path,changeFlage = False):
        json_path = osp.splitext(file_path)[0]+".json"
        txt_path = osp.splitext(file_path)[0]+ self._config["fileType"]["__TXT_SUFFIX__"]
        if osp.isfile(json_path) and osp.isfile(txt_path):
            if self.label_file_format==LabelFileFormat.CULANE:
                self.set_format(FORMAT_CULANE)
                return txt_path
            else:
                if self.canvas.mode == self.canvas.CREATE:
                    self.canvas.createMode = "linestrip"
                    pass
                self.set_format(FORMAT_JSON)
                return json_path
        else:
            if osp.isfile(json_path):
                if not changeFlage:
                    self.set_format(FORMAT_JSON)
                    return json_path
                if self.label_file_format == LabelFileFormat.CULANE:
                    return txt_path
                else:
                    return json_path

            elif osp.isfile(txt_path):
                if not changeFlage:
                    #防止在culane模式中触发矩形框
                    if self.canvas.mode == self.canvas.CREATE:
                        self.canvas.createMode = "linestrip"
                        pass
                    self.set_format(FORMAT_CULANE)
                    return txt_path
                if self.label_file_format == LabelFileFormat.JSON:
                    return json_path
                else:
                    return txt_path

            else:
                return json_path


    def load_image_file(filename):
        try:
            image_pil = Image.open(filename)
        except IOError:
            return

        # 根据图像的exif调整方向
        image_pil =image.apply_exif_orientation(image_pil)

        with io.BytesIO() as f:
            ext = osp.splitext(filename)[1].lower()

            if ext in [".jpg", ".jpeg"]:
                format = "JPEG"
            else:
                format = "PNG"
            image_pil.save(f, format=format)
            f.seek(0)
            return f.read()

    def loadFile(self, filename=None,changeFlage=False,openNextFlag = False):
       #加载指定的文件，如果为None则加载最后一个打开的文件。'''
        self.actions.fitWindow.setEnabled(True)
        self.actions.save_format.setEnabled(True)
        #self.actions.deleteImage.setEnabled(True)
        self.combobox.setEnabled(True)

        self.number = 0
        if not openNextFlag:
            curNumber = self.imageList.index((filename)) + 1
            image_num = len(self.imageList)
            self.fileEdit.setText("{}/{}  {}".format(curNumber, image_num, osp.basename(filename)))
            self.actions.deleteImage.setEnabled(True)
        self.currentFile = filename
        if self.output_dir:
            self.deleFile = osp.join(self.output_dir,osp.basename(filename))
        else:
            self.deleFile = filename
            self.originfile = filename

        if filename in self.imageList and (
                self.fileListWidget.currentRow() != self.imageList.index(filename)
        ):
            self.fileListWidget.setCurrentRow(self.imageList.index(filename))  # 当前行
            self.fileListWidget.repaint()  # 刷新页面效果的方法，如果你要页面进行重画就可以调用
            return

        self.resetState()
        self.canvas.setEnabled(False)
        if filename is None:
            filename = self.settings.value("filename", "")
        filename = str(filename)
        if not QtCore.QFile.exists(filename):
            self.errorMessage(
                "打开文件错误",
                "没有该类型文件: <b>%s</b>" % filename,
            )
            return False
        label_file = osp.splitext(filename)[0] + ".json"

        if self.output_dir:
            label_file_without_path = osp.basename(label_file)
            label_file = osp.join(self.output_dir, label_file_without_path)

        label_file = self.show_annotation_from_file(label_file,changeFlage)

        if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(
            label_file,self._config["fileType"]["__TXT_SUFFIX__"]
        ):
            if self.imageList:
                item = self.fileListWidget.currentItem()
                item.setCheckState(Qt.Checked)

            if osp.splitext(label_file)[1]==".json":
                try:
                    img_suffix = osp.basename(filename)
                    self.labelFile = LabelFile(label_file,img_suffix,txt_suffix=self._config["fileType"]["__TXT_SUFFIX__"])
                except LabelFileError as e:
                    self.errorMessage(
                        "打开文件错误",
                        self.tr(
                            "<p><b>%s</b></p>"
                            "<p>请确认  <i>%s</i> 格式是否正确."
                        )
                        % (e, label_file),
                    )
                    return False

                self.imageData = self.labelFile.imageData
                # 判断以下这个json文件是否没有标签 没有标签就不打钩
                if not self.labelFile.shapes and self.Nimage != 0:
                    item = self.fileListWidget.currentItem()
                    item.setCheckState(Qt.Unchecked)
                    # self.errorMessage("读取标签异常","这个标签是空的")
                    comLabelFile = osp.basename(label_file).split('.')[0]
                    if comLabelFile in self.saveComFile:
                        self.saveComFile.remove(comLabelFile)
                        self.saveComFile.sort()
                self.imagePath = osp.join(
                    osp.dirname(label_file),
                    self.labelFile.imagePath,
                )
                self.otherData = self.labelFile.otherData
            else:

                img_suffix = osp.basename(filename)
                self.labelFile = LabelFile(label_file, img_suffix,txt_suffix=self._config["fileType"]["__TXT_SUFFIX__"])

                # 没有图片数据的话就得到图片的绝对路径
                self.imageData = LabelFile.load_image_file(filename)
                if self.imageData:
                    self.imagePath = filename

        else:
            if self.label_file_format == LabelFileFormat.JSON and self.imageList:
                item = self.fileListWidget.currentItem()

                item.setCheckState(Qt.Unchecked)
            #获得图片数据
            try:
                self.imageData = LabelFile.load_image_file(filename)
            except OSError:
                self.errorMessage("警告","文件图像被截断，请检查图片是否损坏")
                return

            if self.imageData:
                self.imagePath = filename
            self.labelFile = None
        image = QtGui.QImage.fromData(self.imageData)

        if image.isNull():
            formats = [
                "*.{}".format(fmt.data().decode())
                for fmt in QtGui.QImageReader.supportedImageFormats()
            ]
            self.errorMessage(
                "文件打开失败",
                    "<p>Make sure <i>{0}</i> is a valid image file.<br/>"
                    "Supported image formats: {1}</p>"
                ).format(filename, ",".join(formats),
            )
            return False
        self.image = image
        self.filename = filename
        #赋值给self.pixMap对象，用来给paintEvent使用
        self.canvas.loadPixmap(QtGui.QPixmap.fromImage(image))#       flags = {k: False for k in None or []}#zhe li you wen ti
        if self.labelFile:
            if self.label_file_format!=LabelFileFormat.CULANE:
                self.dicValueToKey()#修改self.labelFile.shapes["label"]将标签数字换成文字
            self.loadLabels(self.labelFile.shapes)

        self.setClean()
        self.canvas.setEnabled(True)
        # set zoom values
        is_initial_load = not self.zoom_values
        # if self.filename in self.zoom_values:
        #     self.zoomMode = self.zoom_values[self.filename][0]
        #     self.setZoom(self.zoom_values[self.filename][1])
        # elif is_initial_load or not False:
        #     self.adjustScale(initial=True)
        if is_initial_load or not False:
            self.adjustScale(initial=True)
        # set scroll values
        for orientation in self.scroll_values:
            if self.filename in self.scroll_values[orientation]:
                self.setScroll(
                    orientation, self.scroll_values[orientation][self.filename]
                )
        self.paintCanvas()
        self.canvas.setFocus()
        return True


    def dicValueToKey(self):
        i = 0
        j = 0
        for val in self.labelFile.shapes:
            for key,value in self._config["label"].items():
                if val["label"] == value:
                    self.labelFile.shapes[i]["label"]=key
                    i+=1
            for key,value in self._config["group_id"].items():
                if val["group_id"]==value:
                    self.labelFile.shapes[j]["group_id"] = key
                    j+=1

    def errorMessage(self, title, message):
        return QtWidgets.QMessageBox.critical(
            self, title, "<p><b>%s</b></p>%s" % (title, message)
        )

    def loadLabels(self, shapes):
        s = []
        for shape in shapes:
            label = shape["label"]
            points = shape["points"]
            shape_type = shape["shape_type"]
            flags = shape["flags"]
            group_id = shape["group_id"]
            other_data = shape["other_data"]

            if not points:
                # skip point-empty shape
                continue

            shape = Shape(
                label=label,
                shape_type=shape_type,
                group_id=group_id,
            )
            for x, y in points:
                shape.addPoint(QtCore.QPointF(float(x), float(y)))
            shape.close()

            default_flags = {}
            shape.flags = default_flags
            #shape.flags.update(flags)
            shape.other_data = other_data

            s.append(shape)
        self.loadShapes(s)

    def loadShapes(self, shapes, replace=True):
        self._noSelectionSlot = True
        for shape in shapes:
            self.addLabel(shape)
        self.labelList.clearSelection()
        self._noSelectionSlot = False
        self.canvas.loadShapes(shapes, replace=replace)

    def addLabel(self, shape):
        if shape.group_id is None:
            text = shape.label
        else:
            text = "{} ({})".format(shape.label, shape.group_id)
        label_list_item = LabelListWidgetItem(text, shape)
        self.labelList.addItem(label_list_item)
        if not self.uniqLabelList.findItemsByLabel(shape.label):
            item = self.uniqLabelList.createItemFromLabel(shape.label)
            self.uniqLabelList.addItem(item)
            rgb = self._get_rgb_by_label(shape.label)
            self.uniqLabelList.setItemLabel(item, shape.label, rgb)
        self.labelDialog.addLabelHistory(shape.label)

        self._update_shape_color(shape)
        label_list_item.setText(
            '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                text, *shape.fill_color.getRgb()[:3]
            )
        )
    def _update_shape_color(self, shape):
        r, g, b = self._get_rgb_by_label(shape.label)
        shape.line_color = QtGui.QColor(r, g, b)
        shape.vertex_fill_color = QtGui.QColor(r, g, b)
        shape.hvertex_fill_color = QtGui.QColor(255, 255, 255)
        shape.fill_color = QtGui.QColor(r, g, b, 128)
        shape.select_line_color = QtGui.QColor(255, 255, 255)
        shape.select_fill_color = QtGui.QColor(r, g, b, 155)

    def _get_rgb_by_label(self, label):
        item = self.uniqLabelList.findItemsByLabel(label)[0]
        label_id = self.uniqLabelList.indexFromItem(item).row() + 1
        label_id += 0
        return LABEL_COLORMAP[label_id % len(LABEL_COLORMAP)]

        return (0, 255, 0)

    def setClean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        #self.actions.createMode.setEnabled(True)
        #self.actions.createLineStripMode.setEnabled(True)
        title = self.__version__
        if self.filename is not None:
            title = "{} - {}".format(title, self.filename)
        self.setWindowTitle(title)

    def hasLabelFile(self):
        if self.filename is None:
            return False

    def openDirDialog(self,_value=False, dirpath=None):
        #self.actions.deleteImage.setEnabled(True)
        self.actions.revocationFile.setEnabled(False)
        if not self.mayContinue():#如果打开新的文件，要提示是否保存旧文件
            return
        self.saveComFile.clear()
        #打开目录选择对话框 第3个参数是默认打开目录 默认主目录
        targetDirPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "打开图片目录",
                '.',
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )
        self.Nimage = 0

        self.importDirImages(targetDirPath)

    # 加载图片列表
    #dirpath： 图片父目录
    #pattern:在searchfile 时用到
    def importDirImages(self, dirpath, pattern=None, load=True,revocationFlag = False):
        self.actions.openNextImg.setEnabled(True)
        self.actions.openPrevImg.setEnabled(True)

        if not self.mayContinue() or not dirpath:
            return

        self.lastOpenDir = dirpath
        self.filename = None
        self.fileListWidget.clear()#清空列表框内容 会触发 fileSelectChange 函数
        self.filepath = None
        emptyFlage = True
        for filename in self.scanAllImages(dirpath):
            if pattern and pattern not in filename:
                continue
            emptyFlage = False
            label_file = osp.splitext(filename)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)

            json_path=label_file
            txt_path = osp.splitext(label_file)[0] +  self._config["fileType"]["__TXT_SUFFIX__"]
            if osp.exists(txt_path) :#and osp.isfile(label_file)
                label_file =  txt_path
            if osp.exists(json_path):
                label_file = json_path

            item = QtWidgets.QListWidgetItem(filename)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            # 判断是否有json文件
            if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(
                    label_file,self._config["fileType"]["__TXT_SUFFIX__"]
            ) :
                item.setCheckState(Qt.Checked)
                label_file = osp.basename(label_file).split(".")[0]
                self.saveComFile.append(label_file)#将json 文件加进去
                self.saveComFile.sort()
                self.Nimage += 1
                #self.button.setText("{} {}/{}".format(osp.basename(filename),self.Nimage, self.image_num))
            else:
                item.setCheckState(Qt.Unchecked)
                if not self.saveComFile:
                    #self.button.setText(" {} / {}".format(0, self.image_num) )
                    pass
                item.setCheckState(Qt.Unchecked)  # 没有json文件就不用打钩

            self.fileListWidget.addItem(item)

        if emptyFlage:
            self.fileEdit.setText("{}/{}".format(0,0))
        else:
            subFIleName = self.imageList[0]
            Nimage = len(self.imageList)
            curNumber = self.imageList.index((subFIleName)) + 1
            self.fileEdit.setText("{}/{}  {}".format(curNumber, Nimage, osp.basename(subFIleName)))
        self.openNextImg(load=load,revocationFlags=revocationFlag)

    def resetState(self):
        self.labelList.clear()
        self.filename = None
        self.imagePath = None
        self.imageData = None
        self.labelFile = None
        self.otherData = None
        self.canvas.resetState()

    #扫描得到图片路径存到列表中
    def scanAllImages(self, folderPath):
        #图片扩展名
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        images = []
        #得到相对路径 绝对路径
        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):#判断扩展名是否符合要求
                    relativePath = osp.join(root, file)
                    images.append(relativePath)
        images.sort(key=lambda x: x.lower())
        self.image_num = len(images)
        #self.button.setText(" {} / {}".format(0, self.image_num) )
        #self.proGress.setText(" {} / {}".format(0, self.image_num))
        return images

    def newShape(self):
        """弹出并将焦点放在标签编辑器上。
        """
        items = self.uniqLabelList.selectedItems()
        text = None
        if items:
            text = items[0].data(Qt.UserRole)
        flags = {}
        group_id = None
        if  not text:
            label_format = False
            if self.label_file_format == LabelFileFormat.CULANE:
                self.number = self.labelList.model().rowCount()
                self.number+=1
                label_format=True
            previous_text = self.labelDialog.comBoBox.currentText()
            text, flags, group_id = self.labelDialog.popUp(text,label_format=label_format,number = self.number)
            if not text:
                self.labelDialog.comBoBox.setCurrentText(previous_text)
        if text:
            self.labelList.clearSelection()
            shape = self.canvas.setLastLabel(text, flags)
            shape.group_id = group_id
            self.addLabel(shape)
            self.actions.editMode.setEnabled(True)
            self.actions.undoLastPoint.setEnabled(False)
            self.actions.undo.setEnabled(True)
            #开启编辑模式
            editModeIndex = self.combobox.model().index(2, 0)
            self.combobox.model().setData(editModeIndex, -1, Qt.UserRole - 1)
            self.setDirty()
        else:
            self.canvas.undoLastLine()
            self.canvas.shapesBackups.pop()

    # 滚动条事件
    def scrollRequest(self, delta, orientation):
        units = -delta/(8*15)  #（原先的数值）*0.1  # natural scroll自然滚动
        bar = self.scrollBars[orientation]
        value = bar.value() + bar.singleStep() * units
        self.setScroll(orientation, value)

    def setScroll(self, orientation, value):
        self.scrollBars[orientation].setValue(value)
        self.scroll_values[orientation][self.filename] = value

    def setZoom(self, value):
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)  # 显示窗口设置数值
        self.zoom_values[self.filename] = (self.zoomMode, value)

    def addZoom(self, increment=1.1):#原来是1.1
        zoom_value = self.zoomWidget.value() * increment
        if increment > 1:
            zoom_value = math.ceil(zoom_value)  # 向上取整”， 即小数部分直接舍去，并向正数部分进1
        else:
            zoom_value = math.floor(zoom_value)
        self.setZoom(zoom_value)

    def zoomRequest(self, delta, pos):
        canvas_width_old = self.canvas.width()
        units = 1.1
        if delta < 0:
            units = 0.9
        self.addZoom(units)

        canvas_width_new = self.canvas.width()
        if canvas_width_old != canvas_width_new:
            canvas_scale_factor = canvas_width_new / canvas_width_old

            x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
            y_shift = round(pos.y() * canvas_scale_factor) - pos.y()

            self.setScroll(
                Qt.Horizontal,
                self.scrollBars[Qt.Horizontal].value() + x_shift,
            )
            self.setScroll(
                Qt.Vertical,
                self.scrollBars[Qt.Vertical].value() + y_shift,
            )

    # 对画布信号作出反应。
    def shapeSelectionChanged(self, selected_shapes):
        self._noSelectionSlot = True
        for shape in self.canvas.selectedShapes:
            shape.selected = False
        self.labelList.clearSelection()
        self.canvas.selectedShapes = selected_shapes
        for shape in self.canvas.selectedShapes:
            shape.selected = True
            item = self.labelList.findItemByShape(shape)
            self.labelList.selectItem(item)
            self.labelList.scrollToItem(item)
        self._noSelectionSlot = False
        n_selected = len(selected_shapes)
        self.actions.edit.setEnabled(n_selected == 1)
        self.actions.delete.setEnabled(n_selected)
        self.deleteFlag = n_selected
        if n_selected:
            value = -1
        else:
            value = 0
        deleteIndex = self.combobox.model().index(3, 0)
        self.combobox.model().setData(deleteIndex, value, Qt.UserRole - 1)

    def buttonClick(self):
        """点击跳转按钮时跳到序号最高的已标注文件"""
        if not self.mayContinue():
            return
        if self.saveComFile and self.imageList:
            path = os.path.split(self.imageList[0])[0]
            #file = str(self.button.text()).split(" ")[0]
            file = self.saveComFile[-1]+osp.splitext(self.originfile)[1]
            filename = osp.join(path,file)
            if file !=" " and filename in self.imageList:

                currIndex = self.imageList.index(os.path.join(path,file))
                if currIndex < len(self.imageList):
                    filename = self.imageList[currIndex]
                    if filename:
                        self.loadFile(filename)

    def skipfile(self):
        #QLineEdit 是 enter触发和失去焦点触发，所以会触发两次这个函数，为了避免这个情况判断失去焦点时不执行函数
        if self.fileEdit.hasFocus():
            # 清除缓存
            self.canvas.current = None
            self.canvas.drawingPolygon.emit(False)
            self.canvas.update()

            if not self.mayContinue():
                return

            if self.fileEdit.text() != "":
                if QtCore.QRegExp(r"\d*").exactMatch(self.fileEdit.text().split("/")[0]):
                    index = int(self.fileEdit.text().split("/")[0]) - 1
                    if index >= 0 and index < len(self.imageList):
                        filename = self.imageList[index]
                        if filename:
                            self.loadFile(filename)

                if self.fileEdit.text().split('.')[-1] in ["jpg", 'png'] and self.imageList:
                    basePath = osp.dirname(self.imageList[0])
                    filename = osp.join(basePath, self.fileEdit.text())
                    if filename and filename in self.imageList:
                        self.loadFile(filename)


#触发函数 file选中对象改变时激活
    def fileSelectionChanged(self):
        #清除缓存
        self.canvas.current = None
        self.canvas.drawingPolygon.emit(False)
        self.canvas.update()

        items = self.fileListWidget.selectedItems()
        if not items:
            return
        item = items[0]
        if self.discard:
            if not self.mayContinue():
                return
        self.discard = True

        currIndex = self.imageList.index(str(item.text()))
        if currIndex < len(self.imageList):
            filename = self.imageList[currIndex]
            if filename:
                self.loadFile(filename)

    def setDirty(self):
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)

        if self.actions.saveAuto.isChecked():
            label_file = osp.splitext(self.imagePath)[0] + ".json"
            if self.label_file_format == LabelFileFormat.CULANE:
                label_file = osp.splitext(self.imagePath)[0]+ self._config["fileType"]["__TXT_SUFFIX__"]
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            self.saveLabels(label_file)
            return
        self.dirty = True
        self.actions.save.setEnabled(True)#开启保存按钮
        title = self.__version__
        if self.filename is not None:
            title = "{} - {}*".format(title, self.filename)
        self.setWindowTitle(title)

    def labelSelectionChanged(self):
        if self._noSelectionSlot:
            return
        if self.canvas.editing():
            selected_shapes = []
            for item in self.labelList.selectedItems():
                selected_shapes.append(item.shape())
            if selected_shapes:
                self.canvas.selectShapes(selected_shapes)
            else:
                self.canvas.deSelectShape()

    def labelItemChanged(self, item):
        shape = item.shape()
        self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    def labelOrderChanged(self):
        self.setDirty()
        self.canvas.loadShapes([item.shape() for item in self.labelList])


    def toggleDrawingSensitive(self, drawing=True):
        """在绘图过程中，应禁用模式之间的切换。"""
        # self.actions.editMode.setEnabled(not drawing)
        #
        # editModeIndex = self.combobox.model().index(2, 0)
        # if drawing:
        #     self.combobox.model().setData(editModeIndex, 0, Qt.UserRole - 1)
        # else:
        #     self.combobox.model().setData(editModeIndex, -1, Qt.UserRole - 1)
        self.actions.undoLastPoint.setEnabled(drawing)
        #self.actions.undo.setEnabled(not drawing)
        #self.actions.deleteImage.setEnabled(not drawing)


    # self.actions.delete.setEnabled(not drawing)

#filesearch QLineedit框键入时触发 用于搜索图片路径
    def fileSearchChanged(self):
        self.importDirImages(
            self.lastOpenDir,
            pattern=self.fileSearch.text(),
            load=False,
        )