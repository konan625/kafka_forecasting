# UFS Kafka prototype — end-to-end flow and concepts

This document captures the walkthrough of the local UFS Kafka prototype: **end-to-end flow**, **why each piece exists** (including Docker), and **how Kafka fits together** (ZooKeeper, topics, partitions, “batches,” keys).

---

## 1. Start-to-end flow (who does what)

1. **You start Kafka** (broker + ZooKeeper) so messages have somewhere to live.
2. **You create topics** (`create_topics.py`) so names and partition counts are explicit (we disabled auto-create in Docker).
3. **`report_tool_producer.py`** plays **Report Tool**: it estimates “rows,” applies the **light vs heavy** gate, then on the heavy path **publishes many messages** to **`ufs.bulk.input`** — one message per **node–port–KPI** “batch” in your design doc.
4. **`ufs_worker.py`** plays **UFS**: it **consumes** from `ufs.bulk.input`, runs a tiny fake forecast, **publishes one result** per input to **`ufs.bulk.output`**, then **commits** the input offset (only after publishing — your reliability pattern).
5. **`report_tool_consumer.py`** plays **Report Tool on the way back**: it **consumes** `ufs.bulk.output`, counts which `batch_seq` values arrived, and prints **JOB COMPLETE** when all batches for a `job_id` are seen.

So the loop is: **RT → Topic A → UFS → Topic B → RT**, matching your TDD mentally, just without HTTP and real DB.

---

## 2. Why Docker (and what it is doing here)

**Docker Compose** runs two containers from known images:

- **ZooKeeper** — coordination service the broker uses in this **classic** Kafka setup (see §4).
- **Kafka broker** — the actual message server listening on **localhost:9092**.

### Why Docker here

- **Same Kafka everywhere**: your laptop matches “Linux + broker on port 9092” without installing Java/Kafka by hand.
- **One command** (`docker compose up`) brings up a working cluster-shaped stack.
- **Isolation**: when you’re done, you remove containers; your OS stays clean.

### Why not “Kafka only” without ZooKeeper?

Newer Kafka can run in **KRaft** mode (no ZooKeeper). This project uses **Confluent images wired to ZooKeeper** because it is a very common teaching and dev setup; production often moves to KRaft or managed Kafka (MSK, Confluent Cloud, etc.).

Relevant bits from `docker-compose.yml`:

```yaml
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.3
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:7.5.3
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
```

- **`depends_on: zookeeper`**: broker starts after the ZK container exists.
- **`KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092`**: clients on the host use `localhost:9092` (matches `config.py`).
- **`KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"`**: topics must be created explicitly — that is why **`create_topics.py`** exists (closer to production discipline).

---

## 3. Shared configuration — `config.py`

```python
KAFKA_BOOTSTRAP = "localhost:9092"

TOPIC_INPUT = "ufs.bulk.input"
TOPIC_OUTPUT = "ufs.bulk.output"

INPUT_PARTITIONS = 6
OUTPUT_PARTITIONS = 6

ROW_COUNT_THRESHOLD = 50000

CONSUMER_GROUP_UFS = "ufs-bulk-forecast-workers"
CONSUMER_GROUP_RT = "report-tool-consumer"
```

- **`KAFKA_BOOTSTRAP`**: first contact address(es) for the cluster; single broker here.
- **Topic names**: match your design (`ufs.bulk.input` / `ufs.bulk.output`).
- **Partitions**: how many parallel “pipes” each topic has (see §4).
- **`ROW_COUNT_THRESHOLD`**: same idea as the doc’s 50k row gate (demo uses `force_heavy_demo` to still take the Kafka path with tiny data).
- **Consumer groups**: separate logical apps — UFS workers vs Report Tool consumer — so each tracks its **own offsets**.

---

## 4. Kafka concepts (ZooKeeper, topics, partitions, keys, “batches”)

### What is Kafka?

A **distributed commit log**: producers **append** records; consumers **read** with **offsets** (positions in the log). It decouples **who sends** from **who processes** and allows **replay** and **scale-out**.

### What is ZooKeeper?

In this architecture, **Kafka brokers** use **Apache ZooKeeper** for things like **controller election**, **cluster metadata**, and (in older setups) topic/config state. You don’t talk to ZooKeeper from your Python apps — only the broker does. Your apps only talk to **Kafka on 9092**.

*(Long term, many deployments migrate to **KRaft** so Kafka manages metadata without ZooKeeper.)*

### What is a **topic**?

A **named stream** of messages, like a channel name: here `ufs.bulk.input` and `ufs.bulk.output`. Producers write **to** a topic; consumers **subscribe** to a topic.

### What is a **partition**?

Each topic is split into **partitions** (numbered 0..N-1). Each partition is an **ordered log**. **Order is guaranteed only inside one partition**, not across the whole topic.

- **Why partitions matter**: more partitions → more **parallel consumers** in the same group (up to one consumer per partition per topic, roughly).

This project creates 6 partitions per topic in `create_topics.py`.

### How does a message get to a partition?

When you **send with a key**, Kafka hashes the key and picks a partition **deterministically** for that key (default partitioner). Same key → same partition → **related messages stay ordered together**.

- **Input topic**: key = `node_ip:object_name` → all KPIs for that node/port land on the **same partition** (matches your design intent).
- **Output topic**: key = `job_id` → all result messages for a job go to the **same partition** (ordering per job is easier to reason about).

### What are “batches” in Kafka?

There are **two different “batch” ideas**:

1. **Your business “batch”**  
   In the TDD, each **Kafka message** is one **node–port–KPI** unit, with `batch_seq` / `total_batches`. That is **not** a Kafka batch — it is **your job’s sequence numbering**.

2. **Kafka producer batching (network efficiency)**  
   The client can **buffer** many records and send them in **fewer TCP requests** (`linger.ms`, `batch.size`, etc.). Our code calls `producer.flush()` to force send before exit; internally the library may still group bytes.

So: **your design batches = many messages**; **Kafka batches = optional packing of many records into one produce request**.

### Consumer groups and offsets

- **Consumer group** (`group_id`): a set of consumer instances that **share** work. Kafka stores **committed offsets per group + partition** — “how far have we read?”
- **Manual commit** (`enable_auto_commit=False` + `consumer.commit()`): you only advance the offset when **you** say the message is done — here, **after** publishing to the output topic.

---

## 5. `create_topics.py` — purpose

- **`KafkaAdminClient`**: admin API to create topics (not produce/consume).
- **`NewTopic(..., replication_factor=1)`**: single-broker dev cluster — replication 1 is enough; production would be 3+.
- **`TopicAlreadyExistsError`**: safe re-run without crashing.

---

## 6. `report_tool_producer.py` — flow and why each part exists

**Imports** — JSON, random data, timestamps, `KafkaProducer`, and config.

**`utc_now` / `fake_token`** — ISO timestamps for `published_at`; placeholder Bearer header like your TDD.

**`make_series`** — builds fake `{ds, y}` points; every 97th point is `null` to mimic missing data.

**`build_batch`** — builds **one message**:

- Payload fields mirror your schema: `job_id`, `batch_seq`, `total_batches`, identity, `forecast_params`, `data`, `data_quality`.
- **`partition_key = f"{node_ip}:{object_name}"`** — used as the **Kafka message key** so routing matches the doc.
- **Headers** duplicate key metadata for observability and to mirror “Kafka headers” in the TDD (filters, tracing, auth passthrough in real life).

**`route_and_publish`**:

- Builds **3 node–ports × 4 KPIs = 12 combos**.
- **`estimated_rows = len(combos) * rows_per_combo`** — simulates `COUNT(*)`-style estimate.
- **Gate**: if under threshold **and** not `force_heavy_demo`, it would take the “sync REST” path and **not** publish to Kafka.
- **`force_heavy_demo = True`** — forces the Kafka path for learning even when row count is small.
- **`job_id`**, **`total_batches`** — same as HTTP 202 body in your doc.
- **`KafkaProducer`**: `acks="all"` waits for leader + replicas (here replication 1, but keeps the **habit**); `retries=3` for transient errors.
- **Loop**: `producer.send(topic, key=..., value=..., headers=...)` once per combo — **12 separate Kafka messages** (your “one message per node-port-KPI”).
- **`flush()`** then **`close()`** — ensure records leave the client before the process exits.

---

## 7. `ufs_worker.py` — flow and why each part exists

**`to_header_map`** — kafka-python gives headers as list of pairs; this turns them into a dict if you need them (logged or validated later).

**`three_pass_forecast`** — **not** real ML; it checks length, slices “context” windows, builds four segments into one flat `output` list to mirror the **shape** of your SUCCESS payload.

**Consumer setup**:

- **`enable_auto_commit=False`** — you commit only when safe.
- **`max_poll_records=1`** — one in-flight message per poll (like heavy forecast work).
- **`auto_offset_reset="earliest"`** — if no committed offset yet, start from the beginning of retained log (good for dev).

**Main loop**:

- **`idem = job_id:batch_seq:node_ip:object_name:kpi_name`** — matches your idempotency key idea; **`seen` set** is in-memory only (production would use Redis TTL).
- On duplicate: **commit** anyway so offset moves (at-least-once handling).
- **Try**: build SUCCESS result + headers.
- **Except**: build FAILED with `INSUFFICIENT_DATA`-style error.
- **`producer.send(TOPIC_OUTPUT, key=job_id, ...)`** — partition by **job**.
- **`producer.flush()`** — result is on the broker before you commit input.
- **`seen.add(idem)`** then **`consumer.commit()`** — **process → publish → commit** ordering.

---

## 8. `report_tool_consumer.py` — flow

- Subscribes to **`ufs.bulk.output`** with its **own** `group_id` (independent progress from UFS).
- **`completion[job_id]`** stores which `batch_seq` values arrived; **`totals[job_id]`** stores expected `total_batches`.
- When `len(completion[job_id]) == totals[job_id]` → **job complete** (same idea as your step 12).

---

## 9. `requirements.txt`

```
kafka-python==2.0.2
```

Pure Python Kafka client — no JVM needed in your app process; the **broker** still runs in Docker (JVM inside the container).

---

## 10. Short mental picture

| Piece | Role |
|--------|------|
| **ZooKeeper** | Helps the Kafka broker cluster coordinate (classic mode); apps don’t connect to it. |
| **Broker (Kafka)** | Stores topics; serves produce/consume. |
| **Topic** | Named log (`ufs.bulk.input` / `ufs.bulk.output`). |
| **Partition** | Sharded ordered log; parallel consumers; key picks partition. |
| **Producer** | Appends records (key, value, headers). |
| **Consumer group** | Load-sharing + offset tracking per group. |
| **Offset** | Cursor per partition; commit = “processed up to here.” |
| **Your `batch_seq`** | Business sequencing for one **job**, not Kafka’s internal batching. |

---

## Follow-ups (office-grade Kafka topics)

Natural next topics: **exactly-once vs at-least-once**, **idempotent producer** settings, **consumer rebalance**, and **dead-letter topics** — all map cleanly onto the UFS design.
