import sys
import cv2
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
    """Label que detecta cliques e arrasto do mouse"""
    mouse_pressed = pyqtSignal(QPoint)
    mouse_moved = pyqtSignal(QPoint)
    mouse_released = pyqtSignal(QPoint)
    right_clicked = pyqtSignal(QPoint)
    
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.is_drawing = False
        self.start_point = None
        self.current_point = None
        self.temp_pixmap = None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drawing = True
            self.start_point = event.pos()
            self.mouse_pressed.emit(event.pos())
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(event.pos())
    
    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.current_point = event.pos()
            self.mouse_moved.emit(event.pos())
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            self.mouse_released.emit(event.pos())
            self.start_point = None
            self.current_point = None


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
        self.drawing_start = None
        self.drawing_current = None
        self.parking_spots = []  # Lista de (x, y, width, height)
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
        
        # Título
        title_label = QLabel("🚗 Analisador de Vagas de Estacionamento")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Subtítulo
        self.subtitle_label = QLabel("Faça o upload de um vídeo para começar a análise")
        self.subtitle_label.setFont(QFont("Arial", 12))
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 20px;")
        main_layout.addWidget(self.subtitle_label)
        
        # Scroll area para a imagem
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(500)
        
        # Label clicável para vídeo
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
        self.video_label.mouse_pressed.connect(self.on_mouse_press)
        self.video_label.mouse_moved.connect(self.on_mouse_move)
        self.video_label.mouse_released.connect(self.on_mouse_release)
        self.video_label.right_clicked.connect(self.on_right_click)
        
        scroll_area.setWidget(self.video_label)
        main_layout.addWidget(scroll_area)
        
        # Label de informações
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Arial", 10))
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #27ae60; margin-top: 10px;")
        main_layout.addWidget(self.info_label)
        
        # Barra de progresso
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
        
        # Layout de botões principais
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # Botão de upload
        self.upload_btn = QPushButton("📂 Selecionar Vídeo")
        self.upload_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.upload_btn.setMinimumHeight(50)
        self.upload_btn.setStyleSheet(self._get_button_style("#3498db", "#2980b9", "#21618c"))
        self.upload_btn.clicked.connect(self.upload_video)
        button_layout.addWidget(self.upload_btn)
        
        # Botão de marcar vagas
        self.mark_btn = QPushButton("📍 Marcar Vagas")
        self.mark_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.mark_btn.setMinimumHeight(50)
        self.mark_btn.setEnabled(False)
        self.mark_btn.setStyleSheet(self._get_button_style("#f39c12", "#e67e22", "#d35400"))
        self.mark_btn.clicked.connect(self.toggle_marking_mode)
        button_layout.addWidget(self.mark_btn)
        
        # Botão de iniciar análise
        self.analyze_btn = QPushButton("▶️ Iniciar Análise")
        self.analyze_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.analyze_btn.setMinimumHeight(50)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setStyleSheet(self._get_button_style("#27ae60", "#229954", "#1e8449"))
        self.analyze_btn.clicked.connect(self.start_analysis)
        button_layout.addWidget(self.analyze_btn)
        
        # Botão de parar análise
        self.stop_btn = QPushButton("⏸️ Parar")
        self.stop_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self._get_button_style("#e74c3c", "#c0392b", "#a93226"))
        self.stop_btn.clicked.connect(self.stop_analysis)
        button_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(button_layout)
        
        # Layout de botões de marcação
        self.marking_layout = QHBoxLayout()
        self.marking_layout.setSpacing(10)
        
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
        
        self.help_label = QLabel("💡 Arraste para criar retângulo | Clique DIREITO: remover vaga")
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
            
            # Carregar posições existentes se houver
            try:
                with open("src/estacionamentoPos", 'rb') as f:
                    saved_spots = pickle.load(f)
                    # Converter formato antigo (x, y) para novo (x, y, w, h)
                    self.parking_spots = []
                    for pos in saved_spots:
                        if isinstance(pos, tuple) and len(pos) == 2:
                            self.parking_spots.append((pos[0], pos[1], 107, 48))
                        elif isinstance(pos, tuple) and len(pos) == 4:
                            self.parking_spots.append(pos)
            except:
                self.parking_spots = []
            
            # Carregar primeiro frame
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            if ret:
                self.original_frame = frame
                self.display_frame_with_marks(frame)
            cap.release()
            
            # Verificar se há vagas marcadas
            if len(self.parking_spots) > 0:
                self.analyze_btn.setEnabled(True)
    
    def toggle_marking_mode(self):
        self.is_marking_mode = not self.is_marking_mode
        
        if self.is_marking_mode:
            self.mark_btn.setText("✅ Finalizar Marcação")
            self.mark_btn.setStyleSheet(self._get_button_style("#27ae60", "#229954", "#1e8449"))
            self.upload_btn.setEnabled(False)
            self.analyze_btn.setEnabled(False)
            self.clear_btn.setVisible(True)
            self.save_marks_btn.setVisible(True)
            self.help_label.setVisible(True)
            self.subtitle_label.setText("🖱️ Arraste para marcar as vagas de estacionamento")
        else:
            self.mark_btn.setText("📍 Marcar Vagas")
            self.mark_btn.setStyleSheet(self._get_button_style("#f39c12", "#e67e22", "#d35400"))
            self.upload_btn.setEnabled(True)
            self.clear_btn.setVisible(False)
            self.save_marks_btn.setVisible(False)
            self.help_label.setVisible(False)
            self.subtitle_label.setText("Faça o upload de um vídeo para começar a análise")
            
            if len(self.parking_spots) > 0:
                self.analyze_btn.setEnabled(True)
    
    def on_mouse_press(self, pos: QPoint):
        if not self.is_marking_mode or self.original_frame is None:
            return
        
        # Ajustar coordenadas
        click_x = pos.x() - self.x_offset
        click_y = pos.y() - self.y_offset
        
        if click_x < 0 or click_y < 0 or click_x >= self.scaled_width or click_y >= self.scaled_height:
            return
        
        self.drawing_start = (click_x, click_y)
        self.info_label.setText("🖱️ Arraste para definir o tamanho da vaga...")
    
    def on_mouse_move(self, pos: QPoint):
        if not self.is_marking_mode or self.drawing_start is None or self.original_frame is None:
            return
        
        # Ajustar coordenadas
        click_x = pos.x() - self.x_offset
        click_y = pos.y() - self.y_offset
        
        # Limitar às bordas da imagem
        click_x = max(0, min(click_x, self.scaled_width))
        click_y = max(0, min(click_y, self.scaled_height))
        
        self.drawing_current = (click_x, click_y)
        
        # Redesenhar frame com retângulo temporário
        self.display_frame_with_marks(self.original_frame, temp_rect=True)
    
    def on_mouse_release(self, pos: QPoint):
        if not self.is_marking_mode or self.drawing_start is None or self.original_frame is None:
            return
        
        # Ajustar coordenadas
        click_x = pos.x() - self.x_offset
        click_y = pos.y() - self.y_offset
        
        click_x = max(0, min(click_x, self.scaled_width))
        click_y = max(0, min(click_y, self.scaled_height))
        
        # Converter para coordenadas originais
        x1 = int(self.drawing_start[0] / self.scale_factor)
        y1 = int(self.drawing_start[1] / self.scale_factor)
        x2 = int(click_x / self.scale_factor)
        y2 = int(click_y / self.scale_factor)
        
        # Garantir que x1,y1 seja o canto superior esquerdo
        x = min(x1, x2)
        y = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        # Validar tamanho mínimo
        if width < 10 or height < 10:
            self.info_label.setText("⚠️ Retângulo muito pequeno! Tente novamente.")
        else:
            self.parking_spots.append((x, y, width, height))
            self.info_label.setText(f"✅ Vaga adicionada ({width}x{height})! Total: {len(self.parking_spots)}")
        
        self.drawing_start = None
        self.drawing_current = None
        self.display_frame_with_marks(self.original_frame)
    
    def on_right_click(self, pos: QPoint):
        if not self.is_marking_mode or self.original_frame is None:
            return
        
        # Ajustar coordenadas
        click_x = pos.x() - self.x_offset
        click_y = pos.y() - self.y_offset
        
        if click_x < 0 or click_y < 0 or click_x >= self.scaled_width or click_y >= self.scaled_height:
            return
        
        # Converter para coordenadas originais
        x = int(click_x / self.scale_factor)
        y = int(click_y / self.scale_factor)
        
        # Verificar se clicou em alguma vaga
        removed = False
        for index, (vx, vy, vw, vh) in enumerate(self.parking_spots):
            if vx <= x <= vx + vw and vy <= y <= vy + vh:
                self.parking_spots.pop(index)
                self.info_label.setText(f"❌ Vaga removida! Total: {len(self.parking_spots)}")
                removed = True
                break
        
        if not removed:
            self.info_label.setText("⚠️ Nenhuma vaga encontrada nesta posição")
        
        self.display_frame_with_marks(self.original_frame)
    
    def display_frame_with_marks(self, frame, temp_rect=False):
        """Exibe o frame com as marcações de vagas"""
        display_frame = frame.copy()
        
        # Desenhar vagas salvas
        for (x, y, w, h) in self.parking_spots:
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Desenhar retângulo temporário durante arrasto
        if temp_rect and self.drawing_start and self.drawing_current:
            x1 = int(self.drawing_start[0] / self.scale_factor)
            y1 = int(self.drawing_start[1] / self.scale_factor)
            x2 = int(self.drawing_current[0] / self.scale_factor)
            y2 = int(self.drawing_current[1] / self.scale_factor)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
        
        self.display_frame(display_frame)
    
    def clear_all_marks(self):
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "Deseja realmente limpar todas as marcações?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.parking_spots.clear()
            self.display_frame_with_marks(self.original_frame)
            self.info_label.setText("🗑️ Todas as marcações foram limpas")
    
    def save_marks(self):
        try:
            # Salvar no formato compatível com o sistema existente
            # Usar o centro de cada retângulo como posição
            positions = [(x, y) for x, y, w, h in self.parking_spots]
            
            with open("src/estacionamentoPos", 'wb') as f:
                pickle.dump(positions, f)
            
            # Também salvar o formato completo em outro arquivo
            with open("src/estacionamentoPos_full", 'wb') as f:
                pickle.dump(self.parking_spots, f)
            
            QMessageBox.information(self, "Sucesso", f"✅ {len(self.parking_spots)} vagas salvas com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar marcações:\n{str(e)}")
    
    def start_analysis(self):
        if not self.video_path:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione um vídeo primeiro!")
            return
        
        if len(self.parking_spots) == 0:
            QMessageBox.warning(self, "Aviso", "Marque pelo menos uma vaga antes de iniciar a análise!")
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
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar análise:\n{str(e)}")
    
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
        
        # Obter tamanho disponível na label
        available_width = self.video_label.width()
        available_height = self.video_label.height()
        
        # Calcular dimensões mantendo proporção
        img_ratio = w / h
        label_ratio = available_width / available_height
        
        if img_ratio > label_ratio:
            self.scaled_width = available_width
            self.scaled_height = int(available_width / img_ratio)
        else:
            self.scaled_height = available_height
            self.scaled_width = int(available_height * img_ratio)
        
        # Calcular offsets para centralizar
        self.x_offset = (available_width - self.scaled_width) // 2
        self.y_offset = (available_height - self.scaled_height) // 2
        
        # Calcular fator de escala
        self.scale_factor = self.scaled_width / w
        
        # Redimensionar imagem
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