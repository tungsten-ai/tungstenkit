import typing as t

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from loguru import logger

from tungstenkit._internal.model_def_loader import ModelDefLoader
from tungstenkit._versions import pkg_version

from . import schema, server_exceptions
from .prediction_worker import PredictionWorker

R = t.TypeVar("R", bound=schema.PredictionResponse)

OPENAPI_TITLE = "Tungsten Model"


def create_app(
    prediction_worker: PredictionWorker,
    model_loader: ModelDefLoader,
):
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _add_endpoints(app, prediction_worker=prediction_worker, model_loader=model_loader)
    _setup_openapi(app)

    return app


def _add_endpoints(
    app: FastAPI, prediction_worker: PredictionWorker, model_loader: ModelDefLoader
):
    basic_info = schema.Metadata(
        input_schema=model_loader.input_class.schema(),
        output_schema=model_loader.output_class.schema(),
    )

    PredictionRequest = schema.PredictionRequest.with_type(model_loader.input_class)
    PredictionResponse = schema.PredictionResponse.with_type(model_loader.output_class)
    DemoResponse = schema.DemoResponse.with_type(model_loader.output_class)

    # TODO define route class

    def _predict_async(
        req: PredictionRequest,  # type: ignore
        *,
        is_demo: bool,
    ) -> schema.PredictionID:
        try:
            prediction_id = prediction_worker.create_prediction(
                inputs=req.__root__,  # type: ignore
                is_demo=is_demo,
            )
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)
        return schema.PredictionID(prediction_id=prediction_id)

    def _get_resp(
        prediction_id: str,
        resp_cls: t.Type[R],
    ) -> R:
        try:
            result = prediction_worker.get_prediction_result(prediction_id)
        except server_exceptions.PredictionIDNotFound as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)

        if issubclass(resp_cls, DemoResponse):
            return DemoResponse(
                outputs=result.outputs,  # type: ignore
                status=result.status,
                error_message=result.error_message,
                demo_outputs=result.demo_outputs,
                logs=result.logs,
            )
        else:
            return resp_cls(
                outputs=result.outputs,  # type: ignore
                status=result.status,
                error_message=result.error_message,
            )

    def _predict_sync(
        req: PredictionRequest,  # type: ignore
        output_cls: t.Type[R],
        *,
        demo: bool,
    ) -> R:
        async_resp = _predict_async(req, is_demo=demo)
        try:
            prediction_worker.wait_for_prediction(async_resp.prediction_id)
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)
        resp = _get_resp(async_resp.prediction_id, output_cls)
        prediction_worker.remove_prediction_result(async_resp.prediction_id)
        return resp

    def cancel(prediction_id: str) -> Response:
        try:
            prediction_worker.cancel_prediction(prediction_id)
        except server_exceptions.PredictionIDNotFound as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)
        return Response(status_code=200)

    @app.get("/", response_model=schema.Metadata)
    async def get_metadata():
        return basic_info

    @app.post(
        "/predict",
        response_model=PredictionResponse,
    )
    def predict_synchronously(req: PredictionRequest):  # type: ignore
        return _predict_sync(req, PredictionResponse, demo=False)

    @app.post("/predict_async", response_model=schema.PredictionID)
    def predict_asynchronously(req: PredictionRequest):  # type: ignore
        return _predict_async(req, is_demo=False)

    @app.get(
        "/predict_async/{prediction_id}",
        response_model=PredictionResponse,
    )
    def get_prediction_result(prediction_id: str):
        return _get_resp(prediction_id, PredictionResponse)

    @app.post("/predict_async/{prediction_id}/cancel")
    def cancel_prediction(prediction_id: str):
        return cancel(prediction_id)

    @app.post(
        "/demo",
        response_model=schema.PredictionID,
    )
    def request_demo(req: PredictionRequest):  # type: ignore
        return _predict_async(req, is_demo=True)

    @app.get(
        "/demo/{prediction_id}",
        response_model=DemoResponse,
    )
    def get_demo_result(prediction_id: str):
        return _get_resp(prediction_id, DemoResponse)

    @app.post(
        "/demo/{prediction_id}/cancel",
    )
    def cancel_demo(prediction_id: str):
        return cancel(prediction_id)


def _setup_openapi(app: FastAPI):
    # TODO use user-defined readme here
    openapi_schema = get_openapi(
        title=OPENAPI_TITLE,
        version=str(pkg_version),
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema
