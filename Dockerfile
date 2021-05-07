FROM python:3.8

ENV APP_NAME=price.py
COPY /code/"$APP_NAME" /code/"$APP_NAME"
COPY /code/price.conf /code/price.conf
COPY /code/exchangeratesAPI /code/exchangeratesAPI

WORKDIR /code


ENV FLASK_APP="$APP_NAME"
ENV FLASK_RUN_HOST=0.0.0.0

RUN pip3 install --no-cache-dir --upgrade pip

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 5001

CMD ["flask", "run"]
