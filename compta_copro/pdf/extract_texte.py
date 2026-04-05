"""
Extraction de texte depuis des fichiers PDF.

Deux modes sont supportés :
1. **PDF texte** : extraction directe via ``pdfplumber`` (ou ``pypdf`` en fallback).
   Fonctionne pour les PDF numériques (export logiciel).

2. **PDF scanné (OCR)** : extraction via ``pytesseract`` + ``pdf2image``.
   Nécessite l'installation de Tesseract OCR sur le système :
   - Windows : https://github.com/UB-Mannheim/tesseract/wiki
   - macOS  : ``brew install tesseract``
   - Linux  : ``sudo apt install tesseract-ocr tesseract-ocr-fra``
   Et les paquets Python optionnels : ``pytesseract``, ``pdf2image``, ``Pillow``.

Utilisation depuis la CLI :
    python -m compta_copro extraire-pdf mon_fichier.pdf
    python -m compta_copro extraire-pdf mon_scan.pdf --ocr --sortie resultat.txt
"""

from __future__ import annotations

from pathlib import Path


def extraire_texte(chemin_pdf: Path, ocr: bool = False) -> str:
    """
    Extraire le texte d'un fichier PDF.

    Parameters
    ----------
    chemin_pdf:
        Chemin vers le fichier PDF.
    ocr:
        Si True, utiliser l'OCR (Tesseract) pour les PDF scannés.

    Returns
    -------
    str
        Texte extrait.

    Raises
    ------
    FileNotFoundError
        Si le fichier PDF n'existe pas.
    ImportError
        Si les bibliothèques nécessaires ne sont pas installées.
    """
    chemin_pdf = Path(chemin_pdf)
    if not chemin_pdf.exists():
        raise FileNotFoundError(f"Fichier PDF introuvable : {chemin_pdf}")

    if ocr:
        return _extraire_avec_ocr(chemin_pdf)
    return _extraire_texte_natif(chemin_pdf)


def _extraire_texte_natif(chemin_pdf: Path) -> str:
    """Extraire le texte d'un PDF numérique (sans OCR)."""
    # Essayer pdfplumber en premier
    try:
        import pdfplumber  # noqa: PLC0415

        texte_pages: list[str] = []
        with pdfplumber.open(chemin_pdf) as pdf:
            for page in pdf.pages:
                contenu = page.extract_text()
                if contenu:
                    texte_pages.append(contenu)
        return "\n\n".join(texte_pages)
    except ImportError:
        pass

    # Fallback : pypdf
    try:
        from pypdf import PdfReader  # noqa: PLC0415

        reader = PdfReader(chemin_pdf)
        texte_pages = []
        for page in reader.pages:
            contenu = page.extract_text()
            if contenu:
                texte_pages.append(contenu)
        return "\n\n".join(texte_pages)
    except ImportError:
        pass

    raise ImportError(
        "Aucune bibliothèque PDF disponible.\n"
        "Installez pdfplumber ou pypdf :\n"
        "  pip install pdfplumber\n"
        "  ou : pip install pypdf"
    )


def _extraire_avec_ocr(chemin_pdf: Path) -> str:
    """
    Extraire le texte d'un PDF scanné via OCR (Tesseract).

    Nécessite :
        - Tesseract OCR installé sur le système (avec le pack langue fra)
        - pytesseract, pdf2image, Pillow installés en Python

    Notes
    -----
    Cette fonctionnalité est expérimentale. La qualité de l'extraction dépend
    de la résolution et de la clarté du scan.
    """
    # Vérifier les dépendances optionnelles
    try:
        import pytesseract  # noqa: PLC0415
        from pdf2image import convert_from_path  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "Pour utiliser l'OCR, installez les dépendances optionnelles :\n"
            "  pip install pytesseract pdf2image Pillow\n"
            "Puis installez Tesseract OCR sur votre système :\n"
            "  - Windows : https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  - macOS   : brew install tesseract tesseract-lang\n"
            "  - Linux   : sudo apt install tesseract-ocr tesseract-ocr-fra"
        ) from exc

    images = convert_from_path(chemin_pdf, dpi=300)
    texte_pages: list[str] = []
    for i, image in enumerate(images, start=1):
        print(f"  🔍 OCR page {i}/{len(images)}…")
        texte = pytesseract.image_to_string(image, lang="fra")
        if texte.strip():
            texte_pages.append(texte)

    return "\n\n".join(texte_pages)
