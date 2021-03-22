FROM python:3.8

COPY price.py /home/price-fc/price.py

COPY ./requirements.txt /home/price/requirements.txt
RUN pip install -r /home/price/requirements.txt

ENTRYPOINT ['price.py']
