FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SILVERTRAP_DATA_DIR=/data
WORKDIR /app
RUN groupadd --gid 10001 silvertrap && useradd --uid 10001 --gid silvertrap --create-home silvertrap && mkdir /data && chown silvertrap:silvertrap /data
COPY --chown=silvertrap:silvertrap silvertrap ./silvertrap
USER silvertrap
VOLUME /data
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/',timeout=2)" || exit 1
CMD ["python", "-m", "silvertrap", "serve", "--host", "0.0.0.0", "--seed"]
