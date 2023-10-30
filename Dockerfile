FROM python:3.11-alpine

WORKDIR /code

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "2", "appserver:gunicorn_app"]
