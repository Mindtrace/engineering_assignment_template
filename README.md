Mindtrace Library Enhancement Assignment
==========================================

Overview
--------
You have been provided with the basic Mindtrace library which includes:
  - config.py: A configuration file that wraps Python’s configparser.
  - mnist.py: Provides a starter MNIST dataset class.
  - mlp.py and lightning_wrapper.py: Expose an MLP LightningModule (`from mindtrace.models import MLP`).
  - utils.py: Contains various helper methods.
  - callbacks.py: Contains an MLflow callback that logs metrics and model artifacts.

The library is can be used to train a model as follows:

```python
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
trainer.fit(model, dataset)
```

Currently, the library lacks:
  - A testing framework
  - FastAPI components for exposing endpoints
  - An advanced model registry interface


Assignment Tasks
----------------
Your assignment is to extend the Mindtrace library with the following enhancements. The expected time to complete this 
assignment is 2–3 hours. If one of the following tasks is taking longer than 30 minutes, there is an easier way ^^

1. Integrate a Testing Framework
   - Set up a testing framework using pytest (or your preferred library).
   - Create unit tests for key helper functions in utils.py (e.g., ifnone, flatten_dict).
   - Write integration tests for the MNIST dataset class to verify that data is downloaded and split correctly.
   - Ensure tests can be run via a command (e.g., `pytest`) from the project root.

2. Develop FastAPI Endpoints
   - Build a minimal FastAPI application that exposes two endpoints:
       a. **POST /inference:** Accepts an image (encoded as ASCII/base64) and returns model predictions.
       b. **POST /retrain:** Accepts a configuration file (or parameters) and triggers a model retraining process.
   - Create a new module (e.g., `mindtrace.application.api.py`) that defines the FastAPI app.
   - The `/inference` endpoint should use the existing MLP model to perform inference.
   - The `/retrain` endpoint should reuse the MNIST dataset and MLflow callback to trigger a new training session.
   - Include proper error handling and API documentation using FastAPI’s built-in documentation features.

3. Enhance the Model Registry
   - Expand the current MLflow callback to log additional metadata (such as training configuration, timestamps, or 
   version info).
   - Implement a simple query interface (either as a function or an additional API endpoint) that allows retrieval of 
   logged model versions and metadata.
   - Add comments or a short README section explaining how you would further extend this registry for production use.

4. Design & Documentation
   - Write a brief design document (1–2 pages) that covers:
       a. **Architecture Overview:** How the components (data, model, registry, API, and tests) interact.
       b. **Design Decisions:** Key choices made when integrating tests, building the API, and enhancing the registry.
       c. **Future Considerations:** Ideas for scaling the registry, improving reliability, and automating 
       training/inference workflows.
   - Include inline comments and docstrings to help guide other team members.
   - See the note below on using ChatGPT. It (or equivalent) may be helpful for creating useful documentation, at your 
   guidance.

Submission Guidelines
---------------------
- Package your solution in a Git repository.
- Include clear instructions in a README (this file) on:
    - How to run the tests.
    - How to start the FastAPI service.
    - How to trigger training and inference.
- Ensure your code is clear, maintainable, and well-documented.
- You may use any AI-assisted developer tool (GPT/Claude/cursor/etc.) as much as you like.  

Good luck, and we look forward to seeing how you extend and refine the Mindtrace library both technically and 
architecturally!
