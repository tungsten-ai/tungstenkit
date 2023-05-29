from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from tungstenkit._internal.model_server.input_queues import AbstractInputQueue


def _generate_prediction_id():
    return uuid4().hex


def _test_input_queue(dummy_io_generator, queue: AbstractInputQueue):
    all_inputs = []

    inputs = dummy_io_generator(n=2)[0]
    all_inputs.extend(inputs)
    queue.push(_generate_prediction_id(), inputs, is_demo=False)

    to_be_removed = _generate_prediction_id()
    inputs = dummy_io_generator(n=1)[0]
    queue.push(to_be_removed, inputs, is_demo=False)

    inputs = dummy_io_generator(n=2)[0]
    all_inputs.extend(inputs)
    queue.push(_generate_prediction_id(), inputs, is_demo=False)

    queue.remove(to_be_removed)

    poped = queue.pop(4)
    assert len(poped.data) == 4
    for i in range(4):
        poped.data[i] == jsonable_encoder(all_inputs[i])
    try:
        poped = queue.pop(4, timeout=0.1)
        raise ValueError
    except TimeoutError:
        pass


def test_queues(dummy_io_generator):
    assert len(AbstractInputQueue.__subclasses__()) > 0
    for c in AbstractInputQueue.__subclasses__():
        _test_input_queue(dummy_io_generator, c())
