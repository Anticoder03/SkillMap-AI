"""Seed the career knowledge base, interests, skills and assessment questions.

Idempotent: safe to run any number of times. Existing rows are updated in
place, and everything needed for a first run is created.

Usage::

    python manage.py seed_careers
    python manage.py seed_careers --reset   # wipe knowledge base first
"""
from django.core.management.base import BaseCommand

from assessment.models import Interest, Question, QuestionOption, Skill
from careers.models import Career, CareerInterest, CareerPrerequisite, CareerSkill

# ---------------------------------------------------------------------------
# Interests
# ---------------------------------------------------------------------------
INTERESTS = [
    ("Web Development", "Building websites and web applications."),
    ("Artificial Intelligence", "Machines that learn, reason and act."),
    ("Data Science", "Extracting insight from data."),
    ("Cyber Security", "Protecting systems and data from threats."),
    ("Cloud Computing", "Running infrastructure and services over the internet."),
    ("DevOps", "Automating and streamlining software delivery."),
    ("Mobile Development", "Building apps for phones and tablets."),
    ("Game Development", "Creating interactive games."),
    ("UI/UX Design", "Designing usable and delightful interfaces."),
    ("Networking", "Designing and managing computer networks."),
    ("Database", "Storing, querying and modeling data."),
    ("Automation", "Using scripts and tools to remove manual work."),
]

# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
# (name, category, description)
SKILLS = [
    ("Python", "Programming", "Versatile, readable scripting and applications language."),
    ("Java", "Programming", "Object-oriented language for enterprise and Android."),
    ("JavaScript", "Programming", "The language of the interactive web."),
    ("TypeScript", "Programming", "Typed superset of JavaScript."),
    ("C++", "Programming", "Low-level compiled language for performance."),
    ("C#", "Programming", "Microsoft's object-oriented language."),
    ("HTML", "Web", "Markup for structuring web pages."),
    ("CSS", "Web", "Style and layout for the web."),
    ("Django", "Web", "High-level Python web framework."),
    ("React", "Web", "JavaScript library for building user interfaces."),
    ("Node.js", "Web", "JavaScript runtime for server-side code."),
    ("SQL", "Database", "Query language for relational databases."),
    ("Pandas", "Data", "Python library for data manipulation and analysis."),
    ("NumPy", "Data", "Python library for numerical computing."),
    ("Statistics", "Data", "Mathematical tools for analyzing data."),
    ("Data Visualization", "Data", "Turning data into charts and dashboards."),
    ("Machine Learning", "AI/ML", "Building predictive models from data."),
    ("Deep Learning", "AI/ML", "Neural networks for complex pattern learning."),
    ("Docker", "DevOps", "Containerization of applications."),
    ("Kubernetes", "DevOps", "Orchestration of containerized workloads."),
    ("CI/CD", "DevOps", "Automated build, test and deploy pipelines."),
    ("Linux", "DevOps", "Command-line operating systems skills."),
    ("AWS", "Cloud", "Amazon Web Services cloud platform."),
    ("Network Security", "Security", "Securing networks against intrusion."),
    ("Ethical Hacking", "Security", "Offensive security testing."),
    ("Android", "Mobile", "Building Android applications."),
    ("Kotlin", "Mobile", "Modern Android development language."),
    ("Swift", "Mobile", "Building iOS applications."),
    ("React Native", "Mobile", "Cross-platform mobile development with JavaScript."),
    ("Networking", "Infrastructure", "Designing and managing computer networks."),
    ("Figma", "Design", "Collaborative interface design tool."),
    ("UI Design", "Design", "Designing visual interfaces."),
    ("UX Research", "Design", "Understanding users through research."),
    ("Git", "Engineering", "Version control for code."),
    ("Communication", "Soft Skills", "Clear written and spoken exchange of ideas."),
    ("Problem Solving", "Soft Skills", "Methodically finding solutions to hard problems."),
    ("Agile", "Soft Skills", "Iterative, collaborative software delivery."),
]

# ---------------------------------------------------------------------------
# Careers: (title, category, difficulty, salary_range, demand, education, summary, future_scope)
# ---------------------------------------------------------------------------
CAREERS = [
    (
        "Python Developer",
        "Software Development",
        "beginner",
        "$60k - $110k",
        "very_high",
        "bachelors",
        "Builds and maintains applications and tooling using Python.",
        "Python powers web, data, AI and automation — demand keeps growing across industries.",
    ),
    (
        "Django Developer",
        "Software Development",
        "beginner",
        "$65k - $115k",
        "high",
        "bachelors",
        "Builds secure, scalable web applications with the Django framework.",
        "Django remains a top choice for rapid, maintainable web products.",
    ),
    (
        "Full Stack Developer",
        "Software Development",
        "intermediate",
        "$70k - $130k",
        "very_high",
        "bachelors",
        "Builds both the frontend and backend of web applications.",
        "Versatile full-stack skills remain among the most requested in web hiring.",
    ),
    (
        "Frontend Developer",
        "Software Development",
        "beginner",
        "$60k - $115k",
        "very_high",
        "bachelors",
        "Builds the user-facing part of websites and web apps.",
        "Rich interactive interfaces keep frontend developers in high demand.",
    ),
    (
        "Backend Developer",
        "Software Development",
        "intermediate",
        "$70k - $125k",
        "very_high",
        "bachelors",
        "Builds servers, APIs and the logic that powers applications.",
        "Every product needs robust backends; the role continues to grow.",
    ),
    (
        "Data Analyst",
        "Data",
        "beginner",
        "$55k - $95k",
        "very_high",
        "bachelors",
        "Turns raw data into reports, dashboards and business insight.",
        "Data-driven decision making increases demand for strong analysts.",
    ),
    (
        "Data Scientist",
        "Data",
        "advanced",
        "$90k - $150k",
        "very_high",
        "masters",
        "Applies statistics and machine learning to real-world problems.",
        "Organizations are investing heavily in predictive analytics.",
    ),
    (
        "Machine Learning Engineer",
        "AI/ML",
        "advanced",
        "$105k - $170k",
        "very_high",
        "masters",
        "Builds and ships production machine learning systems.",
        "ML engineering is one of the fastest-growing tech specialisms.",
    ),
    (
        "AI Engineer",
        "AI/ML",
        "advanced",
        "$110k - $180k",
        "very_high",
        "masters",
        "Builds AI products, from LLMs to computer vision systems.",
        "Generative AI is creating enormous demand for AI engineers.",
    ),
    (
        "Cloud Engineer",
        "Infrastructure",
        "intermediate",
        "$85k - $145k",
        "high",
        "bachelors",
        "Designs and manages cloud infrastructure and platforms.",
        "Cloud migration keeps this role consistently in demand.",
    ),
    (
        "DevOps Engineer",
        "Infrastructure",
        "intermediate",
        "$90k - $150k",
        "very_high",
        "bachelors",
        "Automates delivery pipelines and manages infrastructure as code.",
        "Automation culture makes DevOps critical to modern teams.",
    ),
    (
        "Cyber Security Analyst",
        "Security",
        "intermediate",
        "$75k - $130k",
        "very_high",
        "bachelors",
        "Monitors, detects and responds to security threats.",
        "Security roles are expanding faster than the talent pool.",
    ),
    (
        "Android Developer",
        "Mobile",
        "beginner",
        "$65k - $115k",
        "high",
        "bachelors",
        "Builds native Android applications.",
        "Mobile usage keeps Android development a strong career choice.",
    ),
    (
        "UI/UX Designer",
        "Design",
        "beginner",
        "$55k - $100k",
        "high",
        "bachelors",
        "Designs interfaces and experiences that are usable and delightful.",
        "Product teams increasingly invest in design maturity.",
    ),
    (
        "Software Engineer",
        "Software Development",
        "intermediate",
        "$75k - $135k",
        "very_high",
        "bachelors",
        "Designs, builds and maintains software systems of all kinds.",
        "The broadest tech role — adaptable across every industry.",
    ),
    (
        "Database Administrator",
        "Data",
        "intermediate",
        "$70k - $125k",
        "medium",
        "bachelors",
        "Manages, tunes and secures databases.",
        "Heavy data reliance ensures steady demand for DB specialists.",
    ),
]

# ---------------------------------------------------------------------------
# Career → skills: (career, [(skill, importance, required_level), ...])
# ---------------------------------------------------------------------------
CAREER_SKILLS = {
    "Python Developer": [
        ("Python", 10, 4), ("Git", 7, 3), ("SQL", 7, 3), ("Django", 8, 3),
        ("Problem Solving", 6, 3), ("Communication", 5, 2),
    ],
    "Django Developer": [
        ("Python", 10, 4), ("Django", 10, 4), ("SQL", 8, 3), ("HTML", 6, 2),
        ("CSS", 6, 2), ("Git", 7, 3), ("Problem Solving", 6, 3),
    ],
    "Full Stack Developer": [
        ("JavaScript", 10, 4), ("React", 9, 4), ("Node.js", 8, 3), ("HTML", 9, 4),
        ("CSS", 9, 4), ("SQL", 8, 3), ("Git", 8, 4), ("Django", 7, 3),
    ],
    "Frontend Developer": [
        ("JavaScript", 10, 4), ("React", 10, 4), ("HTML", 10, 4), ("CSS", 10, 4),
        ("Figma", 6, 2), ("UX Research", 6, 3), ("Git", 6, 3),
    ],
    "Backend Developer": [
        ("Python", 9, 4), ("Node.js", 8, 3), ("SQL", 9, 4), ("Django", 8, 3),
        ("Docker", 6, 3), ("Git", 7, 3), ("Problem Solving", 6, 3),
    ],
    "Data Analyst": [
        ("SQL", 10, 4), ("Python", 8, 3), ("Pandas", 9, 4), ("Data Visualization", 9, 4),
        ("Statistics", 8, 3), ("Communication", 6, 3),
    ],
    "Data Scientist": [
        ("Python", 10, 4), ("SQL", 8, 3), ("Statistics", 10, 4), ("Machine Learning", 10, 4),
        ("Pandas", 9, 4), ("NumPy", 9, 4), ("Data Visualization", 7, 3),
    ],
    "Machine Learning Engineer": [
        ("Python", 10, 5), ("Machine Learning", 10, 5), ("Deep Learning", 10, 5),
        ("Statistics", 9, 4), ("NumPy", 9, 4), ("Pandas", 9, 4), ("Docker", 6, 3),
    ],
    "AI Engineer": [
        ("Python", 10, 5), ("Machine Learning", 10, 5), ("Deep Learning", 10, 5),
        ("Statistics", 9, 4), ("NumPy", 8, 4), ("Pandas", 8, 4), ("Docker", 6, 3),
        ("Problem Solving", 7, 4),
    ],
    "Cloud Engineer": [
        ("AWS", 10, 4), ("Linux", 9, 4), ("Docker", 9, 4), ("Kubernetes", 9, 4),
        ("CI/CD", 8, 3), ("Python", 6, 3), ("Network Security", 5, 2),
    ],
    "DevOps Engineer": [
        ("Docker", 10, 4), ("Kubernetes", 10, 4), ("Linux", 9, 4), ("CI/CD", 10, 4),
        ("AWS", 8, 4), ("Git", 7, 3), ("Python", 7, 3), ("Communication", 5, 3),
    ],
    "Cyber Security Analyst": [
        ("Network Security", 10, 4), ("Ethical Hacking", 9, 4), ("Linux", 8, 3),
        ("Python", 7, 3), ("Networking", 8, 4), ("SQL", 5, 2), ("Problem Solving", 8, 4),
    ],
    "Android Developer": [
        ("Android", 10, 4), ("Java", 8, 3), ("Kotlin", 9, 4), ("Git", 7, 3),
        ("Problem Solving", 6, 3), ("Communication", 4, 2),
    ],
    "UI/UX Designer": [
        ("UI Design", 10, 4), ("UX Research", 10, 4), ("Figma", 10, 4),
        ("HTML", 7, 3), ("CSS", 7, 3), ("Communication", 7, 3),
    ],
    "Software Engineer": [
        ("Python", 9, 4), ("Java", 8, 3), ("Git", 9, 4), ("SQL", 8, 3),
        ("Problem Solving", 9, 4), ("Communication", 7, 3), ("C++", 6, 2),
    ],
    "Database Administrator": [
        ("SQL", 10, 5), ("Linux", 7, 3), ("Python", 6, 3), ("Networking", 6, 2),
        ("Problem Solving", 7, 3), ("Data Visualization", 4, 2),
    ],
}

# ---------------------------------------------------------------------------
# Career → interests: (career, [(interest, weight), ...])
# ---------------------------------------------------------------------------
CAREER_INTERESTS = {
    "Python Developer": [("Web Development", 8), ("Automation", 6), ("Data Science", 4)],
    "Django Developer": [("Web Development", 10), ("Database", 6)],
    "Full Stack Developer": [("Web Development", 10), ("UI/UX Design", 6), ("Mobile Development", 4)],
    "Frontend Developer": [("Web Development", 10), ("UI/UX Design", 8)],
    "Backend Developer": [("Web Development", 9), ("Database", 8), ("Cloud Computing", 5)],
    "Data Analyst": [("Data Science", 10), ("Database", 7)],
    "Data Scientist": [("Data Science", 10), ("Artificial Intelligence", 8)],
    "Machine Learning Engineer": [("Artificial Intelligence", 10), ("Data Science", 10)],
    "AI Engineer": [("Artificial Intelligence", 10), ("Data Science", 9), ("Automation", 5)],
    "Cloud Engineer": [("Cloud Computing", 10), ("DevOps", 8), ("Networking", 6)],
    "DevOps Engineer": [("DevOps", 10), ("Cloud Computing", 9), ("Automation", 8)],
    "Cyber Security Analyst": [("Cyber Security", 10), ("Networking", 8)],
    "Android Developer": [("Mobile Development", 10), ("Game Development", 4), ("Automation", 3)],
    "UI/UX Designer": [("UI/UX Design", 10), ("Web Development", 7), ("Game Development", 5)],
    "Software Engineer": [("Web Development", 6), ("Artificial Intelligence", 5), ("Database", 6), ("Automation", 5)],
    "Database Administrator": [("Database", 10), ("Networking", 5)],
}

# ---------------------------------------------------------------------------
# Career → prerequisites: (career, [(description, priority)])
# ---------------------------------------------------------------------------
CAREER_PREREQUISITES = {
    "Python Developer": [
        ("Master Python fundamentals including OOP and modules", 1),
        ("Understand how to use Git for version control", 2),
    ],
    "Django Developer": [
        ("Strong Python fundamentals", 1),
        ("Basic understanding of web requests and HTTP", 2),
        ("Familiarity with relational databases and SQL", 3),
    ],
    "Full Stack Developer": [
        ("Comfortable with HTML, CSS and JavaScript", 1),
        ("Understand at least one backend language", 2),
        ("Knowledge of Git and basic deployment", 3),
    ],
    "Frontend Developer": [
        ("Solid HTML and CSS fundamentals", 1),
        ("JavaScript basics including the DOM", 2),
    ],
    "Backend Developer": [
        ("Strong programming fundamentals in one language", 1),
        ("Understand databases and API design", 2),
    ],
    "Data Analyst": [
        ("Comfort with spreadsheet/analytical thinking", 1),
        ("Basic SQL queries", 2),
    ],
    "Data Scientist": [
        ("Solid statistics fundamentals", 1),
        ("Python programming experience", 2),
        ("Linear algebra basics", 3),
    ],
    "Machine Learning Engineer": [
        ("Strong Python and programming skills", 1),
        ("Statistics and linear algebra fundamentals", 2),
    ],
    "AI Engineer": [
        ("Machine learning fundamentals", 1),
        ("Strong Python", 2),
        ("Understanding of neural networks", 3),
    ],
    "Cloud Engineer": [
        ("Comfort with the Linux command line", 1),
        ("Basic networking concepts", 2),
    ],
    "DevOps Engineer": [
        ("Linux fundamentals", 1),
        ("Familiarity with Git", 2),
        ("Basic scripting (Python or Bash)", 3),
    ],
    "Cyber Security Analyst": [
        ("Basic networking knowledge", 1),
        ("Comfort with Linux", 2),
    ],
    "Android Developer": [
        ("Core programming in Java or Kotlin", 1),
        ("Object-oriented thinking", 2),
    ],
    "UI/UX Designer": [
        ("Interest in design fundamentals", 1),
        ("Familiarity with Figma or similar tools", 2),
    ],
    "Software Engineer": [
        ("Strong fundamentals in one or two languages", 1),
        ("Data structures and algorithms basics", 2),
        ("Git proficiency", 3),
    ],
    "Database Administrator": [
        ("Advanced SQL skills", 1),
        ("Linux basics", 2),
    ],
}

# ---------------------------------------------------------------------------
# Assessment questions
# ---------------------------------------------------------------------------
# Question definitions:
#   (text, type, category, weight, order, [ (option text, score, interest|None, skill|None) ... ])
# For scale questions options are generated 1..5 mapping to the linked entity.
QUESTIONS = [
    (
        "Which field excites you the most?",
        "single_choice", "interest", 3, 1,
        [
            ("Web Development", 4, "Web Development", None),
            ("Artificial Intelligence", 4, "Artificial Intelligence", None),
            ("Data Science", 4, "Data Science", None),
            ("Cyber Security", 4, "Cyber Security", None),
            ("Cloud Computing", 3, "Cloud Computing", None),
        ],
    ),
    (
        "If you had a free weekend to learn something new, what would you choose?",
        "single_choice", "interest", 2, 2,
        [
            ("Build a website for a hobby", 3, "Web Development", None),
            ("Train a small AI model", 4, "Artificial Intelligence", None),
            ("Build a mobile app", 4, "Mobile Development", None),
            ("Create a game prototype", 4, "Game Development", None),
            ("Design an app interface", 4, "UI/UX Design", None),
        ],
    ),
    (
        "Which kind of project would you most enjoy working on?",
        "single_choice", "interest", 2, 3,
        [
            ("Designing a database for a company", 4, "Database", None),
            ("Automating repetitive tasks with scripts", 4, "Automation", None),
            ("Setting up enterprise networks", 3, "Networking", None),
            ("Building backend APIs", 3, "Web Development", None),
        ],
    ),
    (
        "Where do you think technology adds the most value in the next decade?",
        "single_choice", "interest", 2, 4,
        [
            ("Intelligent assistants and AI apps", 4, "Artificial Intelligence", None),
            ("Scalable cloud infrastructure", 3, "Cloud Computing", None),
            ("Automated software delivery", 3, "DevOps", None),
            ("Protecting people's data", 4, "Cyber Security", None),
        ],
    ),
    (
        "Which would you rather prototype in your spare time?",
        "single_choice", "interest", 2, 5,
        [
            ("A smart chatbot", 4, "Artificial Intelligence", None),
            ("A browser game", 3, "Game Development", None),
            ("A portfolio website", 3, "Web Development", None),
            ("A script that organizes my files", 4, "Automation", None),
        ],
    ),
    (
        "Pick a portfolio project you would build first:",
        "single_choice", "interest", 2, 6,
        [
            ("A weather web app", 2, "Web Development", None),
            ("A sentiment-analysis chatbot", 4, "Artificial Intelligence", None),
            ("A sales analytics dashboard", 4, "Data Science", None),
            ("A home media server", 2, "Networking", None),
        ],
    ),
    (
        "How do you usually approach a tough problem?",
        "single_choice", "personality", 2, 7,
        [
            ("Break it down step by step", 3, None, "Problem Solving"),
            ("Brainstorm and try creative angles", 2, None, "Problem Solving"),
            ("Research how others solved it first", 2, None, "Communication"),
            ("Get help from peers quickly", 2, None, "Communication"),
        ],
    ),
    (
        "Which work environment suits you best?",
        "single_choice", "career_style", 1, 8,
        [
            ("Independent, deep-focus tasks", 3, None, None),
            ("High collaboration with a team", 3, None, "Communication"),
            ("A mix of both", 3, None, None),
            ("I am flexible", 2, None, None),
        ],
    ),
    (
        "How important is a high starting salary to you?",
        "single_choice", "preference", 1, 9,
        [
            ("Extremely important", 4, None, None),
            ("Somewhat important", 3, None, None),
            ("Not very important", 2, None, None),
        ],
    ),
    (
        "Which outcome appeals to you most at work?",
        "single_choice", "career_style", 2, 10,
        [
            ("Building products people love to use", 3, "UI/UX Design", None),
            ("Solving complex technical puzzles", 4, "Artificial Intelligence", None),
            ("Keeping systems safe from attackers", 4, "Cyber Security", None),
            ("Automating the boring stuff away", 4, "Automation", None),
        ],
    ),
    (
        "How comfortable are you learning new things on your own?",
        "single_choice", "personality", 1, 11,
        [
            ("Very comfortable with self-study", 4, None, None),
            ("Comfortable with good resources", 3, None, None),
            ("I need structured courses and support", 2, None, None),
        ],
    ),
    (
        "Which part of building software sounds most exciting?",
        "single_choice", "career_style", 2, 12,
        [
            ("Designing the look and feel", 3, "UI/UX Design", None),
            ("Writing the core logic", 3, "Database", None),
            ("Making it fast and secure", 3, "Networking", None),
            ("Keeping everything running in production", 4, "DevOps", None),
        ],
    ),
    (
        "Rate your current Python experience.",
        "scale", "skill", 3, 13,
        None,
    ),  # options auto-generated for Skill "Python"
    (
        "Rate your current JavaScript experience.",
        "scale", "skill", 3, 14,
        None,
    ),  # Skill "JavaScript"
    (
        "Rate your current SQL experience.",
        "scale", "skill", 3, 15,
        None,
    ),  # Skill "SQL"
    (
        "Rate your confidence with Git and version control.",
        "scale", "skill", 2, 16,
        None,
    ),  # Skill "Git"
    (
        "Rate your communication and teamwork skills.",
        "scale", "skill", 2, 17,
        None,
    ),  # Skill "Communication"
    (
        "Which skills have you used before? Select all that apply.",
        "multiple_choice", "skill", 2, 18,
        [
            ("Java", 2, None, "Java"),
            ("React", 2, None, "React"),
            ("Docker", 2, None, "Docker"),
            ("AWS", 2, None, "AWS"),
            ("Figma", 2, None, "Figma"),
            ("HTML/CSS", 2, None, "HTML"),
            ("React Native", 2, None, "React Native"),
        ],
    ),
    (
        "Which tools or platforms have you touched? Select all that apply.",
        "multiple_choice", "skill", 2, 19,
        [
            ("Node.js", 2, None, "Node.js"),
            ("Linux", 2, None, "Linux"),
            ("Kubernetes", 2, None, "Kubernetes"),
            ("Pandas", 2, None, "Pandas"),
            ("Android Studio", 2, None, "Android"),
            ("CI/CD pipelines", 2, None, "CI/CD"),
        ],
    ),
    (
        "Which subjects did you enjoy most? Select all that apply.",
        "multiple_choice", "skill", 2, 20,
        [
            ("Mathematics", 3, None, "Problem Solving"),
            ("Computer Science", 3, None, "Python"),
            ("Statistics", 3, None, "Statistics"),
            ("Psychology / people studies", 2, None, "Communication"),
            ("Design or art", 2, None, "UI Design"),
        ],
    ),
    (
        "Have you worked with any cloud or DevOps tooling? Select all that apply.",
        "multiple_choice", "skill", 2, 21,
        [
            ("Google Cloud / AWS / Azure", 3, None, "AWS"),
            ("Docker containers", 3, None, "Docker"),
            ("Git / GitHub", 3, None, "Git"),
            ("Linux terminal", 2, None, "Linux"),
        ],
    ),
    (
        "What are you hoping to get out of CareerPath AI?",
        "text", "preference", 1, 22,
        [],
    ),
]


SCALE_LABELS = {1: "Novice", 2: "Beginner", 3: "Intermediate", 4: "Advanced", 5: "Expert"}


def _scale_options(skill_name: str):
    """Build the 1-5 option list for a scale question linked to a skill."""
    skill = Skill.objects.get(name=skill_name)
    return [(SCALE_LABELS[i], i, None, skill_name) for i in range(1, 6)]


class Command(BaseCommand):
    help = "Seed interests, skills, careers, mappings and assessment questions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing knowledge-base data before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Resetting knowledge base...")
            QuestionOption.objects.all().delete()
            Question.objects.all().delete()
            CareerSkill.objects.all().delete()
            CareerInterest.objects.all().delete()
            CareerPrerequisite.objects.all().delete()
            Career.objects.all().delete()
            Interest.objects.all().delete()
            Skill.objects.all().delete()

        self._seed_interests()
        self._seed_skills()
        self._seed_careers()
        self._seed_questions()

        self.stdout.write(self.style.SUCCESS(
            f"Seeding complete. "
            f"{Interest.objects.count()} interests, {Skill.objects.count()} skills, "
            f"{Career.objects.count()} careers, {Question.objects.count()} questions."
        ))

    # -- helpers ------------------------------------------------------------
    def _seed_interests(self):
        for name, description in INTERESTS:
            Interest.objects.update_or_create(name=name, defaults={"description": description})
        self.stdout.write(f"  • seeded {len(INTERESTS)} interests")

    def _seed_skills(self):
        for name, category, description in SKILLS:
            Skill.objects.update_or_create(name=name, defaults={"category": category, "description": description})
        self.stdout.write(f"  • seeded {len(SKILLS)} skills")

    def _seed_careers(self):
        career_by_title = {}
        for (title, category, difficulty, salary, demand, education, description, future_scope) in CAREERS:
            career, _ = Career.objects.update_or_create(
                title=title,
                defaults={
                    "category": category,
                    "difficulty": difficulty,
                    "salary_range": salary,
                    "demand_level": demand,
                    "required_education": education,
                    "description": description,
                    "future_scope": future_scope,
                },
            )
            career_by_title[title] = career

            for skill_name, importance, required in CAREER_SKILLS.get(title, []):
                CareerSkill.objects.update_or_create(
                    career=career,
                    skill=Skill.objects.get(name=skill_name),
                    defaults={"importance": importance, "required_level": required},
                )

            for interest_name, weight in CAREER_INTERESTS.get(title, []):
                CareerInterest.objects.update_or_create(
                    career=career,
                    interest=Interest.objects.get(name=interest_name),
                    defaults={"weight": weight},
                )

            for description, priority in CAREER_PREREQUISITES.get(title, []):
                CareerPrerequisite.objects.update_or_create(
                    career=career,
                    priority=priority,
                    defaults={"description": description},
                )

        self.stdout.write(f"  • seeded {len(CAREERS)} careers with skills/interests/prerequisites")

    def _seed_questions(self):
        for (text, qtype, category, weight, order, options) in QUESTIONS:
            question, _ = Question.objects.update_or_create(
                order=order,
                defaults={
                    "question_text": text,
                    "question_type": qtype,
                    "category": category,
                    "weight": weight,
                    "is_active": True,
                },
            )

            if options is None:
                # Scale question → generate options 1-5 for the named skill.
                skill_name = self._infer_scale_skill(text)
                options = _scale_options(skill_name)

            for idx, (option_text, score, interest_name, skill_name) in enumerate(options):
                interest = Interest.objects.filter(name=interest_name).first() if interest_name else None
                skill = Skill.objects.get(name=skill_name) if skill_name else None
                QuestionOption.objects.update_or_create(
                    question=question,
                    option_text=option_text,
                    defaults={"score": score, "interest": interest, "skill": skill},
                )
        self.stdout.write(f"  • seeded {len(QUESTIONS)} assessment questions")

    @staticmethod
    def _infer_scale_skill(text: str) -> str:
        """Map a scale question prompt back to its linked skill name."""
        import re

        lowered = text.lower()
        for name, _category, _desc in SKILLS:
            escaped = re.escape(name).lower()
            if re.search(rf"\b{escaped}\b", lowered):
                return name
        return "Python"