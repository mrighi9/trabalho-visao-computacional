import cv2
from src.utils import Coordinate_denoter

def demostration():
    
    coordinate_generator=Coordinate_denoter()

     
    coordinate_generator.ler_posicoes()

    image_path = "src/exemplo.png"
    rect_width, rect_height = coordinate_generator.rect_width, coordinate_generator.rect_height
    
    while True:
        
        image =cv2.imread(image_path)

        for pos in coordinate_generator.posicao_carro_vaga: 
            
            start = pos
            end = (pos[0]+rect_width, pos[1]+rect_height)

            cv2.rectangle(image,start,end,(0,0,255),2)
        
        cv2.imshow("Image",image)

        cv2.setMouseCallback("Image",coordinate_generator.mouseClick)

        
        if cv2.waitKey(1) == ord("q"):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    demostration()