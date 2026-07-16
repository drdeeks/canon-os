FROM python:3.11-slim

RUN groupadd -g 1000 creator && \
    useradd -u 1000 -g creator -m -s /bin/false creator

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY templates/ /app/templates/

RUN mkdir -p /home/creator/ai-studio/{config,models/{text,image,video,audio},projects,exports,uploads,cache}
RUN chown -R 1000:1000 /home/creator/ai-studio

USER 1000

ENV CREATOR_HOME=/home/creator/ai-studio
ENV STUDIO_MOUNT=/mnt/studio

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
