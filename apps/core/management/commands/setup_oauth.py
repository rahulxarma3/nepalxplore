"""
python manage.py setup_oauth

Prints step-by-step instructions for wiring Google OAuth.
Run this once after your first deploy.
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = "Configure Google OAuth site + print setup guide"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            default="localhost:8000",
            help="Your site domain (e.g. nepaxplore.up.railway.app)",
        )
        parser.add_argument(
            "--name",
            type=str,
            default="NepaXplore",
            help="Your site display name",
        )

    def handle(self, *args, **options):
        domain = options["domain"]
        name = options["name"]

        # Update the default django.contrib.sites Site entry
        site, created = Site.objects.update_or_create(
            id=1,
            defaults={"domain": domain, "name": name},
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Site: {domain} ({name})"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("GOOGLE OAUTH SETUP GUIDE"))
        self.stdout.write("=" * 60)

        self.stdout.write("""
STEP 1 — Google Cloud Console
──────────────────────────────
1. Go to https://console.cloud.google.com/
2. Create a new project called "NepaXplore"
3. APIs & Services → OAuth consent screen
   - User type: External
   - App name: NepaXplore
   - Support email: your email
   - Authorized domain: """ + domain.split(":")[0] + """
4. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
   - Application type: Web application
   - Name: NepaXplore Web
   - Authorized redirect URIs:
     http://localhost:8000/accounts/google/login/callback/   ← local dev
     https://""" + domain + """/accounts/google/login/callback/   ← production

STEP 2 — Add credentials to .env
──────────────────────────────────
GOOGLE_CLIENT_ID=<paste Client ID here>
GOOGLE_CLIENT_SECRET=<paste Client Secret here>

STEP 3 — Add Social App in Django admin
────────────────────────────────────────
1. Go to /admin/socialaccount/socialapp/add/
2. Provider: Google
3. Name: Google
4. Client id: <same as GOOGLE_CLIENT_ID>
5. Secret key: <same as GOOGLE_CLIENT_SECRET>
6. Sites: move """ + domain + """ to "Chosen sites"
7. Save

STEP 4 — Test it
─────────────────
Visit /accounts/login/ and click "Continue with Google"
""")

        self.stdout.write(self.style.SUCCESS("✅ Site configured. Complete steps above to finish OAuth setup."))
