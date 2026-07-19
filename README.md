# appPianoBr 🎹

Ideia surgiu depois de ver um app gringo no TikTok que faz exatamente isso: pega um vídeo de piano e transforma em "notas caindo" (tipo Synthesia), ótimo pra quem tá aprendendo a tocar de ouvido. Só que o treco é pago, e eu tenho um PC forte parado, então resolvi tentar fazer minha própria versão, em PT-BR, rodando local.

**Ideia por trás:**
Tenho uns amigos aprendendo piano, e essas notas caindo ajudam demais a visualizar o que tocar. A ideia é usar isso pra mim e pra galera de graça, sem depender de assinatura de app gringo. Se rolar de evoluir pra algo mais robusto no futuro (quem sabe até virar um app de verdade, pago em reais pra galera BR), show, mas por enquanto é projeto pessoal mesmo, aprendendo na prática.

## Como funciona

Tem **dois jeitos** de gerar o vídeo de notas caindo, dependendo do que você tem em mãos:

### Caminho 1: Vídeo/áudio de piano → MIDI → vídeo
1. `transcribe.py` — pega um vídeo ou áudio de piano solo, roda um modelo de IA (transcrição áudio → MIDI) e gera um `.mid`
2. `render_falling_notes.py` — pega esse `.mid` (+ o áudio original, se quiser som no vídeo) e renderiza o vídeo de notas caindo

Limitação conhecida: a transcrição por áudio erra algumas notas (o modelo "adivinha" o que foi tocado ouvindo o som, então não é perfeito, principalmente em músicas mais densas/rápidas).

### Caminho 2: Partitura em PDF → MIDI → vídeo (mais preciso)
1. `sheet_to_midi.py` — lê a partitura direto (OMR - Optical Music Recognition, via `oemer`), converte pra MusicXML e depois MIDI. Se o PDF tiver várias páginas, já junta tudo num MIDI só no final (`..._partitura.mid`)
2. `render_falling_notes.py` — mesmo script de sempre, roda nesse MIDI

Como lê a partitura de verdade (não adivinha pelo som), erra bem menos que a transcrição por áudio. Mas não tem áudio original pra colar no vídeo (partitura não tem som gravado) — o vídeo sai mudo, só com as notas caindo mesmo.

**Bug conhecido:** o `oemer` (que faz a leitura da partitura) quebra com versões mais novas de `numpy`/`opencv`. Se der erro `IndexError: invalid index to scalar variable`, roda:
```
pip install "numpy<2" "opencv-python-headless==4.9.0.80"
```

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
py -3.11 -m venv venv
venv\Scripts\activate
```

Se der erro de política de execução de script no PowerShell:
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
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

## Uso

### Caminho 1 — a partir de vídeo/áudio:
```
python transcribe.py caminho\para\seu\video.mp4
python render_falling_notes.py video_audio.mid video_hq.wav
```

### Caminho 2 — a partir de partitura em PDF:
```
python sheet_to_midi.py partitura.pdf
python render_falling_notes.py partitura_partitura.mid
```

O vídeo final sai como `..._falling_notes.mp4` do lado do MIDI usado.

## Configurações úteis no `render_falling_notes.py`

- `HAND_SPLIT_NOTE` — nota MIDI que separa "mão esquerda" (verde) de "mão direita" (azul). É uma heurística simples por altura, não sabe de verdade qual mão tocou.
- `NUM_WORKERS` — quantos núcleos da CPU usar em paralelo pra renderizar. Por padrão usa (todos - 4), pra não travar o PC inteiro.
- Codificação final tenta usar a GPU (NVENC); se não tiver suporte, cai pro CPU automaticamente.

## Próximos passos (ideias em aberto)

- Sintetizar áudio a partir do MIDI da partitura (pra não sair mudo)
- Interface/site em vez de rodar tudo via terminal
- Adicionar link do YouTube direto (baixar e transcrever numa tacada só)
