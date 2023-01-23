FROM python:3.10-alpine

ARG SERVER_PORT

# Enable logging
ENV PYTHONUNBUFFERED=1
# Set working directory
WORKDIR /service

RUN apk add libffi-dev build-base

# Install poetry
RUN pip install poetry

# Get required poetry files for dependecies
COPY ./transaction-broker/pyproject.toml /service/pyproject.toml
COPY ./transaction-broker/poetry.lock /service/poetry.lock

RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-root

COPY ./transaction-broker /service

ENTRYPOINT [ "python", "main.py"]
