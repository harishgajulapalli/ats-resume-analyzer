"""Skill dictionary: canonical skill name -> aliases that mean the same thing.

An alias starting with "!" is matched case-sensitively (e.g. "Go", "REST"),
for skills whose names are also common English words.
"""

import re
from functools import lru_cache

SKILLS: dict[str, dict[str, list[str]]] = {
    "Programming Languages": {
        "Python": ["python"],
        "Java": ["java"],
        "JavaScript": ["javascript", "js", "ecmascript", "es6"],
        "TypeScript": ["typescript", "ts"],
        "C++": ["c++", "cpp"],
        "C#": ["c#", "csharp"],
        "Go": ["golang", "!Go"],
        "Rust": ["!Rust"],
        "Ruby": ["ruby"],
        "PHP": ["php"],
        "Kotlin": ["kotlin"],
        "Swift": ["!Swift"],
        "Scala": ["scala"],
        "SQL": ["sql"],
        "Bash": ["bash", "shell scripting", "shell script"],
        "PowerShell": ["powershell"],
        "HTML": ["html", "html5"],
        "CSS": ["css", "css3"],
        "MATLAB": ["matlab"],
    },
    "Frameworks & Libraries": {
        "Django": ["django"],
        "Flask": ["flask"],
        "FastAPI": ["fastapi"],
        "Spring Boot": ["spring boot", "springboot", "spring framework"],
        "React": ["react", "react.js", "reactjs"],
        "Angular": ["angular", "angularjs"],
        "Vue.js": ["vue", "vue.js", "vuejs"],
        "Next.js": ["next.js", "nextjs"],
        "Node.js": ["node.js", "nodejs", "node"],
        "Express.js": ["express.js", "expressjs"],
        ".NET": [".net", "dotnet", ".net core", "asp.net"],
        "Ruby on Rails": ["ruby on rails", "rails"],
        "Pandas": ["pandas"],
        "NumPy": ["numpy"],
        "scikit-learn": ["scikit-learn", "sklearn"],
        "TensorFlow": ["tensorflow"],
        "PyTorch": ["pytorch"],
        "Spark": ["spark", "pyspark", "apache spark"],
        "Hadoop": ["hadoop"],
        "Selenium": ["selenium"],
        "pytest": ["pytest"],
        "JUnit": ["junit"],
        "Jest": ["jest"],
        "GraphQL": ["graphql"],
        "Tailwind CSS": ["tailwind", "tailwindcss"],
        "Bootstrap": ["bootstrap"],
        "Redux": ["redux"],
        "LangChain": ["langchain"],
    },
    "Databases": {
        "PostgreSQL": ["postgresql", "postgres"],
        "MySQL": ["mysql"],
        "SQL Server": ["sql server", "mssql", "t-sql"],
        "Oracle": ["oracle", "pl/sql"],
        "SQLite": ["sqlite"],
        "MongoDB": ["mongodb", "mongo"],
        "Redis": ["redis"],
        "Cassandra": ["cassandra"],
        "DynamoDB": ["dynamodb"],
        "Elasticsearch": ["elasticsearch", "elastic search", "opensearch"],
        "Snowflake": ["snowflake"],
        "BigQuery": ["bigquery"],
    },
    "Cloud & DevOps": {
        "AWS": ["aws", "amazon web services"],
        "Azure": ["azure", "microsoft azure"],
        "GCP": ["gcp", "google cloud", "google cloud platform"],
        "Docker": ["docker", "containers", "containerization"],
        "Kubernetes": ["kubernetes", "k8s", "eks", "aks", "gke"],
        "Terraform": ["terraform"],
        "Ansible": ["ansible"],
        "Jenkins": ["jenkins"],
        "GitHub Actions": ["github actions"],
        "GitLab CI": ["gitlab ci", "gitlab-ci"],
        "CI/CD": ["ci/cd", "cicd", "continuous integration", "continuous delivery", "continuous deployment"],
        "Linux": ["linux", "unix", "ubuntu"],
        "Microservices": ["microservices", "microservice"],
        "Serverless": ["serverless", "lambda", "aws lambda", "azure functions"],
        "Kafka": ["kafka", "apache kafka"],
        "RabbitMQ": ["rabbitmq"],
        "Nginx": ["nginx"],
        "Prometheus": ["prometheus"],
        "Grafana": ["grafana"],
        "Airflow": ["airflow", "apache airflow"],
    },
    "Data & AI": {
        "Machine Learning": ["machine learning", "ml"],
        "Deep Learning": ["deep learning"],
        "NLP": ["nlp", "natural language processing"],
        "Computer Vision": ["computer vision"],
        "Generative AI": ["generative ai", "genai", "llm", "llms", "large language models"],
        "Data Analysis": ["data analysis", "data analytics"],
        "Data Engineering": ["data engineering", "etl", "elt", "data pipelines"],
        "Data Visualization": ["data visualization", "data visualisation"],
        "Statistics": ["statistics", "statistical analysis"],
        "Power BI": ["power bi", "powerbi"],
        "Tableau": ["tableau"],
        "Excel": ["excel", "ms excel", "microsoft excel"],
    },
    "Tools & Practices": {
        "Git": ["git", "github", "gitlab", "bitbucket"],
        "Jira": ["jira"],
        "REST APIs": ["rest api", "rest apis", "restful", "!REST"],
        "Unit Testing": ["unit testing", "unit tests", "tdd", "test-driven development"],
        "Automation Testing": ["automation testing", "test automation"],
        "Agile": ["agile"],
        "Scrum": ["scrum"],
        "System Design": ["system design", "distributed systems"],
        "OOP": ["oop", "object-oriented", "object oriented"],
        "Data Structures & Algorithms": ["data structures", "algorithms"],
        "Code Review": ["code review", "code reviews"],
        "Security": ["application security", "oauth", "jwt", "owasp"],
        "Figma": ["figma"],
        "SEO": ["seo"],
        "Salesforce": ["salesforce"],
        "SAP": ["!SAP"],
    },
    "Soft Skills": {
        "Communication": ["communication", "communication skills"],
        "Leadership": ["leadership", "team lead", "mentoring", "mentor"],
        "Teamwork": ["teamwork", "collaboration", "collaborative", "cross-functional"],
        "Problem Solving": ["problem solving", "problem-solving", "analytical skills"],
        "Project Management": ["project management", "stakeholder management"],
        "Time Management": ["time management"],
    },
}


@lru_cache(maxsize=None)
def _compiled() -> list[tuple[str, str, re.Pattern]]:
    """Build one regex per skill that matches any of its aliases as a whole word."""
    result = []
    for category, skills in SKILLS.items():
        for name, aliases in skills.items():
            patterns = []
            for alias in aliases:
                case_sensitive = alias.startswith("!")
                alias = alias.lstrip("!")
                body = re.escape(alias).replace(r"\ ", r"[\s-]+")
                p = rf"(?<![A-Za-z0-9_+#]){body}(?![A-Za-z0-9_+#])"
                patterns.append(p if case_sensitive else f"(?i:{p})")
            result.append((category, name, re.compile("|".join(patterns))))
    return result


def find_skills(text: str) -> dict[str, str]:
    """Return {skill name: category} for every known skill mentioned in text."""
    return {name: cat for cat, name, pattern in _compiled() if pattern.search(text)}


def skill_words() -> set[str]:
    """All lower-case words used in skill aliases (to avoid double counting)."""
    words = set()
    for skills in SKILLS.values():
        for name, aliases in skills.items():
            for alias in [name, *aliases]:
                words.update(alias.lstrip("!").lower().split())
    return words
