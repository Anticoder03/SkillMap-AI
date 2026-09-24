# -*- coding: utf-8 -*-
"""Generate docs/CareerPath_AI_Presentation.pptx

Usage:  python docs/generate_presentation.py
Requires:  pip install -r requirements-docs.txt
"""
from __future__ import annotations

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "CareerPath_AI_Presentation.pptx")

# Brand palette
INDIGO = RGBColor(0x4F, 0x46, 0xE5)
INDIGO_DARK = RGBColor(0x37, 0x30, 0xA3)
VIOLET = RGBColor(0x7C, 0x3A, 0xED)
SLATE = RGBColor(0x33, 0x41, 0x55)
SLATE_LIGHT = RGBColor(0x64, 0x74, 0x8B)
BG = RGBColor(0xF8, 0xF9, 0xFD)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT = RGBColor(0xEE, 0xF2, 0xFF)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = prs.slide_width, prs.slide_height


def add_rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    sp = slide.shapes.add_shape(shape, x, y, w, h)
    sp.fill.solid()
    sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1)
    sp.shadow.inherit = False
    return sp


def add_text(slide, x, y, w, h, text, size=18, color=SLATE, bold=False,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    r = p.runs[0]
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.name = "Calibri"
    return tb


def new_slide():
    slide = prs.slides.add_slide(BLANK)
    add_rect(slide, 0, 0, SW, SH, BG)
    return slide


def header(slide, kicker, title):
    add_rect(slide, 0, 0, Inches(0.24), SH, INDIGO)
    add_text(slide, Inches(0.75), Inches(0.45), Inches(11), Inches(0.4),
             kicker.upper(), size=13, color=SLATE_LIGHT, bold=True)
    add_text(slide, Inches(0.72), Inches(0.82), Inches(12), Inches(0.9),
             title, size=32, color=INDIGO_DARK, bold=True)
    add_rect(slide, Inches(0.75), Inches(1.62), Inches(1.6), Pt(3.2), VIOLET)


def bullets(slide, items, x=Inches(0.85), y=Inches(2.0), w=Inches(11.6),
            h=Inches(4.6), size=17, gap=14):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (lead, rest) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        r0 = p.add_run()
        r0.text = "  " + lead + "  "
        r0.font.size = Pt(size)
        r0.font.color.rgb = INDIGO
        r0.font.bold = True
        r1 = p.add_run()
        r1.text = rest
        r1.font.size = Pt(size)
        r1.font.color.rgb = SLATE
        r1.font.name = "Calibri"
    return tb


def card(slide, x, y, w, h, icon, title, body):
    add_rect(slide, x, y, w, h, WHITE, SOFT, MSO_SHAPE.ROUNDED_RECTANGLE)
    add_rect(slide, x, y, Inches(0.09), h, INDIGO, shape=MSO_SHAPE.RECTANGLE)
    add_text(slide, x + Inches(0.3), y + Inches(0.25), w - Inches(0.6), Inches(0.4),
             icon, size=15, color=INDIGO)
    add_text(slide, x + Inches(0.3), y + Inches(0.62), w - Inches(0.6), Inches(0.6),
             title, size=19, color=INDIGO_DARK, bold=True)
    add_text(slide, x + Inches(0.3), y + Inches(1.3), w - Inches(0.6), h - Inches(1.5),
             body, size=14.5, color=SLATE)


def title_slide():
    s = new_slide()
    add_rect(s, 0, 0, SW, SH, INDIGO)
    add_rect(s, Inches(11.5), Inches(-1.5), Inches(5), Inches(5),
             INDIGO_DARK, shape=MSO_SHAPE.OVAL)
    add_rect(s, Inches(10.2), Inches(5.6), Inches(4.2), Inches(4.2),
             VIOLET, shape=MSO_SHAPE.OVAL)
    add_text(s, Inches(0.9), Inches(2.0), Inches(10), Inches(0.5),
             "HAVE A LOOK AT THE FUTURE OF CAREER GUIDANCE", size=15,
             color=RGBColor(0xC7, 0xD2, 0xFE), bold=True)
    add_text(s, Inches(0.9), Inches(2.4), Inches(11), Inches(1.6),
             "CareerPath AI", size=66, color=WHITE, bold=True)
    add_text(s, Inches(0.95), Inches(3.7), Inches(11), Inches(0.6),
             "AI-Powered Career Assessment, Recommendations, and Learning Roadmaps",
             size=22, color=RGBColor(0xE0, 0xE7, 0xFF))
    add_text(s, Inches(0.95), Inches(6.1), Inches(11), Inches(0.5),
             "Built with Django  •  Gemini / OpenAI / NVIDIA NIM / Ollama  •  SerpAPI live resources",
             size=15, color=RGBColor(0xC7, 0xD2, 0xFE))


def problem_slide():
    s = new_slide()
    header(s, "The Problem", "Choosing a career today is overwhelming")
    bullets(s, [
        ("Confusing.", "Hundreds of resources, no guided order — beginners don't know where to start."),
        ("Generic advice.", "One-size-fits-all articles ignore your skills, interests, and education."),
        ("Outdated links.", "Static 'best resources' lists rot fast; real, current material is hard to find."),
        ("No feedback loop.", "Nobody tracks your progress or adjusts the path as you grow."),
    ])
    card(s, Inches(0.85), Inches(4.55), Inches(5.7), Inches(2.1), "v1",
         "Daily dilemma", "“I like tech and maths — should I do ML, backend, or something else?”")
    card(s, Inches(6.8), Inches(4.55), Inches(5.7), Inches(2.1), "v2",
         "And once chosen", "“There is a 6-month roadmap on YouTube — but is it the right one for me?”")


def solution_slide():
    s = new_slide()
    header(s, "Our solution", "A personal career co-pilot")
    bullets(s, [
        ("One guided assessment.", "Answer ~20 short questions on skills, education, and interests."),
        ("Data-driven matches.", "A transparent scoring engine ranks careers by interest, skill, education, and experience fit."),
        ("Its own roadmap generator.", "Custom learning path with phases, tasks, live tutorials, and YouTube videos per step."),
        ("Live resources, always fresh.", "Google + YouTube searched in real time (SerpAPI), with AI and curated fallbacks."),
    ])


def features_slide():
    s = new_slide()
    header(s, "Key features", "Everything in one small app")
    positions = [
        (Inches(0.85), Inches(2.0)),
        (Inches(6.75), Inches(2.0)),
        (Inches(0.85), Inches(4.55)),
        (Inches(6.75), Inches(4.55)),
    ]
    cards = [
        ("f1", "Career assessment", "Skill/interest/education quizzes with live progress bar, saved per answer."),
        ("f2", "Smart recommendations", "Top-3 careers with match %, reasons, skill gaps, and prerequisites."),
        ("f3", "Living roadmaps", "Auto-generated phases & tasks; check boxes; 0→100% progress ring; per-task resources."),
        ("f4", "Privacy-first accounts", "Login, profile readiness score, skills & interests editors, dark mode, admin panel."),
    ]
    for (x, y), (icon, t, b) in zip(positions, cards):
        card(s, x, y, Inches(5.7), Inches(2.15), icon, t, b)


def pipeline_slide():
    s = new_slide()
    header(s, "How it works", "From answers to a living roadmap")
    steps = [
        ("1", "Assessment", "Skills, education, experience, interests", Inches(0.85)),
        ("2", "Match engine", "Weighted scoring → ranked careers", Inches(3.5)),
        ("3", "Roadmap AI", "Provider builds phases & tasks", Inches(6.15)),
        ("4", "Resource tier", "Live search → AI → curated", Inches(8.8)),
        ("5", "Your roadmap", "Track, update, repeat", Inches(11.45)),
    ]
    for num, title, body, x in steps:
        add_rect(s, x, Inches(2.5), Inches(1.95), Inches(1.95), INDIGO, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        add_text(s, x + Inches(0.38), Inches(2.9), Inches(1.2), Inches(0.9), num,
                 size=40, color=WHITE, bold=True)
        add_text(s, x, Inches(4.62), Inches(1.95), Inches(1.4), title + "\n" + body,
                 size=13.5, color=SLATE, align=PP_ALIGN.CENTER)
    add_text(s, Inches(0.85), Inches(6.6), Inches(11.6), Inches(0.5),
             "AI failures degrade gracefully: live SerpAPI search keeps resources flowing even if the model is down or rate-limited.",
             size=13, color=SLATE_LIGHT)


def architecture_slide():
    s = new_slide()
    header(s, "Architecture", "Three clean layers")
    card(s, Inches(0.85), Inches(2.0), Inches(3.7), Inches(4.4), "a1", "Presentation",
         "Tailwind UI templates (landing, auth, assessment, recommendations, roadmaps, careers, admin). Theme toggle: light / dark.")
    card(s, Inches(4.85), Inches(2.0), Inches(3.7), Inches(4.4), "a2", "Application",
         "Django apps: accounts, assessment, recommendations, roadmap, careers. Signals auto-create profiles; views keep AI optional.")
    card(s, Inches(8.85), Inches(2.0), Inches(3.7), Inches(4.4), "a3", "Data + AI",
         "SQLite/PostgreSQL models; provider registry (Gemini, OpenAI, NVIDIA NIM, Ollama); SerpAPI search client; curation seed data.")


def tech_slide():
    s = new_slide()
    header(s, "Tech stack", "Boring, dependable, easy to run")
    rows = [
        ("Backend", "Django 6.1, Django REST framework"),
        ("Database", "SQLite by default, PostgreSQL when DATABASE_NAME is set"),
        ("AI providers", "Gemini 3.6 Flash, OpenAI, NVIDIA NIM (Nemotron), Ollama — all behind one OpenAI-compatible interface"),
        ("Live search", "SerpAPI Google + YouTube engines"),
        ("Frontend", "Tailwind CSS, Font Awesome, Chart.js"),
        ("Quality", "200+ automated tests; hermetic network calls; SQLite WAL mode"),
    ]
    y = Inches(2.1)
    for k, v in rows:
        add_rect(s, Inches(0.85), y, Inches(2.6), Inches(0.72), WHITE, SOFT, MSO_SHAPE.ROUNDED_RECTANGLE)
        add_text(s, Inches(0.98), y + Inches(0.14), Inches(2.35), Inches(0.5), k,
                 size=15, color=INDIGO_DARK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, Inches(3.7), y + Inches(0.14), Inches(8.7), Inches(0.5), v,
                 size=15, color=SLATE, anchor=MSO_ANCHOR.MIDDLE)
        y += Inches(0.88)


def ai_tier_slide():
    s = new_slide()
    header(s, "Resource engine", "Three fallback tiers keep links alive")
    card(s, Inches(0.85), Inches(2.0), Inches(5.7), Inches(2.3), "t1", "Tier 1 — Live search",
         "SerpAPI queries Google then YouTube for each task. Best, current links, deduped queries, capped budget.")
    card(s, Inches(6.8), Inches(2.0), Inches(5.7), Inches(2.3), "t2", "Tier 2 — AI suggested",
         "Prompted model returns a curated resource + optional video per task, URL-sanitized before saving.")
    card(s, Inches(0.85), Inches(4.6), Inches(5.7), Inches(2.3), "t3", "Tier 3 — Curated seed data",
         "Ship-with-the-app quality links used whenever network/AI is unavailable — every task still gets a resource.")
    card(s, Inches(6.8), Inches(4.6), Inches(5.7), Inches(2.3), "t4", "Videos too",
         "Every tier can attach a YouTube link + title shown inline on the roadmap detail page.")


def demo_slide():
    s = new_slide()
    header(s, "Experience", "A 90-second walkthrough")
    bullets(s, [
        ("Sign up / sign in.", "Pre-styled forms, placeholders, autocomplete, readiness meter on your profile."),
        ("Take the assessment.", "~20 questions, live progress, per-answer saves — pick up where you left off."),
        ("Review recommendations.", "Top careers with match %, reasons, skill gaps, and prerequisites."),
        ("Generate a roadmap.", "One click → phases & tasks stream in from the AI provider."),
        ("Hit refresh resources.", "SerpAPI fills every task with a real article + YouTube video."),
        ("Track progress.", "Mark tasks complete; progress ring drives % on your dashboard and career pages."),
    ])


def tests_slide():
    s = new_slide()
    header(s, "Quality", "Trust, verified automatically")
    bullets(s, [
        ("197+ test cases", "accounts, assessment, recommendations, roadmap, careers, ai_engine — all green."),
        ("Hermetic test data", "Real API keys are zeroed under the test runner (settings guard); tests opt back in with overrides."),
        ("Database in WAL mode", "No 'database is locked' stalls; long AI calls run outside DB transactions."),
        ("Graceful degradation", "Provider down? Rate-limited? Search fails? The app falls back and still delivers."),
    ])
    add_text(s, Inches(0.85), Inches(6.1), Inches(11.6), Inches(0.6),
             "Verified live with real keys: 11/11 tasks received both an article and a YouTube video from live search.",
             size=14, color=INDIGO_DARK, bold=True)


def future_slide():
    s = new_slide()
    header(s, "What's next", "Room to grow")
    bullets(s, [
        ("More AI providers", "Plug in any OpenAI-compatible endpoint — NVIDIA NIM / Nemotron, local Llama, Mistral."),
        ("Progress analytics", "Charts for time-to-complete, streak tracking, and re-scoring after milestones."),
        ("Community paths", "Shared, rateable roadmaps with mentor feedback loops."),
        ("Mobile-ready", "PWA wrapper and push reminders for daily goals."),
    ])


def closing_slide():
    s = new_slide()
    add_rect(s, 0, 0, SW, SH, INDIGO)
    add_rect(s, Inches(-1.6), Inches(5.2), Inches(4.6), Inches(4.6), INDIGO_DARK, shape=MSO_SHAPE.OVAL)
    add_text(s, Inches(0.9), Inches(2.4), Inches(11.5), Inches(1.2), "Thank you",
             size=60, color=WHITE, bold=True)
    add_text(s, Inches(0.95), Inches(3.7), Inches(11.5), Inches(0.6),
             "Every learner deserves a path that is personal and always up to date.",
             size=20, color=RGBColor(0xE0, 0xE7, 0xFF))
    add_text(s, Inches(0.95), Inches(6.3), Inches(11.5), Inches(0.5),
             "CareerPath AI  •  Django 6.1  •  AI + live search, serious about reliability",
             size=15, color=RGBColor(0xC7, 0xD2, 0xFE))


for fn in (title_slide, problem_slide, solution_slide, features_slide, pipeline_slide,
           architecture_slide, tech_slide, ai_tier_slide, demo_slide, tests_slide,
           future_slide, closing_slide):
    fn()

prs.save(OUT)
print("Wrote", OUT, f"({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")