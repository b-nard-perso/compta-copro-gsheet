# compta-copro-gsheet — Analyse des dépenses de copropriété

> Outil Python pour importer les releves CSV du syndic, calculer les variations
> annuelles et generer un **classeur Excel (.xlsx)** facilement partageable.

[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

---

## Sommaire

1. [Fonctionnalités](#fonctionnalités)
2. [Prérequis](#prérequis)
3. [Installation](#installation)
4. [Option Google Sheets (facultatif)](#option-google-sheets-facultatif)
5. [Utilisation](#utilisation)
6. [Structure du projet](#structure-du-projet)
7. [Format des fichiers CSV](#format-des-fichiers-csv)
8. [Extraction PDF (expérimental)](#extraction-pdf-expérimental)
9. [Développement et tests](#développement-et-tests)

---

## Fonctionnalités

- 📥 **Import CSV** — lit les exports du syndic (encodage Windows-1252/latin-1/utf-8-sig, séparateur `;`, décimales `,`).
- 🔄 **Fusion pluri-annuelle** — concatène les fichiers par année et normalise le schéma.
- 📊 **Agrégations** — total par poste et par année, comparaison N vs N-1, top 20 hausses.
- 📘 **Export Excel (.xlsx)** — produit un classeur prêt à copier-coller/importer avec :
  - un onglet par année (dépenses par TYPE DE CHARGE + totaux),
  - un onglet **Comparaison** (delta en € et en %),
  - un onglet **Synthèse** (top hausses).
- 📋 **Google Sheet (optionnel)** — disponible via extra d'installation dédié.
- 📄 **PDF** *(expérimental)* — extraction de texte depuis des PDF numériques ou scannés (OCR Tesseract).

---

## Prérequis

- **Python 3.10 ou supérieur**

---

## Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/b-nard-perso/compta-copro-gsheet.git
cd compta-copro-gsheet

# 2. Créer un environnement virtuel (recommandé)
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Installer le projet
pip install -e .

# Optionnel : support Google Sheets
pip install -e ".[gsheet]"

# Avec le support PDF (optionnel)
pip install -e ".[pdf]"

# Avec le support OCR (optionnel, nécessite Tesseract)
pip install -e ".[ocr]"

# Avec les outils de développement
pip install -e ".[dev]"
```

---

## Option Google Sheets (facultatif)

Cette section n'est utile que si vous souhaitez utiliser la commande `generer-gsheet`.
Le flux recommande par defaut est `generer-xlsx` (sans API Google).

### Étape 1 — Créer un projet Google Cloud

1. Rendez-vous sur [https://console.cloud.google.com/](https://console.cloud.google.com/).
2. Cliquez sur **Sélectionner un projet** → **Nouveau projet**.
3. Donnez un nom (ex : `ComptaCopro`) et cliquez sur **Créer**.

### Étape 2 — Activer les APIs

Dans le menu de gauche : **APIs et services** → **Bibliothèque**.

Recherchez et activez les deux APIs suivantes :

- **Google Sheets API**
- **Google Drive API**

### Étape 3 — Créer les identifiants OAuth 2.0

1. **APIs et services** → **Identifiants** → **Créer des identifiants** → **ID client OAuth**.
2. Si demandé, configurez l'**écran de consentement** :
   - Type d'utilisateur : **Externe** (ou Interne si vous avez Google Workspace).
   - Nom de l'application : `ComptaCopro` (ou autre).
   - Ajoutez votre adresse e-mail comme **utilisateur test**.
3. Type d'application : **Application de bureau**.
4. Cliquez sur **Créer** puis **Télécharger le JSON**.
5. Renommez le fichier téléchargé en `client_secret.json` et placez-le dans le dossier `credentials/` du projet.

### Étape 4 — Premier lancement (autorisation)

Au premier lancement de la commande `generer-gsheet`, une fenêtre de navigateur
s'ouvre pour vous demander d'autoriser l'accès. Après accord, un fichier
`credentials/token.json` est créé automatiquement. Les lancements suivants ne
redemanderont pas l'autorisation.

> ⚠️ **Important** : les fichiers `credentials/client_secret.json` et
> `credentials/token.json` sont ignorés par git (`.gitignore`). Ne les partagez
> jamais et ne les poussez pas sur GitHub.

---

## Utilisation

### Étape 1 — Importer les CSV

Placez vos fichiers CSV dans le dossier `data/csv/` en les nommant par année
(ex : `2024.csv`, `2025.csv`).

```bash
python -m compta_copro importer-csv --input data/csv --sortie data/intermediaire/depenses.parquet
```

Pour tester avec les exemples fournis :

```bash
python -m compta_copro importer-csv --input examples --sortie data/intermediaire/depenses.parquet
```

### Étape 2 — Calculer les analyses

```bash
python -m compta_copro analyser \
    --input data/intermediaire/depenses.parquet \
    --output data/sorties
```

Les fichiers CSV suivants sont produits dans `data/sorties/` :

- `agregation_annee_poste.csv` — total par (année, poste)
- `comparaison_n_n1.csv` — delta N vs N-1
- `top_hausses_eur.csv` — top 20 hausses en €
- `top_hausses_pct.csv` — top 20 hausses en %

### Étape 3 — Générer le classeur Excel (.xlsx)

```bash
python -m compta_copro generer-xlsx \
  --input data/intermediaire/depenses.parquet \
  --sortie data/sorties/rapport_copro_2025.xlsx
```

Pour un usage "annee courante uniquement" (recommande si les annees passees
sont deja dans votre fichier partage) :

```bash
python -m compta_copro generer-xlsx \
  --input data/intermediaire/depenses.parquet \
  --sortie data/sorties/rapport_copro_2025.xlsx \
  --annee-courante
```

Le fichier `.xlsx` contient un onglet par annee, un onglet de comparaison et un
onglet de synthese. Avec `--annee-courante`, seul l'onglet de l'annee la plus
recente est genere, et la comparaison reste limitee a N vs N-1.

### Étape 4 (optionnelle) — Générer le Google Sheet

```bash
python -m compta_copro generer-gsheet \
    --input data/intermediaire/depenses.parquet \
    --spreadsheet "Copro - Analyse 2025"
```

L'URL du Google Sheet est affichée à la fin de l'exécution. Vous pouvez ensuite
le partager avec les membres du conseil syndical via Google Drive.

### Aide

```bash
python -m compta_copro --help
python -m compta_copro importer-csv --help
python -m compta_copro analyser --help
python -m compta_copro generer-xlsx --help
python -m compta_copro generer-gsheet --help
python -m compta_copro extraire-pdf --help
```

---

## Structure du projet

```text
compta-copro-gsheet/
├── compta_copro/               # Package Python principal
│   ├── __init__.py
│   ├── __main__.py             # Point d'entrée : python -m compta_copro
│   ├── cli.py                  # Interface en ligne de commande
│   ├── importation/
│   │   └── lecteur_csv.py      # Import et normalisation des CSV
│   ├── analyse/
│   │   └── agregation.py       # Agrégations et comparaisons inter-annuelles
│   ├── xlsx/
│   │   └── generateur.py       # Génération du classeur Excel (.xlsx)
│   ├── gsheet/
│   │   ├── auth.py             # Authentification OAuth Google
│   │   └── generateur.py       # Génération du Google Sheet
│   └── pdf/
│       └── extract_texte.py    # Extraction de texte PDF (expérimental)
├── tests/                      # Tests pytest
│   ├── test_importation.py
│   ├── test_analyse.py
│   └── test_xlsx.py
├── examples/                   # Exemples CSV anonymisés
│   ├── 2024.csv
│   └── 2025.csv
├── data/                       # Données (ignorées par git)
│   ├── csv/                    # → vos fichiers CSV par année
│   ├── intermediaire/          # → fichiers Parquet intermédiaires
│   ├── sorties/                # → CSV de synthèse
│   └── pdf/                    # → fichiers PDF à analyser
├── credentials/                # Credentials Google OAuth (ignorés par git)
│   └── .gitkeep
├── pyproject.toml              # Configuration du projet
├── .env.example                # Exemple de variables d'environnement
├── .gitignore
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## Format des fichiers CSV

Les fichiers CSV attendus ont le format exporté par les logiciels de syndic
(séparateur `;`, encodage Windows-1252 ou UTF-8, décimales `,`) :

```csv
DATE;CLE DE REPARTITION;TYPE DE CHARGE;LIBELLE;A REPARTIR;TVA;RECUPERABLE
18/03/2025;001 - CHARGES GENERALES;100 - CONTRAT D'ENTRETIEN R;ENTREPRISE A - ENTRETIEN 2025;"650,47";"59,13";"650,47"
```

| Colonne           | Description                                | Type normalisé |
|-------------------|--------------------------------------------|----------------|
| DATE              | Date de la dépense (JJ/MM/AAAA)            | datetime       |
| CLE DE REPARTITION| Code de répartition des charges            | str            |
| TYPE DE CHARGE    | Code et libellé du type de charge          | str            |
| LIBELLE           | Description de la dépense                  | str            |
| A REPARTIR        | Montant à répartir (format FR)             | float          |
| TVA               | Montant TVA (format FR)                    | float          |
| RECUPERABLE       | Montant récupérable (format FR)            | float          |

Les fichiers doivent être nommés par leur année : `2024.csv`, `2025.csv`, etc.

---

## Extraction PDF (expérimental)

```bash
# PDF numérique (texte natif)
python -m compta_copro extraire-pdf data/pdf/releve_2025.pdf --sortie data/sorties/releve_2025.txt

# PDF scanné (OCR — nécessite Tesseract)
python -m compta_copro extraire-pdf data/pdf/facture_scan.pdf --ocr --sortie data/sorties/facture.txt
```

Pour l'OCR, installez Tesseract sur votre système :

- **Windows** : [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
  (cochez le pack langue "French" lors de l'installation)
- **macOS** : `brew install tesseract tesseract-lang`
- **Linux** : `sudo apt install tesseract-ocr tesseract-ocr-fra`

---

## Développement et tests

```bash
# Installer les dépendances de développement
pip install -e ".[dev]"

# Lancer les tests
pytest

# Avec la couverture de code
pytest --cov=compta_copro --cov-report=html
```
