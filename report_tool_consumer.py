import json
from collections import defaultdict

from kafka import KafkaConsumer

from config import CONSUMER_GROUP_RT, KAFKA_BOOTSTRAP, TOPIC_OUTPUT


def main() -> None:
    consumer = KafkaConsumer(
        TOPIC_OUTPUT,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=CONSUMER_GROUP_RT,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        value_deserializer=lambda b: json.loads(b.decode()),
    )
    completion = defaultdict(set)
    totals = {}

    print(f"[RT-CONSUMER] Listening on {TOPIC_OUTPUT} ...")
    for msg in consumer:
        body = msg.value
        job_id = body["job_id"]
        batch_seq = int(body["batch_seq"])
        total = int(body["total_batches"])
        status = body["status"]

        totals[job_id] = total
        completion[job_id].add(batch_seq)

        # In real office flow this writes each row from output.output[] into DB.
        output_rows = 0
        if body.get("output") and body["output"].get("output"):
            output_rows = len(body["output"]["output"])

        print(
            f"[RT-CONSUMER] job={job_id} batch={batch_seq}/{total} "
            f"status={status} output_rows={output_rows}"
        )

        if len(completion[job_id]) == totals[job_id]:
            print(f"[RT-CONSUMER] JOB COMPLETE: {job_id} ({totals[job_id]} batches)")


if __name__ == "__main__":
    main()
