# appPianoBr 🎹

Ideia surgiu depois de ver um app gringo no TikTok que faz exatamente isso: pega um vídeo de piano e transforma em "notas caindo" (tipo Synthesia), ótimo pra quem tá aprendendo a tocar de ouvido. Só que o treco é pago, e eu tenho um PC forte parado, então resolvi tentar fazer minha própria versão, em PT-BR, rodando local.

**Ideia por trás:**
Tenho uns amigos aprendendo piano, e essas notas caindo ajudam demais a visualizar o que tocar. A ideia é usar isso pra mim e pra galera de graça, sem depender de assinatura de app gringo. Se rolar de evoluir pra algo mais robusto no futuro (quem sabe até virar um app de verdade, pago em reais pra galera BR), show, mas por enquanto é projeto pessoal mesmo, aprendendo na prática.

## Como funciona (por enquanto)

O processo é em duas etapas:

1. **Áudio/vídeo → MIDI**: pega um vídeo ou áudio de piano solo e transcreve pra um arquivo `.mid`, identificando as notas tocadas
2. **MIDI → vídeo de notas caindo**: pega esse `.mid` e renderiza um vídeo mostrando as notas caindo no teclado (tipo Synthesia)

Ainda tá na fase 1, rodando local na minha máquina, testando com vídeos de piano solo pra simplificar. O plano é ir evoluindo aos poucos: primeiro deixar o núcleo funcionando bem, depois pensar em interface/site.

## Setup

### 1. Instalar o Python

Baixe o **Python 3.11** (não use 3.13, algumas libs de áudio ainda não têm suporte completo): https://www.python.org/downloads/release/python-3119/

Na instalação, marque a caixinha **"Add python.exe to PATH"**.

Confirma no terminal do VSCode (abre com `` Ctrl+` ``):
```
python --version
```

### 2. Conferir a GPU

```
nvidia-smi
```

Isso tem que listar sua placa. Se der erro, atualiza o driver da NVIDIA antes de continuar.

### 3. Criar o ambiente virtual

Dentro da pasta do projeto:
```
python -m venv venv
venv\Scripts\activate
```

### 4. Instalar o PyTorch com suporte a CUDA (GPU)

Vá em https://pytorch.org/get-started/locally/ e confirma o comando certo pra sua versão de CUDA. Como ponto de partida:
```
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Testa se pegou a GPU:
```
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

### 5. Instalar as libs do projeto

```
pip install -r requirements.txt
```

### 6. Instalar o ffmpeg (pra extrair áudio de vídeo)

Baixa o build estático em https://www.gyan.dev/ffmpeg/builds/ (pegue o "release essentials"), extrai, e adiciona a pasta `bin` dele no PATH do Windows.

Testa:
```
ffmpeg -version
```

### 7. Rodar o teste

Pega qualquer vídeo/áudio de piano solo e roda:
```
python transcribe.py caminho\para\seu\video.mp4
```

Isso gera um `.mid`. Abre num player de MIDI (Windows Media Player ou https://signal.vercel.app/) e confere se bateu com o que foi tocado.

---

**Próximo passo**: pegar esse `.mid` e renderizar o vídeo de notas caindo.
