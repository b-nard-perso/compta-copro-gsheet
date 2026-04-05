"""
Calcul des agrégations et comparaisons inter-annuelles des dépenses de copropriété.

Fonctions principales :
    agregation_annee_poste   Total par (année, type_charge) et optionnellement par cle_repartition
    comparaison_n_n1         Tableau N vs N-1 par poste (total, delta, delta_pct)
    top_hausses              Top N des plus fortes hausses (en € ou en %)
"""

from __future__ import annotations

import pandas as pd

# Garde-fous pour le calcul du delta_pct
_SEUIL_MONTANT_MIN = 10.0       # Montant minimal pour calculer le %
_SEUIL_PCT_MAX = 1_000.0        # Cap à 1 000 % pour éviter les valeurs aberrantes


def agregation_annee_poste(
    df: pd.DataFrame,
    par_cle: bool = False,
) -> pd.DataFrame:
    """
    Calculer le total des dépenses par année et par poste (TYPE DE CHARGE).

    Parameters
    ----------
    df:
        DataFrame normalisé (schéma interne).
    par_cle:
        Si True, ventiler aussi par CLE DE REPARTITION.

    Returns
    -------
    pd.DataFrame
        Colonnes : [cle_repartition (optionnel), type_charge, annee, total_a_repartir,
                    total_tva, total_recuperable, nb_lignes]
    """
    groupby = ["cle_repartition", "type_charge", "annee"] if par_cle else ["type_charge", "annee"]
    agg = (
        df.groupby(groupby, sort=True)
        .agg(
            total_a_repartir=("a_repartir", "sum"),
            total_tva=("tva", "sum"),
            total_recuperable=("recuperable", "sum"),
            nb_lignes=("libelle", "count"),
        )
        .reset_index()
    )
    return agg


def comparaison_n_n1(
    df: pd.DataFrame,
    par_cle: bool = False,
) -> pd.DataFrame:
    """
    Comparer les dépenses année N versus année N-1 par poste.

    Pour chaque couple (poste, année N), on cherche la même année N-1.
    Les postes présents seulement en N ou seulement en N-1 sont conservés
    (avec NaN pour l'année manquante).

    Parameters
    ----------
    df:
        DataFrame normalisé.
    par_cle:
        Si True, ventiler aussi par CLE DE REPARTITION.

    Returns
    -------
    pd.DataFrame
        Colonnes : [type_charge, annee_n, total_n, total_n1, delta, delta_pct]
        Triées par annee_n DESC puis delta DESC.
    """
    agg = agregation_annee_poste(df, par_cle=par_cle)

    groupby_cols = ["cle_repartition", "type_charge"] if par_cle else ["type_charge"]

    annees = sorted(agg["annee"].unique())
    resultats: list[pd.DataFrame] = []

    for i, annee_n in enumerate(annees):
        if i == 0:
            continue
        annee_n1 = annees[i - 1]

        donnees_n = agg[agg["annee"] == annee_n][groupby_cols + ["total_a_repartir"]].rename(
            columns={"total_a_repartir": "total_n"}
        )
        donnees_n1 = agg[agg["annee"] == annee_n1][groupby_cols + ["total_a_repartir"]].rename(
            columns={"total_a_repartir": "total_n1"}
        )

        fusion = donnees_n.merge(donnees_n1, on=groupby_cols, how="outer")
        fusion["annee_n"] = annee_n
        fusion["annee_n1"] = annee_n1
        fusion["total_n"] = fusion["total_n"].fillna(0.0)
        fusion["total_n1"] = fusion["total_n1"].fillna(0.0)
        fusion["delta"] = fusion["total_n"] - fusion["total_n1"]
        fusion["delta_pct"] = fusion.apply(
            lambda row: _calculer_delta_pct(row["total_n"], row["total_n1"]),
            axis=1,
        )
        resultats.append(fusion)

    if not resultats:
        colonnes = groupby_cols + ["annee_n", "annee_n1", "total_n", "total_n1", "delta", "delta_pct"]
        return pd.DataFrame(columns=colonnes)

    resultat_final = pd.concat(resultats, ignore_index=True)
    resultat_final = resultat_final.sort_values(
        ["annee_n", "delta"], ascending=[False, False]
    ).reset_index(drop=True)

    colonnes_ordonnees = groupby_cols + ["annee_n", "annee_n1", "total_n", "total_n1", "delta", "delta_pct"]
    return resultat_final[colonnes_ordonnees]


def _calculer_delta_pct(total_n: float, total_n1: float) -> float | None:
    """
    Calculer le pourcentage de variation entre N et N-1.

    Garde-fous :
    - Retourne None si total_n1 < seuil (division par zéro ou valeur trop faible).
    - Plafonne à ±_SEUIL_PCT_MAX %.

    Parameters
    ----------
    total_n:
        Montant de l'année N.
    total_n1:
        Montant de l'année N-1.

    Returns
    -------
    float | None
    """
    if abs(total_n1) < _SEUIL_MONTANT_MIN:
        return None
    pct = (total_n - total_n1) / abs(total_n1) * 100.0
    # Plafonner pour éviter les valeurs aberrantes
    if pct > _SEUIL_PCT_MAX:
        return _SEUIL_PCT_MAX
    if pct < -_SEUIL_PCT_MAX:
        return -_SEUIL_PCT_MAX
    return round(pct, 2)


def top_hausses(
    df_comparaison: pd.DataFrame,
    colonne_tri: str = "delta",
    n: int = 20,
    annee_n: int | None = None,
) -> pd.DataFrame:
    """
    Retourner le top N des postes avec les plus fortes hausses.

    Parameters
    ----------
    df_comparaison:
        Résultat de :func:`comparaison_n_n1`.
    colonne_tri:
        ``'delta'`` pour les hausses en €, ``'delta_pct'`` pour les hausses en %.
    n:
        Nombre de postes à retourner.
    annee_n:
        Filtrer sur une année N spécifique (si None, prend la plus récente).

    Returns
    -------
    pd.DataFrame
        Top N trié par la colonne demandée (décroissant).
    """
    if df_comparaison.empty:
        return df_comparaison.copy()

    if annee_n is None:
        annee_n = df_comparaison["annee_n"].max()

    filtre = df_comparaison[df_comparaison["annee_n"] == annee_n].copy()

    if colonne_tri == "delta_pct":
        # Exclure les lignes sans delta_pct calculable
        filtre = filtre.dropna(subset=["delta_pct"])

    filtre = filtre.sort_values(colonne_tri, ascending=False).head(n)
    return filtre.reset_index(drop=True)
