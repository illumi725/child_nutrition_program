# Current application version.
# Update this string before pushing a new release tag to GitHub.
import sys

APP_VERSION = "v1.1.3"
APP_RELEASE_DATE = "May 19, 2026"

# Frozen PyInstaller builds are treated as production (no auth debug log).
IS_PRODUCTION_BUILD = getattr(sys, "frozen", False)
