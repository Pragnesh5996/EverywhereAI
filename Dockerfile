FROM python:3.8-slim-bullseye
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/
RUN python3 manage.py migrate
EXPOSE 8000
EXPOSE 6379
RUN apt-get update && apt-get install -y wkhtmltopdf && mkdir -p /tmp/runtime-root && chmod 0700 /tmp/runtime-root
# CMD ["python3", "manage.py", "runserver","0.0.0.0:8000"]
CMD []
