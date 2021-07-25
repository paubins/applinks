import json

from sgqlc.operation import Operation
from sgqlc.endpoint.http import HTTPEndpoint
from urllib.parse import unquote, parse_qs
from twilio.rest import Client
from jinja2 import Environment, PackageLoader, FileSystemLoader, select_autoescape

import base64
import os
import uuid

GRAPHCMS_TOKEN = os.environ.get("GCMS_TOKEN", "")
GRAPHCMS_ENDPOINT = os.environ.get('GRAPHCMS_ENDPOINT', "")
DOMAIN = os.environ.get("DOMAIN", "binshare.co")

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER", "")

APP_ID_KEY = "appIDs[]"
BUNDLE_ID_KEY = "bundleIDs[]"
PATHS_KEY = "paths[]"
PATTERNS_KEY = "patterns[]"
COMMENTS_KEY = "comments[]"
EXCLUDE_KEY = "exclude[]"


SIMPLE_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta name="apple-itunes-app" content="app-id=1534710821, app-argument=myURL">

<title>Universal Link Test Site</title>

<body>
<a href="https://www.binshare.co/" target="_startover">Create a new AASA file</a><br/><br/>
<a href="/.well-known/apple-app-site-association" target="_new">Go to AASA file</a><br/><br/>
<a href="#" target="_new">Delete this AASA file</a><br/>
</body>
</html>
"""

def lambda_handler(event, context):
    # TODO implement
    print(event)
    print(context)
    
    main_path = event['path']
    method = event['httpMethod']
    domain = event['headers']['Host']
    print(main_path)
    print(domain)

    if method == 'POST':
        query = dict(parse_qs(event['body'], keep_blank_values=True))
        phone = query.get("phone")
        if phone:
            phone = phone[0]

        print(query)
        components = []
        for idx, path in enumerate(query[PATHS_KEY]):
            components += [{
                path : query[PATTERNS_KEY][idx],
                "comment" : query[COMMENTS_KEY][idx],
                "exclude" : query[EXCLUDE_KEY][idx] == '1'
            }]

        output = dict()
        app_ids = []
        for item in query[APP_ID_KEY]:
            app_ids += [f"{item}.{query[BUNDLE_ID_KEY][0]}"]

        output["applinks"] = {
            "details" : [{
                "appIDs" : app_ids,
                "components" : components
            }]
        }

        output_json = base64.b64encode(json.dumps(output, indent=2).encode()).decode('ascii')
        print(output_json)
        print(main_path)

        unique_domain = None
        final_domain = None

        if domain == "www.binshare.co":
            unique_domain = uuid.uuid4().hex[:6].lower()
            final_domain = f"{unique_domain}.{DOMAIN}"
        else:
            final_domain = domain

        q3 = """
        mutation {
          upsertConfig(
            where: { domain: "%s" }
            upsert: {
              create: { domain: "%s", content: "%s" }
              update: { domain: "%s", content: "%s" }
            }
          ) {
            id
          }
        }
        """ % (final_domain, final_domain, output_json, final_domain, output_json)
        headers = {'Authorization': f"Bearer {GRAPHCMS_TOKEN}"}
        endpoint = HTTPEndpoint(GRAPHCMS_ENDPOINT, headers)
        result = endpoint(query=q3)
        
        print(result)
        print(f"phone: {phone}")
        if phone:
            client = Client(ACCOUNT_SID, AUTH_TOKEN)

            message = client.messages.create(
                                          body=f"Univeral link created: https://{final_domain}/",
                                          from_=PHONE_NUMBER,
                                          to=f"+{phone}"
                                      )

            print(message.sid)

        return {
            "statusCode": 302,
            "headers": {
              "Location": f"https://{final_domain}/",
            }
        }

    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates"), encoding="utf8"))

    def split(x, idx):
        try:
            return x.split(".", 1)[idx]
        except Exception as e:
            return ""

    env.filters['getappid'] = lambda x: split(x, 0)
    env.filters['getbundleid'] = lambda x: split(x, 1)

    result = None
    result_json = None
    if domain != "www.binshare.co":
        q3 = """
        query {
          config(where: {domain: "%s"}) {
            content
          }
        }
        """ % (domain)

        headers = {'Authorization': f"Bearer {GRAPHCMS_TOKEN}"}
        endpoint = HTTPEndpoint(GRAPHCMS_ENDPOINT, headers)
        result = endpoint(query=q3)

        result_json = base64.b64decode(result["data"]["config"]["content"]).decode('ascii')

    if main_path == '/.well-known/apple-app-site-association':
        print(result)
        print(result_json)
        return {
            "statusCode": 200,
            "body": result_json
        }

    template = env.get_template("index.html")
    aasa_contents = dict()
    created = False
    if result_json:
        aasa_contents = json.loads(result_json)
        created = True
    else:
        aasa_contents = {"applinks" : {"details" : [{"appIDs" : [{"components" : []}]}]}}

    return {
        'statusCode': 200,
        'body': template.render(**aasa_contents, created=created, domain=domain),
        "headers": {
            'Content-Type': 'text/html'
        }
    }