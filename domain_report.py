import argparse
import re
import time as _time
from datetime import date, timedelta, datetime
from socket import socket
import pprint

# Google deps - https://developers.google.com/admin-sdk/reports/v1/api-lib/python
import httplib2
import oauth2client.client
from apiclient import discovery, errors

parser = argparse.ArgumentParser(description='Get daily domain reports from Google Admin SDK Reports API. Defaults to fetching the most recent report and printing it to stdout.')
parser.add_argument('-o', '--output', nargs='+', help='Valid outputs are stdout and graphite. (Default: stdout)', default='stdout')
optgroup = parser.add_mutually_exclusive_group()
optgroup.add_argument('--last', action='store_true', help='Fetch the most recent report available. (Default.)')
optgroup.add_argument('--all', action='store_true', help='Attempt to automatically determine date range of all available reports and fetch them.')
optgroup.add_argument('--daterange', nargs=2, help='Space-separated beginning and end dates for reports in YYYY-MM-DD format.')
args = parser.parse_args()

# See gapps_settings.default.py for example settings
import gapps_settings

pp = pprint.PrettyPrinter()

# Read .p12 file, use it to authorize HTTP requests
f = file(gapps_settings.serviceacct_p12, 'rb')
serviceacct_key = f.read()
f.close()
credentials = oauth2client.client.SignedJwtAssertionCredentials(
        gapps_settings.serviceacct_email,
        serviceacct_key,
        scope = [
          'https://www.googleapis.com/auth/admin.reports.usage.readonly',
          'https://www.googleapis.com/auth/admin.reports.audit.readonly',
        ],
        sub = gapps_settings.admin_email)
http = httplib2.Http()
http = credentials.authorize(http)
 
# Build a service object for interacting with the API with authorized http object
reports = discovery.build('admin', 'reports_v1', http=http)

if args.range:
    earliest_report_date = args.daterange[0]
    latest_report_date = args.daterange[1]

# Attempt to automatically determine the most recent day for which a report is available.
# Request a report for a day we know Google won't have (today), then catch and parse the
# exception which tells us the most recent day they _do_ have a report for in ISO8601
# (YYYY-MM-DD). Do the same thing with an old date to determine how far back we can go.
try:
    events = reports.customerUsageReports().get(date=date.today().strftime("%Y-%m-%d")).execute()
except errors.HttpError, e:
    match = re.search(r'Data for dates later than (?P<latest_report_date>\d{4}-\d{2}-\d{2}) is not yet available', e.content)
    if match is not None:
        latest_report_date = match.group('latest_report_date')
except Exception:
    print "Something went wrong attempting to get the latest report date from Google"
try:
    events = reports.customerUsageReports().get(date="1970-01-01").execute()
except errors.HttpError, e:
    match = re.search(r'Start date can not be earlier than (?P<earliest_report_date>\d{4}-\d{2}-\d{2})', e.content)
    if match is not None:
        earliest_report_date = match.group('earliest_report_date')
except Exception:
    print "Something went wrong attempting to get the earliest report date from Google"

start = datetime.strptime(earliest_report_date, '%Y-%m-%d')
end = datetime.strptime(latest_report_date, '%Y-%m-%d')
# Build list of ISO8601 dates of reports to query between (including) start and end.
dates = [(start + timedelta(days=day)).strftime('%Y-%m-%d') for day in range((end - start).days + 1)]

for date in dates:
    req = reports.customerUsageReports().get(date=date)
    events = req.execute()
    try:
        for report in events['usageReports']:
            report_ts = _time.mktime(datetime.strptime(date, '%Y-%m-%d').timetuple())
            output = '\n'.join(['%s.%s %s %d' % (gapps_settings.graphite_prefix, metric['name'].replace(':', '.'), metric['intValue'], report_ts) for metric in report['parameters']])
    except KeyError:
        print "KeyError, must be missing something!"
    print output

#start = date.today()
#end = date.today()

#sock = socket()
#try:
#    sock.connect( (settings.carbon_server, settings.carbon_port) )
#except:
#    print "Couldn't connect to %(server)s on port %(port)d, is carbon-agent.py running?" % { 'server':settings.carbon_server, 'port':settings.carbon_port }
#sys.exit(1)
#message = '\n'.join(lines) + '\n' #all lines must end in a newline
#sock.sendall(message)

#try:
#    events = req.execute()
#except errors.HttpError, e:
#    print e, e.content
#pp.pprint(events)
