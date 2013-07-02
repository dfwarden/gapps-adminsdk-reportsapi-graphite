Google Apps Admin SDK Reports API -> Graphite
============================

Google has deprecated the Google Apps (gapps) Reporting API (https://developers.google.com/google-apps/reporting/)
in favor of the new Admin SDK Reports API (https://developers.google.com/admin-sdk/reports/). This queries
that API for daily domain reports and sends those metrics to a graphite host.

For info on the reported metrics, see: https://developers.google.com/admin-sdk/reports/v1/reference/usage-ref-appendix-a/users

# Setup

1. Sign in to Google's API Console (https://code.google.com/apis/console/) with a gapps admin account.
2. Create a new "project".
3. In "Services", click the switch to enable the "Admin SDK".
4. In "API Access", click "Create an OAuth 2.0 client ID".
6. Enter a Product name and click next.
5. Select "Service account" and click "Create client ID".
6. Click "Download private key" and save that file somewhere that python will be able to read it.
7. In your gapps admin dashboard, go to Advanced Tools > Manage third party OAuth Client access
8. Paste the "Client ID" of the service account that was created in the API Console in the "Client Name" field.
9. Enter the scopes (comma separated) for the Reports API (found here: https://developers.google.com/admin-sdk/reports/v1/guides/authorizing) in the "One or More API Scopes" field and click Authorize.
10. Copy gapps\_settings.default.py to gapps\_settings.py and edit to your environment.

# Running

domain\_report.py will, by default, fetch the most recent report and send it to graphite without printing anything.

Use domain\_report.py --all to backfill all available reports into graphite or --daterange to fill a specific (inclusive) range.

Determining the most recent or earliest available report relies on parsing text from an exception defined in the Python
library for interacting with the Admin SDK. Google could easily break this.
