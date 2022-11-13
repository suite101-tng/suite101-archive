from __future__ import division
import json
import datetime, time
from dateutil import parser
from django.core.management.base import BaseCommand
from stats.tasks import process_stats_inbox
from stats.sets import StatsFailedEventList

class Command(BaseCommand):
    help = 'usage: python manage.py reprocess_failed_stats_events <start> <finish>'

    def handle(self, *args, **options):
        now = time.time()
        raw_list = StatsFailedEventList().get_list()
        print('raw list: %s' % raw_list)
        if not raw_list:
            return

        events = []
        try:
            lower_limit = datetime.datetime.strptime(args[0], "%Y-%m-%d").date()
            upper_limit = datetime.datetime.strptime(args[1], "%Y-%m-%d").date()
        except:
            print('did not get a date range - process all')
            lower_limit = datetime.datetime.strptime("1975-01-01", "%Y-%m-%d").date()
            upper_limit = datetime.datetime.strptime("2700-01-01", "%Y-%m-%d").date()

        for rl in raw_list:
            try:
                item = json.loads(rl)
            except:
                print('something wrong with %s' % rl)
                continue
            try:
                date = datetime.datetime.strptime(item['date'], "%Y-%m-%d").date()
                if date > lower_limit and date < upper_limit:
                    print('date (%s) is between %s and %s - delete' % (date, lower_limit, upper_limit))
                    events.append(rl)
            except Exception as e:
                print('failed to append events: %s' % e)

        if not events:
            return

        try:
            process_stats_inbox(reprocess=True, reprocess_events=events)
            StatsFailedEventList().delete()
        except Exception as e:
            print(e)
