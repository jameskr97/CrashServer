# Dockerfile created with reccomendations from the following links:
# - https://github.com/hexops/dockerfile
# - https://github.com/juan131/dockerfile-best-practices
# - https://www.youtube.com/watch?v=74rOYNmxfL8
# - https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker
FROM python:3.10.1-slim-bullseye as builder

# Install poetry for building
WORKDIR /build
ENV POETRY_VERSION=1.3.1

COPY poetry.lock pyproject.toml ./
RUN pip install "poetry==$POETRY_VERSION" && python -m venv /venv && poetry export -f requirements.txt | /venv/bin/pip install -r /dev/stdin

# Copy source code, change owner, then build
COPY README.md .
COPY main.py .
COPY crashserver/ crashserver/
RUN poetry build && /venv/bin/pip install dist/*.whl

FROM python:3.10.1-slim-bullseye as runner

# Set enviroment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PUID=10000
ENV PGID=10001
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV ENV_FOR_DYNACONF=docker

# Copy environment, change owner, and install system dependencies
WORKDIR /app
COPY main.py ./
COPY main-rq.py ./
COPY config/ config/
COPY res/ res/
COPY crashserver/migrations crashserver/migrations

# Install linux dependencies
COPY --from=builder /venv /venv
RUN apt update &&\
    apt install libmagic1 libcurl3-gnutls tzdata gosu -y --no-install-recommends &&\
    rm -rf /var/lib/apt/lists/* &&\
    python3 -m venv $VIRTUAL_ENV

COPY .docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "./main.py"]

