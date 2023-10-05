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
        demo_output_schema=model_loader.demo_output_class.schema(),
    )

    PredictionRequest = schema.PredictionRequest.with_type(model_loader.input_class)
    PredictionResponse = schema.PredictionResponse.with_type(model_loader.output_class)
    DemoResponse = schema.DemoResponse.with_type(model_loader.output_class)

    # TODO define route class

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
        try:
            prediction_id = prediction_worker.create_prediction(
                inputs=req.__root__, is_demo=False  # type: ignore
            )
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)

        async_resp = schema.PredictionID(prediction_id=prediction_id)

        try:
            try:
                prediction_worker.wait_for_prediction(async_resp.prediction_id)
            except Exception as e:
                logger.exception(e)
                raise HTTPException(status_code=500)
            try:
                result = prediction_worker.get_prediction_result(prediction_id)
            except server_exceptions.PredictionIDNotFound as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.exception(e)
                raise HTTPException(status_code=500)

            resp = PredictionResponse(
                outputs=result.outputs,  # type: ignore
                status=result.status,
                error_message=result.error_message,
            )

        finally:
            try:
                cancel(async_resp.prediction_id)
            except Exception:
                pass

            try:
                prediction_worker.remove_prediction_result(async_resp.prediction_id)
            except Exception:
                pass

        return resp

    @app.post("/predictions", response_model=schema.PredictionID)
    def predict_asynchronously(req: PredictionRequest):  # type: ignore
        try:
            prediction_id = prediction_worker.create_prediction(
                inputs=req.__root__,  # type: ignore
                is_demo=False,
            )
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)

        return schema.PredictionID(prediction_id=prediction_id)

    @app.get(
        "/predictions/{prediction_id}",
        response_model=PredictionResponse,
    )
    def get_prediction_result(prediction_id: str):
        try:
            result = prediction_worker.get_prediction_result(prediction_id)
        except server_exceptions.PredictionIDNotFound as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)

        return PredictionResponse(
            outputs=result.outputs,  # type: ignore
            status=result.status,
            error_message=result.error_message,
        )

    @app.post("/predictions/{prediction_id}/cancel")
    def cancel_prediction(prediction_id: str):
        return cancel(prediction_id)

    @app.post(
        "/demo",
        response_model=schema.DemoID,
    )
    def request_demo(req: PredictionRequest):  # type: ignore
        try:
            demo_id = prediction_worker.create_prediction(
                inputs=req.__root__,  # type: ignore
                is_demo=True,
            )
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)
        return schema.DemoID(demo_id=demo_id)

    @app.get(
        "/demo/{demo_id}",
        response_model=DemoResponse,
    )
    def get_demo_result(demo_id: str):
        try:
            result = prediction_worker.get_prediction_result(demo_id)
        except server_exceptions.PredictionIDNotFound as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500)

        return DemoResponse(
            outputs=result.outputs,  # type: ignore
            status=result.status,
            error_message=result.error_message,
            demo_outputs=result.demo_outputs,
            logs=result.logs,
        )

    @app.post(
        "/demo/{demo_id}/cancel",
    )
    def cancel_demo(demo_id: str):
        return cancel(demo_id)


def _setup_openapi(app: FastAPI):
    # TODO use user-defined readme here
    openapi_schema = get_openapi(
        title=OPENAPI_TITLE,
        version=str(pkg_version),
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema
