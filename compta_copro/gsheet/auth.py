"""
Authentification OAuth 2.0 pour les APIs Google Sheets et Drive.

Flux « application installée » : une fenêtre navigateur s'ouvre lors du premier
lancement. Le token est ensuite sauvegardé dans ``credentials/token.json``.

Pour configurer :
1. Créer un projet sur https://console.cloud.google.com/
2. Activer les APIs « Google Sheets » et « Google Drive »
3. Créer des identifiants OAuth 2.0 (type « Application de bureau »)
4. Télécharger le fichier JSON et le placer dans ``credentials/client_secret.json``
"""

from __future__ import annotations

from pathlib import Path

import google.auth.exceptions
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Périmètres (scopes) nécessaires
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_NOM_CLIENT_SECRET = "client_secret.json"
_NOM_TOKEN = "token.json"


def obtenir_credentials(dossier_credentials: Path = Path("credentials")) -> Credentials:
    """
    Obtenir (ou renouveler) les credentials OAuth 2.0.

    Parameters
    ----------
    dossier_credentials:
        Dossier contenant ``client_secret.json`` et (optionnellement) ``token.json``.

    Returns
    -------
    google.oauth2.credentials.Credentials
        Credentials valides.

    Raises
    ------
    FileNotFoundError
        Si ``client_secret.json`` est absent.
    """
    chemin_secret = dossier_credentials / _NOM_CLIENT_SECRET
    chemin_token = dossier_credentials / _NOM_TOKEN

    if not chemin_secret.exists():
        raise FileNotFoundError(
            f"Fichier manquant : {chemin_secret}\n"
            "Consultez le README pour créer votre projet Google Cloud et télécharger "
            "le fichier client_secret.json."
        )

    creds: Credentials | None = None

    if chemin_token.exists():
        creds = Credentials.from_authorized_user_file(str(chemin_token), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except google.auth.exceptions.RefreshError:
                creds = None

        if not creds:
            flux = InstalledAppFlow.from_client_secrets_file(str(chemin_secret), SCOPES)
            creds = flux.run_local_server(port=0)

        chemin_token.write_text(creds.to_json(), encoding="utf-8")

    return creds
