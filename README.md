# Detector-Vaga-Estacionamento
- Esse projeto busca identificar vagas de estacionamento vazias utilizando tecnologias de visão computacional.

- Clone o repositório.
```
git clone https://github.com/mrighi9/trabalho-visao-computacional.git
```
- Vá até a pasta copiada.
```
cd trabalho-visao-computacional

```
- Atualize seu pip.
```
pip install --upgrade pip
```
- Instale os requisitos seguindo o comando abaixo.
```
pip install -r requirements.txt
```
- Rode o código com o comando abaixo.

`parking.py`

 
## Exemplo de resultados


<p align="center">
<img src="data/results/example_result.png">





## Definição do Problema
- encontrar as vagas de estacionamento vazias em um estacionamento automaticamente a partir de uma câmera de vigilância.

## Solução
- Extrair as coordenadas do estacionamento da imagem usando o script
- Depois, usar essas coordenadas para processar cada vaga de estacionamento individualmente.
- Implementar técnicas de processamento digital de imagem para descobrir as vagas vazias e ocupadas.
- desenhar os resultados na imagem. 

## Conceitos Utilizados
- Conceitos de OOP (Programação Orientada a Objetos)
- Programação de GUI de Alto Nível com OpenCV
- Processamento Básico de Imagem com OpenCV
- Doc String
- Anotação de Tipos (Type Annotation) do Python



### Controlando o projeto
- rotulando uma vaga
    - você pode clicar com o botão esquerdo do mouse. Isso irá desenhar a sua ordem.
- removendo o rótulo de uma vaga
    - você fará o mesmo acima com o botão do meio do mouse, em vez de clicar com o botão esquerdo.

- Sair do projeto
    - apenas clique no botão q no seu teclado. (Quando a janela do projeto estiver selecionada no seu Sistema Operacional)
- Salvar os resultados
    - apenas clique no botão s no seu teclado. (Quando a janela do projeto estiver selecionada no seu Sistema Operacional)

## Observação 
- estacionamentoPos é um arquivo pickle que armazena as posições das vagas de estacionamento. As áreas das vagas são representadas como retângulos e armazenadas com a coordenada do seu ponto superior esquerdo.
