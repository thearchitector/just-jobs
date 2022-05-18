# syntax=docker/dockerfile:1.2


FROM python:3.7-slim-buster

## configure env vars
ENV POETRY_NO_INTERACTION=1 \
    POETRY_NO_ANSI=1 \
    POETRY_HOME=/etc/poetry \
    PATH="/etc/poetry/bin:${PATH}"

## install system packages
RUN apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install --no-install-recommends -y neovim curl procps && \
    apt-get autoremove --purge && \
    rm -rf /var/lib/apt/lists/*

## install poetry
RUN curl -sSL https://install.python-poetry.org | python - && \
    poetry config virtualenvs.create false

## copy and install project
WORKDIR /just-jobs
COPY . /just-jobs
RUN poetry install

CMD [ "pytest", "tests" ]