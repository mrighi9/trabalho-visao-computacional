import sys
import cv2
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QFileDialog, 
    QMessageBox, QProgressBar, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint, QRect
from PyQt5.QtGui import QFont, QPixmap, QImage, QPainter, QPen, QColor
from src.utils import EstacionaClassifier, Coordinate_denoter
import pickle


class ClickableLabel(QLabel):
    """Label que detecta cliques do mouse"""
    mouse_clicked = pyqtSignal(QPoint)
    right_clicked = pyqtSignal(QPoint)
    
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_clicked.emit(event.pos())
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(event.pos())


class VideoProcessor(QThread):
    """Thread para processar o vídeo sem travar a interface"""
    frame_ready = pyqtSignal(object)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, video_path: str, classifier: EstacionaClassifier):
        super().__init__()
        self.video_path = video_path
        self.classifier = classifier
        self.is_running = True
        
    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        
        while self.is_running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                continue
            
            processed_frame = self.classifier.implement_process(frame)
            result_frame = self.classifier.classificar(frame, processed_frame)
            
            self.frame_ready.emit(result_frame)
            
            frame_count += 1
            progress = int((frame_count / total_frames) * 100)
            self.progress_update.emit(progress)
            
            cv2.waitKey(10)
        
        cap.release()
        self.finished.emit()
    
    def stop(self):
        self.is_running = False


class ParkingAnalyzerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_path = None
        self.classifier = None
        self.video_thread = None
        self.coordinate_denoter = Coordinate_denoter()
        self.original_frame = None
        self.is_marking_mode = False
        self.scale_factor = 1.0
        self.x_offset = 0
        self.y_offset = 0
        self.scaled_width = 0
        self.scaled_height = 0
        
        # Modo de 4 pontos
        self.current_points = []  # Lista de pontos clicados (máximo 4)
        self.parking_spots = []   # Lista de vagas salvas (cada uma com 4 pontos)
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Sistema de Análise de Estacionamento")
        self.setGeometry(100, 100, 1000, 800)
        self.setStyleSheet("background-color: #f0f0f0;")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # titulo
        title_label = QLabel("🚗 Analisador de Vagas de Estacionamento")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # subtitulo
        self.subtitle_label = QLabel("Faça o upload de um vídeo para começar a análise")
        self.subtitle_label.setFont(QFont("Arial", 12))
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 20px;")
        main_layout.addWidget(self.subtitle_label)
        
        # scroll area para a imagem
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(500)
        
        # label clicável para vídeo
        self.video_label = ClickableLabel()
        self.video_label.setMinimumSize(800, 450)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #34495e;
                border: 3px dashed #95a5a6;
                border-radius: 10px;
                color: white;
                font-size: 16px;
            }
        """)
        self.video_label.setText("📹 Nenhum vídeo carregado")
        self.video_label.mouse_clicked.connect(self.on_mouse_click)
        self.video_label.right_clicked.connect(self.on_right_click)
        
        scroll_area.setWidget(self.video_label)
        main_layout.addWidget(scroll_area)
        
        # label de informações
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Arial", 10))
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #27ae60; margin-top: 10px;")
        main_layout.addWidget(self.info_label)
        
        # barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # layout de botões principais
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # botão de upload
        self.upload_btn = QPushButton("📂 Selecionar Vídeo")
        self.upload_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.upload_btn.setMinimumHeight(50)
        self.upload_btn.setStyleSheet(self._get_button_style("#3498db", "#2980b9", "#21618c"))
        self.upload_btn.clicked.connect(self.upload_video)
        button_layout.addWidget(self.upload_btn)
        
        # botão de marcar vagas
        self.mark_btn = QPushButton("📍 Marcar Vagas")
        self.mark_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.mark_btn.setMinimumHeight(50)
        self.mark_btn.setEnabled(False)
        self.mark_btn.setStyleSheet(self._get_button_style("#f39c12", "#e67e22", "#d35400"))
        self.mark_btn.clicked.connect(self.toggle_marking_mode)
        button_layout.addWidget(self.mark_btn)
        
        # botão de iniciar análise
        self.analyze_btn = QPushButton("▶️ Iniciar Análise")
        self.analyze_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.analyze_btn.setMinimumHeight(50)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setStyleSheet(self._get_button_style("#27ae60", "#229954", "#1e8449"))
        self.analyze_btn.clicked.connect(self.start_analysis)
        button_layout.addWidget(self.analyze_btn)
        
        # botão de parar análise
        self.stop_btn = QPushButton("⏸️ Parar")
        self.stop_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self._get_button_style("#e74c3c", "#c0392b", "#a93226"))
        self.stop_btn.clicked.connect(self.stop_analysis)
        button_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(button_layout)
        
        # layout de botões de marcação
        self.marking_layout = QHBoxLayout()
        self.marking_layout.setSpacing(10)
        
        self.undo_btn = QPushButton("↶ Desfazer Ponto")
        self.undo_btn.setFont(QFont("Arial", 10))
        self.undo_btn.setMinimumHeight(40)
        self.undo_btn.setVisible(False)
        self.undo_btn.setStyleSheet(self._get_button_style("#f39c12", "#e67e22", "#d35400"))
        self.undo_btn.clicked.connect(self.undo_point)
        self.marking_layout.addWidget(self.undo_btn)
        
        self.clear_btn = QPushButton("🗑️ Limpar Todas")
        self.clear_btn.setFont(QFont("Arial", 10))
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.setVisible(False)
        self.clear_btn.setStyleSheet(self._get_button_style("#e74c3c", "#c0392b", "#a93226"))
        self.clear_btn.clicked.connect(self.clear_all_marks)
        self.marking_layout.addWidget(self.clear_btn)
        
        self.save_marks_btn = QPushButton("💾 Salvar Marcações")
        self.save_marks_btn.setFont(QFont("Arial", 10))
        self.save_marks_btn.setMinimumHeight(40)
        self.save_marks_btn.setVisible(False)
        self.save_marks_btn.setStyleSheet(self._get_button_style("#27ae60", "#229954", "#1e8449"))
        self.save_marks_btn.clicked.connect(self.save_marks)
        self.marking_layout.addWidget(self.save_marks_btn)
        
        self.help_label = QLabel("💡 Clique nos 4 cantos da vaga | Clique DIREITO para remover")
        self.help_label.setFont(QFont("Arial", 9))
        self.help_label.setAlignment(Qt.AlignCenter)
        self.help_label.setStyleSheet("color: #7f8c8d;")
        self.help_label.setVisible(False)
        self.marking_layout.addWidget(self.help_label)
        
        main_layout.addLayout(self.marking_layout)
        
        central_widget.setLayout(main_layout)
    
    def _get_button_style(self, normal, hover, pressed):
        return f"""
            QPushButton {{
                background-color: {normal};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
            QPushButton:disabled {{
                background-color: #95a5a6;
            }}
        """
    
    def on_mouse_click(self, pos: QPoint):
        """Adiciona ponto ao clicar"""
        if not self.is_marking_mode or self.original_frame is None:
            return
        
        click_x = pos.x() - self.x_offset
        click_y = pos.y() - self.y_offset
        
        if click_x < 0 or click_y < 0 or click_x >= self.scaled_width or click_y >= self.scaled_height:
            return
        
        # converter para coordenadas originais
        x = int(click_x / self.scale_factor)
        y = int(click_y / self.scale_factor)
        
        # adicionar ponto
        self.current_points.append((x, y))
        
        # atualizar info
        if len(self.current_points) < 4:
            self.info_label.setText(f"📍 Ponto {len(self.current_points)}/4 marcado")
        else:
            # 4 pontos completos - criar vaga
            self.parking_spots.append(self.current_points.copy())
            self.info_label.setText(f"✅ Vaga {len(self.parking_spots)} adicionada!")
            self.current_points.clear()
        
        self.display_frame_with_marks(self.original_frame)
    
    def undo_point(self):
        """Remove o último ponto"""
        if len(self.current_points) > 0:
            self.current_points.pop()
            self.info_label.setText(f"↶ Ponto removido | {len(self.current_points)}/4")
            self.display_frame_with_marks(self.original_frame)
        else:
            self.info_label.setText("⚠️ Nenhum ponto para desfazer")
    
    def on_right_click(self, pos: QPoint):
        """Remove vaga ao clicar com botão direito"""
        if not self.is_marking_mode or self.original_frame is None:
            return
        
        click_x = pos.x() - self.x_offset
        click_y = pos.y() - self.y_offset
        
        if click_x < 0 or click_y < 0:
            return
        
        x = int(click_x / self.scale_factor)
        y = int(click_y / self.scale_factor)
        point = (x, y)
        
        # verificar qual vaga contém o ponto clicado
        removed = False
        for index, spot_points in enumerate(self.parking_spots):
            if self._point_in_polygon(point, spot_points):
                self.parking_spots.pop(index)
                removed = True
                break
        
        if removed:
            self.info_label.setText(f"❌ Vaga removida! Total: {len(self.parking_spots)}")
        else:
            self.info_label.setText("⚠️ Nenhuma vaga aqui")
        
        self.display_frame_with_marks(self.original_frame)
    
    def _point_in_polygon(self, point, polygon):
        """Verifica se ponto está dentro do poligono"""
        x, y = point
        points = np.array(polygon, dtype=np.int32)
        result = cv2.pointPolygonTest(points, (float(x), float(y)), False)
        return result >= 0
    
    def _calculate_rect_from_points(self, points):
        """Calcula retangulo rotacionado a partir de 4 pontos"""
        # convertre para numpy array
        pts = np.array(points, dtype=np.float32)
        
        # calcular retângulo mínimo rotacionado
        rect = cv2.minAreaRect(pts)
        
        return rect
    
    def display_frame_with_marks(self, frame):
        """Exibe frame com marcações"""
        display_frame = frame.copy()
        
        # desenhar vagas salvas 
        for spot_points in self.parking_spots:
            pts = np.array(spot_points, dtype=np.int32)
            cv2.polylines(display_frame, [pts], True, (0, 255, 0), 2)
            
            # desenhar círculos nos cantos
            for pt in spot_points:
                cv2.circle(display_frame, pt, 5, (0, 255, 0), -1)
        
        # desenhar pontos atuais 
        for i, pt in enumerate(self.current_points):
            cv2.circle(display_frame, pt, 5, (0, 255, 255), -1)
            cv2.putText(display_frame, str(i+1), (pt[0]+10, pt[1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # desenhar linhas conectando pontos atuais
        if len(self.current_points) > 1:
            pts = np.array(self.current_points, dtype=np.int32)
            cv2.polylines(display_frame, [pts], False, (255, 255, 0), 2)
        
        self.display_frame(display_frame)
    
    def upload_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Vídeo",
            "",
            "Vídeos (*.mp4 *.avi *.mov *.mkv);;Todos os Arquivos (*.*)"
        )
        
        if file_path:
            self.video_path = file_path
            self.info_label.setText(f"✅ Vídeo carregado: {Path(file_path).name}")
            self.mark_btn.setEnabled(True)
            
            # carregar posições existentes
            try:
                with open("src/estacionamentoPos_4points", 'rb') as f:
                    self.parking_spots = pickle.load(f)
            except:
                self.parking_spots = []
            
            # carregar primeiro frame
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            if ret:
                self.original_frame = frame
                self.display_frame_with_marks(frame)
            cap.release()
            
            if len(self.parking_spots) > 0:
                self.analyze_btn.setEnabled(True)
    
    def toggle_marking_mode(self):
        self.is_marking_mode = not self.is_marking_mode
        
        if self.is_marking_mode:
            self.mark_btn.setText("✅ Finalizar Marcação")
            self.mark_btn.setStyleSheet(self._get_button_style("#27ae60", "#229954", "#1e8449"))
            self.upload_btn.setEnabled(False)
            self.analyze_btn.setEnabled(False)
            self.undo_btn.setVisible(True)
            self.clear_btn.setVisible(True)
            self.save_marks_btn.setVisible(True)
            self.help_label.setVisible(True)
            self.subtitle_label.setText("🖱️ Clique nos 4 cantos da vaga")
            self.current_points.clear()
        else:
            self.mark_btn.setText("📍 Marcar Vagas")
            self.mark_btn.setStyleSheet(self._get_button_style("#f39c12", "#e67e22", "#d35400"))
            self.upload_btn.setEnabled(True)
            self.undo_btn.setVisible(False)
            self.clear_btn.setVisible(False)
            self.save_marks_btn.setVisible(False)
            self.help_label.setVisible(False)
            self.subtitle_label.setText("Faça o upload de um vídeo para começar a análise")
            self.current_points.clear()
            
            if len(self.parking_spots) > 0:
                self.analyze_btn.setEnabled(True)
    
    def clear_all_marks(self):
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "Deseja realmente limpar todas as marcações?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.parking_spots.clear()
            self.current_points.clear()
            self.display_frame_with_marks(self.original_frame)
            self.info_label.setText("🗑️ Todas as marcações limpas")
    
    def save_marks(self):
        try:
            # salvar formato de 4 pontos
            with open("src/estacionamentoPos_4points", 'wb') as f:
                pickle.dump(self.parking_spots, f)
            
            # converter para formato compatível
            converted_spots = []
            for spot_points in self.parking_spots:
                rect = self._calculate_rect_from_points(spot_points)
                (cx, cy), (w, h), angle = rect
                x = int(cx - w/2)
                y = int(cy - h/2)
                converted_spots.append((x, y, int(w), int(h), angle))
            
            # salvar formato completo
            with open("src/estacionamentoPos_full", 'wb') as f:
                pickle.dump(converted_spots, f)
            
            # formato compatível 
            positions = [(x, y) for x, y, w, h, angle in converted_spots]
            with open("src/estacionamentoPos", 'wb') as f:
                pickle.dump(positions, f)
            
            QMessageBox.information(self, "Sucesso", f"✅ {len(self.parking_spots)} vagas salvas!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar:\n{str(e)}")
    
    def start_analysis(self):
        if not self.video_path:
            QMessageBox.warning(self, "Aviso", "Selecione um vídeo primeiro!")
            return
        
        if len(self.parking_spots) == 0:
            QMessageBox.warning(self, "Aviso", "Marque pelo menos uma vaga!")
            return
        
        posicoes_path = "src/estacionamentoPos"
        
        try:
            self.classifier = EstacionaClassifier(posicoes_path)
            
            self.video_thread = VideoProcessor(self.video_path, self.classifier)
            self.video_thread.frame_ready.connect(self.display_frame)
            self.video_thread.progress_update.connect(self.update_progress)
            self.video_thread.finished.connect(self.analysis_finished)
            self.video_thread.start()
            
            self.upload_btn.setEnabled(False)
            self.mark_btn.setEnabled(False)
            self.analyze_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.info_label.setText("🔄 Processando vídeo...")
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar:\n{str(e)}")
    
    def stop_analysis(self):
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread.wait()
            self.analysis_finished()
    
    def display_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        available_width = self.video_label.width()
        available_height = self.video_label.height()
        
        img_ratio = w / h
        label_ratio = available_width / available_height
        
        if img_ratio > label_ratio:
            self.scaled_width = available_width
            self.scaled_height = int(available_width / img_ratio)
        else:
            self.scaled_height = available_height
            self.scaled_width = int(available_height * img_ratio)
        
        self.x_offset = (available_width - self.scaled_width) // 2
        self.y_offset = (available_height - self.scaled_height) // 2
        
        self.scale_factor = self.scaled_width / w
        
        scaled_pixmap = pixmap.scaled(
            self.scaled_width,
            self.scaled_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.video_label.setPixmap(scaled_pixmap)
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def analysis_finished(self):
        self.upload_btn.setEnabled(True)
        self.mark_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.info_label.setText("✅ Análise concluída!")


def main():
    app = QApplication(sys.argv)
    window = ParkingAnalyzerUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()