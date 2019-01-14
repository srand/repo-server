FROM python:2

ADD repo-server /opt/repo-server

EXPOSE 9123/tcp

ENV REPO_SERVER_HOME /data/repo-server

CMD ["python", "/opt/repo-server/__main__.py"]
