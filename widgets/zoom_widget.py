from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

class ZoomWidget(QtWidgets.QSpinBox):#一个计数器控件
    def __init__(self, value=100):
        super(ZoomWidget, self).__init__()
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)#	不要显示按钮。
        self.setRange(1, 1000)
        self.setSuffix(" /")
        self.setValue(value)
        self.setToolTip("Zoom Level")
        self.setStatusTip(self.toolTip())
        self.setAlignment(QtCore.Qt.AlignCenter)#QtCore.Qt.AlignCenter

#部件Qt建议的最小值；该值应该是布局的最小大小；
    def minimumSizeHint(self):
        height = super(ZoomWidget, self).minimumSizeHint().height()#minimumSizeHint是部件Qt建议的最小值；
        fm = QtGui.QFontMetrics(self.font())
        width = fm.width(str(self.maximum()))
        return QtCore.QSize(width, height)

