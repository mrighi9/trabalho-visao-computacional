import cv2
import numpy as np
import pickle
from src.utils import EstacionaClassifier



def parking():
   

    rect_width, rect_height = 107, 48
    carro_estaciona_posicao = "src/estacionamentoPos"
    video_path = "src/estacionamento.mp4"

    classifier = EstacionaClassifier(carro_estaciona_posicao, rect_width, rect_height)

    cap = cv2.VideoCapture(video_path)
    while True:

        ret, frame = cap.read()

        if not ret:
            break
        
        prosessed_frame = classifier.implement_process(frame)
        
        # call the correct method name and pass the parameter name expected by the class
        denoted_image = classifier.classificar(image=frame, imagem_proce=prosessed_frame)
        
        cv2.imshow("Imagem de estacionamentos desenhada de acordo com as vagas vazias", denoted_image)
        
        k = cv2.waitKey(1)
        if k & 0xFF == ord('q'):
            break
        
        if k & 0xFF == ord('s'):
            cv2.imwrite("output.jpg", denoted_image)

    cap.release()
    cv2.destroyAllWindows()
        


if __name__ == "__main__":
    parking()
