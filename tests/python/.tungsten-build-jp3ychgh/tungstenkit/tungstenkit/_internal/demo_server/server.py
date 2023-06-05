import shutil
import signal
from pathlib import Path
from threading import Event

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tungstenkit._internal import storables
from tungstenkit._internal.containers import ModelContainer
from tungstenkit._internal.model_clients import ModelContainerClient

from . import schemas
from .services import FileService, PredictionService

frontend_dir_in_pkg = Path(__file__).parent / "frontend"


def create_demo_app(tmp_dir: Path, model_container: ModelContainer):
    # TODO https
    # TODO issue access token like jupyter
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    frontend_dir_in_tmp_dir = tmp_dir / "frontend"
    shutil.copytree(frontend_dir_in_pkg, frontend_dir_in_tmp_dir)

    _add_api_endpoints(
        app=app,
        model_container=model_container,
        file_dir=tmp_dir / "files",
    )
    _mount_frontend_dir(app=app, dir=frontend_dir_in_tmp_dir)

    return app


def _add_api_endpoints(
    app: FastAPI,
    model_container: ModelContainer,
    file_dir: Path,
):
    model_data = storables.ModelData.load(model_container.model_name)

    # Prepare services
    model_client = ModelContainerClient(container=model_container)
    file_service = FileService(base_dir=file_dir)
    prediction_service = PredictionService(
        file_service=file_service,
        model_client=model_client,
        input_schema=model_data.io.input_schema,
        input_filetypes=model_data.io.input_filetypes,
    )

    # Start garbage collection
    gc_term_event = Event()
    file_gc_thread = file_service.start_garbage_collection(gc_term_event)
    prediction_gc_thread = prediction_service.start_garbage_collection(gc_term_event)
    is_gc_error_raised = False

    orig_sig_handler = signal.getsignal(signal.SIGTERM)

    def log_gc_errors(*args, **argv):
        if gc_term_event.is_set():
            gc_term_event.clear()
            if not is_gc_error_raised:
                if not prediction_gc_thread.is_alive():
                    raise RuntimeError("Prediction garbage collector is unexpectedly terminated")
                if not file_gc_thread.is_alive():
                    raise RuntimeError("File garbage collector is unexpectedly terminated")
        else:
            orig_sig_handler(*args, **argv)

    signal.signal(signal.SIGTERM, log_gc_errors)

    # Add endpoints
    @app.get("/metadata", response_model=schemas.Metadata)
    def get_model_metadata(req: Request):
        return schemas.Metadata.build(model=model_data, file_service=file_service, request=req)

    @app.post("/predictions", response_model=schemas.PostPredictionResponse)
    def create_prediction(body: schemas.PostPredictionRequest, req: Request):
        prediction_id = prediction_service.create_prediction(input=body.__root__)
        return schemas.PostPredictionResponse(prediction_id=prediction_id)

    @app.get("/predictions/{prediction_id}", response_model=schemas.Prediction)
    def get_prediction(prediction_id: str, req: Request):
        return prediction_service.get_prediction_by_id(prediction_id=prediction_id, request=req)

    @app.post("/predictions/{prediction_id}/cancel")
    def cancel_prediction(prediction_id: str):
        prediction_service.cancel_prediction_by_id(prediction_id)

    @app.post("/files", response_model=schemas.FileUploadResponse)
    def upload_file(file: UploadFile, req: Request):
        filename = file_service.add_file_by_buffer(
            filename=file.filename if file.filename else "file", buf=file.file, protected=False
        )
        return schemas.FileUploadResponse(
            serving_url=file_service.build_serving_url(filename, request=req)
        )

    @app.get(
        "/files/{filename}",
        response_class=FileResponse,
        dependencies=[Depends(file_service.acquire_read_lock)],
        name="files",
    )
    def download_file(filename: str):
        if not file_service.check_existence(filename, strict=True):
            raise HTTPException(status_code=404, detail=filename)
        path = file_service.get_path_by_filename(filename).resolve()
        return FileResponse(path=path)


def _mount_frontend_dir(app: FastAPI, dir: Path):
    app.mount("/", StaticFiles(directory=dir, html=True), name="webapp")
