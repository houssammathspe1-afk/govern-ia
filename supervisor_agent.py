"""Orchestration séquentielle des agents Govern IA."""

import logging

import database
from agents.agent_result import AgentResult
from agents.classification_agent import ClassificationAgent
from agents.documentation_agent import DocumentationAgent
from agents.lineage_agent import LineageAgent
from agents.quality_agent import QualityAgent
from agents.security_agent import SecurityAgent


logger = logging.getLogger(__name__)


class SupervisorAgent:
    def __init__(self):
        self.agents = (
            QualityAgent(),
            ClassificationAgent(),
            SecurityAgent(),
        )
        self.lineage_agent = LineageAgent()
        self.documentation_agent = DocumentationAgent()

    def run(self, dataframe, dataset_id, dataset_name="dataset"):
        results = []
        for agent in self.agents:
            try:
                result = agent.run(dataframe, dataset_id)
            except Exception as error:
                logger.exception("Échec de l’agent %s.", agent.name)
                result = AgentResult(
                    agent_name=agent.name,
                    status="error",
                    summary=f"Échec de l'agent : {error}",
                    issues=[{"error": str(error)}],
                )
            results.append(result)

        try:
            lineage_result = self.lineage_agent.run(dataset_id, results)
        except Exception as error:
            logger.exception("Échec de l’agent %s.", self.lineage_agent.name)
            lineage_result = AgentResult(
                agent_name=self.lineage_agent.name,
                status="error",
                summary=f"Échec de l'agent : {error}",
                issues=[{"error": str(error)}],
            )
        results.append(lineage_result)

        try:
            documentation_result = self.documentation_agent.run(
                dataframe, dataset_id, dataset_name
            )
        except Exception as error:
            logger.exception("Échec de l’agent %s.", self.documentation_agent.name)
            documentation_result = AgentResult(
                agent_name=self.documentation_agent.name,
                status="error",
                summary=f"Échec de l'agent : {error}",
                issues=[{"error": str(error)}],
            )
        results.append(documentation_result)

        pipeline_status = (
            "success"
            if all(result.status == "success" for result in results)
            else "error"
        )
        try:
            database.insert_lineage(
                dataset_id,
                "SupervisorAgent",
                "PIPELINE_COMPLETED",
                f"Pipeline terminé avec le statut {pipeline_status}.",
            )
        except Exception as error:
            logger.exception("Échec de l’enregistrement de fin du pipeline.")
            results.append(
                AgentResult(
                    agent_name="SupervisorAgent",
                    status="error",
                    summary=f"Échec de l'enregistrement de fin de pipeline : {error}",
                    issues=[{"error": str(error)}],
                )
            )
            pipeline_status = "error"

        return {
            "dataset_id": dataset_id,
            "status": pipeline_status,
            "agents_results": [result.to_dict() for result in results],
            "summary": (
                f"Pipeline {pipeline_status} : {len(results)} résultat(s) agent "
                f"généré(s)."
            ),
        }
