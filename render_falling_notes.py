"""
Passo 2 do projeto: MIDI -> video de "notas caindo" (estilo Synthesia).

Uso:
    python render_falling_notes.py unreve30s_audio.mid unreve30s_hq.wav

Gera um .mp4 do lado do arquivo MIDI, com o áudio embutido.
Renderiza os frames em paralelo (usa vários núcleos da CPU).
"""

import sys
import os
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pretty_midi
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import ImageSequenceClip, AudioFileClip

# ---------------- Configurações que você pode ajustar ----------------
WIDTH, HEIGHT = 1920, 1080
FPS = 60
LOOKAHEAD_SECONDS = 3.0
KEYBOARD_HEIGHT_RATIO = 0.18
MAX_VISUAL_NOTE_SECONDS = 1.2
HAND_SPLIT_NOTE = 60  # C4 — abaixo disso vira "mão esquerda" (verde)

COLOR_LEFT = (90, 210, 140)
COLOR_RIGHT = (80, 160, 255)
WHITE_KEY_COLOR = (245, 245, 245)
BLACK_KEY_COLOR = (20, 20, 20)
BG_COLOR = (12, 13, 18)

# Quantos núcleos usar pra renderizar em paralelo.
# None = usa (todos - 4), deixando um respiro pro Windows não travar.
# Se seu PC tiver poucos núcleos, ajusta esse número na mão (ex: 4).
NUM_WORKERS = None
# -----------------------------------------------------------------------

FIRST_NOTE = 21
LAST_NOTE = 108
NOTE_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

OFFSET_IN_OCTAVE = {
    0: 0.0, 1: 0.75, 2: 1.0, 3: 1.75, 4: 2.0, 5: 3.0,
    6: 3.75, 7: 4.0, 8: 4.75, 9: 5.0, 10: 5.75, 11: 6.0,
}
IS_BLACK = {1, 3, 6, 8, 10}


def note_x_units(note: int) -> float:
    return (note // 12) * 7 + OFFSET_IN_OCTAVE[note % 12]


def note_label(note: int) -> str:
    return NOTE_NAMES_FLAT[note % 12]


def hand_color(note: int, active: bool) -> tuple:
    base = COLOR_LEFT if note < HAND_SPLIT_NOTE else COLOR_RIGHT
    if active:
        return tuple(min(255, c + 60) for c in base)
    return base


X_MIN = note_x_units(FIRST_NOTE)
X_MAX = note_x_units(LAST_NOTE)
X_RANGE = X_MAX - X_MIN

_FONT_CACHE = {}


def load_font(size: int):
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(name, size)
            _FONT_CACHE[size] = font
            return font
        except OSError:
            continue
    font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


def draw_keyboard(draw, top_y, white_key_w, active_notes, font_octave):
    bottom_y = HEIGHT
    for note in range(FIRST_NOTE, LAST_NOTE + 1):
        if note % 12 in IS_BLACK:
            continue
        x = (note_x_units(note) - X_MIN) * white_key_w
        color = (255, 235, 180) if note in active_notes else WHITE_KEY_COLOR
        draw.rectangle([x, top_y, x + white_key_w - 1, bottom_y], fill=color, outline=(190, 190, 190))
        if note % 12 == 0:
            octave = note // 12 - 1
            draw.text((x + white_key_w / 2, bottom_y - 14), f"C{octave}", fill=(90, 90, 90),
                       font=font_octave, anchor="mm")

    black_w = white_key_w * 0.6
    black_h = (bottom_y - top_y) * 0.62
    for note in range(FIRST_NOTE, LAST_NOTE + 1):
        if note % 12 not in IS_BLACK:
            continue
        center_x = (note_x_units(note) - X_MIN) * white_key_w
        color = (255, 210, 120) if note in active_notes else BLACK_KEY_COLOR
        draw.rectangle([center_x - black_w / 2, top_y, center_x + black_w / 2, top_y + black_h], fill=color)


def draw_glow_line(img, keyboard_top, active_columns, white_key_w):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.line([(0, keyboard_top), (WIDTH, keyboard_top)], fill=(255, 255, 255, 120), width=2)
    for x_center, color in active_columns:
        odraw.ellipse(
            [x_center - white_key_w, keyboard_top - 10, x_center + white_key_w, keyboard_top + 10],
            fill=color + (160,),
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(6))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))


def dedupe_same_pitch_overlaps(notes):
    GAP = 0.03
    by_pitch = {}
    for n in notes:
        by_pitch.setdefault(n[0], []).append(list(n))
    for pitch_notes in by_pitch.values():
        pitch_notes.sort(key=lambda n: n[1])
        for i in range(len(pitch_notes) - 1):
            if pitch_notes[i][2] > pitch_notes[i + 1][1] - GAP:
                pitch_notes[i][2] = max(pitch_notes[i][1] + 0.05, pitch_notes[i + 1][1] - GAP)
    result = []
    for pitch_notes in by_pitch.values():
        result.extend(pitch_notes)
    return result


def render_one_frame(args):
    """Desenha UM frame e salva em disco. Roda em paralelo em vários processos."""
    frame_index, t, notes, keyboard_top, white_key_w, pixels_per_second, out_dir = args

    font_label = load_font(max(11, int(white_key_w * 0.55)))
    font_octave = load_font(max(9, int(white_key_w * 0.4)))

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    active_notes = set()
    active_columns = []

    for pitch, start, end in notes:
        is_active = start <= t < end
        if is_active:
            active_notes.add(pitch)

        visual_end = min(end, start + MAX_VISUAL_NOTE_SECONDS)
        time_to_bottom = start - t
        time_to_top = visual_end - t
        if time_to_top < 0 or time_to_bottom > LOOKAHEAD_SECONDS:
            continue

        y_bottom = min(keyboard_top - time_to_bottom * pixels_per_second, keyboard_top)
        y_top = keyboard_top - time_to_top * pixels_per_second

        is_black = pitch % 12 in IS_BLACK
        key_center_x = (note_x_units(pitch) - X_MIN) * white_key_w
        w = white_key_w * (0.55 if is_black else 0.85)
        x_left = key_center_x - w / 2 if is_black else key_center_x + (white_key_w - w) / 2
        bar_center_x = x_left + w / 2
        color = hand_color(pitch, is_active)

        draw.rounded_rectangle([x_left, y_top, x_left + w, y_bottom], radius=w * 0.25,
                                fill=color, outline=(15, 15, 15))

        label_y = min(y_bottom, keyboard_top) - 14
        if label_y > y_top + 6:
            draw.rounded_rectangle(
                [bar_center_x - w * 0.4, label_y - 10, bar_center_x + w * 0.4, label_y + 10],
                radius=6, fill=(15, 15, 18), outline=color,
            )
            draw.text((bar_center_x, label_y), note_label(pitch), fill=(255, 255, 255),
                      font=font_label, anchor="mm")

        if is_active:
            active_columns.append((bar_center_x, color))

    draw_glow_line(img, keyboard_top, active_columns, white_key_w)
    draw = ImageDraw.Draw(img)
    draw_keyboard(draw, keyboard_top, white_key_w, active_notes, font_octave)

    out_path = os.path.join(out_dir, f"frame_{frame_index:06d}.png")
    img.save(out_path)
    return frame_index


def render(midi_path: str, audio_path: str | None):
    pm = pretty_midi.PrettyMIDI(midi_path)
    raw_notes = []
    for inst in pm.instruments:
        for n in inst.notes:
            raw_notes.append((n.pitch, n.start, n.end))
    if not raw_notes:
        print("Nenhuma nota encontrada nesse MIDI.")
        sys.exit(1)

    notes = dedupe_same_pitch_overlaps(raw_notes)

    duration = pm.get_end_time()
    keyboard_top = int(HEIGHT * (1 - KEYBOARD_HEIGHT_RATIO))
    white_key_w = WIDTH / (X_RANGE + 1)
    pixels_per_second = keyboard_top / LOOKAHEAD_SECONDS

    n_frames = int(duration * FPS) + FPS
    workers = NUM_WORKERS or max(1, (os.cpu_count() or 4) - 4)
    print(f"Duração: {duration:.1f}s | Frames a renderizar: {n_frames} | Núcleos em paralelo: {workers}")

    tmp_dir = tempfile.mkdtemp(prefix="falling_notes_frames_")
    try:
        tasks = [
            (f, f / FPS, notes, keyboard_top, white_key_w, pixels_per_second, tmp_dir)
            for f in range(n_frames)
        ]

        done = 0
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(render_one_frame, task) for task in tasks]
            for fut in as_completed(futures):
                fut.result()
                done += 1
                if done % 100 == 0 or done == n_frames:
                    print(f"  {done}/{n_frames} frames renderizados...")

        print("Montando o vídeo...")
        frame_files = sorted(
            os.path.join(tmp_dir, name) for name in os.listdir(tmp_dir) if name.endswith(".png")
        )
        clip = ImageSequenceClip(frame_files, fps=FPS)

        if audio_path and os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)
            final_duration = min(clip.duration, audio.duration)
            clip = clip.subclipped(0, final_duration).with_audio(audio.subclipped(0, final_duration))

        out_path = os.path.splitext(midi_path)[0] + "_falling_notes.mp4"
        try:
            # Tenta codificar usando o encoder de vídeo da GPU NVIDIA (bem mais rápido
            # e tira essa etapa da CPU). Se não tiver NVENC disponível, cai pro libx264 normal.
            clip.write_videofile(
                out_path, fps=FPS, codec="h264_nvenc", audio_codec="aac", audio_bitrate="192k",
                ffmpeg_params=["-preset", "p4", "-b:v", "12M"],
            )
        except Exception as e:
            print(f"Encoder de GPU (NVENC) falhou ({e}), usando CPU (libx264) no lugar...")
            clip.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac", audio_bitrate="192k")
        print(f"Pronto! Vídeo salvo em: {out_path}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python render_falling_notes.py arquivo.mid [audio.wav]")
        sys.exit(1)

    midi_arg = sys.argv[1]
    audio_arg = sys.argv[2] if len(sys.argv) > 2 else None
    render(midi_arg, audio_arg)
