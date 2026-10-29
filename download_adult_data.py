"""Télécharge et prépare un échantillon du dataset Adult officiel UCI."""

import re
from pathlib import Path

import pandas as pd
from ucimlrepo import fetch_ucirepo


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT_DIR / "data" / "adult_census_sample.csv"
SAMPLE_SIZE = 1500
MISSING_VALUES = {"", "?", "na", "n/a"}


def _snake_case(column_name):
    normalized = re.sub(r"[^a-z0-9]+", "_", str(column_name).strip().lower())
    return normalized.strip("_")


def download_adult_sample(output_path=OUTPUT_PATH):
    adult = fetch_ucirepo(id=2)
    dataframe = pd.concat(
        [adult.data.features, adult.data.targets],
        axis=1,
    ).copy()
    dataframe.columns = [_snake_case(column) for column in dataframe.columns]

    for column_index in range(dataframe.shape[1]):
        series = dataframe.iloc[:, column_index]
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        normalized = series.astype("string").str.strip()
        dataframe.iloc[:, column_index] = normalized.mask(
            normalized.str.casefold().isin(MISSING_VALUES),
            pd.NA,
        )

    if "income" in dataframe.columns:
        dataframe["income"] = dataframe["income"].str.rstrip(".")

    sample = dataframe.sample(n=SAMPLE_SIZE, random_state=42).reset_index(drop=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(output_path, index=False)

    missing_count = int(sample.isna().sum().sum())
    print(
        f"Échantillon Adult UCI enregistré : {output_path.name} "
        f"({sample.shape[0]} lignes, {sample.shape[1]} colonnes, "
        f"{missing_count} valeurs manquantes)."
    )
    return output_path


if __name__ == "__main__":
    download_adult_sample()