"""
Lecture et normalisation des fichiers CSV de dépenses de copropriété.

Format attendu (séparateur `;`, encodage Windows-1252 / latin-1 / utf-8-sig) :
    DATE;CLE DE REPARTITION;TYPE DE CHARGE;LIBELLE;A REPARTIR;TVA;RECUPERABLE

Schéma normalisé en sortie :
    date            datetime64[ns]
    cle_repartition str
    type_charge     str
    libelle         str
    a_repartir      float64
    tva             float64
    recuperable     float64
    annee           int64
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from typing import cast

# Encodages à essayer dans l'ordre pour chaque fichier CSV
_ENCODAGES = ["utf-8-sig", "cp1252", "latin-1", "utf-8"]

# Correspondance entre colonnes brutes du CSV et colonnes normalisées
_RENOMMAGE = {
    "DATE": "date",
    "CLE DE REPARTITION": "cle_repartition",
    "TYPE DE CHARGE": "type_charge",
    "LIBELLE": "libelle",
    "A REPARTIR": "a_repartir",
    "TVA": "tva",
    "RECUPERABLE": "recuperable",
}


def _lire_csv(chemin: Path) -> pd.DataFrame:
    """Lire un fichier CSV avec détection automatique de l'encodage."""
    derniere_erreur: Exception | None = None
    for encodage in _ENCODAGES:
        try:
            df = pd.read_csv(
                chemin,
                sep=";",
                encoding=encodage,
                dtype=str,
                skip_blank_lines=True,
            )
            # Supprimer les éventuelles colonnes "Unnamed"
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
            return cast(pd.DataFrame, df)
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            derniere_erreur = exc
            continue
    raise ValueError(
        f"Impossible de lire '{chemin}' avec les encodages {_ENCODAGES}. "
        f"Dernière erreur : {derniere_erreur}"
    )


def _parse_montant_fr(valeur: str | float | None) -> float:
    """
    Convertir un montant au format français en float.

    Exemples :
        '"650,47"' → 650.47
        '650,47'   → 650.47
        '1 234,56' → 1234.56
        ''         → 0.0
        None       → 0.0
    """
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return 0.0
    texte = str(valeur).strip().strip('"').strip("'")
    if not texte:
        return 0.0
    # Supprimer les espaces insécables et les espaces ordinaires utilisés comme séparateurs de milliers
    texte = re.sub(r"[\s\u00a0]", "", texte)
    # Remplacer la virgule décimale par un point
    texte = texte.replace(",", ".")
    try:
        return float(texte)
    except ValueError as exc:
        raise ValueError(f"Montant non reconnu : {valeur!r}") from exc


def _normaliser(df: pd.DataFrame, annee: int) -> pd.DataFrame:
    """Renommer les colonnes et normaliser les types."""
    # Nettoyer les noms de colonnes (espaces superflus)
    df.columns = [c.strip() for c in df.columns]

    # Vérifier que les colonnes attendues sont présentes
    colonnes_manquantes = set(_RENOMMAGE.keys()) - set(df.columns)
    if colonnes_manquantes:
        raise ValueError(
            f"Colonnes manquantes dans le fichier de l'année {annee} : {colonnes_manquantes}"
        )

    df = cast(pd.DataFrame, df.rename(columns=_RENOMMAGE)[list(_RENOMMAGE.values())].copy())

    # Parsing des dates
    df["date"] = pd.to_datetime(df["date"].str.strip(), format="%d/%m/%Y", dayfirst=True)

    # Parsing des montants
    for col in ("a_repartir", "tva", "recuperable"):
        df[col] = df[col].apply(_parse_montant_fr)

    # Nettoyage des colonnes texte
    for col in ("cle_repartition", "type_charge", "libelle"):
        df[col] = df[col].str.strip()

    # Ajout de la colonne année
    df["annee"] = annee

    return df


def importer_fichier(chemin: Path) -> pd.DataFrame:
    """
    Importer un seul fichier CSV et retourner un DataFrame normalisé.

    Le nom du fichier (sans extension) doit être l'année sur 4 chiffres,
    par exemple ``2025.csv``.

    Parameters
    ----------
    chemin:
        Chemin vers le fichier CSV.

    Returns
    -------
    pd.DataFrame
        DataFrame normalisé avec les colonnes du schéma interne.
    """
    nom = chemin.stem
    if not re.fullmatch(r"\d{4}", nom):
        raise ValueError(
            f"Le nom du fichier doit être une année sur 4 chiffres (ex: 2025.csv), "
            f"reçu : '{nom}'"
        )
    annee = int(nom)
    df_brut = _lire_csv(chemin)
    return _normaliser(df_brut, annee)


def importer_dossier(dossier: Path) -> pd.DataFrame:
    """
    Importer tous les fichiers CSV d'un dossier et les concaténer.

    Parameters
    ----------
    dossier:
        Dossier contenant les fichiers CSV (un par année).

    Returns
    -------
    pd.DataFrame
        DataFrame fusionné et trié par date.

    Raises
    ------
    FileNotFoundError
        Si le dossier n'existe pas.
    ValueError
        Si aucun fichier CSV n'est trouvé.
    """
    dossier = Path(dossier)
    if not dossier.exists():
        raise FileNotFoundError(f"Le dossier '{dossier}' n'existe pas.")

    fichiers = sorted(dossier.glob("*.csv"))
    if not fichiers:
        raise ValueError(f"Aucun fichier CSV trouvé dans '{dossier}'.")

    morceaux: list[pd.DataFrame] = []
    for fichier in fichiers:
        try:
            df = importer_fichier(fichier)
            morceaux.append(df)
            print(f"  📄 {fichier.name} : {len(df)} lignes importées")
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠️  {fichier.name} ignoré : {exc}")

    if not morceaux:
        raise ValueError("Aucun fichier n'a pu être importé.")

    df_total = pd.concat(morceaux, ignore_index=True)
    df_total = df_total.sort_values(["annee", "date"]).reset_index(drop=True)
    return df_total
