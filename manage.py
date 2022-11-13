# thanks to http://www.wellfireinteractive.com/blog/easier-12-factor-django/
#!/usr/bin/env python
import os
import sys

from env import read_env


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

    from django.core.management import execute_from_command_line

    read_env()
    execute_from_command_line(sys.argv)
