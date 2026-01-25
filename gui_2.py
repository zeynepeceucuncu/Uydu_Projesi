# gui.py

import os
import sys
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget, QLineEdit, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QMessageBox)
from PyQt5.QtGui import QPixmap
from sentinal2 import * 


class DataWorker(QThread):
    status_signal = pyqtSignal(str) 
    finished_signal = pyqtSignal()

    def __init__(self, start_date, end_date, cloud_rate, lat, lon):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.cloud_rate = cloud_rate
        self.lat = lat
        self.lon = lon

    def run(self):
        try:
            # Callback fonksiyonunu sinyal mekanizmasına bağlıyoruz
            obj = CopernicusDataCatalog(
                self.start_date, self.end_date, self.cloud_rate, 
                self.lat, self.lon, 
                status_callback=self.status_signal.emit 
            )
            
            self.status_signal.emit("Sorgu başlatılıyor...")
            obj.post_request()
            
            if hasattr(obj, 'df') and not obj.df.empty:
                self.status_signal.emit("Token alınıyor...")
                obj.tokenization()
                self.status_signal.emit("Veri erişimi başlıyor...")
                obj.access_the_data()
            else:
                self.status_signal.emit("Veri bulunamadı veya DataFrame boş.")
                
        except Exception as e:
            self.status_signal.emit(f"KRİTİK HATA: {str(e)}")
        finally:
            self.finished_signal.emit()

class DataInputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    
        self.startdate = QLabel("Start Date")
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("YYYY-MM-DD (Örn: 2023-01-01)") # İpucu eklendi
        
        self.enddate = QLabel("End Date")
        self.input2 = QLineEdit(self)
        self.input2.setPlaceholderText("YYYY-MM-DD (Örn: 2023-01-30)") # İpucu eklendi

        self.cloudrate = QLabel("Cloud Rate")
        self.input3 = QLineEdit(self)
        self.input3.setPlaceholderText("0-100 arası sayı (Örn: 10)") # İpucu eklendi


        self.latitude = QLabel("Latitude")
        self.input4 = QLineEdit(self)
        self.input4.setPlaceholderText("Örn: 41.0082") # İpucu eklendi
        
        self.longitude = QLabel("Longitude")
        self.input5 = QLineEdit(self)
        self.input5.setPlaceholderText("Örn: 28.9784") # İpucu eklendi

        self.button = QPushButton("Take Data Set", self)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(450)
        
        self.gallery_content = QWidget()
        self.scroll_area.setWidget(self.gallery_content)
        
        self.gallery_layout = QHBoxLayout(self.gallery_content)
        self.gallery_layout.setAlignment(Qt.AlignLeft)

        self.status_label = QLabel("Durum: Veri bekleniyor...", self)
        self.status_label.setAlignment(Qt.AlignCenter)


        main_layout = QVBoxLayout()
        main_layout.addWidget(self.startdate)
        main_layout.addWidget(self.input)
        main_layout.addWidget(self.enddate)
        main_layout.addWidget(self.input2)
        main_layout.addWidget(self.cloudrate)
        main_layout.addWidget(self.input3)
        main_layout.addWidget(self.latitude)
        main_layout.addWidget(self.input4)
        main_layout.addWidget(self.longitude)
        main_layout.addWidget(self.input5) 
        main_layout.addWidget(self.button)
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)
        self.button.clicked.connect(self.start_processing)


    def update_gui_message(self, message):
        message = str(message).strip()
        if message.startswith("IMAGE_READY:"):
            try:
                image_path = message.split(":", 1)[1].strip()
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    new_image_label = QLabel()
                    new_image_label.setFixedSize(400, 400)
                    new_image_label.setStyleSheet("border: 2px solid #333;")
                    new_image_label.setPixmap(pixmap.scaled(
                        400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    ))
                    self.gallery_layout.addWidget(new_image_label)
                    self.status_label.setText(f"Görsel Eklendi: {os.path.basename(image_path)}")
                    self.status_label.setStyleSheet("color: green;")
            except Exception as e:
                print(e)
   
        else:
            self.status_label.setText(f"Durum: {message}")
            self.status_label.setStyleSheet("color: blue;")

    def start_processing(self):
        start_date = self.input.text().strip()
        end_date = self.input2.text().strip()
        cloud_rate = self.input3.text().strip() 
        lat = self.input4.text().strip()
        lon = self.input5.text().strip()

        if not all([start_date, end_date, cloud_rate, lat, lon]):
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen tüm alanları doldurunuz!")
            return

        self.clear_gallery()
        self.button.setEnabled(False)
        self.button.setText("İşleniyor...")

        self.worker = DataWorker(start_date, end_date, cloud_rate, lat, lon)
        self.worker.status_signal.connect(self.update_gui_message)
        self.worker.finished_signal.connect(self.on_process_finished)
        self.worker.start()

    def on_process_finished(self):
        self.button.setEnabled(True)
        self.button.setText("Take Data Set")
        self.update_gui_message("İşlem Tamamlandı.")

    def clear_gallery(self):
        while self.gallery_layout.count():
            child = self.gallery_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Copernicus Sentinel-2 Gallery")
        self.dataWidget = DataInputWidget(self)
        self.setCentralWidget(self.dataWidget)
        self.setFixedSize(900, 900) 

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()