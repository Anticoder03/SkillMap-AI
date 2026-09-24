# -*- coding: utf-8 -*-
"""Generate docs/CareerPath_AI_User_Manual.pdf

Usage:  python docs/generate_user_manual.py
Requires:  pip install -r requirements-docs.txt
"""
from __future__ import annotations

import os

from fpdf import FPDF

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "CareerPath_AI_User_Manual.pdf")

INDIGO = (79, 70, 229)
INDIGO_DARK = (55, 48, 163)
SLATE = (51, 65, 85)
SLATE_LIGHT = (100, 116, 139)
SOFT = (238, 242, 255)
ROSE = (225, 29, 72)


class Manual(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", size=8.5)
        self.set_text_color(*SLATE_LIGHT)
        self.set_y(8)
        self.cell(0, 5, "CareerPath AI - User Manual", new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_draw_color(*SOFT)
        self.set_line_width(0.4)
        self.line(10, 15, 200, 15)
        self.set_y(20)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font("Helvetica", size=8.5)
        self.set_text_color(*SLATE_LIGHT)
        self.cell(0, 5, f"Page {self.page_no()}", align="L")
        self.cell(0, 5, "CareerPath AI", align="R")

    def h1(self, num, title):
        self.start_section(f"{num}. {title}", level=0)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*INDIGO_DARK)
        self.cell(0, 9, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*INDIGO)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(5)

    def h2(self, title):
        self.start_section(title, level=1)
        self.set_font("Helvetica", "B", 12.5)
        self.set_text_color(*INDIGO)
        self.ln(2)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body(self, text):
        self.set_font("Helvetica", size=10)
        self.set_text_color(*SLATE)
        self.multi_cell(0, 5.6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.6)

    def bullet(self, text, indent=5):
        self.set_font("Helvetica", size=10)
        self.set_text_color(*SLATE)
        self.set_x(self.l_margin + indent)
        self.cell(5, 5.6, "-")
        self.multi_cell(0, 5.6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(0.6)

    def code(self, text):
        self.set_font("Courier", size=8.6)
        self.set_fill_color(241, 245, 249)
        self.set_text_color(15, 23, 42)
        for line in text.splitlines():
            if line.strip():
                self.set_x(self.l_margin + 4)
                self.cell(0, 5.2, "  " + line, fill=True, new_x="LMARGIN", new_y="NEXT")
            else:
                self.ln(5.2)
        self.ln(2)

    def kv_table(self, rows, col1=0.42, col2=0.58):
        self.set_font("Helvetica", size=9)
        for k, v in rows:
            self.set_fill_color(*SOFT)
            self.set_text_color(*INDIGO_DARK)
            self.set_x(self.l_margin)
            self.cell(self.w * col1, 7, f"  {k}", border="B", fill=True, new_x="END")
            self.set_text_color(*SLATE)
            self.cell(self.w * col2, 7, f" {v}", border="B", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


pdf = Manual(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(12, 20, 12)

# ---------------- Cover ----------------
pdf.add_page()
pdf.set_fill_color(*INDIGO)
pdf.rect(0, 0, 210, 108, "F")
pdf.set_fill_color(*INDIGO_DARK)
pdf.ellipse(150, -44, 110, 110, "F")
pdf.set_fill_color(124, 58, 237)
pdf.ellipse(-30, 196, 90, 90, "F")

pdf.set_y(40)
pdf.set_font("Helvetica", "B", 15)
pdf.set_text_color(199, 210, 254)
pdf.cell(0, 8, "USER MANUAL", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 40)
pdf.set_text_color(255, 255, 255)
pdf.cell(0, 18, "CareerPath AI", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 14)
pdf.set_text_color(224, 231, 255)
pdf.cell(0, 8, "AI-powered career guidance made personal", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.set_y(128)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(199, 210, 254)
pdf.cell(0, 6, "Version 1.0  |  Django 6.1  |  Documentation & walkthrough", align="C", new_x="LMARGIN", new_y="NEXT")

# ---------------- TOC ----------------
pdf.add_page()


def render_toc(doc, outline):
    doc.set_font("Helvetica", "B", 16)
    doc.set_text_color(*INDIGO_DARK)
    doc.cell(0, 9, "Contents", new_x="LMARGIN", new_y="NEXT")
    doc.ln(4)
    for section in outline:
        indent = section.level * 5
        page = getattr(section, "page", "")
        doc.set_font("Helvetica", "", 11 if section.level == 0 else 10.5)
        doc.set_text_color(*SLATE)
        doc.set_x(doc.l_margin + indent)
        doc.cell(doc.epw - indent - 16, 7, section.name, new_x="END")
        if page:
            doc.set_text_color(*SLATE_LIGHT)
            doc.cell(16, 7, str(page), align="R", new_x="LMARGIN", new_y="NEXT")
        else:
            doc.ln()


pdf.insert_toc_placeholder(render_toc, pages=1, allow_extra_pages=True)

# ---------------- 1. Introduction ----------------
pdf.add_page()
pdf.h1(1, "Introduction")
pdf.body(
    "CareerPath AI is a web application that helps students, graduates, and career switchers discover "
    "a suitable career and follow a personalised learning roadmap to get there. You answer a short "
    "assessment about your skills, education, experience, and interests; the app scores the match "
    "against a built-in set of careers, shows you the best fits with reasons, and then generates a "
    "step-by-step roadmap. Every task on the roadmap points to a real, current learning resource and "
    "optionally a YouTube video, found through live search, AI suggestions, or a curated fallback."
)
pdf.h2("What you can do")
pdf.bullet("Assess yourself with a guided, save-as-you-go questionnaire.")
pdf.bullet("See ranked career recommendations with match percentages and skill gaps.")
pdf.bullet("Browse the careers library with required skills and future scope.")
pdf.bullet("Generate and track a personalised roadmap: phases, tasks, resources, and videos.")
pdf.bullet("Keep your profile fresh and watch your readiness score grow.")
pdf.bullet("Manage everything from one Django admin panel.")
pdf.body(
    "The application is deliberately resilient: if the AI provider is unavailable or rate-limited, "
    "roadmaps still generate from curated seed data, and live resource search (Google/YouTube via "
    "SerpAPI) keeps links current."
)

# ---------------- 2. Requirements ----------------
pdf.add_page()
pdf.h1(2, "Requirements")
pdf.bullet("Windows, macOS, or Linux with Python 3.12 or newer (Windows 11 recommended).")
pdf.bullet("A web browser (Chrome, Edge, Firefox, or Safari).")
pdf.bullet("Internet access for the AI provider and live search features (optional for offline use).")
pdf.bullet("Optional API keys: one for Google Gemini / OpenAI / NVIDIA NIM, and one for SerpAPI.")
pdf.body(
    "You can run the entire application locally with no API keys at all. In that case roadmaps use "
    "curated content, and resources come from the built-in lists."
)

# ---------------- 3. Installation ----------------
pdf.add_page()
pdf.h1(3, "Installation on Windows")
pdf.h2("3.1  Get the code and create a virtual environment")
pdf.code(
    "git clone <repository-url>\n"
    "cd django-ai-path-finder\n"
    "python -m venv venv\n"
    "venv\\Scripts\\activate"
)
pdf.h2("3.2  Install dependencies")
pdf.code(
    "pip install -r requirements.txt\n"
    "# optional, only if you want to regenerate the PPT/PDF docs:\n"
    "pip install -r requirements-docs.txt"
)
pdf.h2("3.3  Configure environment variables")
pdf.body(
    "Copy .env.example to .env and fill in your keys. A minimal .env looks like this:"
)
pdf.code(
    "SECRET_KEY=django-insecure-CHANGE-ME\n"
    "DEBUG=True\n"
    "AI_PROVIDER=gemini\n"
    "AI_API_KEY=your_gemini_api_key\n"
    "SERPAPI_API_KEY=your_serpapi_api_key"
)
pdf.body(
    "Every key is optional except SECRET_KEY. See section 11 for the full reference."
)
pdf.h2("3.4  Prepare the database and run")
pdf.code(
    "python manage.py migrate\n"
    "python manage.py seed_careers       # load careers, skills, and interests\n"
    "python manage.py runserver\n"
)
pdf.body("Open http://127.0.0.1:8000/ in your browser. Use a single runserver instance per database.")

# ---------------- 4. First steps ----------------
pdf.add_page()
pdf.h1(4, "First steps - register and sign in")
pdf.h2("Create an account")
pdf.bullet("Open the landing page and click 'Get started' or 'Create account'.")
pdf.bullet("Enter a username, email, optional first/last name, and a strong password twice.")
pdf.bullet("Click 'Create account'. You are signed in automatically.")
pdf.h2("Sign in")
pdf.bullet("Enter your username and password on the sign-in page.")
pdf.bullet("Tick 'Remember me' to stay signed in on your device.")
pdf.h2("Change your password")
pdf.bullet("From your profile, click 'Change password' (keyboard icon on small screens).")
pdf.bullet("Enter the current password, then your new password twice, and save.")

# ---------------- 5. Profile ----------------
pdf.add_page()
pdf.h1(5, "Your profile")
pdf.body(
    "Your profile stores the information that powers your career matches. Keep it up to date."
)
pdf.h2("Account details")
pdf.bullet("First name, last name, and email address.")
pdf.h2("Education and experience")
pdf.body("Degree, college/institute, graduation year, education level, experience level, a short bio, and your location. Graduation year must be between 1950 and 2099.")
pdf.h2("My skills and My interests")
pdf.bullet("Skill list with a 1-5 proficiency rating; completed assessments add skills automatically.")
pdf.bullet("Interest list with a 1-5 level; use it to tune your matches.")
pdf.bullet("Use the dropdown + Add button under each list to add new entries, or click the x to remove one.")
pdf.h2("Profile readiness")
pdf.body(
    "A progress ring/bar on the profile page shows how complete your profile is. Higher completeness "
    "gives the recommendation engine richer signals, so the scores you see become more accurate."
)

# ---------------- 6. Assessment ----------------
pdf.add_page()
pdf.h1(6, "The career assessment")
pdf.body("The assessment is a set of short questions across skills, education, experience, and interests.")
pdf.bullet("Start from the dashboard or the 'Assessment' menu.")
pdf.bullet("Answer each question and press Next; your answers are saved as you go.")
pdf.bullet("A progress bar shows where you are. You can resume later from where you left off.")
pdf.bullet("When the last question is answered, the engine computes your recommendations.")
pdf.h2("What the questions measure")
pdf.bullet("Skills: what you already know or enjoy practising (coding, design, communication...).")
pdf.bullet("Education: your degree level and focus areas.")
pdf.bullet("Experience: years and type of hands-on work.")
pdf.bullet("Interests: what you genuinely enjoy doing.")
pdf.body("Your answers map onto the imported skill/interest catalogue. The more honestly you answer, the better the matches.")

# ---------------- 7. Recommendations ----------------
pdf.add_page()
pdf.h1(7, "Career recommendations")
pdf.body("After the assessment you see your top career matches, each with a clear breakdown:")
pdf.bullet("Match score: an overall percentage of fit.")
pdf.bullet("Reason: a short, human explanation of why this career fits you.")
pdf.bullet("Skill match: how well your current skills line up.")
pdf.bullet("Interest match and education fit: the remaining score components.")
pdf.bullet("Skill gaps and prerequisites: what to learn next to close the gap.")
pdf.body("You can regenerate the assessment later (it updates your scores), and the app tracks the components transparently instead of hiding them behind a 'black box'.")

# ---------------- 8. Careers library ----------------
pdf.add_page()
pdf.h1(8, "Careers library")
pdf.bullet("Browse all supported careers with search and category filters.")
pdf.bullet("Open a career to see its description, required skills with importance bars, prerequisites, related interests, and future scope.")
pdf.bullet("If you already have a roadmap for that career, the page shows your current progress.")
pdf.bullet("Clicking 'Start / Generate roadmap' jumps straight into roadmap creation.")

# ---------------- 9. Roadmaps ----------------
pdf.add_page()
pdf.h1(9, "Learning roadmaps")
pdf.h2("Generate a roadmap")
pdf.bullet("Pick a career, then click 'Generate roadmap' (or in the roadmap section).")
pdf.bullet("The AI provider builds phases (Foundations, Core skills, Projects...) and tasks under each.")
pdf.bullet("If AI is unavailable the roadmap falls back to curated data - it always completes.")
pdf.h2("Refresh resources")
pdf.bullet("After generation, use 'Refresh resources' to enrich each task.")
pdf.bullet("Each task receives one reliable link: live Google result first, AI suggestion second, curated link as the safety net.")
pdf.bullet("Videos are optional per task and searched on YouTube when enabled; the video title is shown inline.")
pdf.bullet("Resource links open in a new tab ('noopener' for safety).")
pdf.h2("Track progress")
pdf.bullet("Mark a task Completed or In progress to move the progress ring.")
pdf.bullet("Phase progress and overall roadmap progress (%) update automatically.")
pdf.bullet("The dashboard reads the same numbers, so your home page stays in sync.")
pdf.h2("Regenerating")
pdf.bullet("Regenerating rebuilds the roadmap for the same career. Your completion status is reset for the new phases/tasks.")

# ---------------- 10. Admin ----------------
pdf.add_page()
pdf.h1(10, "Admin panel")
pdf.body("A Django superuser can manage everything from the web admin at /admin/.")
pdf.code(
    "python manage.py createsuperuser\n"
    "python manage.py runserver  # then open http://127.0.0.1:8000/admin/"
)
pdf.bullet("Users: view/disable accounts, reset passwords.")
pdf.bullet("Careers, skills, interests: add, edit, or remove catalogue entries.")
pdf.bullet("Roadmaps: inspect generated plans, phases, and tasks.")
pdf.bullet("Assessment submissions: see answers and history.")

# ---------------- 11. Configuration ----------------
pdf.add_page()
pdf.h1(11, "Configuration reference (.env)")
pdf.kv_table([
    ("SECRET_KEY", "Required. Django secret - keep it secret."),
    ("DEBUG", "True/False. Never True in production."),
    ("BASE_URL", "Public base URL for links."),
    ("ALLOWED_HOSTS", "Comma-separated hosts (empty allows localhost)."),
    ("DATABASE_NAME", "Optional. Set to switch SQLite -> PostgreSQL."),
    ("AI_PROVIDER", "gemini | openai | nvidia | ollama."),
    ("AI_API_KEY", "API key for the chosen provider."),
    ("AI_MODEL", "Optional. Model name to override the default."),
    ("AI_TIMEOUT_SECONDS", "Per-call timeout (default 45)."),
    ("AI_MAX_RETRIES", "Retries before falling back (default 2)."),
    ("NVIDIA_BASE_URL", "NIM endpoint (defaults to build.nvidia.com)."),
    ("SERPAPI_API_KEY", "Optional. Enables live Google/YouTube search."),
    ("SERPAPI_MAX_QUERIES", "Search budget per refresh (default 20)."),
    ("SERPAPI_RESULTS_NUM", "Results per query (default 5)."),
    ("SERPAPI_LOCATION", "Optional geo context for search."),
], col1=0.40, col2=0.60)
pdf.body("Environment variables are read from .env at startup. Restart the server after changing them. Secrets committed to git are a serious risk: never put real keys in .env.example.")

# ---------------- 12. AI providers ----------------
pdf.add_page()
pdf.h1(12, "Switching AI providers (incl. NVIDIA NIM / Nemotron)")
pdf.body("All providers share one OpenAI-compatible interface. A roadmap always works even when AI is down (curated fallback), so provider switching is purely a preference/perf/price choice.")
pdf.h2("Gemini (default)")
pdf.code("AI_PROVIDER=gemini\nAI_API_KEY=your_google_api_key\nAI_MODEL=gemini-3.6-flash")
pdf.h2("OpenAI")
pdf.code("AI_PROVIDER=openai\nAI_API_KEY=sk-...\nAI_MODEL=gpt-4o-mini")
pdf.h2("Ollama (local, no key)")
pdf.code("AI_PROVIDER=ollama\nAI_MODEL=llama3.2   # any model you have pulled locally")
pdf.h2("NVIDIA NIM - hosted Nemotron")
pdf.body("Get a free API key from build.nvidia.com (or an NGC enterprise key), then:")
pdf.code(
    "AI_PROVIDER=nvidia\n"
    "AI_API_KEY=nvapi-<your-nim-key>\n"
    "AI_MODEL=nvidia/<the-nemotron-model-id>\n"
    "# NVIDIA_BASE_URL stays default for hosted NIM"
)
pdf.body("Find the exact model id on the build.nvidia.com model card (for example nvidia/llama-3.3-nemotron-super-49b-v1, or the latest Nemotron 3 release listed there).")
pdf.h2("NVIDIA NIM - self-hosted container")
pdf.body("If you run Nemotron NIM locally with Docker, point the app at your container instead:")
pdf.code(
    "docker run -d --gpus all -p 8000:8000 \\\n"
    "  -e NVIDIA_NIM_API_KEY=nvapi-<key> \\\n"
    "  nvcr.io/nim/<org>/<nemotron-model>:latest\n\n"
    "NVIDIA_BASE_URL=http://localhost:8000/v1"
)
pdf.body("Remove the trailing /chat/completions from packaged URLs - the provider appends it to the base URL.")

# ---------------- 13. Tests ----------------
pdf.add_page()
pdf.h1(13, "Running tests")
pdf.body("The suite is hermetic: during tests the real API keys are zeroed automatically, so tests never hit live services unless a test opts back in explicitly.")
pdf.code(
    "python manage.py test           # full suite\n"
    "python manage.py test ai_engine # just the AI/search engine\n"
    "python manage.py check          # configuration sanity\n"
)
pdf.bullet("197+ tests cover auth, profile, assessment, recommendations, roadmaps, careers, AI providers, search tiers, and sanitisation.")
pdf.bullet("Expect 'OK' and 'Destroying test database...' on completion.")

# ---------------- 14. Troubleshooting ----------------
pdf.add_page()
pdf.h1(14, "Troubleshooting")
pdf.h2("'OperationalError: table ... has no column named X'")
pdf.bullet("Your database predates a schema change. Run: python manage.py migrate")
pdf.h2("'OperationalError: database is locked'")
pdf.bullet("Two server instances share one SQLite file. Stop all runservers and start exactly one.")
pdf.bullet("The app uses WAL mode and a 30-second timeout to minimise this.")
pdf.h2("Roadmap generated, but no resources attached")
pdf.bullet("No API keys configured. Either add SERPAPI_API_KEY / AI_API_KEY, or run 'Refresh resources' after adding them.")
pdf.h2("AI provider returns 429 / 503")
pdf.bullet("Rate limit or demand: the app retries then falls back to curated content. Wait a minute and retry, or switch providers in .env.")
pdf.h2("'Unknown AI provider' on startup")
pdf.bullet("AI_PROVIDER must be one of: gemini, openai, nvidia, ollama.")
pdf.h2("Hints don't look right in dark mode")
pdf.bullet("Hint text exists to demo placeholders; the app ships both light and dark palettes and follows your system preference.")

# ---------------- 15. Support ----------------
pdf.add_page()
pdf.h1(15, "Getting support")
pdf.body("For help, share: the exact page, the error message, and the relevant .env keys you set (without revealing the actual key values).")
pdf.bullet("Report issues at the project repository.")
pdf.bullet("Mention the Django version (6.1), your Python version, and whether you use SQLite or PostgreSQL.")
pdf.body("Enjoy your career journey - CareerPath AI's job is to make it easier to keep moving.")

pdf.output(OUT)
print("Wrote", OUT, f"({pdf.page_no()} pages)")