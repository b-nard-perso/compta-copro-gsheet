"""
Point d'entrée CLI du package compta_copro.

Utilisation :
    python -m compta_copro <commande> [options]

Commandes disponibles :
    importer-csv      Importer les CSV d'un dossier
    analyser          Calculer les agrégations et comparaisons
    generer-xlsx      Produire un classeur Excel (.xlsx)
    generer-gsheet    Créer ou mettre à jour le Google Sheet
    extraire-pdf      Extraire le texte d'un fichier PDF (expérimental)
"""

from compta_copro.cli import principale

if __name__ == "__main__":
    principale()
