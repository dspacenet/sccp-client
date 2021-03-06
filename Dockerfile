FROM ubuntu:latest
RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential
RUN pip install flask
RUN pip install parse
RUN pip install python-crontab

ENTRYPOINT ["python"]
CMD ["sccp.py"]