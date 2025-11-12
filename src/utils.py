import cv2
import pickle
import numpy as np
from pathlib import Path
from typing import List


class EstacionaClassifier:
    def __init__(self, posicoes_path: str | Path, rect_width: int = 107, rect_height: int = 48):
        self.rect_width = rect_width
        self.rect_height = rect_height
        self.posicao_carro_vaga = self._ler_posicoes(posicoes_path)

    def _ler_posicoes(self, caminho: str | Path) -> List:
        try:
            with open(caminho, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Erro: {e}\nOcorreu um erro ao ler o arquivo de posições do estacionamento.")
            return []

    def implement_process(self, image: np.ndarray) -> np.ndarray:
        kernel = np.ones((3, 3), np.uint8)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 1)
        thr = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16
        )
        thr = cv2.medianBlur(thr, 5)
        dil = cv2.dilate(thr, kernel, iterations=1)
        return dil
