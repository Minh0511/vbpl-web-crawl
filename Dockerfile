FROM python:3.10.12-slim as compile-image

RUN apt-get -y update && apt-get -y --no-install-recommends install git default-libmysqlclient-dev build-essential

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.10.12-slim
COPY --from=compile-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
ADD . /app/
CMD ["python", "main.py"]