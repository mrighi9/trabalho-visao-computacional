import cv2
from src.utils import Coordinate_denoter

def demostration():
    
    coordinate_generator=Coordinate_denoter()

     
    coordinate_generator.ler_posicoes()

    image_path = "src/exemplo.png"
    rect_width, rect_height = coordinate_generator.rect_width, coordinate_generator.rect_height