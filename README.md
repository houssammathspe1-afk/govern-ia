# Govern IA

Govern IA est un prototype étudiant de gouvernance des données. Il analyse un fichier CSV avec cinq agents spécialisés, conserve les résultats dans SQLite et les présente dans une interface Flask.

## Architecture

```text
CSV utilisateur -> Flask -> DatasetService/pandas -> SupervisorAgent
               -> QualityAgent, ClassificationAgent, SecurityAgent
               -> LineageAgent, DocumentationAgent -> SQLite -> pages HTML
```

Les routes web sont dans `app.py`, l'accès SQLite dans `database.py`, le chargement CSV dans `services/`, l'orchestration dans `agents/supervisor_agent.py` et les agents dans `agents/`. Les pages Jinja sont dans `templates/` et les styles dans `static/css/style.css`.

## Technologies

- Python 3.10 ou supérieur
- Flask
- pandas
- ucimlrepo, uniquement pour télécharger le dataset officiel UCI Adult
- SQLite, inclus avec Python
- HTML, CSS et un peu de JavaScript natif pour le formulaire d'import

## Fonctionnalités

- Import CSV sécurisé avec nom de fichier nettoyé et limite de 16 Mo.
- Analyse déclenchée uniquement par un nouvel upload.
- Détection des anomalies, classification des colonnes, alertes de sécurité, lignage et documentation.
- Dashboard avec compteurs et répartitions calculés depuis SQLite.
- Filtres et pagination des anomalies.
- Décision du Data Owner : validation ou refus avec motif.

## Les cinq agents

- **QualityAgent** : valeurs manquantes, colonnes vides, doublons et valeurs extrêmes.
- **ClassificationAgent** : classification heuristique des colonnes.
- **SecurityAgent** : repérage heuristique de champs personnels ou sensibles.
- **LineageAgent** : enregistrement des étapes de traitement.
- **DocumentationAgent** : résumé, types de colonnes et statistiques descriptives.

## Installation

Depuis la racine du projet :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Initialisation

La base existante `dataguard.db` est conservée. Cette commande crée les tables et index manquants sans supprimer les données :

```powershell
python init_db.py
```

## Lancement

```powershell
python app.py
```

Ouvrir ensuite : <http://127.0.0.1:5000/>

Deux datasets réels sont disponibles pour la démonstration :

- `data/nyc_311_sample.csv` : échantillon NYC 311 d'environ 1 000 lignes et 10 colonnes.
- `data/adult_census_sample.csv` : échantillon déterministe de 1 500 lignes du dataset Adult officiel UCI (ID 2).

Pour (re)télécharger l'échantillon Adult depuis UCI :

```powershell
python download_adult_data.py
```

Source officielle : <https://archive.ics.uci.edu/dataset/2/adult>

## Workflow

1. Choisir un fichier CSV dans l'interface.
2. Flask vérifie et sauvegarde le fichier dans `uploads/`.
3. `DatasetService` charge le fichier avec pandas et crée l'enregistrement dataset.
4. `SupervisorAgent` exécute les cinq agents une seule fois pour cet upload.
5. Les pages Dashboard, Anomalies, Gouvernance et Validation lisent les résultats persistés.
6. Le Data Owner valide ou refuse les résultats depuis la page Validation.

Le rafraîchissement des pages de résultats ne relance pas l'analyse.

## Déploiement Render

Le service web Render utilise la commande de build suivante :

```text
pip install -r requirements.txt
```

Commande de démarrage :

```text
gunicorn app
```

Render peut vérifier que le service est disponible avec `GET /health`. Une URL possible est <https://govern-ia.onrender.com/> ; le sous-domaine exact dépend de sa disponibilité sur Render.

La clé Flask doit être configurée dans Render avec une variable d'environnement `SECRET_KEY`. Le chemin SQLite est configurable via `DATABASE_PATH`; sans cette variable, l'application utilise `dataguard.db` à la racine du projet et crée les tables manquantes sans effacer les données.

SQLite et les fichiers téléversés résident sur le système de fichiers éphémère de Render sans disque persistant. Ils peuvent donc disparaître lors d'un redéploiement ou du remplacement de l'instance. Cette configuration convient à une démonstration, mais ne garantit pas la conservation des imports.

Le pipeline CLI conserve NYC 311 comme défaut et accepte aussi n'importe quel chemin CSV :

```powershell
python run_pipeline.py
python run_pipeline.py data/adult_census_sample.csv
```

## Structure

```text
app.py
database.py
init_db.py
run_pipeline.py
download_adult_data.py
agents/
services/
templates/
static/css/style.css
data/
uploads/
dataguard.db
requirements.txt
```

## Limites de la V1

- Les règles de classification et de sécurité sont heuristiques et doivent être revues avant tout usage métier.
- L'analyse s'exécute de façon synchrone dans le processus Flask ; les fichiers volumineux peuvent prendre du temps.
- L'application n'a pas d'authentification et le serveur intégré Flask est prévu pour le développement local, pas pour la production.
- Les fichiers importés restent sur le disque local et ne sont pas supprimés automatiquement après une analyse réussie.
