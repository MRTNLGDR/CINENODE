FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir .
ENV CINENODE_HOME=/data CINENODE_HOST=0.0.0.0 CINENODE_PORT=8765 CINENODE_MODE=server
VOLUME ["/data"]
EXPOSE 8765
CMD ["python","-m","cinenode","serve","--host","0.0.0.0","--port","8765","--mode","server","--no-open"]
