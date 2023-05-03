# syntax=docker/dockerfile:1

FROM python:3.7

RUN pip install -U pip setuptools wheel && \
    pip install pdm

COPY . ./just-jobs

WORKDIR /just-jobs
RUN pdm export -G :all -o requirements.txt --without-hashes && \
    pip install -r requirements.txt

ENV PYTHONPATH=/just-jobs

CMD [ "bash" ]
