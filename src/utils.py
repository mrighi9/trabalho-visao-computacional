from pathlib import Path
from typing import List
import pickle
import cv2
import numpy as np


class EstacionaClassifier:
    def __init__(self, posicoes_path: str | Path, rect_width: int = 107, rect_height: int = 48):
        self.rect_width = rect_width
        self.rect_height = rect_height
        self.posicao_carro_vaga = self._ler_posicoes(posicoes_path)
        self.posicao_carro_vaga_full = self._ler_posicoes_full(posicoes_path)
        self.posicao_carro_vaga_path = posicoes_path
        
        # parametros adaptativos
        self.threshold_base = 900
        self.threshold_margin = 0.15
        self.motion_history = {}
        self.empty_reference = {}
    
    def _ler_posicoes(self, caminho: str | Path) -> List:
        try:
            with open(caminho, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Erro: {e}\nOcorreu um erro ao ler o arquivo de posições.")
            return []
    
    def _ler_posicoes_full(self, caminho: str | Path) -> List:
        """Lê arquivo completo com dimensões e ângulos"""
        try:
            full_path = str(caminho).replace("estacionamentoPos", "estacionamentoPos_full")
            with open(full_path, "rb") as f:
                spots = pickle.load(f)
                # garantir 5 elementos
                return [(*spot, 0) if len(spot) == 4 else spot for spot in spots]
        except:
            return [(x, y, self.rect_width, self.rect_height, 0) for x, y in self.posicao_carro_vaga]
    
    def _get_rotated_crop(self, image: np.ndarray, x: int, y: int, w: int, h: int, angle: float) -> np.ndarray:
        """Extrai região rotacionada"""
        if angle == 0:
            return image[y:y+h, x:x+w]
        
        cx, cy = x + w // 2, y + h // 2
        M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
        
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        M[0, 2] += (new_w / 2) - cx
        M[1, 2] += (new_h / 2) - cy
        
        rotated = cv2.warpAffine(image, M, (new_w, new_h))
        
        start_x = (new_w - w) // 2
        start_y = (new_h - h) // 2
        
        return rotated[start_y:start_y+h, start_x:start_x+w]
    
    def _calculate_dynamic_threshold(self, crop: np.ndarray, spot_index: int) -> int:
        mean_intensity = np.mean(crop)
        std_intensity = np.std(crop)
        non_zero_count = cv2.countNonZero(crop)
        
        if spot_index in self.empty_reference:
            ref_count = self.empty_reference[spot_index]
            dynamic_threshold = ref_count * (1 + self.threshold_margin)
        else:
            dynamic_threshold = self.threshold_base * (1 + std_intensity / 100)
        
        if spot_index not in self.motion_history:
            self.motion_history[spot_index] = []
        
        self.motion_history[spot_index].append(non_zero_count)
        
        if len(self.motion_history[spot_index]) > 30:
            self.motion_history[spot_index].pop(0)
        
        return int(dynamic_threshold)
    
    def _detect_edges_features(self, crop: np.ndarray) -> float:
        """Densidade de bordas"""
        edges = cv2.Canny(crop, 50, 150)
        edge_density = np.sum(edges) / (crop.shape[0] * crop.shape[1])
        return edge_density
    
    def _analyze_texture(self, crop_gray: np.ndarray) -> float:
        """Análise de textura"""
        kernel_size = 5
        kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
        
        local_mean = cv2.filter2D(crop_gray.astype(np.float32), -1, kernel)
        local_var = cv2.filter2D((crop_gray.astype(np.float32) - local_mean) ** 2, -1, kernel)
        texture_score = np.mean(local_var)
        
        return texture_score
    
    def classificar(self, image: np.ndarray, imagem_proce: np.ndarray, threshold: int = 900) -> np.ndarray:
        """Classifica vagas com suporte a rotação"""
        EstacionamentoVazio = 0
        
        for index, spot in enumerate(self.posicao_carro_vaga_full):
            if len(spot) == 5:
                x, y, w, h, angle = spot
            elif len(spot) == 4:
                x, y, w, h = spot
                angle = 0
            elif len(spot) == 2:
                x, y = spot
                w, h, angle = self.rect_width, self.rect_height, 0
            else:
                continue
            
            # extrair região 
            crop = self._get_rotated_crop(imagem_proce, x, y, w, h, angle)
            crop_color = self._get_rotated_crop(image, x, y, w, h, angle)
            
            if crop.size == 0 or crop_color.size == 0:
                continue
            
            crop_gray = cv2.cvtColor(crop_color, cv2.COLOR_BGR2GRAY)
            
            # analise multi-criterio
            count = cv2.countNonZero(crop)
            dynamic_threshold = self._calculate_dynamic_threshold(crop, index)
            edge_density = self._detect_edges_features(crop_gray)
            texture_score = self._analyze_texture(crop_gray)
            color_std = np.std(crop_color)
            
            score = 0
            if count < dynamic_threshold:
                score += 0.4
            if edge_density < 0.15:
                score += 0.3
            if texture_score < 150:
                score += 0.2
            if color_std < 30:
                score += 0.1
            
            is_empty = score >= 0.5
            
            if is_empty:
                EstacionamentoVazio += 1
                color, thick = (0, 255, 0), 5
                
                if index not in self.empty_reference:
                    self.empty_reference[index] = count
                else:
                    self.empty_reference[index] = int(0.9 * self.empty_reference[index] + 0.1 * count)
            else:
                color, thick = (0, 0, 255), 2
            
            # desenhar retângulo
            if angle == 0:
                cv2.rectangle(image, (x, y), (x + w, y + h), color, thick)
                confidence = int(score * 100)
                cv2.putText(image, f"{confidence}%", (x + 5, y + 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            else:
                # desenhar retângulo rotacionado
                cx, cy = x + w // 2, y + h // 2
                rect = ((cx, cy), (w, h), angle)
                box = cv2.boxPoints(rect)
                box = np.int32(box)
                cv2.drawContours(image, [box], 0, color, thick)
                
                confidence = int(score * 100)
                cv2.putText(image, f"{confidence}%", (int(cx - 15), int(cy)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        cv2.rectangle(image, (45, 30), (300, 75), (180, 0, 180), -1)
        ratio_text = f'Livres: {EstacionamentoVazio}/{len(self.posicao_carro_vaga_full)}'
        cv2.putText(image, ratio_text, (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        
        return image
    
    def implement_process(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        blur = cv2.GaussianBlur(gray, (5, 5), 1.5)
        
        thr = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            25, 12
        )
        
        thr = cv2.medianBlur(thr, 5)
        kernel = np.ones((3, 3), np.uint8)
        thr = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=1)
        dil = cv2.dilate(thr, kernel, iterations=1)
        
        return dil


class Coordinate_denoter():
    def __init__(self, rect_width: int = 107, rect_height: int = 48, posicoes_path: str = "src/estacionamentoPos"):
        self.rect_width = rect_width
        self.rect_height = rect_height
        self.posicao_carro_vaga = list()
        self.posicao_carro_vaga_path = posicoes_path

    def ler_posicoes(self) -> list:
        try:
            self.posicao_carro_vaga = pickle.load(open(self.posicao_carro_vaga_path, 'rb'))
        except Exception as e:
            print(f"Error: {e}\n Falha ao ler posições.")

        return self.posicao_carro_vaga
    
    def mouseClick(self, events: int, x: int, y: int, flags: int, params: int):
        if events == cv2.EVENT_LBUTTONDOWN:
            self.posicao_carro_vaga.append((x, y))
        
        if events == cv2.EVENT_MBUTTONDOWN:
            for index, pos in enumerate(self.posicao_carro_vaga):
                x1, y1 = pos
                
                is_x_in_range = x1 <= x <= x1 + self.rect_width
                is_y_in_range = y1 <= y <= y1 + self.rect_height
                
                if is_x_in_range and is_y_in_range:
                    self.posicao_carro_vaga.pop(index)
                    break

        with open(self.posicao_carro_vaga_path, 'wb') as f:
            pickle.dump(self.posicao_carro_vaga, f)