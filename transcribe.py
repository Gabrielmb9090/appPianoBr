"""
Passo 1 do projeto: video (ou audio) de piano -> arquivo MIDI.

Uso:
    python transcribe.py caminho\para\video.mp4

Gera um arquivo .mid do lado do vídeo original.
"""

import sys
import os
import pretty_midi
from moviepy import VideoFileClip
from piano_transcription_inference import PianoTranscription, sample_rate, load_audio

# ---------------- Filtro de "alucinações" (ajuste se precisar) ----------------
# O modelo às vezes capta notas espúrias: bem curtas e/ou bem fracas.
# Aumentar esses números filtra mais (menos lixo, mas risco de perder notas
# tocadas de leve/rápido de verdade). Diminuir filtra menos.
MIN_NOTE_DURATION = 0.05   # segundos — notas mais curtas que isso são descartadas
MIN_VELOCITY = 12          # 0-127 — notas mais fracas que isso são descartadas
# --------------------------------------------------------------------------------


def clean_midi(midi_path: str) -> None:
    """Remove notas muito curtas/fracas do MIDI gerado (reduz alucinações)."""
    pm = pretty_midi.PrettyMIDI(midi_path)
    total_before = 0
    total_after = 0
    for inst in pm.instruments:
        total_before += len(inst.notes)
        inst.notes = [
            n for n in inst.notes
            if (n.end - n.start) >= MIN_NOTE_DURATION and n.velocity >= MIN_VELOCITY
        ]
        total_after += len(inst.notes)
    pm.write(midi_path)
    removed = total_before - total_after
    print(f"Limpeza: removidas {removed} de {total_before} notas suspeitas "
          f"({total_after} notas restantes).")


def extract_audio(video_path: str) -> str:
    """Se for vídeo, extrai o áudio como .wav. Se já for áudio, retorna direto."""
    ext = os.path.splitext(video_path)[1].lower()
    audio_exts = {".wav", ".mp3", ".flac", ".m4a"}

    if ext in audio_exts:
        return video_path

    wav_path = os.path.splitext(video_path)[0] + "_audio.wav"
    print(f"Extraindo áudio de {video_path} -> {wav_path}")
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(wav_path, fps=sample_rate)
    clip.close()
    return wav_path


def transcribe(audio_path: str) -> str:
    midi_path = os.path.splitext(audio_path)[0] + ".mid"

    print("Carregando áudio...")
    audio, _ = load_audio(audio_path, sr=sample_rate, mono=True)

    print("Carregando modelo (primeira vez baixa os pesos, pode demorar um pouco)...")
    # device='cuda' usa sua GPU. Se não tiver CUDA configurado, troca pra 'cpu'.
    transcriptor = PianoTranscription(device="cuda")

    print("Transcrevendo... isso roda o modelo de IA em cima do áudio.")
    transcriptor.transcribe(audio, midi_path)

    clean_midi(midi_path)

    print(f"Pronto! MIDI salvo em: {midi_path}")
    return midi_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python transcribe.py caminho\\para\\video.mp4")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"Arquivo não encontrado: {input_path}")
        sys.exit(1)

    audio_path = extract_audio(input_path)
    transcribe(audio_path)
