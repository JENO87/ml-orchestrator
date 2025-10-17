

FROM python:3.8-slim
WORKDIR /app
COPY . .
RUN pip install uv
RUN uv pip install --system -e .
CMD ["uv", "run", "python", "scripts/main.py"]
