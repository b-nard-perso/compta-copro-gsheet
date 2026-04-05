"""
Tests du module importation.lecteur_csv.

Couvre :
- Parsing des montants au format français
- Parsing des dates au format JJ/MM/AAAA
- Importation d'un fichier CSV complet
- Gestion des encodages Windows-1252 / utf-8-sig
- Validation du schéma de sortie
"""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from compta_copro.importation.lecteur_csv import (
    _parse_montant_fr,
    importer_dossier,
    importer_fichier,
)


class TestParseMontantFr:
    """Tests de la fonction _parse_montant_fr."""

    def test_montant_simple(self):
        assert _parse_montant_fr("650,47") == pytest.approx(650.47)

    def test_montant_avec_guillemets(self):
        assert _parse_montant_fr('"650,47"') == pytest.approx(650.47)

    def test_montant_avec_apostrophes(self):
        assert _parse_montant_fr("'472,12'") == pytest.approx(472.12)

    def test_montant_avec_separateur_milliers_espace(self):
        assert _parse_montant_fr("1 234,56") == pytest.approx(1234.56)

    def test_montant_avec_separateur_milliers_insecable(self):
        assert _parse_montant_fr("1\u00a0234,56") == pytest.approx(1234.56)

    def test_montant_zero(self):
        assert _parse_montant_fr("0,00") == pytest.approx(0.0)

    def test_montant_vide(self):
        assert _parse_montant_fr("") == pytest.approx(0.0)

    def test_montant_none(self):
        assert _parse_montant_fr(None) == pytest.approx(0.0)

    def test_montant_nan(self):
        import math
        assert _parse_montant_fr(float("nan")) == pytest.approx(0.0)

    def test_montant_negatif(self):
        assert _parse_montant_fr("-123,45") == pytest.approx(-123.45)

    def test_montant_invalide(self):
        with pytest.raises(ValueError, match="Montant non reconnu"):
            _parse_montant_fr("abc")

    def test_montant_guillemets_et_espace(self):
        assert _parse_montant_fr('"59,13"') == pytest.approx(59.13)


class TestImporterFichier:
    """Tests de la fonction importer_fichier."""

    CSV_CONTENU = textwrap.dedent("""\
        DATE;CLE DE REPARTITION;TYPE DE CHARGE;LIBELLE;A REPARTIR;TVA;RECUPERABLE
        18/03/2025;001 - CHARGES GENERALES;100 - CONTRAT D'ENTRETIEN R;ITEC ENTRETIEN 2025;"650,47";"59,13";"650,47"
        15/12/2025;001 - CHARGES GENERALES;110 - CONTRAT ESPACES VERTS R;HARTMANN 4E TRIM 2025;"472,12";"78,69";"472,12"
    """)

    def test_schema_colonnes(self, tmp_path: Path):
        csv = tmp_path / "2025.csv"
        csv.write_text(self.CSV_CONTENU, encoding="utf-8-sig")
        df = importer_fichier(csv)
        assert list(df.columns) == [
            "date", "cle_repartition", "type_charge", "libelle",
            "a_repartir", "tva", "recuperable", "annee",
        ]

    def test_types_colonnes(self, tmp_path: Path):
        csv = tmp_path / "2025.csv"
        csv.write_text(self.CSV_CONTENU, encoding="utf-8-sig")
        df = importer_fichier(csv)
        # pandas >= 2 peut utiliser datetime64[us] au lieu de datetime64[ns]
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert df["a_repartir"].dtype == float
        assert df["tva"].dtype == float
        assert df["recuperable"].dtype == float
        assert df["annee"].dtype == int

    def test_annee_extraite_du_nom(self, tmp_path: Path):
        csv = tmp_path / "2025.csv"
        csv.write_text(self.CSV_CONTENU, encoding="utf-8-sig")
        df = importer_fichier(csv)
        assert (df["annee"] == 2025).all()

    def test_parsing_date(self, tmp_path: Path):
        csv = tmp_path / "2025.csv"
        csv.write_text(self.CSV_CONTENU, encoding="utf-8-sig")
        df = importer_fichier(csv)
        assert df["date"].iloc[0] == pd.Timestamp("2025-03-18")

    def test_parsing_montant(self, tmp_path: Path):
        csv = tmp_path / "2025.csv"
        csv.write_text(self.CSV_CONTENU, encoding="utf-8-sig")
        df = importer_fichier(csv)
        assert df["a_repartir"].iloc[0] == pytest.approx(650.47)
        assert df["tva"].iloc[0] == pytest.approx(59.13)

    def test_nb_lignes(self, tmp_path: Path):
        csv = tmp_path / "2025.csv"
        csv.write_text(self.CSV_CONTENU, encoding="utf-8-sig")
        df = importer_fichier(csv)
        assert len(df) == 2

    def test_nom_fichier_invalide(self, tmp_path: Path):
        csv = tmp_path / "charges.csv"
        csv.write_text(self.CSV_CONTENU, encoding="utf-8-sig")
        with pytest.raises(ValueError, match="année sur 4 chiffres"):
            importer_fichier(csv)

    def test_encodage_windows1252(self, tmp_path: Path):
        contenu = (
            "DATE;CLE DE REPARTITION;TYPE DE CHARGE;LIBELLE;A REPARTIR;TVA;RECUPERABLE\n"
            "18/03/2024;001 - CHARGES GENERALES;100 - ENTRETIEN;Été été;\"100,00\";\"10,00\";\"100,00\"\n"
        )
        csv = tmp_path / "2024.csv"
        csv.write_bytes(contenu.encode("cp1252"))
        df = importer_fichier(csv)
        assert len(df) == 1
        assert "été" in df["libelle"].iloc[0].lower()


class TestImporterDossier:
    """Tests de la fonction importer_dossier."""

    CSV_2024 = textwrap.dedent("""\
        DATE;CLE DE REPARTITION;TYPE DE CHARGE;LIBELLE;A REPARTIR;TVA;RECUPERABLE
        06/03/2024;001 - CHARGES GENERALES;100 - CONTRAT D'ENTRETIEN;ITEC 2024;"645,95";"58,72";"645,95"
        31/12/2024;001 - CHARGES GENERALES;110 - CONTRAT ESPACES VERTS;HARTMANN 4E TRIM 2024;"465,83";"77,64";"465,83"
    """)

    CSV_2025 = textwrap.dedent("""\
        DATE;CLE DE REPARTITION;TYPE DE CHARGE;LIBELLE;A REPARTIR;TVA;RECUPERABLE
        18/03/2025;001 - CHARGES GENERALES;100 - CONTRAT D'ENTRETIEN R;ITEC 2025;"650,47";"59,13";"650,47"
        15/12/2025;001 - CHARGES GENERALES;110 - CONTRAT ESPACES VERTS R;HARTMANN 4E TRIM 2025;"472,12";"78,69";"472,12"
    """)

    def test_fusion_deux_annees(self, tmp_path: Path):
        (tmp_path / "2024.csv").write_text(self.CSV_2024, encoding="utf-8-sig")
        (tmp_path / "2025.csv").write_text(self.CSV_2025, encoding="utf-8-sig")
        df = importer_dossier(tmp_path)
        assert len(df) == 4
        assert set(df["annee"].unique()) == {2024, 2025}

    def test_tri_par_annee_date(self, tmp_path: Path):
        (tmp_path / "2024.csv").write_text(self.CSV_2024, encoding="utf-8-sig")
        (tmp_path / "2025.csv").write_text(self.CSV_2025, encoding="utf-8-sig")
        df = importer_dossier(tmp_path)
        assert df["annee"].iloc[0] == 2024
        assert df["annee"].iloc[-1] == 2025

    def test_dossier_inexistant(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            importer_dossier(tmp_path / "inexistant")

    def test_dossier_sans_csv(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Aucun fichier CSV"):
            importer_dossier(tmp_path)
