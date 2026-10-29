"""Repérage de colonnes pouvant contenir des données personnelles."""

import database
from agents.agent_result import AgentResult


class SecurityAgent:
    name = "SecurityAgent"

    _direct_identifier_keywords = (
        "email",
        "mail",
        "phone",
        "telephone",
        "mobile",
        "address",
        "adresse",
        "passport",
        "cin",
        "ssn",
        "social_security",
        "identifier",
        "unique_key",
    )
    _credential_keywords = ("password", "passwd", "api_key", "token")
    _financial_keywords = (
        "income",
        "salary",
        "salaire",
        "revenue",
        "capital_gain",
        "capital_loss",
    )
    _personal_demographic_columns = {
        "age",
        "sex",
        "marital_status",
        "native_country",
        "relationship",
    }

    def run(self, dataframe, dataset_id):
        findings = []
        for column in dataframe.columns:
            column_name = str(column)
            normalized = column_name.strip().lower().replace("-", "_")
            if any(keyword in normalized for keyword in self._credential_keywords):
                finding_type = "CREDENTIAL_DATA"
                recommendation = (
                    "Identifiant d’authentification potentiel : restreindre fortement "
                    "l’accès et masquer la valeur."
                )
            elif any(keyword in normalized for keyword in self._direct_identifier_keywords):
                finding_type = "DIRECT_IDENTIFIER"
                recommendation = (
                    "Donnée potentiellement identifiante : contrôler l’accès et "
                    "appliquer un masquage si nécessaire."
                )
            elif normalized in {"race", "ethnicity"}:
                finding_type = "SENSITIVE_DEMOGRAPHIC"
                recommendation = (
                    "Attribut démographique sensible : minimiser l’exposition, "
                    "contrôler l’accès et vérifier les règles de protection applicables."
                )
            elif any(keyword in normalized for keyword in self._financial_keywords):
                finding_type = "FINANCIAL_DATA"
                recommendation = (
                    "Attribut financier : contrôler l’accès, minimiser l’exposition "
                    "et vérifier les règles de protection applicables."
                )
            elif normalized in self._personal_demographic_columns:
                finding_type = "PERSONAL_DATA"
                recommendation = (
                    "Attribut personnel ou démographique : limiter l’accès et "
                    "masquer si nécessaire. Aucun incident n’est inféré."
                )
            elif any(
                keyword in normalized
                for keyword in ("name", "nom", "birth_date", "date_of_birth")
            ):
                finding_type = "PERSONAL_DATA"
                recommendation = (
                    "Attribut personnel potentiel : contrôler l’accès et "
                    "minimiser l’exposition."
                )
            else:
                continue

            findings.append(
                {
                    "column_name": column_name,
                    "finding_type": finding_type,
                    "recommendation": recommendation,
                }
            )

        database.insert_security_findings(dataset_id, findings)

        return AgentResult(
            agent_name=self.name,
            status="success",
            summary=f"{len(findings)} alerte(s) de sécurité détectée(s).",
            issues=findings,
            recommendations=list(
                dict.fromkeys(item["recommendation"] for item in findings)
            ),
            metadata={"finding_count": len(findings)},
        )
