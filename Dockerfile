# Dockerfile created with reccomendations from the following repos:
# - https://github.com/hexops/dockerfile
# - https://github.com/juan131/dockerfile-best-practices
# - https://www.youtube.com/watch?v=74rOYNmxfL8
FROM python:3.7.11-slim-buster

# Create non-root user and group
RUN addgroup --gid 10001 --system nonroot &&\
    adduser  --uid 10000 --system --ingroup nonroot --home /home/nonroot nonroot

# Copy source code and change owner
WORKDIR /crashserver_app
COPY requirements.txt .
COPY main.py .
COPY crashserver/ crashserver/
COPY res/ res/
COPY config/ config/
RUN chown nonroot:nonroot /crashserver_app

# libmagic is needed to check if an uploaded file is actually a minidump.
RUN apt update && apt upgrade && apt install libmagic1 -y --no-install-recommends
RUN pip install --no-cache-dir -r requirements.txt

USER nonroot
EXPOSE 8888
CMD ["gunicorn", "main:app", "-b", "0.0.0.0:8888"]

