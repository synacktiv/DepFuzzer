"""
File used to declare the class used to check if an email exists
"""

import re

import dns.resolver
import requests
import whois


class DisposableDomainChecker:
    DISPOSABLE_DOMAINS_URL = "https://disposable.github.io/disposable-email-domains/domains.txt"
    _domains: set[str] | None = None

    @classmethod
    def get_domains(cls) -> set[str]:
        if cls._domains is not None:
            return cls._domains

        try:
            res = requests.get(cls.DISPOSABLE_DOMAINS_URL, timeout=10)
            if res.status_code == 200:
                cls._domains = set(line.strip().lower() for line in res.text.splitlines() if line.strip())
            else:
                cls._domains = set()
        except Exception:
            cls._domains = set()

        if not len(cls._domains):
            print("[!] Could not load list of disposable email providers, this test will be skipped")
        return cls._domains

    @classmethod
    def is_disposable(cls, domain: str) -> bool:
        domains = cls.get_domains()
        return domain.lower() in domains


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

    def get_emails(self) -> list[str]:
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
                            if (info := data.get("info")) and (mail := info.get("author_email")):
                                return [mail]
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
        return []

    def check_email(self) -> tuple[list[list[str]], list[list[str]]]:
        """
        Method used to check if an email exists
        """
        res = self.get_emails()
        real_emails = []
        takeoverable = []
        disposable: list[list[str]] = []
        for r in res:
            match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', r)
            if match is not None:
                real_emails.append(match.group(0))

        if len(real_emails) == 0:
            return ([], [],)

        for email in real_emails:
            domain = email.split("@")[1].strip()
            if domain in self.known_domains:
                continue
            if DisposableDomainChecker.is_disposable(domain):
                disposable.append([domain, email])
            try:
                dns.resolver.resolve(domain, "MX")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers,):
                try:
                    res = whois.whois(domain)
                    if res["registrar"] is None:
                        takeoverable.append([domain, email])
                except Exception:
                    takeoverable.append([domain, email])

        return (takeoverable, disposable,)
