FROM python:3.12.2-slim-bookworm

WORKDIR /application
COPY . /application
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry==2.1.1
#RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"
RUN poetry install
CMD ["tail", "-f", "/dev/null"]