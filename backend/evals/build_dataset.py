"""Regenerate evals/dataset.jsonl from the synthetic items below.

All content is synthetic (fictional candidate, fictional companies). `human_scores` are
intentionally left null: they must be filled in by a human rater, never generated.
`author_intended_quality` records what the item author aimed for; it is NOT a label.

Usage (from backend/): python -m evals.build_dataset
Re-running overwrites dataset.jsonl, including any labels, so only run it before labelling.
"""

import json
from pathlib import Path

ITEMS: list[tuple[str, str, list[str], list[str]]] = [
    (
        "technical",
        "Your resume mentions a FastAPI document-processing service. How did you handle validation, failures and reliability?",
        ["Input validation", "Failure handling", "Reliability"],
        [
            "I used FastAPI and it was reliable. We tested it and it worked.",
            "I validated requests with Pydantic models and returned 422 errors. For failures I wrapped the OCR call in try/except and logged errors. We had some unit tests.",
            "Every upload was validated with Pydantic, including file type and size limits, and field-level 422 errors went back to clients. OCR ran in a background worker with three retries and exponential backoff, and permanently failing documents moved to a dead-letter table we reviewed weekly. I added idempotency keys because clients retried uploads. Error rate fell from roughly 4% to under 1% over the following month, measured from our logs.",
        ],
    ),
    (
        "technical",
        "Describe a PySpark transformation you implemented, why you chose that approach, and how you validated its correctness and performance.",
        ["Spark internals", "Validation", "Performance reasoning"],
        [
            "I wrote PySpark code to transform data. It was fast enough.",
            "I deduplicated clickstream events with a window function over user_id ordered by timestamp. I checked the row counts before and after.",
            "I deduplicated clickstream events using a window partitioned by session_id and ordered by event_time, keeping row_number = 1. I chose this over dropDuplicates because we needed the latest event, not an arbitrary one. For correctness I compared counts and spot-checked 200 sessions against the raw source; for performance I repartitioned on session_id to avoid a skewed shuffle, which cut the job from about 40 to 15 minutes in the Spark UI.",
        ],
    ),
    (
        "project_deepdive",
        "Walk me through the Airflow migration on your resume. What was your ownership and what would you change?",
        ["Ownership", "Decision making", "Reflection"],
        [
            "We moved to Airflow. It was a team effort and went fine.",
            "I migrated about twenty cron jobs to Airflow DAGs and added retries. Next time I would plan better.",
            "I owned the migration of 22 nightly cron jobs into Airflow. I grouped them into four DAGs by data domain, added sensors for upstream files and data-quality checks with row-count thresholds. The hardest decision was whether to backfill history; I chose not to, to keep the cutover small. Today I would add alert routing per owner from day one, because early alerts all went to me.",
        ],
    ),
    (
        "project_deepdive",
        "How did you measure whether the Redis caching you added to the tracking API succeeded?",
        ["Outcome measurement", "Impact", "Honesty about limitations"],
        [
            "The caching made things faster for users.",
            "We looked at latency dashboards after the release and they were lower. Users were happier.",
            "Before release I recorded p50 and p95 latency for the tracking endpoint from our APM: about 180 ms and 800 ms. After adding Redis with a 60-second TTL, p95 dropped to around 120 ms. I also tracked cache hit rate, which settled near 85%, and checked that stale-data complaints did not increase. One limitation is that we never ran a controlled experiment, so traffic changes may explain part of the gain.",
        ],
    ),
    (
        "behavioral",
        "Tell me about a time you disagreed with a teammate about a technical approach.",
        ["Collaboration", "Influence", "Outcome"],
        [
            "I do not really have disagreements, I get along with everyone.",
            "A teammate wanted to use MongoDB but I preferred PostgreSQL. We discussed it and used PostgreSQL in the end.",
            "Situation: a teammate proposed caching full API responses to meet a latency target. Task: I owned that endpoint's correctness. Action: I wrote a one-page comparison showing full-response caching would return stale shipment states, proposed caching only the expensive lookup, and suggested we load test both. Result: the targeted cache met the goal without stale data, and we agreed to use short design notes for future disagreements.",
        ],
    ),
    (
        "behavioral",
        "Describe a time a deadline was at risk because of something you underestimated.",
        ["Ownership", "Communication", "Learning"],
        [
            "I worked late and it was fine.",
            "I underestimated a migration. I told my manager and we moved the date by a week.",
            "Situation: I estimated an ETL migration at two weeks, then found undocumented downstream consumers. Task: deliver before quarter close. Action: on day three I told my manager, proposed migrating the critical jobs first and documented the rest as follow-ups. Result: critical jobs moved on time, the remainder finished two weeks later, and I now run a short discovery spike before estimating migrations.",
        ],
    ),
    (
        "system_design",
        "Design an API for booking freight shipments. Cover the data model, failure handling and scaling.",
        ["Architecture", "Trade-offs", "Reliability"],
        [
            "I would use microservices and Kubernetes so it scales.",
            "A REST API with a Postgres database for bookings and a cache. Put it behind a load balancer and add more servers when needed.",
            "A stateless FastAPI service behind a load balancer, with PostgreSQL as the source of truth: bookings, shipments and quotes tables keyed by UUID. Booking writes require an idempotency key so client retries are safe. An outbox table publishes booking events to Kafka for pricing and analytics consumers, accepting eventual consistency there. Hot quote reads go through Redis with short TTLs. I would validate with load tests against a p95 target, add per-endpoint SLO alerts, and scale reads with replicas before considering sharding.",
        ],
    ),
    (
        "case_study",
        "Weekly active shippers dropped 15% week over week. How would you investigate?",
        ["Structured problem solving", "Hypotheses", "Communication"],
        [
            "I would look at the data and find the problem.",
            "First I would check if the data pipeline broke. Then I would look at different segments to see where the drop is.",
            "First rule out measurement issues: check pipeline freshness, tracking changes and the metric definition. Then segment the drop by region, customer size, acquisition channel and platform to localise it. In parallel list hypotheses such as a release, pricing change, seasonality or an outage, and check each against the timeline. I would report a short summary with the size of the drop, the segments driving it, confidence level and next steps, rather than waiting for a perfect answer.",
        ],
    ),
    (
        "motivation",
        "Why are you interested in this backend role at Contoso Freight?",
        ["Role fit", "Specific motivation", "Self-awareness"],
        [
            "I need a job and this one pays well.",
            "I like backend work and logistics seems interesting. The company has a good reputation.",
            "The role centres on reliable production APIs, which is what I have been doing with FastAPI and PostgreSQL, so I can contribute quickly. It also uses Kafka, which I have not used in production and want to learn properly. Logistics appeals to me because reliability problems have direct real-world consequences, and I want my next role to grow my ownership of observability and on-call practices.",
        ],
    ),
    (
        "technical",
        "The role lists Kafka, which your resume does not mention. How would you approach learning and using it here?",
        ["Learning strategy", "Honesty about gaps", "Practical reasoning"],
        [
            "I already know Kafka well.",
            "I would read the documentation and do a tutorial, then ask teammates for help.",
            "I have not used Kafka, so I would start with the concepts most likely to cause production issues here: partitioning and ordering, consumer groups and offsets, and delivery semantics. I would build a small producer and consumer that mirrors one of your event flows, then read the team's existing consumers and runbooks. My background with idempotent APIs and retries transfers well to designing idempotent consumers, which is where I would focus first.",
        ],
    ),
]


def build() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for category, question, focus, answers in ITEMS:
        for quality, answer in zip(("weak", "medium", "strong"), answers, strict=True):
            out.append(
                {
                    "id": f"item-{len(out) + 1:03d}",
                    "category": category,
                    "question": question,
                    "evaluation_focus": focus,
                    "job_title": "Backend Engineer",
                    "role_type": "software_engineering",
                    "seniority": "mid",
                    "answer": answer,
                    "author_intended_quality": quality,
                    "expected_characteristics": "A strong answer covers the evaluation_focus with specific, "
                    "structured detail and states outcomes or reasoning appropriate to the question type.",
                    "human_scores": {
                        "clarity": None,
                        "specificity": None,
                        "result_orientation": None,
                        "relevance": None,
                    },
                    "evaluator_notes": "",
                }
            )
    return out


if __name__ == "__main__":
    items = build()
    path = Path(__file__).parent / "dataset.jsonl"
    path.write_text("".join(json.dumps(i) + "\n" for i in items), encoding="utf-8")
    print(f"Wrote {len(items)} items to {path}")
