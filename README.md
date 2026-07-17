# Falling Notes App — Passo 1: Áudio → MIDI

Esse é o ponto de partida. Antes de pensar em site, vamos deixar rodando localmente
o núcleo do negócio: **vídeo de piano → arquivo MIDI**. Depois a gente pluga a
renderização das "notas caindo" e só no final embrulha isso num site.

## 1. Instalar o Python

Baixe o **Python 3.11** (não use 3.13, algumas libs de áudio ainda não têm suporte
completo): https://www.python.org/downloads/release/python-3119/

Na instalação, marque a caixinha **"Add python.exe to PATH"**.

Confirma no terminal do VSCode (abre com `` Ctrl+` ``):
```powershell
python --version
```

## 2. Conferir a GPU

```powershell
nvidia-smi
```
Isso tem que listar sua placa. Se der erro, você precisa atualizar o driver da
NVIDIA (Geforce Experience ou site da NVIDIA) antes de continuar.

## 3. Criar o ambiente virtual

Dentro da pasta do projeto (essa mesma que você abriu no VSCode):

```powershell
python -m venv venv
venv\Scripts\activate
```

Você vai ver `(venv)` aparecer no início da linha do terminal. É nesse ambiente
que vamos instalar tudo — assim não bagunça o Python do sistema.

## 4. Instalar o PyTorch com suporte a CUDA (GPU)

Vá em https://pytorch.org/get-started/locally/ e confirma o comando certo pra
sua versão de CUDA (o site já detecta e monta o comando). Como ponto de partida,
normalmente é algo assim:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Depois de instalar, testa se pegou a GPU:
```powershell
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Tem que aparecer `True` e o nome da sua placa.

## 5. Instalar as libs do projeto

```powershell
pip install -r requirements.txt
```

## 6. Instalar o ffmpeg (pra extrair áudio de vídeo)

Mais fácil: baixa o build estático em https://www.gyan.dev/ffmpeg/builds/
(pegue o "release essentials"), extrai, e adiciona a pasta `bin` dele nas
variáveis de ambiente PATH do Windows.

Testa:
```powershell
ffmpeg -version
```

## 7. Rodar o teste

Pega qualquer vídeo/áudio de piano solo (só piano, sem outros instrumentos por
enquanto — isso simplifica muito) e roda:

```powershell
python transcribe.py caminho\para\seu\video.mp4
```

Isso vai gerar um arquivo `.mid` do lado. Abre esse `.mid` num player de MIDI
(o próprio Windows Media Player toca, ou o site https://signal.vercel.app/ pra
visualizar as notas) e vê se bateu com o que você tocou.

---

**Próximo passo** (depois que isso funcionar): pegar esse `.mid` e renderizar
o vídeo de notas caindo. Me chama quando chegar até aqui que a gente monta essa parte.
