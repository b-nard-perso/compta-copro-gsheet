"""
Tests du module analyse.agregation.

Couvre :
- agregation_annee_poste
- comparaison_n_n1
- top_hausses
- _calculer_delta_pct (gestion division par zéro, garde-fous)
"""

from __future__ import annotations

import pandas as pd
import pytest

from compta_copro.analyse.agregation import (
    _calculer_delta_pct,
    agregation_annee_poste,
    comparaison_n_n1,
    top_hausses,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def df_exemple() -> pd.DataFrame:
    """DataFrame minimal couvrant deux années et plusieurs postes."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-03-01", "2024-06-01", "2024-12-01", "2025-03-01", "2025-06-01", "2025-12-01"]
            ),
            "cle_repartition": ["001 - CG"] * 6,
            "type_charge": [
                "100 - ENTRETIEN", "110 - ESPACES VERTS", "110 - ESPACES VERTS",
                "100 - ENTRETIEN", "110 - ESPACES VERTS", "120 - NOUVEAU POSTE",
            ],
            "libelle": ["A", "B", "C", "D", "E", "F"],
            "a_repartir": [645.95, 465.83, 465.83, 650.47, 472.12, 100.0],
            "tva": [58.72, 77.64, 77.64, 59.13, 78.69, 10.0],
            "recuperable": [645.95, 465.83, 465.83, 650.47, 472.12, 100.0],
            "annee": [2024, 2024, 2024, 2025, 2025, 2025],
        }
    )


# ---------------------------------------------------------------------------
# Tests agregation_annee_poste
# ---------------------------------------------------------------------------


class TestAgregationAnneePoste:
    def test_colonnes_sorties(self, df_exemple):
        agg = agregation_annee_poste(df_exemple)
        assert "type_charge" in agg.columns
        assert "annee" in agg.columns
        assert "total_a_repartir" in agg.columns
        assert "nb_lignes" in agg.columns

    def test_somme_correcte(self, df_exemple):
        agg = agregation_annee_poste(df_exemple)
        ligne = agg[(agg["annee"] == 2024) & (agg["type_charge"] == "110 - ESPACES VERTS")]
        assert ligne["total_a_repartir"].iloc[0] == pytest.approx(465.83 + 465.83)

    def test_par_cle(self, df_exemple):
        agg = agregation_annee_poste(df_exemple, par_cle=True)
        assert "cle_repartition" in agg.columns

    def test_nb_lignes_correct(self, df_exemple):
        agg = agregation_annee_poste(df_exemple)
        ligne = agg[(agg["annee"] == 2024) & (agg["type_charge"] == "110 - ESPACES VERTS")]
        assert ligne["nb_lignes"].iloc[0] == 2


# ---------------------------------------------------------------------------
# Tests comparaison_n_n1
# ---------------------------------------------------------------------------


class TestComparaisonNN1:
    def test_colonnes_sorties(self, df_exemple):
        comp = comparaison_n_n1(df_exemple)
        for col in ("type_charge", "annee_n", "annee_n1", "total_n", "total_n1", "delta", "delta_pct"):
            assert col in comp.columns

    def test_delta_calcule(self, df_exemple):
        comp = comparaison_n_n1(df_exemple)
        ligne = comp[comp["type_charge"] == "100 - ENTRETIEN"]
        assert ligne["delta"].iloc[0] == pytest.approx(650.47 - 645.95)

    def test_poste_nouveau_total_n1_zero(self, df_exemple):
        """Un poste inexistant en N-1 doit avoir total_n1 = 0."""
        comp = comparaison_n_n1(df_exemple)
        ligne = comp[comp["type_charge"] == "120 - NOUVEAU POSTE"]
        assert ligne["total_n1"].iloc[0] == pytest.approx(0.0)
        assert ligne["total_n"].iloc[0] == pytest.approx(100.0)

    def test_annee_n_correcte(self, df_exemple):
        comp = comparaison_n_n1(df_exemple)
        assert (comp["annee_n"] == 2025).all()

    def test_dataframe_vide_une_seule_annee(self):
        """Avec une seule année, aucune comparaison n'est possible."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-01-01"]),
                "cle_repartition": ["001"],
                "type_charge": ["100 - ENTRETIEN"],
                "libelle": ["test"],
                "a_repartir": [100.0],
                "tva": [10.0],
                "recuperable": [100.0],
                "annee": [2025],
            }
        )
        comp = comparaison_n_n1(df)
        assert comp.empty


# ---------------------------------------------------------------------------
# Tests _calculer_delta_pct
# ---------------------------------------------------------------------------


class TestCalculerDeltaPct:
    def test_hausse(self):
        pct = _calculer_delta_pct(110.0, 100.0)
        assert pct == pytest.approx(10.0)

    def test_baisse(self):
        pct = _calculer_delta_pct(90.0, 100.0)
        assert pct == pytest.approx(-10.0)

    def test_stable(self):
        pct = _calculer_delta_pct(100.0, 100.0)
        assert pct == pytest.approx(0.0)

    def test_division_par_zero(self):
        """Retourner None si le montant N-1 est trop faible (garde-fou)."""
        assert _calculer_delta_pct(100.0, 0.0) is None

    def test_montant_n1_inferieur_seuil(self):
        """Retourner None si N-1 est inférieur au seuil minimal."""
        assert _calculer_delta_pct(100.0, 5.0) is None

    def test_cap_maximum(self):
        """Le delta_pct est plafonné à _SEUIL_PCT_MAX."""
        from compta_copro.analyse.agregation import _SEUIL_PCT_MAX
        pct = _calculer_delta_pct(1_000_000.0, 10.0)
        # total_n1 = 10, juste au-dessus du seuil de 10
        # → calcul effectué mais plafonné
        assert pct == pytest.approx(_SEUIL_PCT_MAX)

    def test_cap_minimum(self):
        """Le delta_pct est plafonné à -_SEUIL_PCT_MAX."""
        from compta_copro.analyse.agregation import _SEUIL_PCT_MAX
        # total_n1 juste au-dessus du seuil, total_n très négatif → cap déclenché
        pct = _calculer_delta_pct(-_SEUIL_PCT_MAX * 1000, 10.0)
        assert pct == pytest.approx(-_SEUIL_PCT_MAX)


# ---------------------------------------------------------------------------
# Tests top_hausses
# ---------------------------------------------------------------------------


class TestTopHausses:
    def test_top_n(self, df_exemple):
        comp = comparaison_n_n1(df_exemple)
        top = top_hausses(comp, colonne_tri="delta", n=2)
        assert len(top) <= 2

    def test_tri_decroissant(self, df_exemple):
        comp = comparaison_n_n1(df_exemple)
        top = top_hausses(comp, colonne_tri="delta", n=10)
        assert top["delta"].is_monotonic_decreasing

    def test_top_pct_exclut_nan(self, df_exemple):
        """Les lignes avec delta_pct=None (nouveau poste) doivent être exclues du top %."""
        comp = comparaison_n_n1(df_exemple)
        # Le poste "120 - NOUVEAU POSTE" a total_n1=0 donc delta_pct=None
        top_pct = top_hausses(comp, colonne_tri="delta_pct", n=20)
        assert top_pct["delta_pct"].notna().all()

    def test_dataframe_vide(self):
        comp = pd.DataFrame(
            columns=["type_charge", "annee_n", "annee_n1", "total_n", "total_n1", "delta", "delta_pct"]
        )
        top = top_hausses(comp, colonne_tri="delta", n=20)
        assert top.empty
