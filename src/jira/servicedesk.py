from .jira import Jira

import re
from email_reply_parser import EmailReplyParser




def strip_jira_wiki_markup(text):
    # Remove code/pre/code blocks
    text = re.sub(r'\{code.*?\}(.*?)\{code\}', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\{noformat\}(.*?)\{noformat\}', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\{quote\}', '', text, flags=re.IGNORECASE)
    
    # Remove color, panel, etc.
    text = re.sub(r'\{color:[^}]+\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{panel:[^}]+\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{panel\}', '', text, flags=re.IGNORECASE)

    # Remove headings (# or h1. style)
    text = re.sub(r'^h[1-6]\.\s*', '', text, flags=re.MULTILINE)

    # Remove bold (*bold*), italic (_italic_)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)

    # Remove lists (- or * at line start)
    text = re.sub(r'^[\*\-]\s*', '', text, flags=re.MULTILINE)

    # Remove link markup [text|url]
    text = re.sub(r'\[([^\|\]]+)\|[^\]]+\]', r'\1', text)

    # Remove any remaining braces {stuff}
    text = re.sub(r'\{[^}]+\}', '', text)

    # Remove extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def unmailify(text):
    mail_contents = EmailReplyParser.read(text)
    
    return mail_contents.fragments[0].content


def subdict(d: dict, keys):
    assert isinstance(d, dict)
    #assert all((x in d.keys() for x in keys)) 

    return { k: d.get(k, None) for k in keys }


def unnest_items(d, keys=None):
    assert keys == None or isinstance(keys, list)
    result = []
    
    def recurse(val, keys=None):
        if isinstance(val, dict):
            for k, v in val.items():
                if keys == None or k in keys:
                    recurse(v, keys)
                    
        elif isinstance(val, list):
            for item in val:
                recurse(item, keys)
        else:
            result.append(val)
    
    recurse(d, keys)

    
    return result





class JiraServicedesk():

    def __init__(self, jira: Jira, name: str, fields=["creator", "assignee", "updated", "description", "summary"]):
        self.jira = jira
        self.project = next(filter(lambda x: name.lower() in x.get("projectName", "").lower(), self.fetchServicedesks()), None)
        assert self.project
        self.fields =  fields #"assignee,status,issuekey,updated,description,summary,comment"


    def fetchServicedesks(self):
        projects = self.jira.call("/rest/servicedeskapi/servicedesk").get("values", [])

        return [ {"id": x.get("id", None), "projectKey": x.get("projectKey", None), "projectName": x.get("projectName", None)} for x in projects if "servicedesk" in x.get("_links", {}).get("self", "") ]


    #TODO: dont like the jql handling yet
    def fetchTickets(self, limit=50, additonal_jql=None):
        tickets = self.jira.call(
            # f"rest/api/3/search", #https://developer.atlassian.com/changelog/#CHANGE-2046
            "/rest/api/3/search/jql",
            params={
                "jql": f"project={self.project.get("projectKey")} {"" if not additonal_jql else additonal_jql}", # AND statusCategory != Done", 
                "fields": f'"{str.join(", ", self.fields)}"'  
            } | ({"maxResults": limit} if limit else {})
        ).get("issues", [])
        tickets = [ subdict(x, ["id", "key"]) | subdict(x.get("fields", {}), self.fields) for x in tickets ]
   
        return tickets
    

    def fetchTicket(self, ticketid):
        ticket = self.jira.call(f"rest/api/3/issue/{ticketid}", params={"fields": f'{str.join(", ", self.fields + ["comment"])}'})
        ticket = subdict(ticket, ["id", "key"]) | subdict(ticket.get("fields"), self.fields) | {"messages": ticket.get("fields", {}).get("comment", {}).get("comments", [])}
        ticket["creator"] = (ticket["creator"] or {}).get("accountId", None)
        ticket["assignee"] = (ticket["assignee"] or {}).get("accountId", None)
        ticket["messages"] = [ {
            "id": x.get("id", None),
            "author": x.get("author", {}).get("accountId", None),
            "text": unmailify(strip_jira_wiki_markup(str.join("", unnest_items(x.get("body", {}), ["text"]))))
        } for x in ticket["messages"] ]

        #TODO: super ugly sofar
        initial_title = ticket["summary"] if ticket["summary"] else ""
        initial_desc = str.join("",[ x for x in unnest_items(ticket["description"], ["text"]) if x ])
        initial = ""

        if initial_title:
            initial += initial_title
        if initial_desc:
            if initial:
                initial += ": "
            initial += initial_desc
        if initial:
            ticket["messages"].insert(0, {"id": None, "author": ticket.get("creator"), "text": initial})


        return ticket
    
    
    def postMessageTo(self, ticketid, message, public=True):
        self.jira.call(
            f"rest/servicedeskapi/request/{ticketid}/comment", 
            "POST", 
            payload={"body": message, "public": public}
        )