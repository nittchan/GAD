"""Model version registry — append-only audit trail with R2 backup."""

import json
import logging

from gad.engine.db_write import write_model_version
from gad.engine.r2_upload import upload_determination  # reuse R2 upload

log = logging.getLogger("gad.engine.model_registry")


def register_model_version(trigger_id, model_type, parameters, metrics):
    """Register a new model version. Writes to DuckDB + R2."""
    from gad.engine.models import ModelVersion

    mv = ModelVersion(
        trigger_id=trigger_id,
        model_type=model_type,
        parameters=json.dumps(parameters) if parameters else None,
        metrics=json.dumps(metrics) if metrics else None,
    )
    # Write to DuckDB
    write_model_version(
        mv.version_id, mv.trigger_id, mv.model_type, mv.parameters, mv.metrics
    )
    # Copy to R2 model-registry/
    try:
        upload_determination(
            f"model-registry/{mv.version_id}", mv.model_dump_json(indent=2)
        )
    except Exception as e:
        log.debug(f"R2 model registry upload skipped: {e}")
    return mv.version_id
