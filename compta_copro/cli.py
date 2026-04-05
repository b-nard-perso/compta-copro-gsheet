"""
Interface en ligne de commande (CLI) de compta_copro.

Sous-commandes :
    importer-csv      Importer les CSV d'un dossier vers un fichier Parquet/CSV
    analyser          Calculer les agrégations et produire des CSV de synthèse
    generer-gsheet    Créer ou mettre à jour le Google Sheet
    extraire-pdf      Extraire le texte d'un fichier PDF
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _commande_importer_csv(args: argparse.Namespace) -> None:
    from compta_copro.importation.lecteur_csv import importer_dossier

    df = importer_dossier(Path(args.input))
    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)

    if sortie.suffix == ".parquet":
        df.to_parquet(sortie, index=False)
    else:
        df.to_csv(sortie, index=False, sep=";", encoding="utf-8-sig")

    print(f"✅  {len(df)} lignes importées → {sortie}")


def _commande_analyser(args: argparse.Namespace) -> None:
    import pandas as pd

    from compta_copro.analyse.agregation import (
        agregation_annee_poste,
        comparaison_n_n1,
        top_hausses,
    )

    entree = Path(args.input)
    if entree.suffix == ".parquet":
        df = pd.read_parquet(entree)
    else:
        df = pd.read_csv(entree, sep=";", encoding="utf-8-sig")
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)
        df["a_repartir"] = df["a_repartir"].astype(float)
        df["tva"] = df["tva"].astype(float)
        df["recuperable"] = df["recuperable"].astype(float)
        df["annee"] = df["annee"].astype(int)

    sortie = Path(args.output)
    sortie.mkdir(parents=True, exist_ok=True)

    agg = agregation_annee_poste(df)
    agg.to_csv(sortie / "agregation_annee_poste.csv", index=False, sep=";", encoding="utf-8-sig")

    comp = comparaison_n_n1(df)
    comp.to_csv(sortie / "comparaison_n_n1.csv", index=False, sep=";", encoding="utf-8-sig")

    hausses_eur = top_hausses(comp, colonne_tri="delta", n=20)
    hausses_pct = top_hausses(comp, colonne_tri="delta_pct", n=20)
    hausses_eur.to_csv(sortie / "top_hausses_eur.csv", index=False, sep=";", encoding="utf-8-sig")
    hausses_pct.to_csv(sortie / "top_hausses_pct.csv", index=False, sep=";", encoding="utf-8-sig")

    print(f"✅  Analyses exportées dans {sortie}")


def _commande_generer_gsheet(args: argparse.Namespace) -> None:
    import os

    import pandas as pd

    from compta_copro.gsheet.generateur import generer_google_sheet

    entree = Path(args.input)
    if entree.suffix == ".parquet":
        df = pd.read_parquet(entree)
    else:
        df = pd.read_csv(entree, sep=";", encoding="utf-8-sig")
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)
        df["a_repartir"] = df["a_repartir"].astype(float)
        df["tva"] = df["tva"].astype(float)
        df["recuperable"] = df["recuperable"].astype(float)
        df["annee"] = df["annee"].astype(int)

    nom_sheet = args.spreadsheet or os.getenv("GSHEET_NOM", "Copro - Analyse")
    dossier_credentials = Path(args.credentials)

    generer_google_sheet(df, nom_sheet=nom_sheet, dossier_credentials=dossier_credentials)


def _commande_extraire_pdf(args: argparse.Namespace) -> None:
    from compta_copro.pdf.extract_texte import extraire_texte

    texte = extraire_texte(Path(args.fichier), ocr=args.ocr)
    if args.sortie:
        sortie = Path(args.sortie)
        sortie.parent.mkdir(parents=True, exist_ok=True)
        sortie.write_text(texte, encoding="utf-8")
        print(f"✅  Texte extrait → {sortie}")
    else:
        print(texte)


def principale() -> None:
    """Point d'entrée principal de la CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m compta_copro",
        description="Outil d'analyse des dépenses de copropriété",
    )
    sous_commandes = parser.add_subparsers(dest="commande", metavar="<commande>")
    sous_commandes.required = True

    # --- importer-csv ---
    p_import = sous_commandes.add_parser(
        "importer-csv",
        help="Importer les CSV d'un dossier vers un fichier Parquet ou CSV normalisé",
    )
    p_import.add_argument(
        "--input",
        default="data/csv",
        metavar="DOSSIER",
        help="Dossier contenant les fichiers CSV (défaut : data/csv)",
    )
    p_import.add_argument(
        "--sortie",
        default="data/intermediaire/depenses.parquet",
        metavar="FICHIER",
        help="Fichier de sortie (.parquet ou .csv) (défaut : data/intermediaire/depenses.parquet)",
    )

    # --- analyser ---
    p_analyse = sous_commandes.add_parser(
        "analyser",
        help="Calculer les agrégations et comparaisons inter-annuelles",
    )
    p_analyse.add_argument(
        "--input",
        default="data/intermediaire/depenses.parquet",
        metavar="FICHIER",
        help="Fichier source (.parquet ou .csv) (défaut : data/intermediaire/depenses.parquet)",
    )
    p_analyse.add_argument(
        "--output",
        default="data/sorties",
        metavar="DOSSIER",
        help="Dossier de sortie pour les CSV de synthèse (défaut : data/sorties)",
    )

    # --- generer-gsheet ---
    p_gsheet = sous_commandes.add_parser(
        "generer-gsheet",
        help="Créer ou mettre à jour le Google Sheet",
    )
    p_gsheet.add_argument(
        "--input",
        default="data/intermediaire/depenses.parquet",
        metavar="FICHIER",
        help="Fichier source (.parquet ou .csv) (défaut : data/intermediaire/depenses.parquet)",
    )
    p_gsheet.add_argument(
        "--spreadsheet",
        default=None,
        metavar="NOM",
        help="Nom du Google Sheet (défaut : variable d'env GSHEET_NOM ou 'Copro - Analyse')",
    )
    p_gsheet.add_argument(
        "--credentials",
        default="credentials",
        metavar="DOSSIER",
        help="Dossier contenant client_secret.json et token.json (défaut : credentials/)",
    )

    # --- extraire-pdf ---
    p_pdf = sous_commandes.add_parser(
        "extraire-pdf",
        help="Extraire le texte d'un fichier PDF (expérimental)",
    )
    p_pdf.add_argument("fichier", metavar="FICHIER_PDF", help="Chemin vers le fichier PDF")
    p_pdf.add_argument(
        "--sortie",
        default=None,
        metavar="FICHIER_TXT",
        help="Fichier texte de sortie (défaut : affichage console)",
    )
    p_pdf.add_argument(
        "--ocr",
        action="store_true",
        help="Utiliser l'OCR (Tesseract) pour les PDF scannés",
    )

    args = parser.parse_args()

    commandes = {
        "importer-csv": _commande_importer_csv,
        "analyser": _commande_analyser,
        "generer-gsheet": _commande_generer_gsheet,
        "extraire-pdf": _commande_extraire_pdf,
    }

    try:
        commandes[args.commande](args)
    except KeyboardInterrupt:
        print("\nInterrompu.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"❌  Erreur : {exc}", file=sys.stderr)
        sys.exit(1)
