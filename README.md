# UFS Bulk Forecasting (Minimal Local Prototype)

This is a very small, local project that mirrors your office design:

- routing gate (light vs heavy path)
- Topic A: `ufs.bulk.input` (Report Tool -> UFS)
- Topic B: `ufs.bulk.output` (UFS -> Report Tool)
- one message per node-port-KPI
- manual offset commit only after result publish
- idempotency key check
- success/failure payload styles

It is intentionally simple but keeps the same architecture concepts.

## 1) Start Kafka

```bash
docker compose up -d
```

## 2) Create Python env + install deps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Create topics

```bash
python create_topics.py
```

## 4) Run services in 3 terminals

Terminal A (UFS worker):

```bash
source .venv/bin/activate
python ufs_worker.py
```

Terminal B (Report Tool output consumer):

```bash
source .venv/bin/activate
python report_tool_consumer.py
```

Terminal C (simulate Report Tool gateway + DB interface publish):

```bash
source .venv/bin/activate
python report_tool_producer.py
```

You should see:

- producer publishes `N` batches to `ufs.bulk.input`
- UFS worker consumes one-by-one, runs 3-pass mock logic, publishes results
- RT consumer receives all results and marks `JOB COMPLETE`

## Concept mapping to your design

- **Routing gate**: `report_tool_producer.py` estimates row count and picks heavy path.
- **Partition keys**:
  - input key = `node_ip:object_name`
  - output key = `job_id`
- **Idempotency**: `ufs_worker.py` tracks `job_id:batch_seq:node_ip:object_name:kpi_name`.
- **Reliability pattern**: worker commits input offset only after successful publish to output topic.
- **Same result contract idea**: output payload includes job identity, status, processing meta, and `output.output[]`.

## Notes

- This demo uses a tiny in-memory idempotency cache (`set()`), not Redis.
- The 3-pass forecast is mocked to keep the project small and easy to inspect.
- `force_heavy_demo=True` is enabled so you can test Kafka path quickly even with small data.

## Optional next upgrades (office-like)

- replace in-memory idempotency with Redis TTL cache
- add retry/backoff and dead-letter topic
- add token validation middleware on RT consumer
- switch to Avro/Protobuf with schema registry
- add Prometheus metrics and Grafana dashboard
