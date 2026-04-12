# Journal des modifications

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet respecte [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

## [0.1.0] — 2025-04-05

### Ajouté

- Initialisation du projet Python entièrement en français.
- Module `compta_copro/importation/lecteur_csv.py` :
  - Import de fichiers CSV (un par année, nommés `AAAA.csv`).
  - Détection automatique de l'encodage (utf-8-sig, cp1252, latin-1).
  - Normalisation du schéma interne (date, cle_repartition, type_charge, libelle, a_repartir, tva, recuperable, annee).
  - Parsing des montants au format français (virgule décimale, guillemets).
- Module `compta_copro/analyse/agregation.py` :
  - `agregation_annee_poste` : total par (année, type de charge).
  - `comparaison_n_n1` : tableau delta N vs N-1 avec gestion des nouveaux postes.
  - `top_hausses` : top 20 des plus fortes hausses en € et en %.
  - Garde-fous sur le calcul du delta_pct (seuil minimal, plafond).
- Module `compta_copro/gsheet/` :
  - Authentification OAuth 2.0 "application installée" (`auth.py`).
  - Génération du Google Sheet avec onglets par année, Comparaison, Synthèse (`generateur.py`).
  - Formatage léger : en-têtes en gras, 1ère ligne gelée, filtre, format monétaire €.
- Module `compta_copro/pdf/extract_texte.py` (stub/expérimental) :
  - Extraction de texte depuis PDF numérique (pdfplumber / pypdf en fallback).
  - Support OCR via Tesseract (dépendance optionnelle).
- CLI `python -m compta_copro` avec commandes :
  - `importer-csv` — import et normalisation des CSV.
  - `analyser` — calcul des agrégations et comparaisons.
  - `generer-gsheet` — création/mise à jour du Google Sheet.
  - `extraire-pdf` — extraction de texte PDF.
- Tests pytest : parsing montants FR, parsing dates, calcul delta_pct, import CSV.
- Exemples anonymisés : `examples/2024.csv`, `examples/2025.csv`.
- Fichiers de configuration : `pyproject.toml`, `.env.example`, `.gitignore`.
- Documentation : `README.md` (procédure Google API pas-à-pas), `CHANGELOG.md`, `LICENSE` (MIT).
