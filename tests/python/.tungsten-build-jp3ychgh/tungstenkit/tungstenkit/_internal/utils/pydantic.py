import pydantic


def run_validation(model: pydantic.BaseModel):
    values, fields_set, validation_error = pydantic.validate_model(model.__class__, model.__dict__)
    if validation_error:
        raise validation_error
    try:
        object.__setattr__(model, "__dict__", values)
    except TypeError as e:
        raise TypeError(
            "Model values must be a dict; you may not have returned "
            + "a dictionary from a root validator"
        ) from e
    object.__setattr__(model, "__fields_set__", fields_set)
    return model
