import unittest

from django.test import TestCase
from django.test.utils import override_settings
from django.conf import settings
from wagtail.search.backends import get_search_backend
from wagtail.test.search import models


@override_settings(
    WAGTAILSEARCH_BACKENDS={
        "default": {
            "BACKEND": "wagtail.search.backends.elasticsearch7",
            "URLS": ["http://localhost:9200"],
            "INDEX": "wagtail",
        }
    }
)
class TestElasticsearchAccentSearch(TestCase):
    backend_path = "wagtail.search.backends.elasticsearch7"

    def setUp(self):
        for backend_name, backend_conf in settings.WAGTAILSEARCH_BACKENDS.items():
            if backend_conf["BACKEND"] == self.backend_path:
                self.backend = get_search_backend(backend_name)
                self.backend_name = backend_name
                break
        else:
            raise unittest.SkipTest(
                "No WAGTAILSEARCH_BACKENDS entry for the backend %s" % self.backend_path
            )

    def add_page(self, title):
        page = models.Book.objects.create(title=title)
        self.backend.add(page)
        self.backend.refresh_index()
        return page

    def assertSearch(self, query, expected_titles):
        results = self.backend.search(query, models.Book)
        result_titles = [r.title for r in results]
        self.assertEqual(result_titles, expected_titles)

    def test_accented_query_returns_result(self):
        self.add_page(title="Bäckerei Wagtail")
        self.assertSearch("Bäckerei", expected_titles=["Bäckerei Wagtail"])

    def test_non_accented_query_returns_accented_title(self):
        self.add_page(title="Bäckerei Wagtail")
        self.assertSearch("Backerei", expected_titles=["Bäckerei Wagtail"])

    def test_accented_query_returns_non_accented_title(self):
        self.add_page(title="Backerei Wagtail")
        self.assertSearch("Bäckerei", expected_titles=["Backerei Wagtail"])