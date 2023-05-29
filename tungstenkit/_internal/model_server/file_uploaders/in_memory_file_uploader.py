import typing as t
from concurrent.futures import ThreadPoolExecutor

from tungstenkit._internal import io

from .abstract_file_uploader import AbstractFileUploader


class InMemoryFileUploader(AbstractFileUploader):
    def upload(self, files: t.List[io.File]) -> t.List[io.File]:
        """Load files as data uris"""
        classes = [f.__class__ for f in files]
        rets = []
        with ThreadPoolExecutor(max_workers=1) as executor:
            for i, file in enumerate(files):
                fut = executor.submit(file.__root__.to_data_uri)
                data_uri = fut.result()
                rets.append(classes[i](__root__=data_uri))

        return rets
