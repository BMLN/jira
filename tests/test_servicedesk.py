import unittest

from os import environ







from src import servicedesk







class IntegrationTest(unittest.TestCase):
    envars = ["JIRA_BASEURL", "JIRA_AUTH_EMAIL", "JIRA_AUTH_TOKEN", "JIRA_PROJECT"]


    @unittest.skipUnless(all(environ.get(x, None) for x in envars), "no envars set")
    def testInit(self):
        to_test = servicedesk.JiraServicedesk

        
        #args
        args = {
            "jira": servicedesk.Jira(environ["JIRA_BASEURL"], {"email": environ["JIRA_AUTH_EMAIL"], "api_token": environ["JIRA_AUTH_TOKEN"]}),
            "name": environ["JIRA_PROJECT"]
        }

        #test
        self.assertIsNotNone(to_test(**args))




    @unittest.skipUnless(all(environ.get(x, None) for x in envars), "no envars set")
    def testFetchTickets(self):
        to_test = servicedesk.JiraServicedesk.fetchTickets

        
        #args
        args = {
            "self": servicedesk.JiraServicedesk(
                servicedesk.Jira(environ["JIRA_BASEURL"], {"email": environ["JIRA_AUTH_EMAIL"], "api_token": environ["JIRA_AUTH_TOKEN"]}),
                environ["JIRA_PROJECT"]
            )
        }

        #test
        self.assertIsNotNone(**args)