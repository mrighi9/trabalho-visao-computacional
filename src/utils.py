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
        
    def classificar(self, image:np.ndarray, imagem_proce:np.ndarray,threshold:int=900)->np.ndarray:
        
        EstacionamentoVazio = 0
        for x, y in self.posicao_carro_vaga:
            
           
            col_start, col_stop = x, x + self.rect_width
            row_start, row_stop = y, y + self.rect_height

            
            crop=imagem_proce[row_start:row_stop, col_start:x+col_stop]
            
            
            count=cv2.countNonZero(crop)
            
           
            EstacionamentoVazio, color, thick = [EstacionamentoVazio + 1, (0,255,0), 5] if count<threshold else [EstacionamentoVazio, (0,0,255), 2]
                
            
            start_point, stop_point = (x,y), (x+self.rect_width, y+self.rect_height)
            cv2.rectangle(image, start_point, stop_point, color, thick)
        
        
        
        cv2.rectangle(image,(45,30),(250,75),(180,0,180),-1)

        ratio_text = f'Free: {EstacionamentoVazio}/{len(self.posicao_carro_vaga)}'
        cv2.putText(image,ratio_text,(50,60),cv2.FONT_HERSHEY_SIMPLEX,0.9,(255,255,255),2)
        
        return image    

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
    
class Coordinate_denoter():

    def __init__(self, rect_width:int=107, rect_height:int=48, posicoes_path:pickle="src/estacionamentoPos"):
        self.rect_width = rect_width
        self.rect_height = rect_height
        self.posicoes_path = posicoes_path
        self.posicao_carro_vaga = list()
        
    def ler_posicoes(self)->list:
        
        try:
            self.posicao_carro_vaga = pickle.load(open(self.posicao_carro_vaga_path, 'rb'))
        except Exception as e:
            print(f"Error: {e}\n Falha ao ler o arquivo de posições do estacionamento.")

        return self.posicao_carro_vaga
    def mouseClick(self, events:int, x:int, y:int, flags:int, params:int):

        
        if events==cv2.EVENT_LBUTTONDOWN:
            self.posicao_carro_vaga.append((x,y))
        
        if events==cv2.EVENT_MBUTTONDOWN:

            for index, pos in enumerate(self.posicao_carro_vaga):
                
                x1,y1=pos
                
                is_x_in_range= x1 <= x <= x1+self.rect_width
                is_y_in_range= y1 <= y <= y1+self.rect_height

                if is_x_in_range and is_y_in_range:
                    self.posicao_carro_vaga.pop(index)

        with open(self.posicao_carro_vaga_path,'wb') as f:
            pickle.dump(self.posicao_carro_vaga,f)
        