"""
Extract skills from job descriptions using keyword matching.
This is the v1 approach — fast and predictable.
Can be upgraded to spaCy NER or an LLM-based extractor later.
"""

import re

# Curated skill taxonomy — extend as needed
SKILL_TAXONOMY: dict[str, list[str]] = {
    "language": [
        "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust",
        "C++", "C#", "Ruby", "PHP", "Kotlin", "Swift", "Scala",
        "R", "SQL", "HTML", "CSS", "Bash", "Shell",
    ],
    "framework": [
        "React", "Next.js", "Angular", "Vue.js", "Svelte",
        "Django", "Flask", "FastAPI", "Spring Boot", "Express",
        "Node.js", "Rails", "ASP.NET", ".NET",
        "TailwindCSS", "Tailwind", "Bootstrap",
    ],
    "tool": [
        "Docker", "Kubernetes", "Terraform", "Ansible",
        "Git", "GitHub Actions", "Jenkins", "CircleCI",
        "Webpack", "Vite", "npm", "yarn",
        "Figma", "Storybook", "Playwright", "Cypress", "Jest",
        "Selenium", "Postman",
    ],
    "cloud": [
        "AWS", "Azure", "GCP", "Google Cloud",
        "S3", "Lambda", "EC2", "ECS", "EKS",
        "CloudFormation", "CDK",
        "Vercel", "Netlify", "Heroku", "Railway",
    ],
    "database": [
        "PostgreSQL", "Postgres", "MySQL", "MongoDB", "Redis",
        "Elasticsearch", "DynamoDB", "Cassandra", "SQLite",
        "Snowflake", "BigQuery", "Redshift",
    ],
    "data": [
        "Pandas", "NumPy", "Spark", "Airflow", "dbt",
        "Kafka", "RabbitMQ", "Celery",
        "Tableau", "Power BI", "Looker", "Grafana",
        "Jupyter", "Scikit-learn", "TensorFlow", "PyTorch",
    ],
    "practice": [
        "REST", "GraphQL", "gRPC", "Microservices",
        "CI/CD", "Agile", "Scrum", "TDD",
        "OAuth", "JWT", "SSO",
    ],
}

# Build a lookup: normalized_name -> (canonical_name, category)
_SKILL_LOOKUP: dict[str, tuple[str, str]] = {}
for category, skills in SKILL_TAXONOMY.items():
    for skill in skills:
        _SKILL_LOOKUP[skill.lower()] = (skill, category)


def extract_skills(text: str) -> list[dict]:
    """
    Extract skills from a job description.
    Returns list of {"name": str, "category": str, "confidence": float}.
    """
    if not text:
        return []

    found: dict[str, dict] = {}
    text_lower = text.lower()

    for normalized, (canonical, category) in _SKILL_LOOKUP.items():
        # Use word boundary matching to avoid false positives
        # e.g. "React" shouldn't match "reactive"
        pattern = r'\b' + re.escape(normalized) + r'\b'
        if re.search(pattern, text_lower):
            # Count occurrences for confidence weighting
            count = len(re.findall(pattern, text_lower))
            confidence = min(1.0, 0.5 + (count * 0.15))

            if canonical not in found:
                found[canonical] = {
                    "name": canonical,
                    "category": category,
                    "confidence": round(confidence, 2),
                }

    return list(found.values())


def detect_seniority(title: str) -> str | None:
    """Infer seniority level from job title."""
    title_lower = title.lower()
    if any(kw in title_lower for kw in ["staff", "principal", "distinguished"]):
        return "staff"
    if any(kw in title_lower for kw in ["senior", "sr.", "sr "]):
        return "senior"
    if any(kw in title_lower for kw in ["lead", "manager", "head of"]):
        return "lead"
    if any(kw in title_lower for kw in ["junior", "jr.", "jr ", "entry", "associate"]):
        return "junior"
    if any(kw in title_lower for kw in ["intern"]):
        return "intern"
    return "mid"


def detect_location_type(text: str) -> str | None:
    """Infer remote/hybrid/onsite from description or location string."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["fully remote", "100% remote", "remote only", "work from anywhere"]):
        return "remote"
    if any(kw in text_lower for kw in ["hybrid", "flexible", "partial remote"]):
        return "hybrid"
    if any(kw in text_lower for kw in ["on-site", "onsite", "in-office", "in office"]):
        return "onsite"
    if "remote" in text_lower:
        return "remote"
    return None
