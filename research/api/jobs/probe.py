import json, sys, urllib.request, concurrent.futures as cf
OUT = sys.argv[1]
# company slug -> category; each slug is tried on all three boards
CATS = {
 "payments": """stripe adyen plaid ramp brex mercury marqeta checkout checkoutcom affirm chime block square squareup paypal
  wise transferwise revolut robinhood coinbase sofi klarna gocardless moderntreasury increase lithic unit synctera column
  airwallex rapyd nium payoneer toast billcom navan gusto rippling deel remote carta chargebee recurly paddle orb metronome
  lago bolt finix dwolla alloy sardine persona socure current dave monzo n26 nubank flutterwave truelayer yapily mollie
  primer spreedly forter riskified stash acorns betterment wealthfront circle kraken gemini anchorage fireblocks alchemy
  ripple tipalti melio pipe airbase jeeves upgrade oportun mx treasuryprime bond highnote galileo imprint""",
 "devplatform": """twilio vercel netlify supabase postman kong temporal temporaltechnologies sentry launchdarkly segment algolia
  auth0 okta clerk workos retool airtable notion figma linear github gitlab mailgun resend svix zapier airbyte fivetran
  hashicorp render railway fly flyio neon neondatabase planetscale convex inngest stytch mux courier knock pagerduty asana
  dropbox atlassian hubspot intercom zendesk attentive openai anthropic replit sourcegraph posthog mixpanel amplitude heap
  braze iterable customerio apollo apollographql hasura prisma buildkite circleci""",
 "commerce": """shopify instacart doordash doordashusa airbnb lyft uber etsy faire whatnot poshmark stockx goat wayfair chewy
  thumbtack taskrabbit rover turo offerup mercari depop vinted bigcommerce commercetools saleor flexport shipbob gopuff
  grubhub deliveroo glovo booking hopper getyourguide squarespace wix fanatics seatgeek eventbrite opentable grammarly
  duolingo reddit discord pinterest""",
 "infra": """cloudflare datadog databricks snowflake confluent mongodb elastic cockroachlabs yugabyte redis grafanalabs
  honeycomb chronosphere clickhouse fastly digitalocean tailscale nvidia coreweave lambda crusoe modal scaleai materialize
  singlestore starburst dbtlabs harness pulumi teleport gravitational wiz snyk 1password samsara palantir anduril netflix
  spotify box nutanix""",
}
C = {}
for cat, s in CATS.items():
    for slug in s.split():
        C.setdefault(slug, cat)

def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "readcode-research/0.1"})
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read())
    except Exception:
        return None

def norm(board, d):
    out = []
    if board == "gh":
        for j in d.get("jobs", []):
            out.append({"title": j.get("title"), "location": (j.get("location") or {}).get("name"),
                        "departments": [x.get("name") for x in j.get("departments", [])],
                        "url": j.get("absolute_url"), "updated": j.get("updated_at"),
                        "content": j.get("content") or ""})
    elif board == "ashby":
        for j in d.get("jobs", []):
            out.append({"title": j.get("title"), "location": j.get("location"),
                        "departments": [j.get("department"), j.get("team")], "url": j.get("jobUrl"),
                        "updated": j.get("publishedAt"),
                        "content": j.get("descriptionPlain") or j.get("descriptionHtml") or ""})
    else:
        if not isinstance(d, list):
            return out
        for j in d:
            cats = j.get("categories") or {}
            lists = " ".join((l.get("text", "") + " " + l.get("content", "")) for l in j.get("lists", []))
            out.append({"title": j.get("text"), "location": cats.get("location"),
                        "departments": [cats.get("team"), cats.get("department")], "url": j.get("hostedUrl"),
                        "updated": j.get("createdAt"),
                        "content": (j.get("descriptionPlain") or "") + " " + lists + " " + (j.get("additionalPlain") or "")})
    return out

def probe(slug):
    res = []
    for board, url in [("gh", f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"),
                       ("ashby", f"https://api.ashbyhq.com/posting-api/job-board/{slug}"),
                       ("lever", f"https://api.lever.co/v0/postings/{slug}?mode=json")]:
        d = get(url)
        if d is None:
            continue
        jobs = norm(board, d)
        if jobs:
            res.append((board, jobs))
    return slug, res

found = {}
with cf.ThreadPoolExecutor(16) as ex:
    for slug, res in ex.map(probe, C):
        for board, jobs in res:
            found[f"{board}:{slug}"] = {"slug": slug, "board": board, "category": C[slug], "jobs": jobs}
        print(slug, [(b, len(j)) for b, j in res], flush=True)
json.dump(found, open(OUT, "w", encoding="utf-8"))
print("boards", len(found), "jobs", sum(len(v["jobs"]) for v in found.values()))
