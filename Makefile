up:
	DOCKER_CLIENT_TIMEOUT=120 COMPOSE_HTTP_TIMEOUT=120 \
	docker compose up -d

down:
	DOCKER_CLIENT_TIMEOUT=120 COMPOSE_HTTP_TIMEOUT=120 \
	docker compose down

build:
	docker build -t clicker . --no-cache
