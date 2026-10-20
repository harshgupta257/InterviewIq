"""Synthetic sample content. Fictional person and company; no real personal data."""

SAMPLE_RESUME = """Alex Rivera
Backend Software Engineer | alex.rivera@example.com

SUMMARY
Backend engineer with 4 years of experience building Python services and data pipelines.

EXPERIENCE
Software Engineer, Northwind Logistics (2022 - present)
- Built a FastAPI service for document processing that extracts fields from shipping invoices.
- Designed PostgreSQL schemas and added Redis caching for the shipment tracking API.
- Migrated nightly ETL jobs from cron scripts to Airflow with automated data-quality checks.
- Set up CI/CD with GitHub Actions and Docker for five internal services.

Junior Developer, Brightside Analytics (2020 - 2022)
- Developed REST endpoints in Django for a customer reporting dashboard.
- Used Databricks and PySpark for ETL on clickstream data.
- Wrote unit and integration tests with pytest.

PROJECTS
- Implemented a small RAG prototype that answers questions over internal runbooks.

SKILLS
Python, SQL, FastAPI, Django, PostgreSQL, Redis, Airflow, PySpark, Docker, AWS, Git
"""

SAMPLE_JD = """Backend Engineer - Platform Team (Contoso Freight)

About the role
We are looking for a backend engineer to design and operate reliable production APIs that
power our freight booking platform.

Responsibilities
- Design, build and operate reliable production APIs in Python.
- Build scalable data pipelines that feed pricing and analytics.
- Collaborate with product managers and data scientists on new features.
- Improve observability, testing and deployment practices.

Requirements
- 3+ years of backend development experience with Python.
- Strong SQL and PostgreSQL knowledge.
- Experience with Docker, CI/CD and AWS.
- Experience with Kafka or other event streaming systems is a plus.
- Clear written and verbal communication.
"""

# Two answer sets of different quality, used to seed demo history with a visible trend.
WEAK_ANSWERS = [
    "I like the role because it is backend and I enjoy Python a lot and it seems like a good team.",
    "I used FastAPI for the service. It worked well and handled the documents fine for the users.",
    "We validated inputs and had some tests. Postgres was used for storage of the data in the end.",
    "I built the document service. It was hard but we finished it and people used it afterwards.",
    "The Airflow migration was successful and the jobs ran better after we moved them over there.",
    "Once I disagreed with a teammate but we talked about it and agreed on a solution together.",
    "A deadline slipped once because a task was bigger than I thought, so I worked more hours.",
    "I would build an API with a database and a cache and make it scale with more servers.",
]

STRONG_ANSWERS = [
    "I'm interested because the role centres on reliable production APIs, which is exactly what I "
    "have been doing at Northwind with FastAPI and PostgreSQL. I want to go deeper on event streaming "
    "with Kafka, which your team uses, and I like that the platform team owns observability end to end.",
    "In the document-processing FastAPI service I used Pydantic models to validate every extracted field, "
    "returned 422 errors with field-level messages, and moved slow OCR work to a background queue. I "
    "considered synchronous processing but rejected it because large invoices exceeded the 30 second "
    "gateway timeout. I verified correctness with pytest fixtures built from 40 real invoice layouts, "
    "which reduced parsing errors reported by the operations team.",
    "For the shipment tracking API I designed the PostgreSQL schema around the main query pattern, added "
    "a composite index on shipment_id and updated_at, and introduced Redis caching with a 60 second TTL. "
    "The trade-off was slightly stale data, which product accepted. As a result p95 latency dropped from "
    "about 800 ms to 120 ms in our dashboards.",
    "My ownership on the document service was the API design and the retry strategy. The hardest decision "
    "was idempotency: clients retried uploads, so I added an idempotency key stored in PostgreSQL. Today I "
    "would add structured tracing earlier, because debugging the queue without it cost us time.",
    "I measured the Airflow migration by job success rate and data freshness. Before the migration about "
    "one nightly job per week failed silently; afterwards data-quality checks caught issues and alerted us, "
    "and silent failures dropped to zero over the next two months. The lesson was that monitoring mattered "
    "more than the scheduler itself.",
    "Situation: a teammate wanted to cache whole API responses. Task: I owned the tracking API's latency "
    "goal. Action: I wrote a short comparison showing response caching would serve stale shipment states, "
    "proposed caching only the expensive lookup, and we load tested both. Result: we shipped my approach, "
    "met the latency goal and avoided stale data incidents.",
    "Situation: I estimated the ETL migration at two weeks but discovered undocumented dependencies. Task: "
    "deliver before quarter close. Action: I told my manager on day three, proposed migrating the critical "
    "jobs first, and documented the rest. Result: critical jobs moved on time and I now add a discovery "
    "spike before estimating migrations.",
    "I would design the booking API as a stateless FastAPI service behind a load balancer, with PostgreSQL "
    "as the source of truth and an outbox table publishing events to Kafka. Writes use idempotency keys, "
    "reads use Redis for hot quotes. I'd validate it with load tests, track p95 latency and error budgets, "
    "and accept eventual consistency for analytics consumers as the main trade-off.",
]
