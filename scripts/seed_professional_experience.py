"""Seed `professional_experience` entries in the knowledge_base table.

Each role from Andrés's career becomes one KB entry that the agent retrieves
via `search_knowledge_base(category="professional_experience", ...)`.

Idempotent: entries with the same (type, title) are skipped by default.
Pass --force to overwrite content and recompute embeddings for existing rows
(the row id and created_at are preserved).

Local:
    docker compose run --rm backend uv run python -m scripts.seed_professional_experience
    docker compose run --rm backend uv run python -m scripts.seed_professional_experience --force

Production:
    docker compose -f docker-compose.prod.yml run --rm backend \\
        uv run python -m scripts.seed_professional_experience
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select

from modules.knowledge_base.models import KnowledgeBase, KnowledgeBaseTypeEnum
from modules.utils.database import async_session
from modules.utils.embeddings import embed_document


CATEGORY = KnowledgeBaseTypeEnum.professional_experience


ENTRIES: list[dict[str, str]] = [
    {
        "title": "Thoughtful AI - Forward Deployed Engineer (Sep 2025 - Present)",
        "content": (
            "**Role**: Forward Deployed Engineer\n"
            "**Company**: Thoughtful AI\n"
            "**Dates**: September 2025 - Present\n"
            "**Domain**: AI-powered automation for healthcare workflows\n\n"
            "**What I do**:\n"
            "- Partner directly with clients to understand their workflows and deliver tailored AI automation solutions.\n"
            "- Design, implement, and deploy scalable Python-based software that brings Thoughtful's AI platform into production environments.\n"
            "- Build integrations, optimize performance, and ensure reliable, secure deployments.\n"
            "- Collaborate with product and customer success teams to translate real-world requirements into technical solutions.\n\n"
            "**Technologies**: Python, AI platform integration, automation systems.\n\n"
            "**Impact**: Deliver measurable business impact through high-value automation that improves efficiency and outcomes across healthcare operations."
        ),
    },
    {
        "title": "Buildertrend - Senior Software Engineer (Jul 2022 - Aug 2025)",
        "content": (
            "**Role**: Senior Software Engineer\n"
            "**Company**: Buildertrend\n"
            "**Dates**: July 2022 - August 2025\n"
            "**Domain**: Banking as a Service innovation in fintech\n\n"
            "**What I did**:\n"
            "- Led development of high-performance, scalable financial applications.\n"
            "- Designed and maintained critical banking systems built on a microservices architecture.\n"
            "- Implemented event-driven systems and cloud-native solutions.\n"
            "- Ensured reliability at scale with extensive unit and integration testing.\n\n"
            "**Technologies**: Python, FastAPI, JavaScript, TypeScript, React.js, MongoDB, Docker, Kubernetes, GCP."
        ),
    },
    {
        "title": "JetBridge - Senior Software Engineer (Aug 2021 - Aug 2022)",
        "content": (
            "**Role**: Senior Software Engineer\n"
            "**Company**: JetBridge\n"
            "**Dates**: August 2021 - August 2022\n"
            "**Domain**: Elite consulting team building products with $3+ billion in collective equity value\n\n"
            "**What I did**:\n"
            "- Contributed to products worth over $3 billion in equity value.\n"
            "- Built microservices for high-scale applications.\n\n"
            "**Technologies**: Python, Django, NestJS, React.js, Docker, Kubernetes, Elasticsearch, Kafka.\n\n"
            "**Notable**: The team included founders of Five9 (NASDAQ: FIVN) and consultants to IPOs like UpWork and RingCentral."
        ),
    },
    {
        "title": "Playvox - Software Engineer (Aug 2020 - Aug 2021)",
        "content": (
            "**Role**: Software Engineer\n"
            "**Company**: Playvox\n"
            "**Dates**: August 2020 - August 2021\n"
            "**Domain**: Enterprise solutions for tech giants\n\n"
            "**What I did**:\n"
            "- Developed features used by major customers including Facebook, Google, Glovo, Sutherland, and Rappi.\n"
            "- Specialized in async Python with the Tornado framework.\n"
            "- Focused on performance optimization, scalability, and test-driven development.\n\n"
            "**Technologies**: Python, Tornado, MongoDB, microservices, serverless."
        ),
    },
    {
        "title": "Anomali - Software Engineer (Dec 2018 - Jun 2020)",
        "content": (
            "**Role**: Software Engineer\n"
            "**Company**: Anomali\n"
            "**Dates**: December 2018 - June 2020\n"
            "**Domain**: Cybersecurity - threat intelligence platform\n\n"
            "**What I did**:\n"
            "- Backend development for the threat intelligence platform.\n"
            "- Implemented secure coding practices and vulnerability prevention.\n"
            "- Focused on security compliance and data protection.\n\n"
            "**Technologies**: Python, Django, Celery, REST APIs, AWS, Elasticsearch, Docker."
        ),
    },
    {
        "title": "Brizant - Software Engineer (Jul 2018 - Dec 2018)",
        "content": (
            "**Role**: Software Engineer\n"
            "**Company**: Brizant\n"
            "**Dates**: July 2018 - December 2018\n"
            "**Domain**: Advanced data systems with real-time processing and AI integration\n\n"
            "**What I did**:\n"
            "- Implemented Saga patterns and event-sourcing architectures.\n"
            "- Built face-recognition systems with Amazon Rekognition.\n"
            "- Worked on real-time data processing pipelines.\n\n"
            "**Technologies**: Python, Django, DRF, React.js, Redux, Kafka, RabbitMQ."
        ),
    },
    {
        "title": "Datagran - Software Engineer (Jan 2018 - Jul 2018)",
        "content": (
            "**Role**: Software Engineer\n"
            "**Company**: Datagran\n"
            "**Dates**: January 2018 - July 2018\n"
            "**Domain**: Data platform development\n\n"
            "**What I did**:\n"
            "- Built Google Ads platform integrations.\n"
            "- Applied machine learning for business automation.\n"
            "- Designed ETL pipelines and event-driven architectures.\n\n"
            "**Technologies**: Python (Flask), MongoDB, Luigi, Kafka, GCP."
        ),
    },
    {
        "title": "LendingFront - Software Engineer (May 2016 - Sep 2017)",
        "content": (
            "**Role**: Software Engineer\n"
            "**Company**: LendingFront\n"
            "**Dates**: May 2016 - September 2017\n"
            "**Domain**: Fintech solutions\n\n"
            "**What I did**:\n"
            "- Full-stack development on a microservices architecture.\n"
            "- PostgreSQL optimization including Foreign Data Wrappers (FDW).\n"
            "- Followed clean architecture, test-driven development, and rigorous database design.\n\n"
            "**Technologies**: Python (Flask), PostgreSQL, SQLAlchemy, AWS."
        ),
    },
    {
        "title": "Metis Consultores SAS - Software Engineer (Jul 2015 - Apr 2016)",
        "content": (
            "**Role**: Software Engineer\n"
            "**Company**: Metis Consultores SAS\n"
            "**Dates**: July 2015 - April 2016\n"
            "**Domain**: Full-stack foundation\n\n"
            "**What I did**:\n"
            "- End-to-end application development on AWS.\n"
            "- Server administration and deployment.\n"
            "- Managed infrastructure with Nginx, Gunicorn, Supervisor on Linux.\n\n"
            "**Technologies**: Python, Django, PostgreSQL, HTML5, CSS3, JavaScript."
        ),
    },
]


def _build_embedding_text(title: str, content: str) -> str:
    """Mirror the format used by the admin save path so query- and index-time
    text encodings stay aligned."""
    return f"type: {CATEGORY.value}\ntitle: {title}\ncontent: {content}"


async def _upsert(session, title: str, content: str, force: bool) -> str:
    existing = (
        await session.exec(
            select(KnowledgeBase)
            .where(KnowledgeBase.type == CATEGORY)
            .where(KnowledgeBase.title == title)
        )
    ).first()

    if existing and not force:
        return "skipped"

    embedding = await embed_document(_build_embedding_text(title, content))

    if existing:
        existing.content = content
        existing.embedding = embedding
        session.add(existing)
        await session.commit()
        return "updated"

    session.add(
        KnowledgeBase(
            type=CATEGORY,
            title=title,
            content=content,
            embedding=embedding,
        )
    )
    await session.commit()
    return "created"


async def main(force: bool) -> None:
    print(f"Seeding {len(ENTRIES)} '{CATEGORY.value}' KB entries (force={force})")
    print(f"Started: {datetime.now().isoformat(timespec='seconds')}\n")

    counts = {"created": 0, "updated": 0, "skipped": 0}
    async with async_session() as session:
        for i, entry in enumerate(ENTRIES, 1):
            title = entry["title"]
            print(f"  [{i}/{len(ENTRIES)}] {title}")
            action = await _upsert(session, title, entry["content"], force)
            counts[action] += 1
            print(f"      -> {action}")

    print("\n--- Summary ---")
    for k in ("created", "updated", "skipped"):
        print(f"  {k}: {counts[k]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed professional_experience entries in the knowledge_base table.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite content and re-embed existing entries (matched by title).",
    )
    args = parser.parse_args()
    asyncio.run(main(force=args.force))
