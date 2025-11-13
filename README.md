# 🚗 Detector de Vagas de Estacionamento

Sistema inteligente de análise de vagas de estacionamento utilizando **Visão Computacional** e **Interface Gráfica PyQt5**.

## 📥 Download

**Executável Windows (recomendado):**  
👉 [Baixar DetectordeVagasEstacionamento.exe](https://drive.google.com/drive/folders/17L-TvSkp7kA-_OLXtAXnhL-at4PqGOcg?usp=drive_link)

**Vídeo Demonstração:**  
🎥 [Assistir no Google Drive](https://drive.google.com/drive/folders/17L-TvSkp7kA-_OLXtAXnhL-at4PqGOcg?usp=drive_link)

---

## 🚀 Instalação e Uso

### Opção 1: Executável Windows

1. Baixe o arquivo `.exe` do link acima
2. Execute `DetectordeVagasEstacionamento.exe`

---

### **Opção 2: Rodar o Código Fonte**

#### **1. Clone o repositório:**
```bash
git clone https://github.com/mrighi9/trabalho-visao-computacional.git
cd trabalho-visao-computacional
```

#### **2. Instale as dependências:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### **3. Execute a interface gráfica:**
```bash
python main_interface.py
```

### **Opção 3: Compilar Você Mesmo**

```bash
pip install pyinstaller
pyinstaller DetectordeVagasEstacionamento.spec
```

O executável estará em `dist/DetectordeVagasEstacionamento.exe`

---

## 🎯 Como Usar a Interface Gráfica

### **1. Selecionar Vídeo**
- Clique em **"📂 Selecionar Vídeo"**
- Escolha um arquivo `.mp4`, `.avi`, `.mov` ou `.mkv`

### **2. Marcar Vagas**
- Clique em **"📍 Marcar Vagas"**
- **Clique nos 4 cantos** de cada vaga de estacionamento
- Para remover uma vaga: **clique direito** sobre ela
- Para desfazer o último ponto: **botão "↶ Desfazer"**

### **3. Salvar Marcações**
- Clique em **"💾 Salvar Marcações"**
- As vagas ficam salvas em arquivos pickle

### **4. Iniciar Análise**
- Clique em **"▶️ Iniciar Análise"**
- O sistema detecta automaticamente vagas livres/ocupadas
- Para parar: **botão "⏸️ Parar"**

---

## 🔧 Tecnologias Utilizadas

| Tecnologia | Versão | Finalidade |
|-----------|--------|------------|
| **Python** | 3.12+ | Linguagem principal |
| **OpenCV** | 4.8+ | Processamento de imagem |
| **PyQt5** | 5.15+ | Interface gráfica |
| **NumPy** | 1.24+ | Operações numéricas |
| **PyInstaller** | 6.10+ | Geração do executável |

---

## 📁 Estrutura do Projeto

```
trabalho-visao-computacional/
├── src/
│   ├── interface.py              # Interface gráfica PyQt5
│   ├── utils.py                  # Classificador e processamento
│   ├── estacionamentoPos         # Dados de vagas (pickle)
│   ├── estacionamentoPos_4points # Vagas com 4 pontos
│   └── estacionamentoPos_full    # Vagas completas 
├── main_interface.py             # Interface Gráfica
├── parking.py                    # Versão CLI 
├── gerador_coordenada_estacionamento.py # Marcação manual 
├── requirements.txt              # Dependências Python
├── DetectordeVagasEstacionamento.spec # Configuração PyInstaller
└── README.md                     # Este arquivo
```

---

## 🧠 Definição do Problema

Identificar automaticamente vagas de estacionamento **livres** e **ocupadas** a partir de:
- Câmeras de vigilância estáticas
- Vídeos pré-gravados
- Imagens fixas

---

## 💡 Solução Implementada

### **1. Marcação de Vagas**
- Interface gráfica para clicar nos 4 cantos de cada vaga
- Salva coordenadas em arquivos pickle

### **2. Processamento de Imagem**
```python
# Técnicas aplicadas:
1. Conversão para escala de cinza
2. Equalização de histograma
3. Threshold adaptativo (Gaussian)
4. Filtro mediano (redução de ruído)
5. Operações morfológicas (fechamento)
6. Dilatação (realce de contornos)
```

### **3. Classificação Inteligente**
- **Threshold Dinâmico:** Ajusta-se por vaga
- **Densidade de Bordas:** Carros têm mais bordas
- **Análise de Textura:** Detecta padrões de textura
- **Variação de Cor:** Carros têm maior variação
- **Score Combinado:** Média ponderada das métricas

### **4. Visualização**
- Retângulos verdes: Vagas livres
- Retângulos vermelhos: Vagas ocupadas
- Confiança: Percentual de certeza da detecção
- Contador: Total de vagas disponíveis

---

## 🎮 Controles (Versão CLI)

| Tecla | Ação |
|-------|------|
| **Botão Esquerdo** | Adicionar vaga |
| **Botão Direito** | Remover vaga |
| **Q** | Sair do programa |
| **S** | Salvar imagem resultado |

---