"""
Passo alternativo: partitura em PDF -> arquivo MIDI (sem passar por áudio).

Usa OMR (Optical Music Recognition) pra "ler" a partitura de verdade,
em vez de adivinhar notas a partir do som. Tende a ser bem mais preciso
que a transcrição de áudio, desde que a partitura esteja limpa (impressa,
sem manuscrito, sem muita sujeira de scanner).

Uso:
    python sheet_to_midi.py partitura.pdf

Gera um arquivo .mid do lado do PDF.

Dependências extras desse passo (ver requirements.txt):
    pip install oemer pymupdf music21
"""

import sys
import os
import glob
import subprocess

import fitz  # PyMuPDF
import pretty_midi
from music21 import converter

DPI = 300  # resolução da imagem de cada página (mais alto = mais preciso, mais lento)


def pdf_to_images(pdf_path: str, out_dir: str) -> list[str]:
    """Converte cada página do PDF numa imagem PNG de alta resolução."""
    doc = fitz.open(pdf_path)
    zoom = DPI / 72
    mat = fitz.Matrix(zoom, zoom)
    image_paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        img_path = os.path.join(out_dir, f"page_{i + 1:03d}.png")
        pix.save(img_path)
        image_paths.append(img_path)
    doc.close()
    print(f"PDF convertido em {len(image_paths)} imagem(ns) de página.")
    return image_paths


def run_oemer(image_path: str, out_dir: str) -> str | None:
    """Roda o oemer (leitor de partitura) numa imagem de página. Retorna o
    caminho do .musicxml gerado, ou None se falhar."""
    print(f"Lendo partitura: {os.path.basename(image_path)} "
          f"(primeira vez baixa os modelos, pode demorar alguns minutos)...")
    before = set(glob.glob(os.path.join(out_dir, "*.musicxml")))

    result = subprocess.run(
        ["oemer", image_path, "-o", out_dir],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  Aviso: oemer falhou nessa página.\n{result.stderr[-800:]}")
        return None

    after = set(glob.glob(os.path.join(out_dir, "*.musicxml")))
    new_files = after - before
    if new_files:
        return sorted(new_files)[0]

    # fallback: pega o .musicxml mais recente na pasta
    candidates = sorted(glob.glob(os.path.join(out_dir, "*.musicxml")),
                         key=os.path.getmtime, reverse=True)
    return candidates[0] if candidates else None


def musicxml_to_midi(xml_path: str, midi_path: str) -> str:
    score = converter.parse(xml_path)
    score.write("midi", fp=midi_path)
    return midi_path


def merge_midis(midi_paths: list[str], out_path: str) -> str:
    """Junta os MIDIs de várias páginas em um só, um atrás do outro no tempo."""
    combined = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=0, name="piano")
    offset = 0.0

    for path in midi_paths:
        pm = pretty_midi.PrettyMIDI(path)
        page_notes = [n for i in pm.instruments for n in i.notes]
        if not page_notes:
            continue
        for n in page_notes:
            inst.notes.append(pretty_midi.Note(
                velocity=n.velocity, pitch=n.pitch,
                start=n.start + offset, end=n.end + offset,
            ))
        offset += max(n.end for n in page_notes)

    combined.instruments.append(inst)
    combined.write(out_path)
    return out_path


def process_pdf(pdf_path: str) -> str:
    base = os.path.splitext(pdf_path)[0]
    work_dir = base + "_paginas"
    os.makedirs(work_dir, exist_ok=True)

    images = pdf_to_images(pdf_path, work_dir)

    midi_paths = []
    for img in images:
        xml_path = run_oemer(img, work_dir)
        if not xml_path or not os.path.exists(xml_path):
            print(f"  Não consegui ler a página {os.path.basename(img)}, pulando.")
            continue
        midi_path = os.path.splitext(img)[0] + ".mid"
        musicxml_to_midi(xml_path, midi_path)
        midi_paths.append(midi_path)
        print(f"  Página {os.path.basename(img)} -> {os.path.basename(midi_path)} OK")

    if not midi_paths:
        print("Não consegui extrair nenhuma nota da partitura.")
        sys.exit(1)

    final_midi = base + "_partitura.mid"
    merge_midis(midi_paths, final_midi)
    print(f"Pronto! MIDI da partitura salvo em: {final_midi}")
    return final_midi


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python sheet_to_midi.py partitura.pdf")
        sys.exit(1)

    pdf_arg = sys.argv[1]
    if not os.path.exists(pdf_arg):
        print(f"Arquivo não encontrado: {pdf_arg}")
        sys.exit(1)

    process_pdf(pdf_arg)
