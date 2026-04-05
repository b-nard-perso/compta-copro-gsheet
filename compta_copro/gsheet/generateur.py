"""
Génération et mise à jour du Google Sheet de synthèse.

Structure du Google Sheet :
    - Un onglet par année  : dépenses par TYPE DE CHARGE + total
    - Onglet « Comparaison » : tableau delta N vs N-1
    - Onglet « Synthèse »    : top hausses (€ et %)

Formatage :
    - En-têtes en gras
    - 1ère ligne gelée
    - Filtre automatique
    - Format monétaire € pour les colonnes de montants
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import gspread
import pandas as pd
from gspread.utils import rowcol_to_a1

from compta_copro.analyse.agregation import (
    agregation_annee_poste,
    comparaison_n_n1,
    top_hausses,
)
from compta_copro.gsheet.auth import obtenir_credentials

# Largeur des colonnes (en pixels)
_LARGEUR_COL_TEXTE = 250
_LARGEUR_COL_MONTANT = 130

# Format monétaire euro
_FORMAT_EURO = {
    "numberFormat": {
        "type": "CURRENCY",
        "pattern": '#,##0.00\\ "€"',
    }
}

# Format pourcentage
_FORMAT_PCT = {
    "numberFormat": {
        "type": "PERCENT",
        "pattern": "0.00%",
    }
}


def generer_google_sheet(
    df: pd.DataFrame,
    nom_sheet: str = "Copro - Analyse",
    dossier_credentials: Path = Path("credentials"),
) -> str:
    """
    Créer ou mettre à jour le Google Sheet.

    Parameters
    ----------
    df:
        DataFrame normalisé (schéma interne).
    nom_sheet:
        Nom du Google Sheet à créer ou mettre à jour.
    dossier_credentials:
        Dossier contenant les fichiers d'authentification.

    Returns
    -------
    str
        URL du Google Sheet.
    """
    creds = obtenir_credentials(dossier_credentials)
    gc = gspread.authorize(creds)

    # Ouvrir ou créer le spreadsheet
    try:
        sh = gc.open(nom_sheet)
        print(f"📋  Spreadsheet existant trouvé : {nom_sheet}")
    except gspread.SpreadsheetNotFound:
        sh = gc.create(nom_sheet)
        print(f"📋  Nouveau spreadsheet créé : {nom_sheet}")

    annees = sorted(df["annee"].unique())
    noms_onglets_utilises: list[str] = []

    # --- Onglets par année ---
    for annee in annees:
        nom_onglet = str(annee)
        noms_onglets_utilises.append(nom_onglet)
        df_annee = df[df["annee"] == annee].copy()
        _ecrire_onglet_annee(sh, nom_onglet, df_annee, annee)

    # --- Onglet Comparaison ---
    noms_onglets_utilises.append("Comparaison")
    comp = comparaison_n_n1(df)
    _ecrire_onglet_comparaison(sh, comp)

    # --- Onglet Synthèse ---
    noms_onglets_utilises.append("Synthèse")
    _ecrire_onglet_synthese(sh, comp)

    # Supprimer les onglets inutilisés (sauf si c'est le seul)
    feuilles_existantes = [ws.title for ws in sh.worksheets()]
    for titre in feuilles_existantes:
        if titre not in noms_onglets_utilises and len(sh.worksheets()) > 1:
            sh.del_worksheet(sh.worksheet(titre))

    url = f"https://docs.google.com/spreadsheets/d/{sh.id}"
    print(f"✅  Google Sheet disponible : {url}")
    return url


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


def _obtenir_ou_creer_feuille(sh: gspread.Spreadsheet, titre: str) -> gspread.Worksheet:
    """Obtenir une feuille existante ou en créer une nouvelle."""
    try:
        ws = sh.worksheet(titre)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=titre, rows=1000, cols=20)
    return ws


def _appliquer_formatage_entete(
    sh: gspread.Spreadsheet,
    ws: gspread.Worksheet,
    nb_colonnes: int,
) -> None:
    """Mettre les en-têtes en gras, geler la 1ère ligne et activer le filtre."""
    sheet_id = ws.id

    requetes: list[dict[str, Any]] = [
        # En-têtes en gras
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": nb_colonnes,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.85, "green": 0.90, "blue": 0.95},
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        },
        # Gel de la 1ère ligne
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Filtre automatique
        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": nb_colonnes,
                    }
                }
            }
        },
    ]
    sh.batch_update({"requests": requetes})


def _appliquer_format_monnetaire(
    sh: gspread.Spreadsheet,
    ws: gspread.Worksheet,
    indices_colonnes: list[int],
    nb_lignes: int,
) -> None:
    """Appliquer le format monétaire € aux colonnes spécifiées."""
    requetes: list[dict[str, Any]] = []
    for idx in indices_colonnes:
        requetes.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 1,
                        "endRowIndex": nb_lignes + 1,
                        "startColumnIndex": idx,
                        "endColumnIndex": idx + 1,
                    },
                    "cell": {"userEnteredFormat": _FORMAT_EURO},
                    "fields": "userEnteredFormat.numberFormat",
                }
            }
        )
    if requetes:
        sh.batch_update({"requests": requetes})


def _nan_vers_vide(valeur: Any) -> Any:
    """Remplacer NaN/None par chaîne vide pour l'écriture dans le sheet."""
    if valeur is None:
        return ""
    if isinstance(valeur, float) and math.isnan(valeur):
        return ""
    return valeur


def _df_vers_lignes(df: pd.DataFrame) -> list[list[Any]]:
    """Convertir un DataFrame en liste de lignes (en-tête + données)."""
    entete = list(df.columns)
    lignes = [
        [_nan_vers_vide(v) for v in row]
        for row in df.itertuples(index=False, name=None)
    ]
    return [entete] + lignes


def _ecrire_onglet_annee(
    sh: gspread.Spreadsheet,
    nom_onglet: str,
    df_annee: pd.DataFrame,
    annee: int,
) -> None:
    """Écrire l'onglet d'une année : dépenses par TYPE DE CHARGE + total."""
    ws = _obtenir_ou_creer_feuille(sh, nom_onglet)

    # Agrégation pour l'onglet annuel
    agg = (
        df_annee.groupby("type_charge", sort=True)
        .agg(
            total_a_repartir=("a_repartir", "sum"),
            total_tva=("tva", "sum"),
            total_recuperable=("recuperable", "sum"),
            nb_lignes=("libelle", "count"),
        )
        .reset_index()
    )
    agg.columns = ["Type de charge", "Total à répartir (€)", "TVA (€)", "Récupérable (€)", "Nb lignes"]

    # Ligne de total
    total = {
        "Type de charge": "TOTAL",
        "Total à répartir (€)": agg["Total à répartir (€)"].sum(),
        "TVA (€)": agg["TVA (€)"].sum(),
        "Récupérable (€)": agg["Récupérable (€)"].sum(),
        "Nb lignes": agg["Nb lignes"].sum(),
    }
    agg = pd.concat([agg, pd.DataFrame([total])], ignore_index=True)

    lignes = _df_vers_lignes(agg)
    ws.update("A1", lignes)

    _appliquer_formatage_entete(sh, ws, len(agg.columns))
    _appliquer_format_monnetaire(sh, ws, [1, 2, 3], len(agg))
    print(f"  📊 Onglet '{nom_onglet}' écrit ({len(agg) - 1} postes + total)")


def _ecrire_onglet_comparaison(
    sh: gspread.Spreadsheet,
    comp: pd.DataFrame,
) -> None:
    """Écrire l'onglet Comparaison : delta N vs N-1 par poste."""
    ws = _obtenir_ou_creer_feuille(sh, "Comparaison")

    if comp.empty:
        ws.update("A1", [["Aucune donnée de comparaison disponible."]])
        return

    df_affichage = comp.copy()

    # Noms de colonnes lisibles
    renommage: dict[str, str] = {
        "type_charge": "Type de charge",
        "annee_n": "Année N",
        "annee_n1": "Année N-1",
        "total_n": "Total N (€)",
        "total_n1": "Total N-1 (€)",
        "delta": "Delta (€)",
        "delta_pct": "Delta (%)",
    }
    if "cle_repartition" in df_affichage.columns:
        renommage["cle_repartition"] = "Clé de répartition"

    df_affichage = df_affichage.rename(columns=renommage)
    colonnes_affichees = [c for c in renommage.values() if c in df_affichage.columns]
    df_affichage = df_affichage[colonnes_affichees]

    lignes = _df_vers_lignes(df_affichage)
    ws.update("A1", lignes)

    nb_col = len(df_affichage.columns)
    _appliquer_formatage_entete(sh, ws, nb_col)

    # Colonnes monétaires
    cols_eur = [i for i, c in enumerate(df_affichage.columns) if "(€)" in c]
    _appliquer_format_monnetaire(sh, ws, cols_eur, len(df_affichage))

    print(f"  📊 Onglet 'Comparaison' écrit ({len(df_affichage)} lignes)")


def _ecrire_onglet_synthese(
    sh: gspread.Spreadsheet,
    comp: pd.DataFrame,
) -> None:
    """Écrire l'onglet Synthèse : top hausses en € et en %."""
    ws = _obtenir_ou_creer_feuille(sh, "Synthèse")

    if comp.empty:
        ws.update("A1", [["Aucune donnée de synthèse disponible."]])
        return

    hausses_eur = top_hausses(comp, colonne_tri="delta", n=20)
    hausses_pct = top_hausses(comp, colonne_tri="delta_pct", n=20)

    renommage: dict[str, str] = {
        "type_charge": "Type de charge",
        "annee_n": "Année N",
        "annee_n1": "Année N-1",
        "total_n": "Total N (€)",
        "total_n1": "Total N-1 (€)",
        "delta": "Delta (€)",
        "delta_pct": "Delta (%)",
    }
    if "cle_repartition" in comp.columns:
        renommage["cle_repartition"] = "Clé de répartition"

    colonnes_affichees = [c for c in renommage.values() if c in hausses_eur.rename(columns=renommage).columns]

    def _preparer(df: pd.DataFrame) -> pd.DataFrame:
        d = df.rename(columns=renommage)
        return d[[c for c in colonnes_affichees if c in d.columns]]

    eur = _preparer(hausses_eur)
    pct = _preparer(hausses_pct)

    # Top hausses en €
    ligne_debut = 1
    ws.update(
        f"A{ligne_debut}",
        [[f"TOP 20 HAUSSES EN € (année {comp['annee_n'].max()})"]] + _df_vers_lignes(eur),
    )

    # Top hausses en % (décalé de nb_lignes + 3)
    ligne_pct = ligne_debut + len(eur) + 3
    ws.update(
        f"A{ligne_pct}",
        [[f"TOP 20 HAUSSES EN % (année {comp['annee_n'].max()})"]] + _df_vers_lignes(pct),
    )

    _appliquer_formatage_entete(sh, ws, len(eur.columns))
    print(f"  📊 Onglet 'Synthèse' écrit (top {len(eur)} € + top {len(pct)} %)")
