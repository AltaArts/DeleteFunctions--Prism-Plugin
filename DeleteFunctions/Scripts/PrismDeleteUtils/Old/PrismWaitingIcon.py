import sys
import os
from PySide2.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QMainWindow, QDesktopWidget
from PySide2.QtGui import QPixmap, QBitmap, QPainter
from PySide2.QtCore import Qt, QTimer

class PrismWaitingIcon(QGraphicsView):
    def __init__(self):
        super(PrismWaitingIcon, self).__init__()

        prismWaitingCircleDir = os.path.dirname(__file__)
        self.imageSeqDir = os.path.join(prismWaitingCircleDir, "Images")

        self.imageSeq = [os.path.join(self.imageSeqDir, f"{i}.png") for i in range(1, 16)]
        self.currentImageIndex = 0

        self.init_ui()

    def init_ui(self):
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateImage)
        self.timer.start(150)  # Change the interval based on your preference

        # Center the window on the screen
        self.setGeometry(0, 0, 220, 220)
        screenGeo = QDesktopWidget().availableGeometry(self)
        self.move((screenGeo.width() - self.width()) // 2, (screenGeo.height() - self.height()) // 2)

        self.setWindowTitle('Waiting Circle')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Set background color to black
        self.setStyleSheet("background-color: black;")

        # Create a mask with transparency
        mask = QBitmap(self.size())
        mask.clear()
        painter = QPainter(mask)
        painter.fillRect(0, 0, self.width(), self.height(), Qt.white)
        painter.setBrush(Qt.black)
        painter.drawEllipse(50, 50, 120, 120)  # Adjust the shape as needed
        painter.end()  # Add this line
        self.setMask(mask)

    def updateImage(self):
        pixmap = QPixmap(self.imageSeq[self.currentImageIndex])
        item = QGraphicsPixmapItem(pixmap)
        self.scene.clear()
        self.scene.addItem(item)

        self.currentImageIndex = (self.currentImageIndex + 1) % len(self.imageSeq)

    def showWaitingIcon(self):
        self.show()

if __name__ == '__main__':

    app = QApplication(sys.argv)
    window = PrismWaitingIcon()
    window.showWaitingIcon()  # Add this line to show the icon
    sys.exit(app.exec_())
