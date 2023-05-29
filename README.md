# Tungstenkit

ML containerization tool with a focus on developer productivity and versatility.

![Version](https://img.shields.io/pypi/v/tungstenkit?color=%2334D058&label=pypi%20package)
![License](https://img.shields.io/github/license/tungsten-ai/tungstenkit)
![Downloads](https://static.pepy.tech/badge/tungstenkit?style=flat-square)
![Supported Python versions](https://img.shields.io/pypi/pyversions/tungstenkit.svg?color=%2334D058)

[Features](#features) | [Installation](#prerequisites) | [Usage](#usage) | [Getting Started](https://tungsten-ai.github.io/docs/tungsten_model/getting_started) | [Documentation](https://tungsten-ai.github.io/docs) 

## Features
- **Easy**: [Require only a few lines of Python code.](#build-a-tungsten-model)
- **Versatile**: Support multiple usages:
    - [REST API server](#run-as-a-rest-api-server)
    - [GUI application](#run-as-a-gui-application)
    - [CLI application](#run-as-a-cli-application)
    - [Python function](#run-in-a-python-script)
- **Abstracted**: [User-defined JSON input/output.](#run-as-a-rest-api-server)
- **Scalable**: Support adaptive batching and clustering (coming soon).

## Prerequisites
- Python 3.7+
- [Docker](https://docs.docker.com/get-docker/)
- (Optional) [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker) for running GPU models.


## Installation
```shell
pip install tungstenkit
```

## Usage
### Build a Tungsten model
Building a Tungsten model is easy. All you have to do is write a simple ``tungsten_model.py`` like below:

```python
from typing import List

import torch

from tungstenkit import BaseIO, Image, TungstenModel, model_config


class Input(BaseIO):
    prompt: str


class Output(BaseIO):
    image: Image


@model_config(gpu=True, python_packages=["torch", "torchvision"], batch_size=4)
class TextToImageModel(TungstenModel[Input, Output]):
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

### Run as a REST API server

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

### Run as a GUI application
If you need a more user-friendly way to make predictions, start a GUI app with the following command:

```console
$ tungsten demo text-to-image:latest -p 8080

INFO:     Uvicorn running on http://localhost:8080 (Press CTRL+C to quit)
```

![tungsten-dashboard](https://github.com/tungsten-ai/assets/blob/main/common/local-model-demo.gif?raw=true "Tungsten Dashboard")

### Run as a CLI application
Run a prediction in a terminal:
```console
$ tungsten predict text-to-image \
   -i prompt="a professional photograph of an astronaut riding a horse"

{
  "image": "./output.png"
}
```

### Run in a Python script
If you want to use a Tungsten model in your Python application, use the Python API:
```python
>>> from tungstenkit import models
>>> model = models.get("text-to-image:latest")
>>> model.predict(
    {"prompt": "a professional photograph of an astronaut riding a horse"}
)
{"image": PosixPath("./output.png")}
```

