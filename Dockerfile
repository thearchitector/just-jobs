# syntax=docker/dockerfile:1.2


FROM python:3.6-slim-buster

ARG GROUPID=1000
ARG USERID=1000
ARG USERNAME=developer

## configure python and pip runtime settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PYTHONFAULTHANDLER=1 \
    PYTHONCOERCECLOCALE=0 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1

## setup user and install system packages
RUN set -ex && \
    groupadd -g $GROUPID $USERNAME && \
    useradd -lmu $USERID -g $USERNAME -s /bin/bash $USERNAME && \
    apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install --no-install-recommends -y neovim curl procps && \
    apt-get autoremove --purge && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip

## set user $HOME and set working directory
ENV HOME=/home/$USERNAME
USER $USERNAME
WORKDIR $HOME/just-jobs

## configure poetry settings
ENV POETRY_NO_INTERACTION=1 \
    POETRY_NO_ANSI=1 \
    PATH="${HOME}/.poetry/bin:${PATH}"

## install poetry
SHELL [ "/bin/bash", "-o", "pipefail", "-c" ]
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

## copy and install project dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev --no-root --remove-untracked

## copy everything else
COPY . ./
RUN poetry install

SHELL [ "poetry", "shell" ]
CMD [ "tail", "-f", "/dev/null" ]