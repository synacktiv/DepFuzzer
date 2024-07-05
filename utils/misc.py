"""
Script defining several functions used in main program
"""
import urllib.parse
from functools import cache
from time import sleep
import re

@cache
def dependency_exists(name, provider, session):
    """
    Method used to check if a dependency is deprecated or not claimed
    """
    try:
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
        package = urllib.parse.quote(name,safe='')
        version = re.sub('[^0-9A-Za-z\-\.]+', '', version)
        return session.get(f"https://deps.dev/_/s/{provider}/p/{package}/v/{version}/dependencies"
                            , timeout=10)
    except Exception:
        print("[-] We have been rate limited, going to sleep for 5 minutes.")
        sleep(300) #this means the API drop our requests
        return None
