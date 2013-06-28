import re
from datetime import date, timedelta
import pprint

# Google deps - https://developers.google.com/admin-sdk/reports/v1/api-lib/python
import httplib2
import oauth2client.client
from apiclient import discovery, errors

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

today = date.today()
latest_report_date = None
earliest_report_date = None

# Attempt to automatically determine the most recent day for which a report is available.
# Request a report for a day we know Google won't have (today), then catch and parse the
# exception which tells us the most recent day they _do_ have a report for in ISO8601
# (YYYY-MM-DD). Do the same thing with an old date to determine how far back we can go.
try:
    events = reports.customerUsageReports().get(date=today.strftime("%Y-%m-%d")).execute()
    pp.pprint(events)
except errors.HttpError, e:
    match = re.search(r'Data for dates later than (?P<latest_report_date>\d{4}-\d{2}-\d{2}) is not yet available', e.content)
    if match is not None:
        latest_report_date = match.group('latest_report_date')
except Exception:
    print "Something went wrong attempting to get the latest report date from Google"
#try:
#    events = reports.customerUsageReports().get(date="1970-01-01").execute()
#    pp.pprint(events)
#except errors.HttpError, e:
#    match = re.search(r'Start date can not be earlier than (?P<earliest_report_date>\d{4}-\d{2}-\d{2})', e.content)
#    if match is not None:
#        earliest_report_date = match.group('earliest_report_date')
#except Exception:
#    print "Something went wrong attempting to get the earliest report date from Google"


#events = service.activities().list(userKey="passwordadmin@geneseo.edu", applicationName="admin", eventName="CHANGE_PASSWORD", filters="USER_EMAIL==warden@geneseo.edu").execute()
#pp.pprint(events)
#events = service.activities().list(userKey="passwordadmin@geneseo.edu", applicationName="admin", eventName="CHANGE_PASSWORD", filters="USER_EMAIL==cdahl@geneseo.edu").execute()
#req = service.customerUsageReports().get(date="2013-06-25")
#events = req.execute()
#pp.pprint(events)
#events = service.userUsageReport().get(userKey="warden@geneseo.edu", date="2013-06-24").execute()
#pp.pprint(events)
#events = service.userUsageReport().get(userKey="warden@geneseo.edu", date="2013-06-25").execute()
#pp.pprint(events)
#report_date = date.today() - timedelta(days=3)
#print report_date
req = reports.customerUsageReports().get(date=latest_report_date)
events = req.execute()
pp.pprint(events)
#req = reports.customerUsageReports().get(date="2013-06-26")
#try:
#    events = req.execute()
#except errors.HttpError, e:
#    print e, e.content
#pp.pprint(events)
