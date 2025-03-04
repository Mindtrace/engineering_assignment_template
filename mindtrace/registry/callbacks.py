import os

import mlflow
from pytorch_lightning import LightningModule, Trainer
from pytorch_lightning.callbacks import Callback
from pytorch_lightning.utilities import rank_zero_only
import torch

from mindtrace import Config
from mindtrace.utils import flatten_dict, ifnone


class MlflowLightningCallback(Callback):
    """PyTorch Lightning MLflow logging callback with system and GPU metrics.

    Example::

        from pytorch_lightning import Trainer
        from mindtrace.data import MNIST
        from mindtrace.models import MLP
        from mindtrace.registry import MlflowLightningCallback

        # Initialize the callback
        mlflow_callback = MlflowLightningCallback(
            params={"param1": "value1"},
            experiment_name="my_experiment"
        )

        # Initialize a model and dataset
        model = MLP()
        dataset = MNIST()

        # Add the callback to the Trainer
        trainer = Trainer(callbacks=[mlflow_callback], max_epochs=10)

        # Train your model
        trainer.fit(model, dataset)  # Results can be seen at "http://localhost:5000"
    """

    def __init__(
        self,
        experiment_name: str = "default_experiment",
        run_name: str | None = None,
        tracking_uri: str | None = None,
        job_id: str | None = None,
        log_system_metrics: bool = True,
        **kwargs,
    ):
        """Initialize the MLflow callback.

        Args:
            experiment_name: Name of the MLflow experiment.
            run_name: Individual run name.
            tracking_uri: URI for MLflow tracking.
            job_id: An explicit job id for the training job.
            log_system_metrics: Whether to log system metrics during training.
            **kwargs: Additional hyperparameters to log.
        """
        self.experiment_name = experiment_name
        self.run_name = run_name
        self.tracking_uri = ifnone(tracking_uri, default=os.path.join(Config()["DIR_PATHS"]["CHECKPOINTS"], "mlruns"))
        self.log_system_metrics = log_system_metrics
        self.job_id = job_id
        if self.job_id:
            if self.run_name:
                self.run_name = f"{self.run_name}:{self.job_id}"
        self.hyperparams = ifnone(kwargs, default={})

        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        self.run = None

    @property
    def params(self):
        return dict(
            {
                "experiment_name": self.experiment_name,
                "run_name": self.run_name,
                "tracking_uri": self.tracking_uri,
                "log_system_metrics": self.log_system_metrics,
                "job_id": self.job_id,
            },
            **self.hyperparams,
        )

    @rank_zero_only
    def on_train_start(self, trainer: Trainer, pl_module: LightningModule) -> None:
        """Start MLflow run and log parameters at the start of training."""
        self.run = mlflow.start_run(run_name=self.run_name, log_system_metrics=self.log_system_metrics)
        mlflow.log_params(flatten_dict(self.params))

    @rank_zero_only
    def on_train_epoch_end(self, trainer: Trainer, pl_module: LightningModule):
        """Log metrics at the end of each training epoch."""
        metrics = trainer.callback_metrics
        for metric_name, metric_value in metrics.items():
            if metric_value is not None and isinstance(metric_value, (float, int, torch.Tensor)):
                if isinstance(metric_value, torch.Tensor):
                    metric_value = metric_value.item()
                mlflow.log_metric(metric_name, metric_value, step=trainer.current_epoch)

    @rank_zero_only
    def on_train_end(self, trainer: Trainer, pl_module: LightningModule):
        """Log the trained model and end the MLflow run."""
        if self.run:
            mlflow.pytorch.log_model(pl_module, artifact_path="model")

            # Log best checkpoint safely
            if hasattr(trainer, "checkpoint_callback") and trainer.checkpoint_callback:
                best_model_path = trainer.checkpoint_callback.best_model_path
                if best_model_path:
                    mlflow.log_artifact(best_model_path, artifact_path="best_model")

            mlflow.end_run()
