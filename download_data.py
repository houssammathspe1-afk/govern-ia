"""Téléchargement d'un échantillon réel du dataset NYC 311."""

import json
import os
import ssl
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


DATASET_ID = "erm2-nwe9"
TARGET_COLUMNS = [
    "unique_key",
    "created_date",
    "agency",
    "complaint_type",
    "descriptor",
    "incident_zip",
    "city",
    "status",
    "latitude",
    "longitude",
]
API_URL = f"https://data.cityofnewyork.us/resource/{DATASET_ID}.json"


def _create_ssl_context():
    """Use Windows trusted certificates as well as Python's default roots."""
    context = ssl.create_default_context()
    if os.name == "nt":
        for store in ("ROOT", "CA"):
            for certificate_entry in ssl.enum_certificates(store):
                certificate, encoding = certificate_entry[:2]
                if encoding == "x509_asn":
                    context.load_verify_locations(
                        cadata=ssl.DER_cert_to_PEM_cert(certificate)
                    )
    return context


def download_nyc_311_sample(output_path=None):
    """Télécharge jusqu'à 1000 enregistrements et retourne le chemin du CSV."""
    if output_path is None:
        output_path = Path(__file__).resolve().parent / "data" / "nyc_311_sample.csv"
    else:
        output_path = Path(output_path)

    query = urlencode({"$limit": 1000, "$select": ",".join(TARGET_COLUMNS)})
    request_url = f"{API_URL}?{query}"
    with urlopen(
        request_url, timeout=60, context=_create_ssl_context()
    ) as response:
        records = json.loads(response.read().decode("utf-8"))

    frame = pd.DataFrame.from_records(records)
    available_columns = [column for column in TARGET_COLUMNS if column in frame.columns]
    if not available_columns:
        raise ValueError("L'API NYC 311 n'a retourné aucune des colonnes attendues.")

    frame = frame[available_columns]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8")
    print(
        f"Dataset réel enregistré : {output_path} "
        f"({len(frame)} lignes, {len(frame.columns)} colonnes)."
    )
    return output_path


if __name__ == "__main__":
    download_nyc_311_sample()
