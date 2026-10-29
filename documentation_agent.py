"""Création d'un résumé et de métadonnées descriptives du dataset."""

import pandas as pd

import database
from agents.agent_result import AgentResult


class DocumentationAgent:
    name = "DocumentationAgent"

    def run(self, dataframe, dataset_id, dataset_name):
        row_count, column_count = dataframe.shape
        missing_count = int(dataframe.isna().sum().sum())
        duplicate_count = int(dataframe.duplicated().sum())
        column_types = {
            str(column): str(dtype) for column, dtype in dataframe.dtypes.items()
        }
        statistics = {}

        for column in dataframe.columns:
            series = dataframe[column]
            if pd.api.types.is_numeric_dtype(series):
                stats = series.describe()
                statistics[str(column)] = {
                    key: float(value)
                    for key, value in stats.items()
                    if pd.notna(value)
                }
            else:
                top_values = series.dropna().astype(str).value_counts().head(3)
                statistics[str(column)] = {
                    "distinct_values": int(series.nunique(dropna=True)),
                    "most_common": {
                        str(value): int(count)
                        for value, count in top_values.items()
                    },
                }

        summary = (
            f"Le dataset {dataset_name} contient {row_count} lignes et "
            f"{column_count} colonnes. {missing_count} valeurs manquantes "
            f"et {duplicate_count} doublons ont été détectés."
        )
        documentation = {
            "dataset_name": dataset_name,
            "row_count": row_count,
            "column_count": column_count,
            "columns": [str(column) for column in dataframe.columns],
            "column_types": column_types,
            "missing_values": missing_count,
            "duplicate_rows": duplicate_count,
            "statistics": statistics,
            "summary": summary,
        }
        database.insert_documentation(dataset_id, summary)
        database.insert_lineage(
            dataset_id,
            self.name,
            "DOCUMENTATION",
            "Documentation automatique du dataset enregistrée.",
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            summary=summary,
            metadata=documentation,
        )
