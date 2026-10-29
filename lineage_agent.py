"""Enregistrement des étapes du traitement dans la table lineage."""

import database
from agents.agent_result import AgentResult


class LineageAgent:
    name = "LineageAgent"

    def run(self, dataset_id, previous_results):
        events = [("IMPORT", "Dataset importé depuis un fichier CSV local.")]
        event_by_agent = {
            "QualityAgent": ("QUALITY_CHECK", "Contrôle de qualité terminé."),
            "ClassificationAgent": (
                "CLASSIFICATION",
                "Classification des colonnes terminée.",
            ),
            "SecurityAgent": ("SECURITY_CHECK", "Contrôle de sécurité terminé."),
        }
        for result in previous_results:
            event = event_by_agent.get(result.agent_name)
            if event is not None:
                events.append((event[0], f"{event[1]} Statut : {result.status}."))

        database.insert_lineage_events(dataset_id, self.name, events)

        return AgentResult(
            agent_name=self.name,
            status="success",
            summary=f"{len(events)} événement(s) de traçabilité enregistré(s).",
            metadata={"event_count": len(events)},
        )
