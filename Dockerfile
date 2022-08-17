FROM python:3.9.9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/scripts:${PATH}"

COPY requirements.txt .
WORKDIR /app
COPY aarons_kit /aarons_kit
COPY scripts /scripts

RUN pip3 install --upgrade pip && \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc libc-dev python3-dev postgresql && \
    pip3 install -r ../requirements.txt && \
    chmod +x /scripts/* && \
    mkdir -p /vol/web/media && \
    mkdir -p /vol/web/static && \
    mkdir -p /home/user/ && \
    useradd user && \
    chown -R user:user /vol && \
    chown -R user:user /home/user && \
    chmod -R 755 /vol/web && \
    chown -R user:user /app && \
    chmod -R 755 /app

USER user

CMD ["entrypoint.sh"]
