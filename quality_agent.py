"""Détection simple des anomalies de qualité d'un DataFrame."""

import database
from agents.agent_result import AgentResult


class QualityAgent:
    """Repère les valeurs manquantes, doublons, colonnes vides et valeurs extrêmes."""

    name = "QualityAgent"

    def run(self, dataframe, dataset_id):
        issues = []

        for column in dataframe.columns:
            missing_rows = dataframe.index[dataframe[column].isna()].tolist()
            for row_index in missing_rows:
                issues.append(
                    {
                        "row_number": int(row_index) + 1,
                        "column_name": str(column),
                        "anomaly_type": "MISSING_VALUE",
                        "original_value": None,
                        "severity": "MEDIUM",
                    }
                )

            if dataframe[column].isna().all():
                issues.append(
                    {
                        "row_number": None,
                        "column_name": str(column),
                        "anomaly_type": "EMPTY_COLUMN",
                        "original_value": None,
                        "severity": "HIGH",
                    }
                )

        duplicate_rows = dataframe.index[dataframe.duplicated(keep="first")].tolist()
        for row_index in duplicate_rows:
            issues.append(
                {
                    "row_number": int(row_index) + 1,
                    "column_name": None,
                    "anomaly_type": "DUPLICATE_ROW",
                    "original_value": None,
                    "severity": "MEDIUM",
                }
            )

        numeric_columns = dataframe.select_dtypes(include="number").columns
        for column in numeric_columns:
            values = dataframe[column].dropna()
            if values.empty:
                continue
            first_quartile = values.quantile(0.25)
            third_quartile = values.quantile(0.75)
            spread = third_quartile - first_quartile
            if spread == 0:
                continue
            lower_bound = first_quartile - 1.5 * spread
            upper_bound = third_quartile + 1.5 * spread
            outlier_mask = (dataframe[column] < lower_bound) | (
                dataframe[column] > upper_bound
            )
            for row_index in dataframe.index[outlier_mask.fillna(False)].tolist():
                value = dataframe.at[row_index, column]
                distance = max(lower_bound - value, value - upper_bound)
                issues.append(
                    {
                        "row_number": int(row_index) + 1,
                        "column_name": str(column),
                        "anomaly_type": "OUTLIER",
                        "original_value": value.item()
                        if hasattr(value, "item")
                        else value,
                        "severity": "HIGH" if distance > 3 * spread else "MEDIUM",
                    }
                )

        agent_id = database.get_agent_id(self.name)
        database.insert_anomalies(dataset_id, agent_id, issues)

        return AgentResult(
            agent_name=self.name,
            status="success",
            summary=f"{len(issues)} anomalie(s) détectée(s).",
            issues=issues,
            metadata={"anomaly_count": len(issues)},
        )