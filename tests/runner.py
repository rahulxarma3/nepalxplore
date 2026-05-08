"""
tests/runner.py

Custom test runner with useful configuration.
Usage:
  python manage.py test tests                        # all tests
  python manage.py test tests.test_models            # one file
  python manage.py test tests.test_models.VideoModelTest  # one class
  python manage.py test tests.test_models.VideoModelTest.test_duration_display_formats_correctly  # one test
  python manage.py test tests --verbosity=2          # verbose output
  python manage.py test tests --keepdb               # reuse test DB (faster reruns)
  python manage.py test tests --failfast             # stop on first failure

Coverage (install coverage first: pip install coverage):
  coverage run manage.py test tests
  coverage report
  coverage html  # opens htmlcov/index.html
"""
