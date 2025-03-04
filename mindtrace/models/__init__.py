from mindtrace.models.mlp import MLPModule
from mindtrace.models.lightning_wrapper import ClassificationLightningWrapper


def MLP(*args, **kwargs):
    """Factory function to return a trainable MLP model."""
    return ClassificationLightningWrapper(MLPModule(*args, **kwargs))


__all__ = ["MLP"]