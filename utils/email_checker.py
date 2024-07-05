"""
File used to declare the class used to check if an email exists
"""

import re
import socket
import whois
import requests

class EmailChecker:
    """
    Class used to check if an email exists
    """

    def __init__(self, provider, package):
        self.provider = provider
        self.package = package
        self.email_urls = {"npm":"https://registry.npmjs.org/%s",
                           "pypi":"https://pypi.org/pypi/%s/json",
                           "cargo":"https://crates.io/api/v1/crates/%s"}
        self.known_domains = ["gmail.com","outlook.com","hotmail.com","protonmail.com"]

    def get_emails(self):
        """
        Method used to make HTTP requests to recover the email
        """
        if self.provider not in ["go","cargo"]:
            try:
                res = requests.get(self.email_urls[self.provider]%(self.package), timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    match self.provider:
                        case "pypi":
                            return [data.get("info").get("author_email")]
                        case "npm":
                            emails = []
                            if data.get("maintainers") is not None:
                                for maintainer in data.get("maintainers"):
                                    if maintainer.get("email"):
                                        emails.append(maintainer["email"])
                            if data.get("contributors") is not None:
                                for contributor in data.get("contributors"):
                                    if contributor.get("email"):
                                        emails.append(contributor["email"])
                            return emails
            except Exception:
                return []
        else:
            return []

    def check_email(self):
        """
        Method used to check if an email exists
        """
        res = self.get_emails()
        real_emails = []
        takeoverable = []
        for r in res:
            match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', r)
            if match is not None:
                real_emails.append(match.group(0))

        if len(real_emails) == 0:
            return []

        for email in real_emails:
            domain = email.split("@")[1].strip()
            if domain in self.known_domains:
                continue
            try:
                socket.gethostbyname(domain)
            except socket.error:
                try:
                    res = whois.whois(domain)
                    if res["registrar"] is None:
                        takeoverable.append([domain, email])
                    else:
                        return []
                except Exception:
                    takeoverable.append([domain, email])

        return takeoverable
    