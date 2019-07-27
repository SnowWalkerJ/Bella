FROM python:3.7

RUN apt update && apt install python3-pip

WORKDIR /root

COPY . .

RUN pip3 install -r requirements.txt && python setup.py install
