from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from twoD import edgefunction as ef
import cv2
import numpy as np
import pydicom


class QPaintLabel2(QLabel):

    def __init__(self, parent):
        super(QLabel, self).__init__(parent)
        self.window = None
        self.setMouseTracking(False)
       
        self.setMinimumSize(1, 1)
        self.drawornot, self.seed = False, False
        self.image = None
        self.processedImage = None
        self.imgr, self.imgc = None, None
        self.pos_x = 20
        self.pos_y = 20
        self.imgpos_x = 0
        self.imgpos_y = 0
       
        self.pos_xy = []
        self.mor_Kersize = 3
        self.mor_Iter = 3

    def mouseMoveEvent(self, event):
        if self.drawornot:
            self.pos_x = event.pos().x()
            self.pos_y = event.pos().y()
            self.imgpos_x = int(self.pos_x * self.imgc / self.width())
            self.imgpos_y = int(self.pos_y * self.imgr / self.height())
            self.pos_xy.append((self.imgpos_x, self.imgpos_y))
            self.drawing()

    def mousePressEvent(self, event):
        if self.drawornot:
            self.pos_x = event.pos().x()
            self.pos_y = event.pos().y()
            self.imgpos_x = int(self.pos_x * self.imgc / self.width())
            self.imgpos_y = int(self.pos_y * self.imgr / self.height())
            self.pos_xy.append((self.imgpos_x, self.imgpos_y))
            self.drawing()
        if self.seed:
            self.pos_x = event.pos().x()
            self.pos_y = event.pos().y()
            self.imgpos_x = int(self.pos_x * self.imgc / self.width())
            self.imgpos_y = int(self.pos_y * self.imgr / self.height())
            self.seed_clicked(seedx=self.imgpos_x, seedy=self.imgpos_y)
            self.seed = False


    def edge_detection(self, _type):
        try:
            self.processedImage = cv2.cvtColor(self.processedImage, cv2.COLOR_BGR2GRAY)
        except Exception:
            pass
        self.processedImage = linear_convert(self.processedImage).astype(np.uint8)
        if _type == 'Laplacian':
            self.processedImage = cv2.convertScaleAbs(cv2.Laplacian(self.processedImage, cv2.CV_16S, ksize=1))
        elif _type == 'Sobel':
            img = linear_convert(ef.sobel(self.processedImage)).astype(np.uint8)
            ret, img = cv2.threshold(img, 110, 255, cv2.THRESH_BINARY)
            self.processedImage = img
        elif _type == 'Perwitt':
            img = linear_convert(ef.perwitt(self.processedImage)).astype(np.uint8)
            ret, img = cv2.threshold(img, 70, 255, cv2.THRESH_BINARY)
            self.processedImage = img
        elif _type == 'Frei & Chen':
            img = linear_convert(ef.frei_chen(self.processedImage)).astype(np.uint8)
            ret, img = cv2.threshold(img, 80, 255, cv2.THRESH_BINARY)
            self.processedImage = img

        self.display_image()

    def morthology(self, _type):
        kernel = np.ones((self.mor_Kersize, self.mor_Kersize), np.uint8)

        if _type == 'Dilation':
            self.processedImage = cv2.dilate(self.processedImage, kernel, iterations=self.mor_Iter)
        elif _type == 'Erosion':
            self.processedImage = cv2.erode(self.processedImage, kernel, iterations=self.mor_Iter)
        elif _type == 'Opening':
            self.processedImage = cv2.morphologyEx(self.processedImage, cv2.MORPH_OPEN,
                                                   kernel, iterations=self.mor_Iter)
        elif _type == 'Closing':
            self.processedImage = cv2.morphologyEx(self.processedImage, cv2.MORPH_CLOSE,
                                                   kernel, iterations=self.mor_Iter)

        self.display_image()

    def load_dicom_image(self, fname):
        dcm = pydicom.read_file(fname, force=True)
        # veya dosya için doğru aktarım sözdizimi ne olursa olsun
        dcm.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian
        print(np.nanmax(dcm.pixel_array), np.nanmin(dcm.pixel_array))
        dcm.image = dcm.pixel_array * dcm.RescaleSlope + dcm.RescaleIntercept
        self.image = linear_convert(dcm.image).astype(np.uint8)
        self.processedImage = self.image.copy()
        self.imgr, self.imgc = self.processedImage.shape[0:2]
        self.display_image()

    def load_image(self, fname):
        print(fname)
        self.image = cv2.imread(fname)
        self.processedImage = self.image.copy()
        self.imgr, self.imgc = self.processedImage.shape[0:2]
        self.display_image()

    def display_image(self):
        qformat = QImage.Format_Indexed8
        if len(self.processedImage.shape) == 3:  # rows[0], cols[1], channels[2]
            if (self.processedImage.shape[2]) == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        w, h = self.width(), self.height()
        img = QImage(self.processedImage, self.processedImage.shape[1],
                     self.processedImage.shape[0], self.processedImage.strides[0], qformat)
        img = img.rgbSwapped()
        # Resmin Qlabel boyutuyla değişmesine izin verir
        self.setScaledContents(True)
        # Çizgi genişliğinin çıkarılması
        backlash = self.lineWidth()*2
        self.setPixmap(QPixmap.fromImage(img).scaled(w-backlash, h-backlash, Qt.IgnoreAspectRatio))
        self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

    def drawing(self):
        self.processedImage[self.imgpos_y:self.imgpos_y+20, self.imgpos_x:self.imgpos_x+20] = 255
        self.display_image()

    def thresholding(self, threshold):
        ret, img = cv2.threshold(self.processedImage, threshold, 255, cv2.THRESH_BINARY)
        self.processedImage = img
        self.display_image()

    def seed_clicked(self, seedx, seedy):
        try:
            self.processedImage = cv2.cvtColor(self.processedImage, cv2.COLOR_BGR2GRAY)
        except Exception:
            pass
        tobeprocessed = self.processedImage.copy()
        result = self.region_growing(tobeprocessed, (seedy, seedx))
        self.processedImage = result
        self.display_image()

    def region_growing(self, img, seed):
        _list = []
        
        outimg = np.zeros_like(img)
        _list.append((seed[0], seed[1]))
        processed = []
       
        while len(_list) > 0:
            pix = _list[0]
            outimg[pix[0], pix[1]] = 255
            for coord in get8n(pix[0], pix[1], img.shape):
                if img[coord[0], coord[1]] != 0:
                    outimg[coord[0], coord[1]] = 255
                    
                    if coord not in processed:
                        _list.append(coord)
                    processed.append(coord)
            
            _list.pop(0)
            self.processedImage = outimg
            self.display_image()
        cv2.destroyAllWindows()
        return outimg


def get8n(x, y, shape):
    out = []
    maxx = shape[1]-1
    maxy = shape[0]-1
    # top left
    outx = min(max(x-1, 0), maxx)
    outy = min(max(y-1, 0), maxy)
    out.append((outx, outy))
    # top center
    outx = x
    outy = min(max(y-1, 0), maxy)
    out.append((outx, outy))
    # top right
    outx = min(max(x+1, 0), maxx)
    outy = min(max(y-1, 0), maxy)
    out.append((outx, outy))
    # left
    outx = min(max(x-1, 0), maxx)
    outy = y
    out.append((outx, outy))
    # right
    outx = min(max(x+1, 0), maxx)
    outy = y
    out.append((outx, outy))
    # bottom left
    outx = min(max(x-1, 0), maxx)
    outy = min(max(y+1, 0), maxy)
    out.append((outx, outy))
    # bottom center
    outx = x
    outy = min(max(y+1, 0), maxy)
    out.append((outx, outy))
    # bottom right
    outx = min(max(x+1, 0), maxx)
    outy = min(max(y+1, 0), maxy)
    out.append((outx, outy))
    return out


def linear_convert(img):
    convert_scale = 255.0 / (np.max(img) - np.min(img))
    converted_img = convert_scale*img-(convert_scale*np.min(img))
    return converted_img
