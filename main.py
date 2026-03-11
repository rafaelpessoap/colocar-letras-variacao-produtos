import sys
import os
from pathlib import Path

# PyQt6
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsTextItem, QHBoxLayout, QPushButton, QMessageBox,
    QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QColor, QPixmap, QImage, QPainter, QPen

# Ultralytics (YOLO)
from ultralytics import YOLO

# Pillow
from PIL import Image, ImageDraw, ImageFont


class QInteractiveLetter(QGraphicsTextItem):
    """
    Subclass of QGraphicsTextItem for the letters.
    Allows for dragging, selecting, and deleting.
    """
    def __init__(self, text, font_size, parent=None):
        super().__init__(text, parent)
        self.setFlags(
            QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable
        )
        
        # Adjust appearance
        font = QFont("Arial", int(font_size), QFont.Weight.Bold)
        self.setFont(font)
        self.setDefaultTextColor(Qt.GlobalColor.white)
        # Ensure it is painted on top
        # Drop shadow for better contrast against varied backgrounds
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(5)
        shadow.setXOffset(2)
        shadow.setYOffset(2)
        shadow.setColor(Qt.GlobalColor.black)
        
        self.setGraphicsEffect(shadow)

from PyQt6.QtGui import QPainterPath

class YOLOProcessingThread(QThread):
    # Sends back (image_path, list_of_boxes, error_msg, method_used)
    finished_signal = pyqtSignal(str, list, str, str)

    def __init__(self, image_path, model_name="yolo26n.pt"):
        super().__init__()
        self.image_path = image_path
        self.model_name = model_name

    def run(self):
        try:
            if self.model_name == "OpenCV (Rápido)":
                import cv2
                import numpy as np
                
                img_cv = cv2.imread(self.image_path)
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
                
                kernel = np.ones((25, 25), np.uint8)
                closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                closed = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
                
                contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                boxes = []
                img_h, img_w = img_cv.shape[:2]
                min_area = (img_h * img_w) * 0.02 
                
                for c in contours:
                    if cv2.contourArea(c) > min_area:
                        x, y, w, h = cv2.boundingRect(c)
                        boxes.append([x, y, x+w, y+h])
                method_used = "OpenCV (Rápido)"
            else:
                method_used = f"YOLO ({self.model_name})"
                
                # Get model path ensuring it downloads to local project dir
                project_dir = os.path.dirname(os.path.abspath(__file__))
                model_full_path = os.path.join(project_dir, self.model_name)
                
                # Load YOLO and predict
                model = YOLO(model_full_path)
                results = model(self.image_path, conf=0.15)
                result = results[0]
                yolo_boxes = result.boxes.xyxy.cpu().numpy()
                
                # Determine image area to filter excessively small noise boxes
                try:
                    from PIL import Image
                    with Image.open(self.image_path) as img:
                        img_w, img_h = img.size
                except:
                    img_w, img_h = 1000, 1000
                    
                min_area = (img_w * img_h) * 0.01 
                
                boxes = []
                for b in yolo_boxes:
                    bx_min, by_min, bx_max, by_max = b
                    b_area = (bx_max - bx_min) * (by_max - by_min)
                    if b_area > min_area:
                        boxes.append([int(bx_min), int(by_min), int(bx_max), int(by_max)])
            
            # Sort left to right
            sorted_boxes = sorted(boxes, key=lambda b: b[0])
            self.finished_signal.emit(self.image_path, sorted_boxes, "", method_used)
            
        except Exception as e:
            self.finished_signal.emit(self.image_path, [], str(e), "")


class CanvasView(QGraphicsView):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.image_path = None
        
        # Enables dropping files on the view
        self.setAcceptDrops(True)
        self.zoom_factor = 1.0
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg')):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.main_window.start_processing(file_path)
                event.acceptProposedAction()
                break
                
    def zoom_in(self):
        self.zoom_factor *= 1.2
        self.scale(1.2, 1.2)
        
    def zoom_out(self):
        self.zoom_factor *= (1.0 / 1.2)
        self.scale(1.0 / 1.2, 1.0 / 1.2)
                
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Se usuário já alterou o zoom original, não força o resize para 'caber na janela' novamente
        if self.zoom_factor == 1.0:
            self.fit_image()
        
    def fit_image(self):
        if self.pixmap_item:
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            
    def keyPressEvent(self, event):
        # Allow deleting selected letters via Backspace/Delete keyboard keys
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            for item in self.scene.selectedItems():
                if isinstance(item, QInteractiveLetter):
                    self.scene.removeItem(item)
            self.main_window.recalculate_letters()
            return
        super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Aplicativo de Editor de Mapeamento YOLO26")
        self.resize(1000, 700)
        
        # Habilita drag and drop na janela principal toda
        self.setAcceptDrops(True)
        
        # Setup UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout_main = QVBoxLayout(self.central_widget)
        
        # Top Panel (Toolbar)
        self.toolbar_layout = QHBoxLayout()
        
        self.status_label = QLabel("Arraste uma imagem no painel abaixo!")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        # Model Selection
        self.combo_model = QComboBox()
        self.combo_model.addItems(["yolo26n.pt", "OpenCV (Rápido)", "yolo26s.pt", "yolo26m.pt", "yolo26l.pt", "yolo26x.pt"])
        self.combo_model.setToolTip("Selecione o método (IA ou OpenCV)")
        self.combo_model.currentTextChanged.connect(self.on_model_changed)
        
        self.btn_add = QPushButton("Adicionar Letra (+)")
        self.btn_add.setEnabled(False)
        self.btn_add.clicked.connect(self.add_new_letter)
        
        self.btn_recalc = QPushButton("↻ Reordenar Letras")
        self.btn_recalc.setEnabled(False)
        self.btn_recalc.clicked.connect(self.recalculate_letters)
        
        self.btn_zoom_in = QPushButton("Zoom In (+)")
        self.btn_zoom_in.setEnabled(False)
        self.btn_zoom_in.clicked.connect(lambda: self.view.zoom_in())

        self.btn_zoom_out = QPushButton("Zoom Out (-)")
        self.btn_zoom_out.setEnabled(False)
        self.btn_zoom_out.clicked.connect(lambda: self.view.zoom_out())
        
        self.btn_save = QPushButton("💾 Salvar Imagem Final")
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_image)
        
        self.toolbar_layout.addWidget(self.status_label)
        self.toolbar_layout.addStretch()
        self.toolbar_layout.addWidget(QLabel("Modelo IA:"))
        self.toolbar_layout.addWidget(self.combo_model)
        self.toolbar_layout.addWidget(self.btn_zoom_out)
        self.toolbar_layout.addWidget(self.btn_zoom_in)
        self.toolbar_layout.addWidget(self.btn_add)
        self.toolbar_layout.addWidget(self.btn_recalc)
        self.toolbar_layout.addWidget(self.btn_save)
        
        self.layout_main.addLayout(self.toolbar_layout)
        
        # Central Editor Canvas
        self.view = CanvasView(self)
        self.layout_main.addWidget(self.view)
        
        # Internal state
        self.worker = None
        self.current_image_path = None
        self.original_image_size = (0, 0)
        self.base_font_size = 20

    def on_model_changed(self, text):
        if self.current_image_path:
            self.start_processing(self.current_image_path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg')):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.start_processing(file_path)
                event.acceptProposedAction()
                break

    def start_processing(self, file_path):
        self.status_label.setText(f"Processando imagem: {os.path.basename(file_path)}...")
        self.status_label.setStyleSheet("color: #FF8F00; font-weight: bold;")
        
        self.btn_add.setEnabled(False)
        self.btn_recalc.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_zoom_in.setEnabled(False)
        self.btn_zoom_out.setEnabled(False)
        
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            
        selected_model = self.combo_model.currentText()
        self.worker = YOLOProcessingThread(file_path, selected_model)
        self.worker.finished_signal.connect(self.on_processing_finished)
        self.worker.start()

    def on_processing_finished(self, image_path, boxes, error, method_used):
        if error:
            self.status_label.setText(f"Erro: {error}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            return
            
        self.status_label.setText(f"Sucesso usando {method_used}. Arraste as letras ou pressione Delete.")
        self.status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        
        self.current_image_path = image_path
        
        # Setup Graphics Scene
        self.view.scene.clear()
        
        # Load Pixmap into Scene
        pixmap = QPixmap(image_path)
        self.original_image_size = (pixmap.width(), pixmap.height())
        self.view.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.view.scene.addItem(self.view.pixmap_item)
        
        # Set scene rect
        self.view.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self.view.fit_image()
        
        # Calculate dynamic text size based on image width
        self.base_font_size = max(20, int(pixmap.width() * 0.05))
        
        # Place letters at detected positions
        for i, box in enumerate(boxes):
            x_min, y_min, x_max, y_max = box
            letter_item = QInteractiveLetter("A", self.base_font_size)
            self.view.scene.addItem(letter_item)
            
            # Position above the top-left corner
            # Using QFontMetrics on the actual item to subtract height
            fm = letter_item.font()
            # Rough estimate height based on pointSize
            y_pos = y_min - (self.base_font_size + 15)
            if y_pos < 0:
                y_pos = y_min + 15
                
            letter_item.setPos(x_min, y_pos)
            
        # Refreshes the letters to A, B, C based on X-axis ordering
        self.recalculate_letters()
        
        # Enable UI
        self.btn_add.setEnabled(True)
        self.btn_recalc.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.btn_zoom_in.setEnabled(True)
        self.btn_zoom_out.setEnabled(True)

    def add_new_letter(self):
        # Drop a new letter in the middle of the current view port
        center_point = self.view.mapToScene(self.view.viewport().rect().center())
        
        # Determine next letter
        letters = [item for item in self.view.scene.items() if isinstance(item, QInteractiveLetter)]
        count = len(letters)
        
        def get_letter_str(index):
            res = ""
            index += 1
            while index > 0:
                index -= 1
                res = chr((index % 26) + 65) + res
                index //= 26
            return res
            
        next_text = get_letter_str(count)
        
        letter_item = QInteractiveLetter(next_text, self.base_font_size)
        self.view.scene.addItem(letter_item)
        letter_item.setPos(center_point.x() - 20, center_point.y() - 20)
        
        # Apenas adiciona, sem reordenar automaticamente para não bagunçar as letras atuais do usuário

    def recalculate_letters(self):
        """ Sorts all QInteractiveLetter objects based on their X position from Left to Right and re-labels them. """
        letters = []
        for item in self.view.scene.items():
            if isinstance(item, QInteractiveLetter):
                letters.append(item)
                
        # Sort by actual Scene X coordinate
        letters.sort(key=lambda x: x.scenePos().x())
        
        def get_letter_str(index):
            res = ""
            index += 1
            while index > 0:
                index -= 1
                res = chr((index % 26) + 65) + res
                index //= 26
            return res
            
        for i, item in enumerate(letters):
            item.setPlainText(get_letter_str(i))

    def save_image(self):
        if not self.current_image_path: return
        self.status_label.setText("Salvando arquivo de alta resolução...")
        
        # To maintain the 100% original pixel quality safely, we use PIL to recreate the image
        # based on the final coordinates in the GraphicsScene.
        # This prevents rendering issues entirely if QPixmap changes things.
        
        try:
            img = Image.open(self.current_image_path)
            
            # Convert to RGB (JPEG requirement) and handle RGBA transparency
            if img.mode == 'RGBA':
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                
            draw = ImageDraw.Draw(img)
            
            # Try to load a generic system TrueType font for Pillow
            try:
                font = ImageFont.truetype("Arial.ttf", self.base_font_size)
            except IOError:
                try:
                    font = ImageFont.truetype("Helvetica.ttc", self.base_font_size)
                except IOError:
                    font = ImageFont.load_default()
                    
            outline_color = "black"
            fill_color = "white"
            outline_width = max(1, self.base_font_size // 15)
            
            # Get all interactive letters and draw them via PIL
            for item in self.view.scene.items():
                if isinstance(item, QInteractiveLetter):
                    text = item.toPlainText()
                    pos = item.scenePos()
                    x_pos = int(pos.x())
                    y_pos = int(pos.y())
                    
                    # Draw outline
                    for dx in range(-outline_width, outline_width+1):
                        for dy in range(-outline_width, outline_width+1):
                            if dx != 0 or dy != 0:
                                draw.text((x_pos+dx, y_pos+dy), text, font=font, fill=outline_color)
                    
                    # Draw main text
                    draw.text((x_pos, y_pos), text, font=font, fill=fill_color)
            
            # Save the image
            original_path = Path(self.current_image_path)
            new_filename = f"{original_path.stem}_.jpg" 
            save_path = original_path.parent / new_filename
            
            # Save preserving quality.
            save_kwargs = {'quality': 100, 'subsampling': 0}
            img.save(save_path, **save_kwargs)
            
            QMessageBox.information(self, "Sucesso", f"Imagem salva com sucesso!\n{save_path}")
            self.status_label.setText(f"Salvo: {new_filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar: {str(e)}")
            self.status_label.setText("Erro durante o salvamento.")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
