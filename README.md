# Dashboard Compteurs Routiers

Tableau de bord d'analyse de trafic routier basé sur Dash et Plotly.  
Cette application est **générique** : elle s'adapte automatiquement au site et aux directions détectés dans les fichiers CSV de données brutes. Elle se base sur l'export des mesures individuelles depuis la plateforme WebStation d'une station de comptage routier.

## Fonctionnalités

*   **Détection automatique** du nom du site et des sens de circulation.
*   **Performance** : Utilisation du format Parquet pour un chargement instantané des données historiques.
*   **Analyses** :
    *   Synthèse globale (Parts modales, TMJ).
    *   Heatmap (Jour/Heure) des flux.
    *   Comparaison pluriannuelle (Saisonnalité, TMJ par an).
*   **Interface** : Graphiques interactifs et bulles d'aide.
*   **Rapport** : Export d'un rapport complet au format HTML (incluant tableaux de synthèse, graphiques et lexique).

## Installation Locale

1.  **Prérequis** : Python 3.9 ou supérieur.
2.  **Installation des dépendances** :
    ```bash
    cd compteurs_dashboard
    python -m venv .venv
    source .venv/bin/activate # ou .venv\Scripts\activate sous windows
    pip install -r requirements.txt
    ```

## Préparation des Données

Avant de lancer l'application, vous devez convertir les fichiers CSV bruts en un format optimisé.

1.  Placez vos fichiers `WebTraffic_*.csv` dans le dossier parent (racine du projet) ou spécifiez un dossier.
2.  Lancez le script de construction :
    ```bash
    # Si les CSV sont dans le dossier parent (défaut)
    python build_dataset.py

    # Ou spécifiez un dossier source personnalisé
    python build_dataset.py --source "C:/Chemin/Vers/Mes/CSVs"
    ```
    *Ce script va générer un dossier `data/parquet_store` et un fichier `data/metadata.json`.*

##  Démarrage

Une fois les données prêtes :
```bash
python app.py
```
L'application sera accessible sur `http://localhost:8050`.

---

## Déploiement sur Serveur (Linux/Ubuntu)

Voici la procédure pour mettre en production l'application avec **Gunicorn** et **Nginx**.

### 1. Préparation du Serveur
```bash
sudo apt update && sudo apt install python3-pip python3-venv nginx git -y
```

### 2. Installation de l'App
Créez un utilisateur ou utilisez www-data. L'utilisateur créé s'appellera WHOAMI dans la suite de la documentation, il sera à remplacer par l'utilisateur créé.

```bash
# Clonez votre projet ou copiez les fichiers dans /var/www ou /home/WHOAMI
cd /home/WHOAMI/compteurs_dashboard

# Créer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Générer les données (Assurez-vous que vos CSV sont présents)
python build_dataset.py --source ..
```

### 3. Service Systemd (Gunicorn)
Créez le fichier `/etc/systemd/system/compteurs.service` :

```ini
[Unit]
Description=Gunicorn Compteurs Dashboard
After=network.target

[Service]
User=WHOAMI
WorkingDirectory=/home/WHOAMI/compteurs_dashboard
Environment="PATH=/home/user/compteurs_dashboard/.venv/bin"
# Lancer l'app avec 3 workers
ExecStart=/home/WHOAMI/compteurs_dashboard/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8050 app:server

[Install]
WantedBy=multi-user.target
```
Remplacez WHOAMI par l'utilisateur qui lance l'application


Activez le service :
```bash
sudo systemctl start compteurs
sudo systemctl enable compteurs
```

### 4. Configuration Nginx (Proxy Inverse)
Créez le fichier `/etc/nginx/sites-available/compteurs` :

```nginx
server {
    listen 80;
    server_name votre.domaine. ou_votre_ip;

    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Activez le site :
```bash
sudo ln -s /etc/nginx/sites-available/compteurs /etc/nginx/sites-enabled
sudo systemctl restart nginx
```

### Mise à jour Annuelle des Données

1.  Déposez le nouveau fichier CSV sur le serveur.
2.  Lancez le script de génération des datasets :
    ```bash
    /home/user/compteurs/compteurs_dashboard/venv/bin/python build_dataset.py --source /dossier/csv
    ```
3.  Puis redémarrez le service pour prendre en compte les changements :
    ```bash
    sudo systemctl restart compteurs
    ```


### Possibilité d'évolutions
- Script automatique de mise à jour des données (Eventuellement un dossier spécifique accesible avec une interface graphique, dès qu'on repère un changement dans le dossier relance le script build_dataset)
- Pouvoir intégrer plusieurs sites
- Retravailler les graphiques et mettre des interprétations
- Penser à quelles données on veut afficher