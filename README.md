# Tungstenkit: ML container made simple
[![Version](https://img.shields.io/pypi/v/tungstenkit?color=%2334D058&label=pypi%20package)](https://pypi.org/project/tungstenkit/)
[![License](https://img.shields.io/github/license/tungsten-ai/tungstenkit)](https://raw.githubusercontent.com/tungsten-ai/tungstenkit/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/tungstenkit?style=flat-square)](https://pypi.org/project/tungstenkit/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/tungstenkit.svg?color=%2334D058)](https://pypi.org/project/tungstenkit/)

[Introduction](#tungstenkit-ml-container-made-simple) | [Installation](#prerequisites) | [Documentation](#documentation) | [Community](#join-our-community)

**Tungstenkit** is ML containerization tool with a focus on developer productivity and versatility. 

Have you ever struggled to use models from github?
You may have repeated tedious steps like: cuda/dependency problems, file handling, and scripting for testing.

Standing on the shoulder of Docker, this project aims to make using ML models less painful by adding functionalities for typical use cases - REST API server, GUI, CLI, and Python script.

With Tungstenkit, sharing and consuming ML models can be quick and enjoyable.


## Features
- [Requires only a few lines of Python code](#requires-only-a-few-lines-of-python-code)
- [Build once, use everywhere](#build-once-use-everywhere):
    - [REST API server](#rest-api-server)
    - [GUI application](#gui-application)
    - [CLI application](#cli-application)
    - [Python function](#python-function)
- [Framework-agnostic and lightweight](#framework-agnostic-and-lightweight)
- [Pydantic input/output definitions with convenient file handling](#pydantic-inputoutput-definitions-with-convenient-file-handling)
- [Supports batched prediction](#supports-batched-prediction)
- Supports clustering with distributed machines (coming soon)

## Take the tour
### Requires only a few lines of python code
Building a Tungsten model is easy. All you have to do is write a simple ``tungsten_model.py`` like:

```python
from typing import List
import torch
from tungstenkit import BaseIO, Image, define_model


class Input(BaseIO):
    prompt: str


class Output(BaseIO):
    image: Image


@define_model(
    input=Input,
    output=Output,
    gpu=True,
    python_packages=["torch", "torchvision"],
    batch_size=4,
    gpu_mem_gb=16,
)
class TextToImageModel:
    def setup(self):
        weights = torch.load("./weights.pth")
        self.model = load_torch_model(weights)

    def predict(self, inputs: List[Input]) -> List[Output]:
        input_tensor = preprocess(inputs)
        output_tensor = self.model(input_tensor)
        outputs = postprocess(output_tensor)
        return outputs

```

Start a build process:

```console
$ tungsten build . -n text-to-image

✅ Successfully built tungsten model: 'text-to-image:e3a5de56'
```

Check the built image:
```
$ tungsten models

Repository        Tag       Create Time          Docker Image ID
----------------  --------  -------------------  ---------------
text-to-image     latest    2023-04-26 05:23:58  830eb82f0fcd
text-to-image     e3a5de56  2023-04-26 05:23:58  830eb82f0fcd
```

### Build once, use everywhere

#### REST API server

Start a server:

```console
$ tungsten serve text-to-image -p 3000

INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
```

Send a prediction request with a JSON payload:

```console
$ curl -X 'POST' 'http://localhost:3000/predictions' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[{"prompt": "a professional photograph of an astronaut riding a horse"}]'

{
    "prediction_id": "39c9eb6b"
}
```

Get the result:
```console
$ curl -X 'GET' 'http://localhost:3000/predictions/39c9eb6b' \
  -H 'Accept: application/json'

{
    "outputs": [{"image": "data:image/png;base64,..."}],
    "status": "success"
}
```


#### GUI application
If you need a more user-friendly way to make predictions, start a GUI app with the following command:

```console
$ tungsten demo text-to-image -p 8080

INFO:     Uvicorn running on http://localhost:8080 (Press CTRL+C to quit)
```

![tungsten-dashboard](https://github.com/tungsten-ai/assets/blob/main/common/local-model-demo.gif?raw=true "Demo GIF")

#### CLI application
Run a prediction in a terminal:
```console
$ tungsten predict text-to-image \
   -i prompt="a professional photograph of an astronaut riding a horse"

{
  "image": "./output.png"
}
```

#### Python function
If you want to run a model in your Python application, use the Python API:
```python
>>> from tungstenkit import models
>>> model = models.get("text-to-image")
>>> model.predict(
    {"prompt": "a professional photograph of an astronaut riding a horse"}
)
{"image": PosixPath("./output.png")}
```

### Framework-agnostic and lightweight
Tungstenkit doesn't restrict you to use specific ML libraries. Just use any library you want, and declare dependencies:

```python
# The latest cpu-only build of Tensorflow will be included
@define_model(gpu=False, python_packages=["tensorflow"])
class TensorflowModel:
    def predict(self, inputs):
        """Run a batch prediction"""
        # ...ops using tensorflow...
        return outputs
```

### Pydantic input/output definitions with convenient file handling
Let's look at the example below:
```python
from tungstenkit import BaseIO, Image, define_model


class Input(BaseIO):
    image: Image


class Output(BaseIO):
    image: Image


@define_model(input=Input, output=Output)
class StyleTransferModel:
    ...
```
As you see, input/output types are defined as subclasses of the ``BaseIO`` class. The ``BaseIO`` class is a simple wrapper of the [``BaseModel``](https://docs.pydantic.dev/latest/usage/models/) class of [Pydantic](https://docs.pydantic.dev/latest/), and Tungstenkit validates JSON requests utilizing functionalities Pydantic provides.

Also, you can see that the ``Image`` class is used. Tungstenkit provides four file classes for easing file handling - ``Image``, ``Audio``, ``Video``, and ``Binary``. They have useful methods for writing a model's ``predict`` method:

```python
class StyleTransferModel:
    def predict(self, inputs: List[Input]) -> List[Output]:
        # Preprocessing
        input_pil_images = [inp.image.to_pil_image() for inp in inputs]
        # Inference
        output_pil_images = do_inference(input_pil_images)
        # Postprocessing
        output_images = [Image.from_pil_image(pil_image) for pil_image in output_pil_images]
        outputs = [Output(image=image) for image in output_images]
        return outputs
```

### Supports batched prediction
Tungstenkit supports both server-side and client-side batching.

- **Server-side batching**  
    <!-- Explain more? Mention hashing? -->
    A server groups inputs across multiple requests and processes them together.
    You can configure the max batch size:
    ```python
    @define_model(input=Input, output=Output, gpu=True, batch_size=32)
    ```
    The max batch size can be changed when running a server:
    ```console
    $ tungsten serve mymodel -p 3000 --batch-size 16
    ```

- **Client-side batching**  
    Also, you can reduce traffic volume by putting multiple inputs in a single prediction request:
    ```console
    $ curl -X 'POST' 'http://localhost:3000/predictions' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '[{"field": "input1"}, {"field": "input2"}, {"field": "input3"}]'
    ```

## Prerequisites
- Python 3.7+
- [Docker](https://docs.docker.com/get-docker/)

## Installation
```shell
pip install tungstenkit
```

## Documentation
- [Getting Started](https://tungsten-ai.github.io/docs/getting_started/installation/)
- [Building Your Model](https://tungsten-ai.github.io/docs/building_your_model/model_definition/)
- [Running Models](https://tungsten-ai.github.io/docs/running_models/using_gpus/)
- [Pushing and Pulling Models](https://tungsten-ai.github.io/docs/pushing_and_pulling_models/pushing/)
- [CLI Reference](https://tungsten-ai.github.io/docs/cli_reference/)
- [REST API Reference](https://tungsten-ai.github.io/docs/rest_api_reference/)
- [Examples](https://tungsten-ai.github.io/docs/examples/image_blurring/)

## Join our community
If you have questions about anything related to Tungstenkit, you're always welcome to ask our community on [Discord](https://discord.gg/NESFeXzFuy).
