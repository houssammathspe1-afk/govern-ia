"""Point d'entrée terminal du pipeline Python Govern IA."""

import argparse
import sqlite3
from pathlib import Path

import database
from agents.supervisor_agent import SupervisorAgent
from download_data import download_nyc_311_sample
from init_db import initialize_agents
from services.dataset_service import DatasetService


ROOT_DIR = Path(__file__).resolve().parent
DATASET_PATH = ROOT_DIR / "data" / "nyc_311_sample.csv"
DATASET_SOURCE = "NYC Open Data - 311 Service Requests"


def _print_agent_report(result):
    name = result["agent_name"]
    label = name.replace("Agent", " Agent").upper()
    metadata = result["metadata"]
    print(f"\n-------------------------------------\n{label}\n-------------------------------------")
    print(f"Status : {result['status']}")
    if name == "QualityAgent":
        print(f"Anomalies détectées : {metadata.get('anomaly_count', 0)}")
    elif name == "ClassificationAgent":
        print(f"Colonnes classifiées : {metadata.get('classification_count', 0)}")
    elif name == "SecurityAgent":
        print(f"Alertes : {metadata.get('finding_count', 0)}")
    elif name == "LineageAgent":
        print(result["summary"])
    elif name == "DocumentationAgent":
        print(result["summary"])
    if result["status"] == "error":
        print(result["summary"])


def main(csv_path=None):
    dataset_path = DATASET_PATH if csv_path is None else Path(csv_path)
    if not dataset_path.is_absolute():
        dataset_path = ROOT_DIR / dataset_path

    if csv_path is None and not dataset_path.is_file():
        print("Le CSV NYC 311 est absent ; téléchargement de données réelles...")
        download_nyc_311_sample(dataset_path)
    elif not dataset_path.is_file():
        raise FileNotFoundError(f"Fichier CSV introuvable : {dataset_path}")

    service = DatasetService()
    dataframe = service.load_csv(dataset_path)
    source = DATASET_SOURCE if csv_path is None else "CSV local"
    metadata = service.get_metadata(dataframe, source)

    print("=====================================")
    print("GOVERN IA")
    print("=====================================")
    print(f"\nDataset :\n{metadata['name']}")
    print(f"\nLignes :\n{metadata['row_count']}")
    print(f"\nColonnes :\n{metadata['column_count']}")

    database.create_database()
    initialize_agents()
    dataset_id = service.register_dataset(dataframe, DATASET_SOURCE)
    results = SupervisorAgent().run(dataframe, dataset_id, metadata["name"])

    for result in results["agents_results"]:
        _print_agent_report(result)

    print("\n=====================================")
    print("PIPELINE TERMINÉ")
    print("=====================================")
    print(f"\nDataset ID : {dataset_id}")
    print("Les résultats ont été enregistrés dans SQLite.")

    connection = sqlite3.connect(database.DB_PATH)
    try:
        for table in (
            "datasets",
            "anomalies",
            "classifications",
            "security_findings",
            "lineage",
            "documentations",
        ):
            id_column = "id" if table == "datasets" else "dataset_id"
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {id_column} = ?",
                (dataset_id,),
            ).fetchone()[0]
            print(f"{table} : {count}")
    finally:
        connection.close()

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse un dataset CSV avec Govern IA.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        help="Chemin CSV à analyser (par défaut : échantillon NYC 311).",
    )
    arguments = parser.parse_args()
    main(arguments.csv_path)
