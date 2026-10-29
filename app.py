"""Application web Flask de Govern IA."""

import logging
import os
import shutil
import sqlite3
import uuid
from pathlib import Path

import pandas as pd
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.utils import secure_filename

import database
from agents.supervisor_agent import SupervisorAgent
from init_db import initialize_agents
from services.dataset_service import DatasetService


ROOT_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT_DIR / "uploads"
MAX_UPLOAD_SIZE = 16 * 1024 * 1024
DATASET_SOURCE = "Téléversement CSV utilisateur"
ANOMALY_PAGE_SIZE = 50
AGENT_ACTIONS = {
    "QualityAgent": "QUALITY_CHECK",
    "ClassificationAgent": "CLASSIFICATION",
    "SecurityAgent": "SECURITY_CHECK",
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
app.config["DEBUG"] = False
secret_key = os.environ.get("SECRET_KEY")
if not secret_key and os.environ.get("RENDER") == "true":
    raise RuntimeError("La variable SECRET_KEY doit être configurée sur Render.")
app.secret_key = secret_key or "dev-only-secret"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
database.create_database()
initialize_agents()


def _get_pipeline_status(lineage):
    completion = next(
        (event for event in reversed(lineage) if event["action"] == "PIPELINE_COMPLETED"),
        None,
    )
    if completion is None:
        return "unknown"
    if "error" in completion["description"].lower():
        return "error"
    return "success"


def _get_agent_statuses(lineage, documentation):
    agent_statuses = {}
    for agent_name, action in AGENT_ACTIONS.items():
        event = next(
            (item for item in reversed(lineage) if item["action"] == action),
            None,
        )
        agent_statuses[agent_name] = (
            "error"
            if event and "statut : error" in event["description"].lower()
            else "success" if event else "unknown"
        )
    agent_statuses["LineageAgent"] = "success" if lineage else "unknown"
    agent_statuses["DocumentationAgent"] = (
        "success" if documentation else "unknown"
    )
    return agent_statuses

def _dataset_or_404(dataset_id):
    dataset = database.get_dataset(dataset_id)
    if dataset is None:
        flash("Ce dataset n’existe pas dans la base Govern IA.", "error")
    return dataset


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_error):
    flash("Le fichier dépasse la taille maximale autorisée de 16 Mo.", "error")
    return redirect(url_for("index"))


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return error
    logger.exception("Erreur non gérée pendant le traitement d’une requête.")
    return render_template("error.html"), 500


@app.route("/")
def index():
    datasets = database.get_datasets(limit=8)
    return render_template(
        "index.html",
        datasets=datasets,
        dataset=datasets[0] if datasets else None,
    )


@app.get("/health")
def health():
    return jsonify(status="ok", service="Govern IA"), 200


@app.post("/upload")
def upload():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        flash("Choisissez un fichier CSV avant de lancer l’analyse.", "error")
        return redirect(url_for("index"))

    original_name = secure_filename(uploaded_file.filename)
    if not original_name or Path(original_name).suffix.lower() != ".csv":
        flash("Seuls les fichiers portant l’extension .csv sont acceptés.", "error")
        return redirect(url_for("index"))

    upload_folder = None
    dataset_id = None
    try:
        upload_folder = UPLOAD_DIR / uuid.uuid4().hex
        upload_folder.mkdir(parents=True, exist_ok=False)
        saved_path = upload_folder / original_name
        uploaded_file.save(saved_path)
        service = DatasetService()
        dataframe = service.load_csv(saved_path)
        if dataframe.empty or len(dataframe.columns) == 0:
            raise ValueError("Le fichier CSV ne contient aucune donnée exploitable.")

        metadata = service.get_metadata(dataframe, DATASET_SOURCE)
        dataset_id = service.register_dataset(dataframe, DATASET_SOURCE)
        results = SupervisorAgent().run(
            dataframe, dataset_id, metadata["name"]
        )
        if results["status"] != "success":
            flash(
                "L’analyse est terminée, mais au moins un agent a rencontré une "
                "erreur. Consultez le tableau de bord pour les détails.",
                "error",
            )
        else:
            flash("Analyse terminée. Les résultats sont enregistrés.", "success")
        return redirect(url_for("dashboard", dataset_id=dataset_id))
    except pd.errors.EmptyDataError:
        logger.info("CSV vide ou sans en-tête refusé : %s", original_name)
        flash("Le fichier CSV est vide ou ne contient pas d’en-tête lisible.", "error")
    except pd.errors.ParserError:
        logger.info("CSV mal formé refusé : %s", original_name)
        flash("Le CSV est mal formé et ne peut pas être analysé.", "error")
    except UnicodeDecodeError:
        logger.info("CSV avec encodage invalide refusé : %s", original_name)
        flash("L’encodage du CSV est illisible. Utilisez un fichier UTF-8.", "error")
    except ValueError as error:
        logger.info("CSV refusé (%s) : %s", original_name, error)
        flash(str(error), "error")
    except (OSError, sqlite3.Error):
        logger.exception("Erreur de stockage ou de lecture du CSV %s.", original_name)
        flash("Le fichier n’a pas pu être sauvegardé ou lu.", "error")
    except Exception:
        logger.exception("Erreur lors de l’analyse du dataset %s.", original_name)
        flash("Une erreur inattendue est survenue pendant l’analyse.", "error")
    finally:
        if upload_folder is not None and dataset_id is None:
            shutil.rmtree(upload_folder, ignore_errors=True)

    return redirect(url_for("index"))


@app.get("/dashboard/<int:dataset_id>")
def dashboard(dataset_id):
    dataset = _dataset_or_404(dataset_id)
    if dataset is None:
        return redirect(url_for("index"))
    counts = database.get_dataset_counts(dataset_id)
    lineage = database.get_lineage(dataset_id)
    documentation = database.get_documentation(dataset_id)
    validation = database.get_validation(dataset_id)
    pipeline_status = _get_pipeline_status(lineage)
    agent_statuses = _get_agent_statuses(lineage, documentation)
    agent_summaries = {
        "QualityAgent": f"{counts['anomaly_count']} anomalie(s) détectée(s).",
        "ClassificationAgent": (
            f"{counts['classification_count']} colonne(s) classifiée(s)."
        ),
        "SecurityAgent": f"{counts['security_count']} alerte(s) de sécurité.",
        "LineageAgent": f"{counts['lineage_count']} événement(s) de traçabilité.",
        "DocumentationAgent": (
            documentation["summary"]
            if documentation
            else "Aucune documentation n’a été enregistrée."
        ),
    }
    global_summary = (
        "Le pipeline a rencontré une erreur. Consultez les états des agents et le lignage."
        if pipeline_status == "error"
        else (
            f"Analyse terminée : {counts['anomaly_count']} anomalies, "
            f"{counts['classification_count']} colonnes classifiées et "
            f"{counts['security_count']} alertes de sécurité."
        )
    )
    return render_template(
        "dashboard.html",
        dataset=dataset,
        counts=counts,
        lineage=lineage,
        documentation=documentation,
        validation=validation,
        pipeline_status=pipeline_status,
        agent_statuses=agent_statuses,
        agent_summaries=agent_summaries,
        global_summary=global_summary,
        distributions=database.get_dashboard_distributions(dataset_id),
    )


@app.get("/anomalies/<int:dataset_id>")
def anomalies(dataset_id):
    dataset = _dataset_or_404(dataset_id)
    if dataset is None:
        return redirect(url_for("index"))
    anomaly_type = request.args.get("type", "").strip()[:80]
    severity = request.args.get("severity", "").strip()[:20]
    column_search = request.args.get("column", "").strip()[:80]
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    counts = database.get_dataset_counts(dataset_id)
    filters = database.get_anomaly_filter_options(dataset_id)
    result_page = database.get_anomalies_page(
        dataset_id,
        page=page,
        page_size=ANOMALY_PAGE_SIZE,
        anomaly_type=anomaly_type,
        severity=severity,
        column_search=column_search,
    )
    page_count = max(
        (result_page["total"] + ANOMALY_PAGE_SIZE - 1) // ANOMALY_PAGE_SIZE,
        1,
    )
    if page > page_count:
        page = page_count
        result_page = database.get_anomalies_page(
            dataset_id,
            page=page,
            page_size=ANOMALY_PAGE_SIZE,
            anomaly_type=anomaly_type,
            severity=severity,
            column_search=column_search,
        )
    return render_template(
        "anomalies.html",
        dataset=dataset,
        anomalies=result_page["items"],
        total_count=counts["anomaly_count"],
        filtered_count=result_page["total"],
        page=page,
        page_count=page_count,
        filters=filters,
        selected_type=anomaly_type,
        selected_severity=severity,
        column_search=column_search,
    )


@app.get("/governance/<int:dataset_id>")
def governance(dataset_id):
    dataset = _dataset_or_404(dataset_id)
    if dataset is None:
        return redirect(url_for("index"))
    return render_template(
        "governance.html",
        dataset=dataset,
        classifications=database.get_classifications(dataset_id),
        security_findings=database.get_security_findings(dataset_id),
        lineage=database.get_lineage(dataset_id),
        documentation=database.get_documentation(dataset_id),
    )


@app.get("/validation/<int:dataset_id>")
def validation(dataset_id):
    dataset = _dataset_or_404(dataset_id)
    if dataset is None:
        return redirect(url_for("index"))
    return render_template(
        "validation.html",
        dataset=dataset,
        counts=database.get_dataset_counts(dataset_id),
        validation=database.get_validation(dataset_id),
    )


@app.post("/validate/<int:dataset_id>")
def validate(dataset_id):
    if database.get_dataset(dataset_id) is None:
        flash("Ce dataset n’existe pas dans la base Govern IA.", "error")
        return redirect(url_for("index"))
    database.insert_validation(dataset_id, "VALIDATED", "Data Owner")
    flash("L’analyse a été validée.", "success")
    return redirect(url_for("validation", dataset_id=dataset_id))


@app.post("/reject/<int:dataset_id>")
def reject(dataset_id):
    if database.get_dataset(dataset_id) is None:
        flash("Ce dataset n’existe pas dans la base Govern IA.", "error")
        return redirect(url_for("index"))
    reason = request.form.get("rejection_reason", "").strip()
    if not 3 <= len(reason) <= 500:
        flash(
            "Le motif du refus doit contenir entre 3 et 500 caractères.",
            "error",
        )
        return redirect(url_for("validation", dataset_id=dataset_id))
    database.insert_validation(
        dataset_id,
        "REJECTED",
        "Data Owner",
        rejection_reason=reason,
    )
    flash("Le refus a été enregistré avec son motif.", "success")
    return redirect(url_for("validation", dataset_id=dataset_id))


if __name__ == "__main__":
    print("Govern IA est disponible sur http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
