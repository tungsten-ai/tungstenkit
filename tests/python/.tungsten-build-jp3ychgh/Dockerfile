
FROM library/python:3.7.16-slim
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked apt-get update -y && \
    apt-get install -y --no-install-recommends tini
WORKDIR /tungsten



ENV TUNGSTEN_MODEL_MODULE=dummy_model TUNGSTEN_MODEL_CLASS=DummyModel TUNGSTEN_MAX_BATCH_SIZE=4



COPY .tungsten-build-jp3ychgh/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked pip install -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt




COPY . .


COPY .tungsten-build-jp3ychgh/tungstenkit /etc/tungsten

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked cd /etc/tungsten && pip install .

ENTRYPOINT ["/usr/bin/tini","--","python","-m","tungstenkit._internal.model_server"]

LABEL device="cpu"
