FROM ubuntu:16.04

RUN apt-get update && apt-get upgrade -y
RUN apt-get install jq python3-pip curl -y

COPY . /root/aws-cost-report
WORKDIR /root/aws-cost-report
RUN pip3 install -r requirements.txt

ENV PYTHONUNBUFFERED=0

ENTRYPOINT ["/root/aws-cost-report/run.py"]
