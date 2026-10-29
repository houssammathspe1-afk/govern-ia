"""Classification pédagogique des colonnes d'un DataFrame."""

import pandas as pd

import database
from agents.agent_result import AgentResult


class ClassificationAgent:
    name = "ClassificationAgent"

    _financial_columns = {
        "income",
        "salary",
        "salaire",
        "revenue",
        "capital_gain",
        "capital_loss",
    }
    _sensitive_demographic_columns = {"race", "ethnicity"}
    _demographic_columns = {"sex", "age", "marital_status", "relationship"}
    _categorical_columns = {
        "education",
        "workclass",
        "occupation",
        "employment_type",
    }

    def run(self, dataframe, dataset_id):
        results = []
        for column in dataframe.columns:
            normalized = str(column).strip().lower().replace("-", "_")
            series = dataframe[column]

            if (
                normalized in {"id", "identifier"}
                or normalized.endswith("_id")
                or "unique_key" in normalized
                or "identifier" in normalized
            ):
                classification, confidence = "IDENTIFIER", 0.9
            elif normalized in self._sensitive_demographic_columns:
                classification, confidence = "SENSITIVE_DEMOGRAPHIC", 0.9
            elif normalized in self._financial_columns:
                classification, confidence = "FINANCIAL", 0.9
            elif normalized in self._demographic_columns:
                classification, confidence = "DEMOGRAPHIC", 0.85
            elif normalized in self._categorical_columns:
                classification, confidence = "CATEGORICAL", 0.85
            elif any(
                keyword in normalized
                for keyword in (
                    "salary",
                    "salaire",
                    "cin",
                    "passport",
                    "password",
                    "ssn",
                )
            ):
                classification, confidence = "SENSITIVE", 0.9
            elif any(
                keyword in normalized
                for keyword in (
                    "email",
                    "mail",
                    "phone",
                    "telephone",
                    "mobile",
                    "address",
                    "adresse",
                    "name",
                    "nom",
                    "email",
                )
            ):
                classification, confidence = "PERSONAL", 0.9
            elif any(
                keyword in normalized
                for keyword in (
                    "latitude",
                    "longitude",
                    "city",
                    "ville",
                    "zip",
                    "postal",
                    "native_country",
                )
            ):
                classification, confidence = "GEOGRAPHIC", 0.9
            elif any(
                keyword in normalized for keyword in ("date", "time", "timestamp")
            ) or pd.api.types.is_datetime64_any_dtype(series):
                classification, confidence = "DATETIME", 0.9
            elif pd.api.types.is_numeric_dtype(series):
                classification, confidence = "NUMERIC", 0.9
            elif pd.api.types.is_string_dtype(series) or series.dtype == object:
                distinct_count = int(series.nunique(dropna=True))
                non_missing_count = int(series.notna().sum())
                if distinct_count <= 50 and distinct_count <= non_missing_count * 0.25:
                    classification, confidence = "CATEGORICAL", 0.8
                else:
                    classification, confidence = "TEXT", 0.7
            else:
                classification, confidence = "GENERAL", 0.5

            result = {
                "column_name": str(column),
                "classification": classification,
                "confidence": confidence,
            }
            results.append(result)

        database.insert_classifications(dataset_id, results)

        return AgentResult(
            agent_name=self.name,
            status="success",
            summary=f"{len(results)} colonne(s) classifiée(s).",
            issues=results,
            metadata={"classification_count": len(results)},
        )
