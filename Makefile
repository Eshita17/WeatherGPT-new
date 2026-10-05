dev:
	docker compose up --build

down:
	docker compose down

test:
	python -m pytest -q

api:
	uvicorn apps.api.main:app --reload --port 8000

eval:
	python eval/run_eval.py

cluster-up:
	kind create cluster --name weathergpt --config infra/cluster/kind.yaml

cluster-delete:
	kind delete cluster --name weathergpt

k8s:
	kubectl apply -k infra/k8s/overlays/dev
