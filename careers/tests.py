"""Tests for the careers knowledge base: models and browse views."""
from django.test import TestCase
from django.urls import reverse

from assessment.models import Interest, Skill
from careers.models import Career, CareerInterest, CareerPrerequisite, CareerSkill


class CareerModelTests(TestCase):
    def test_slug_auto_generated(self):
        career = Career.objects.create(title="Data Scientist")
        self.assertEqual(career.slug, "data-scientist")

    def test_duplicate_slug_is_uniquified(self):
        Career.objects.create(title="Software Engineer")
        # Same slug after slugification (punctuation is stripped).
        career = Career.objects.create(title="Software Engineer!")
        self.assertNotEqual(career.slug, "software-engineer")
        self.assertTrue(career.slug.startswith("software-engineer"))

    def test_career_ordering_by_title(self):
        Career.objects.create(title="Zebra Keeper", category="other")
        Career.objects.create(title="Alpha Analyst", category="tech")
        titles = [c.title for c in Career.objects.all()]
        self.assertEqual(titles, sorted(titles))

    def test_related_skill_and_interest_links(self):
        career = Career.objects.create(title="ML Engineer", required_education="masters")
        skill = Skill.objects.create(name="TensorFlow", category="ml")
        interest = Interest.objects.create(name="AI/ML", description="Machine learning")
        CareerSkill.objects.create(career=career, skill=skill, importance=10, required_level=4)
        CareerInterest.objects.create(career=career, interest=interest, weight=8)

        self.assertEqual(career.career_skills.count(), 1)
        self.assertEqual(career.career_interests.count(), 1)
        self.assertIn(career, list(skill.careers.all()))

    def test_prerequisites_ordered(self):
        career = Career.objects.create(title="Physicist")
        CareerPrerequisite.objects.create(career=career, description="Later", priority=2)
        CareerPrerequisite.objects.create(career=career, description="First", priority=1)
        prereqs = list(career.prerequisites.all())
        self.assertEqual(prereqs[0].description, "First")

    def test_label_properties(self):
        career = Career.objects.create(
            title="Doctor", required_education="masters", difficulty="advanced", demand_level="high"
        )
        self.assertEqual(career.education_label, "Master's Degree")
        self.assertEqual(career.difficulty_label, "Advanced (3-7 years)")
        self.assertEqual(career.demand_label, "High")

    def test_unique_title_enforced(self):
        Career.objects.create(title="Designer")
        with self.assertRaises(Exception):
            Career.objects.create(title="Designer")


class CareerViewTests(TestCase):
    def setUp(self):
        self.python = Skill.objects.create(name="Python", category="programming")
        self.dev = Career.objects.create(
            title="Python Developer", category="Software", description="Write Python apps"
        )
        CareerSkill.objects.create(career=self.dev, skill=self.python, importance=8, required_level=3)
        self.analyst = Career.objects.create(
            title="Data Analyst", category="Data", description="Analyze data with Python"
        )
        CareerSkill.objects.create(career=self.analyst, skill=self.python, importance=5, required_level=2)

    def test_career_list_renders_all(self):
        response = self.client.get(reverse("careers:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Developer")
        self.assertContains(response, "Data Analyst")

    def test_career_list_search(self):
        response = self.client.get(reverse("careers:list"), {"q": "developer"})
        self.assertContains(response, "Python Developer")
        self.assertNotContains(response, "Data Analyst")

    def test_career_list_search_matches_skill_name(self):
        response = self.client.get(reverse("careers:list"), {"q": "python"})
        self.assertContains(response, "Python Developer")
        self.assertContains(response, "Data Analyst")

    def test_career_list_category_filter(self):
        response = self.client.get(reverse("careers:list"), {"category": "Data"})
        self.assertNotContains(response, "Python Developer")
        self.assertContains(response, "Data Analyst")

    def test_career_detail_renders(self):
        response = self.client.get(reverse("careers:detail", args=[self.dev.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Developer")

    def test_career_detail_404_for_unknown_slug(self):
        response = self.client.get(reverse("careers:detail", args=["no-such-career"]))
        self.assertEqual(response.status_code, 404)