from prefect import flow, task

from app.services import retrain_service


@task(retries=2, retry_delay_seconds=3)
def run_retraining(trigger_reason):
    return retrain_service.run(trigger_reason)


@flow(name="retraining")
def retraining_flow(trigger_reason="scheduled"):
    return run_retraining(trigger_reason)
