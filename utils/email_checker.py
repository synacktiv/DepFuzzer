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
        # Class-level cache to store domain check results across instances
        if not hasattr(EmailChecker, '_domain_cache'):
            EmailChecker._domain_cache = {}

    def get_emails(self) -> list[tuple[str, str]]:
        """
        Method used to make HTTP requests to recover the email
        Returns list of tuples: (email, role) where role is 'maintainer', 'contributor', or 'author'
        """
        if self.provider not in ["go","cargo"]:
            try:
                res = requests.get(self.email_urls[self.provider]%(self.package), timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    match self.provider:
                        case "pypi":
                            if (info := data.get("info")) and (mail := info.get("author_email")):
                                return [(mail, "author")]
                        case "npm":
                            emails = []
                            if data.get("maintainers") is not None:
                                for maintainer in data.get("maintainers"):
                                    if maintainer.get("email"):
                                        emails.append((maintainer["email"], "maintainer"))
                            if data.get("contributors") is not None:
                                for contributor in data.get("contributors"):
                                    if contributor.get("email"):
                                        emails.append((contributor["email"], "contributor"))
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
        for email_tuple in res:
            if isinstance(email_tuple, tuple):
                email, role = email_tuple
            else:
                # Handle backward compatibility for old format
                email = email_tuple
                role = "unknown"

            match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', email)
            if match is not None:
                real_emails.append((match.group(0), role))

        if len(real_emails) == 0:
            return ([], [],)

        print(f"[EMAIL CHECK] Starting email domain analysis for dependency: {self.package}")

        for email_data in real_emails:
            if isinstance(email_data, tuple):
                email, role = email_data
            else:
                # Handle backward compatibility
                email, role = email_data, "unknown"

            domain = email.split("@")[1].strip()
            print(f"[EMAIL CHECK] Dependency: {self.package} | Email: {email} ({role}) | Domain: {domain}")

            if domain in self.known_domains:
                print(f"[EMAIL CHECK] Dependency: {self.package} | Domain {domain} is in known domains list - SKIPPING")
                continue
            if DisposableDomainChecker.is_disposable(domain):
                print(f"[EMAIL CHECK] Dependency: {self.package} | Domain {domain} is disposable email provider")
                disposable.append([domain, email, role])

            # Extract root domain for availability checking
            root_domain = self._extract_root_domain(domain)

            # Check if we've already analyzed this root domain
            if root_domain in EmailChecker._domain_cache:
                cached_result = EmailChecker._domain_cache[root_domain]
                status_msg = f"[DOMAIN CHECK] Dependency: {self.package} | Domain {root_domain} - STATUS: {'AVAILABLE' if cached_result else 'NOT AVAILABLE'} (cached result)"
                if cached_result:
                    status_msg += f" - Email: {email} ({role})"
                    takeoverable.append([domain, email, role])
                print(status_msg)
            else:
                # Check domain availability using whois (check root domain)
                is_available = self._is_domain_available(root_domain, self.package, email, role)
                # Cache the result for future use
                EmailChecker._domain_cache[root_domain] = is_available
                if is_available:
                    takeoverable.append([domain, email, role])

        return (takeoverable, disposable,)

    def _extract_root_domain(self, domain: str) -> str:
        """
        Extract the root domain from a subdomain
        e.g., NormanDev2.telogical.com -> telogical.com
        """
        domain = domain.lower().strip()

        # Common TLD patterns - this is a simplified approach
        # For production, consider using a library like tldextract
        common_tlds = [
            '.com', '.org', '.net', '.edu', '.gov', '.mil', '.int',
            '.co.uk', '.ac.uk', '.org.uk', '.gov.uk',
            '.co.jp', '.ne.jp', '.ac.jp', '.go.jp',
            '.com.au', '.net.au', '.org.au', '.edu.au',
            '.ca', '.de', '.fr', '.it', '.es', '.nl', '.be',
            '.ch', '.at', '.se', '.no', '.dk', '.fi',
            '.ru', '.cn', '.in', '.br', '.mx', '.ar'
        ]

        # Sort TLDs by length (longest first) to match multi-part TLDs first
        common_tlds.sort(key=len, reverse=True)

        for tld in common_tlds:
            if domain.endswith(tld):
                # Remove the TLD, then take the last part before TLD as root domain
                without_tld = domain[:-len(tld)]
                parts = without_tld.split('.')
                if len(parts) >= 1:
                    root_domain = parts[-1] + tld
                    return root_domain
                break

        # Fallback: assume .com if no known TLD found
        parts = domain.split('.')
        if len(parts) >= 2:
            return f"{parts[-2]}.{parts[-1]}"

        return domain

    def _is_domain_available(self, domain: str, package: str = "", email: str = "", role: str = "") -> bool:
        """
        Check if a domain is available for registration using whois
        """
        import subprocess

        try:
            # Use the system whois command
            result = subprocess.run(['whois', domain],
                                  capture_output=True,
                                  text=True,
                                  timeout=30)

            output = result.stdout.lower()

            # Debug: print first part of whois output for troubleshooting
            # print(f"[DEBUG] Checking domain: {domain}")
            # print(f"[DEBUG] Whois output for {domain}: {output[:300]}...")
            # print(f"[DEBUG] Return code: {result.returncode}")

            # Strong indicators that domain is definitely NOT available
            definitely_registered_indicators = [
                "registrar:",
                "creation date:",
                "created:",
                "status: active",
                "status: ok",
                "status: clienttransferprohibited",
                "registry domain id:",
                "registrar whois server:",
                "registrar url:",
                "registrar iana id:",
                "sponsoring registrar:",
                "status.............: registered",  # .fi domains
                "status: registered",  # Alternative .fi format
                "holder.............: ",  # .fi domains
                "registrar.........:", # .fi domains
                "domain.............: ",  # .fi domains (indicates registration data)
                "expires............:",  # .fi domains expiry
                "nameservers",  # Active nameservers indicate registration
                "nserver............:",  # .fi nameserver format
            ]

            # Clear availability indicators (only when no registration data)
            available_indicators = [
                "no match for",
                "no entries found",
                "status: available",
                "no data found",
                "not found in database",
                "no matching record",
                "domain status: available",
                "no matching entries found",
                "\" not found.",  # .se domains: 'domain "example.se" not found.'
                "the query is not valid",  # Alpine whois for .se domains
                "not available"  # Some registries use this
            ]

            # Special case: redemption period (available but requires checking registration data)
            in_redemption = "redemptionperiod" in output

            print(f"[DOMAIN CHECK] Dependency: {package} | Analyzing domain: {domain}")

            # FIRST: Check for redemption period - this overrides registration indicators
            if in_redemption:
                role_info = f" - Email: {email} ({role})" if email and role else ""
                print(f"[WARNING] Dependency: {package} | Domain {domain} - STATUS: AVAILABLE (REDEMPTION PERIOD - Expired domain, emails likely unmonitored!){role_info}")
                return True

            # SECOND: Check if definitely registered (has active registration data)
            registration_found = False
            for indicator in definitely_registered_indicators:
                if indicator in output:
                    role_info = f" - Email: {email} ({role})" if email and role else ""
                    print(f"[DOMAIN CHECK] Dependency: {package} | Domain {domain} - STATUS: NOT AVAILABLE (found indicator: '{indicator}'){role_info}")
                    registration_found = True
                    break

            # If we found registration indicators, domain is NOT available
            if registration_found:
                return False

            # THIRD: Check clear availability indicators if NO registration data was found
            for indicator in available_indicators:
                if indicator in output:
                    role_info = f" - Email: {email} ({role})" if email and role else ""
                    print(f"[DOMAIN CHECK] Dependency: {package} | Domain {domain} - STATUS: AVAILABLE (found indicator: '{indicator}'){role_info}")
                    return True

            # If we got substantial whois data but no clear indicators, likely registered
            if len(output.strip()) > 100 and result.returncode == 0:
                role_info = f" - Email: {email} ({role})" if email and role else ""
                print(f"[DOMAIN CHECK] Dependency: {package} | Domain {domain} - STATUS: NOT AVAILABLE (substantial whois data, assuming registered){role_info}")
                return False

            # If no data or error, assume not available to avoid false positives
            role_info = f" - Email: {email} ({role})" if email and role else ""
            print(f"[DOMAIN CHECK] Dependency: {package} | Domain {domain} - STATUS: NOT AVAILABLE (insufficient data, assuming registered){role_info}")
            return False

        except subprocess.TimeoutExpired:
            print(f"[!] Dependency: {package} | Whois timeout for {domain}")
            return False
        except FileNotFoundError:
            print(f"[!] Dependency: {package} | Whois command not found. Install whois package.")
            return False
        except Exception as e:
            print(f"[!] Dependency: {package} | Whois error for {domain}: {e}")
            return False

        return (takeoverable, disposable,)
