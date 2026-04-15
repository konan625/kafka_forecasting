# UFS Non-Batch Project Flow

This document describes the new branch design where UFS only does:

1. Subscribe to input topic from Report Tool
2. Read one Kafka message (one node-port + one KPI)
3. Call UFS forecast endpoint (`xyz.something`)
4. Publish result to output topic from Report Tool

No batch-seq logic and no topic creation logic are implemented here.

---

## 1) End-to-end runtime flow

1. Start UFS Kafka bridge service (`ufs_kafka_bridge.py`).
2. Service subscribes to `INPUT_TOPIC`.
3. For each message consumed:
   - Parse payload JSON.
   - Keep key identity fields (`job_id`, `node_ip`, `object_name`, `kpi_name`).
   - Call UFS endpoint via HTTP POST.
4. Build output payload:
   - `SUCCESS` with UFS response, or
   - `FAILED` with error details.
5. Publish output to `OUTPUT_TOPIC`.
6. Commit Kafka offset only after publish is successful.
7. Loop forever and process next message sequentially.

---

## 2) File creation order (and why)

This is the order used to implement the project in a way that is easy to explain in office:

1. `config.py`
   - Added environment-driven config so Report Tool-provided topics can be used directly.
   - Keeps topic names, group id, endpoint URL, and timeout outside code.

2. `ufs_client.py`
   - Added a very small HTTP helper that sends one message payload to UFS endpoint.
   - Isolated this logic to keep the main loop readable.

3. `ufs_kafka_bridge.py`
   - Added the core workflow: consume -> call UFS -> produce result -> commit.
   - Kept `max_poll_records=1` for clear sequential processing.

4. `requirements.txt`
   - Added only required libraries: Kafka client + HTTP client.

5. `README.md`
   - Rewritten for this branch behavior only (no mock producer/consumer, no topic creation).

6. `docker-compose.yml` (optional local test helper)
   - Updated to a latest Kafka image to match your requirement.
   - This is optional because in office Report Tool Kafka already exists.

---

## 3) Files in this branch and purpose

- `config.py`
  - Reads env vars:
    - `KAFKA_BOOTSTRAP`
    - `INPUT_TOPIC`
    - `OUTPUT_TOPIC`
    - `CONSUMER_GROUP_ID`
    - `UFS_FORECAST_ENDPOINT`
    - `UFS_TIMEOUT_SECONDS`
    - `MAX_POLL_RECORDS`

- `ufs_client.py`
  - `call_ufs_forecast(input_payload)` sends input payload to UFS endpoint.
  - Returns response JSON or raises HTTP/network error.

- `ufs_kafka_bridge.py`
  - Kafka consumer on input topic.
  - Kafka producer on output topic.
  - Builds SUCCESS/FAILED output payload.
  - Copies key headers (`job-id`, `node-ip`, `object-name`, `kpi-name`) if present.
  - Commits offset only after output publish.

- `README.md`
  - Setup + run commands for this branch.

- `docker-compose.yml`
  - Optional local broker for testing.

---

## 4) Message model in this branch (simple)

Input message assumptions (from Report Tool):

- One message = one node-port + one KPI
- Payload contains at least:
  - `job_id`
  - `node_ip`
  - `object_name`
  - `kpi_name`
  - time-series data fields used by UFS endpoint

Output message produced by UFS bridge:

- Always includes:
  - `job_id`
  - `node_ip`
  - `object_name`
  - `kpi_name`
  - `status` (`SUCCESS` or `FAILED`)
  - `processed_at`
  - `processing_ms`
- On success:
  - `ufs_response` = endpoint response body
- On failure:
  - `error.message`
  - `ufs_response = null`

---

## 5) Sequential processing behavior

This branch is intentionally simple:

- One consumer process
- `max_poll_records=1`
- Message processed in the order received per partition
- Offset commit after successful output publish

This makes debugging very easy and is good for understanding integration before parallel scaling.

---

## 6) Office-style execution plan (with intern assignment)

Use these tasks if you need to present this project as an office execution plan.

### Task 1 - Environment and configuration (Intern)
- Prepare `.env` values for Kafka/bootstrap/topics and UFS endpoint.
- Validate connectivity to Kafka brokers and endpoint.

### Task 2 - Build UFS endpoint contract adapter (You)
- Confirm exact request/response JSON contract for `xyz.something`.
- Update `ufs_client.py` mapping if payload format differs.

### Task 3 - Build and validate Kafka bridge loop (You)
- Run `ufs_kafka_bridge.py` with real input topic.
- Verify consume -> endpoint call -> output publish -> offset commit behavior.

### Task 4 - Add operational safeguards (Intern + You review)
- Add structured logging fields (`job_id`, `kpi_name`, `status`, `processing_ms`).
- Add simple retry/backoff policy for transient endpoint failures.

### Task 5 - Go-live checklist and handover (You)
- Document runbook (start/stop, env vars, common errors).
- Share deployment and rollback checklist with team.

---

## 7) Notes

- Report Tool owns topic lifecycle; this branch does not create topics.
- This branch keeps code minimal first; scaling (parallel consumers, retries, dead-letter topic, metrics) can be added after integration confidence is high.
