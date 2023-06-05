import typing as t


def get_input_ids_from_prediction_id(prediction_id: str, num_inputs: int) -> t.List[str]:
    num_digits = len(str(num_inputs))
    input_ids: t.List[str] = list()
    for idx in range(num_inputs):
        idx_str = str(idx).rjust(num_digits, "0")
        input_ids.append(prediction_id + "-" + idx_str)
    return input_ids


def get_prediction_id_from_input_id(input_id: str) -> str:
    return input_id.split("-")[0]


def check_input_in_prediction(input_id: str, prediction_id: str) -> bool:
    return input_id.startswith(prediction_id)
