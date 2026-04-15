# UFS Non-Batch Kafka Bridge

This branch is a fresh, simple project for the office-like flow you asked:

- No Report Tool mock in code
- No topic creation in code (Report Tool already manages topics)
- Consume from input topic
- Call UFS forecast endpoint (`xyz.something`)
- Publish result to output topic
- Process messages sequentially (one by one)

## Runtime assumptions

- Python: `3.12.x` (you mentioned `31.12.3`, assumed this means `3.12.3`)
- Docker: compatible with your office VM (`29.4.0`)
- Kafka image: `apache/kafka:latest` in `docker-compose.yml`

## Project files

- `config.py` - env-based runtime configuration
- `ufs_client.py` - HTTP client to call UFS endpoint
- `ufs_kafka_bridge.py` - main consumer -> UFS -> producer flow
- `docker-compose.yml` - optional local Kafka (latest image)
- `flow.md` - full project flow and implementation order

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set these variables before running:

```bash
export KAFKA_BOOTSTRAP=localhost:9092
export INPUT_TOPIC=ufs.bulk.input
export OUTPUT_TOPIC=ufs.bulk.output
export CONSUMER_GROUP_ID=ufs-service-non-batch
export UFS_FORECAST_ENDPOINT=https://xyz.something/forecast
export UFS_TIMEOUT_SECONDS=30
```

## Run

### A) Run with real Report Tool topics (office flow)

```bash
source .venv/bin/activate
python ufs_kafka_bridge.py
```

The service keeps polling, processes each message sequentially, sends it to UFS endpoint, and publishes SUCCESS/FAILED message to output topic.

## Independent local testing (when Report Tool topics are not ready)

Use these helper scripts for a fully local test loop:

1) (Optional) start local Kafka:

```bash
docker compose up -d
```

2) Create input/output topics for local test only:

```bash
source .venv/bin/activate
python local_test_create_topics.py
```

3) Start a tiny local UFS mock API:

```bash
source .venv/bin/activate
python local_mock_ufs_api.py
```

4) In another terminal, point bridge to local mock endpoint and start bridge:

```bash
source .venv/bin/activate
export UFS_FORECAST_ENDPOINT=http://localhost:8080/forecast
python ufs_kafka_bridge.py
```

5) In another terminal, publish sample input messages:

```bash
source .venv/bin/activate
python local_test_publish_input.py
```

6) In another terminal, read output topic:

```bash
source .venv/bin/activate
python local_test_read_output.py
```

This gives you an end-to-end bridge test without waiting for Report Tool implementation.

### B) One-command local demo launcher

You can also run:

```bash
chmod +x run_local_demo.sh
./run_local_demo.sh
```

This script will:
- start local Kafka
- create local test topics
- open 4 terminals (mock UFS, bridge, output reader, publisher prompt)

In the publisher terminal, run:

```bash
python local_test_publish_input.py
```
