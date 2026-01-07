import requests
from requests.auth import HTTPBasicAuth







def unquote(s):
    s = s.strip()
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in {"'", '"'} else s









class Jira():
    
    def __init__(self, jira_url, auth=None):
        self.jira_url = unquote(jira_url)
        if auth:
            self.auth(**auth)
        else:
            self.creds = auth

    
    #currently only basicauth
    def auth(self, **kwargs):
        assert "email" in kwargs and "api_token" in kwargs

        self.creds = HTTPBasicAuth(kwargs.get("email"), kwargs.get("api_token"))
        self.accountId = self.call("api/3/myself").get("accountId") #also involves auth check


    def call(self, resource, type="GET", params=None, payload=None):
        url =  f"{self.jira_url}/rest/{resource}"   
        headers = { "Accept": "application/json", "Content-Type": "application/json" }

        match type:
            case "GET":
                httpcall = requests.get
            case "POST":
                httpcall = requests.post
            case "PUT":
                httpcall = requests.put
            case "DELETE":
                httpcall = requests.delete
            case _:
                raise ValueError(f"Expected [GET, POST, PUT, DELETE], got {type}")


        if (response := httpcall(url, headers=headers, params=params, json=payload, auth=self.creds)).ok:
            return response.json()
            
        else:
            raise ConnectionError(response.status_code)
            

    def fetchServicedesks(self):
        projects = self.call("/rest/servicedeskapi/servicedesk").get("values", [])

        return [ {"id": x.get("id", None), "projectKey": x.get("projectKey", None), "projectName": x.get("projectName", None)} for x in projects if "servicedesk" in x.get("_links", {}).get("self", "") ]

    