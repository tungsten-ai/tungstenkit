# Tungstenkit: Developer-friendly container toolkit for machine learning

Tungstenkit is an open-source tool for building standardized containers for machine learning models.

The key features are:

- **Easy**: [Require only a few lines of Python code.](#build-a-tungsten-model)
- **Versatile**: Support multiple usages:
    - [REST API server](#run-it-as-a-restful-api-server)
    - [GUI application](#run-it-as-a-gui-application)
    - [CLI application](#run-it-as-a-cli-application)
    - [Python function](#run-it-as-a-python-function)
- **Abstracted**: [User-defined JSON input/output.](#run-it-as-a-restful-api-server)
- **Standardized**: [Support advanced workflows.](#run-it-as-a-restful-api-server)
- **Scalable**: Support adaptive batching and clustering (coming soon).

# Learn More
- [Documentation](https://tungsten-ai.github.io/docs)
- [Getting Started](https://tungsten-ai.github.io/docs/tungsten_model/getting_started/)

---


# Take the tour
## Build a Tungsten model
Building a Tungsten model is easy. All you have to do is write a simple ``tungsten_model.py`` like below:

```python
from typing import List

import torch
from tungstenkit import BaseIO, model_config, TungstenModel


class Input(BaseIO):
    prompt: str


class Output(BaseIO):
    image: io.Image


@model_config(
    gpu=True,
    python_packages=["torch", "torchvision"],
    batch_size=4,
    description="Text to image"
)
class Model(TungstenModel[Input, Output]):
    def setup(self):
        weights = torch.load("./weights.pth")
        self.model = load_torch_model(weights)

    def predict(self, inputs: List[Input]) -> List[Output]:
        input_tensor = preprocess(inputs)
        output_tensor = self.model(input_tensor)
        outputs = postprocess(output_tensor)
        return outputs
```

Now, you can start a build process with the following command:
```console
$ tungsten build

✅ Successfully built tungsten model: 'text-to-image:latest'
```


## Run it as a REST API server

You can start a prediction with a REST API call.

Start a server:

```console
$ docker run -p 3000:3000 --gpus all text-to-image:latest

INFO:     Setting up the model
INFO:     Getting inputs from the input queue
INFO:     Starting the prediction service
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
```

Send a prediction request with a JSON payload:

```console
$ curl -X 'POST' 'http://localhost:3000/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[{"prompt": "a professional photograph of an astronaut riding a horse"}]'

{
    "outputs": [{"image": "data:image/png;base64,..."}],
}
```

## Run it as a GUI application
If you need a more user-friendly way to make predictions, start a GUI app with the following command:

```console
$ tungsten demo text-to-image:latest -p 8080

INFO:     Uvicorn running on http://localhost:8080 (Press CTRL+C to quit)
```

![tungsten-dashboard](https://github.com/tungsten-ai/assets/blob/main/common/local-model-demo.gif?raw=true "Tungsten Dashboard")

## Run it as a CLI application
Also, you can run a prediction through a simple command:
```console
$ tungsten predict text-to-image \
   -i prompt="a professional photograph of an astronaut riding a horse"

{
  "image": "./output.png"
}
```

## Run it in a Python script
If you want to use a Tungsten model in your Python application, use the Python API:
```python
>>> from tungstenkit import models
>>> model = models.get("text-to-image:latest")
>>> model.predict(
    {"prompt": "a professional photograph of an astronaut riding a horse"}
)
{"image": PosixPath("./output.png")}
```

---

# Prerequisites
- Python 3.7+
- [Docker](https://docs.docker.com/engine/install/)
- (Optional) [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker) for running GPU models locally. 


# Installation
```shell
pip install tungstenkit
```