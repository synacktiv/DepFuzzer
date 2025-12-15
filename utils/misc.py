"""
Script defining several functions used in main program
"""
import urllib.parse
from functools import cache
from time import sleep
import re

NUGET_RESERVED_PREFIXES = [
    "Microsoft",
    "System",
    "Azure",
    "Serilog",
    "Newtonsoft",
    "Xamarin",
    "xunit",
    "OpenTelemetry",
    "Spectre",
    "Grpc",
    "NuGet",
    "Google",
    "AWSSDK",
    "Castle",
    "Polly",
    "Moq",
    "AutoMapper"
]

@cache
def dependency_exists(name, provider, session):
    """
    Method used to check if a dependency is deprecated or not claimed
    """
    try:
        if "gradle" in provider :
            groupId, artifactId = name.split(':')[0], name.split(':')[1]
            output = session.get(f'https://search.maven.org/solrsearch/select?q=g:{groupId}+AND+a:{artifactId}&core=gav&rows=20&wt=json',
                                timeout=10)
            if output.json()['response']['numFound'] != 0:
                return output
            
        else:
            package = urllib.parse.quote(name,safe='')
            output = session.get(f"https://deps.dev/_/s/{provider}/p/{package}/v/",
                                timeout=10)
            return output.status_code != 404
    except Exception:
        print("[-] We have been rate limited, going to sleep for 5 minutes.")
        sleep(300) #this means the API drop our requests
        return None

@cache
def recover_dependencies(name, version, provider, session):
    """
    Method used to return all dependencies of a dependency
    """
    try:
        if "gradle" in provider :
            groupId, artifactId = name.split(':')[0], name.split(':')[1]
            output = session.get(f'https://search.maven.org/solrsearch/select?q=g:{groupId}+AND+a:{artifactId}+AND+v:{version}&core=gav&rows=20&wt=json',
                                timeout=10)
            if output.json()['response']['numFound'] != 0:
                return output
        else:
            package = urllib.parse.quote(name,safe='')
            version = re.sub('[^0-9A-Za-z\-\.]+', '', version)
            return session.get(f"https://deps.dev/_/s/{provider}/p/{package}/v/{version}/dependencies"
                            , timeout=10)
    except Exception:
        print("[-] We have been rate limited, going to sleep for 5 minutes.")
        sleep(300) #this means the API drop our requests
        return None

def is_nuget_package_reserved(package_id, reserved_prefixes):
    """
    Check if a NuGet package ID matches any reserved prefix.

    Args:
        package_id (str): The NuGet package ID to check.
        reserved_prefixes (list[str]): List of reserved prefixes (case-insensitive).

    Returns:
        bool: True if package ID starts with any reserved prefix, False otherwise.
    """
    package_id_lower = package_id.lower()
    for prefix in reserved_prefixes:
        # Compare case-insensitively and allow prefix with dot or exact match
        prefix_lower = prefix.lower()
        if package_id_lower == prefix_lower or package_id_lower.startswith(f"{prefix_lower}."):
            return True
    return False
