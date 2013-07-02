import argparse
import re
import time as _time
from datetime import date, timedelta, datetime
from socket import socket
import pprint

# Google deps - https://developers.google.com/admin-sdk/reports/v1/api-lib/python
import httplib2
import oauth2client.client
from apiclient import discovery, errors as apiclient_errors

parser = argparse.ArgumentParser(description='Get daily domain reports from Google Admin SDK Reports API. Defaults to fetching the most recent report and sending it to your graphite host defined in settings.py.')
parser.add_argument('-v', '--verbose', action='store_true', help='Print graphite lines to stdout.')
optgroup = parser.add_mutually_exclusive_group()
optgroup.add_argument('--last', action='store_true', help='Fetch the most recent report available. (Default.)')
optgroup.add_argument('--all', action='store_true', help='Attempt to automatically determine date range of all available reports and fetch them.')
optgroup.add_argument('--daterange', nargs=2, help='Space-separated beginning and end dates for reports in iso8601 YYYY-MM-DD format.')
args = parser.parse_args()

# See settings.default.py for example settings
import settings

pp = pprint.PrettyPrinter()

# Read .p12 file, use it to authorize HTTP requests to Google API.
f = file(settings.serviceacct_p12, 'rb')
serviceacct_key = f.read()
f.close()
credentials = oauth2client.client.SignedJwtAssertionCredentials(
        settings.serviceacct_email,
        serviceacct_key,
        scope = [
          'https://www.googleapis.com/auth/admin.reports.usage.readonly',
          'https://www.googleapis.com/auth/admin.reports.audit.readonly',
        ],
        sub = settings.admin_email)
http = httplib2.Http()
http = credentials.authorize(http)
reports = discovery.build('admin', 'reports_v1', http=http)

# Determine inclusive start and stop dates for reports.
earliest_report_date = None
latest_report_date = None
if args.daterange:
    earliest_report_date = args.daterange[0]
    latest_report_date = args.daterange[1]
else:
    # Attempt to automatically determine the most recent day for which a report is available.
    # Request a report for a day we know Google won't have (today), then catch and parse the
    # exception which tells us the most recent day they _do_ have a report for in ISO8601
    # (YYYY-MM-DD). Do the same thing with an old date to determine how far back we can go if
    # the user requests all reports.
    try:
        events = reports.customerUsageReports().get(date=date.today().strftime("%Y-%m-%d")).execute()
    except apiclient_errors.HttpError, e:
        match = re.search(r'Data for dates later than (?P<latest_report_date>\d{4}-\d{2}-\d{2}) is not yet available', e.content)
        if match is not None:
            latest_report_date = match.group('latest_report_date')
    if args.all:
        try:
            events = reports.customerUsageReports().get(date="1970-01-01").execute()
        except apiclient_errors.HttpError, e:
            match = re.search(r'Start date can not be earlier than (?P<earliest_report_date>\d{4}-\d{2}-\d{2})', e.content)
            if match is not None:
                earliest_report_date = match.group('earliest_report_date')
    else:
        # Default, request only latest report
        earliest_report_date = latest_report_date

# earliest_report_date and latest_report_date must both be valid iso8601 dates.
iso8601_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
if not re.match(iso8601_pattern, earliest_report_date) or not re.match(iso8601_pattern, latest_report_date):
    raise ValueError('earliest_report_date (%s) or latest_report_date (%s) is not a valid iso8601 date.' % (earliest_report_date, latest_report_date))

# Build list of iso8601 dates of reports to query between (including) start and end
start = datetime.strptime(earliest_report_date, '%Y-%m-%d')
end = datetime.strptime(latest_report_date, '%Y-%m-%d')
dates = [(start + timedelta(days=day)).strftime('%Y-%m-%d') for day in range((end - start).days + 1)]

# Generate reports for list of dates
for date in dates:
    output = None
    req = reports.customerUsageReports().get(date=date)
    try:
        events = req.execute()
    except apiclient_errors.HttpError, e:
        print 'Failed to fetch report for %s:' % (date), e
        continue
    try:
        for report in events['usageReports']:
            report_ts = _time.mktime(datetime.strptime(date, '%Y-%m-%d').timetuple())
            output = '\n'.join(['%s.%s %s %d' % (settings.graphite_prefix, metric['name'].replace(':', '.'), metric['intValue'], report_ts) for metric in report['parameters']])
    except KeyError:
        print 'Failed to find expected field in report for %s.' % (date)
        continue
    if args.verbose:
        print output
    sock = socket()
    try:
        sock.connect( (settings.graphite_host, settings.graphite_port) )
    except:
        print "Couldn't connect to %(server)s on port %(port)d, is carbon-agent.py running?" % { 'server':settings.graphite_host, 'port':settings.graphite_port }
        continue
    sock.sendall(output + '\n')
    sock.close()
