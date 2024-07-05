"""
File used to declare the analyzer for dependencies
"""

import requests
from utils.misc import dependency_exists, recover_dependencies
from utils.email_checker import EmailChecker


class AnalyzeDependencies:
    """
    Class used to analyze and recover all dependencies of environment
    """

    def __init__(self, provider, dependencies, print_takeover, output, check_email):
        self.packages_json = []
        self.dependencies = dependencies
        self.already_done = {}
        self.provider = provider
        self.takeover = {}
        self.print_takeover = print_takeover
        self.output = output
        self.check = check_email
        self.email_takeover = []
        self.session = requests.Session()

    def check_dependency(self, root_package, root_version):
        """
        Method used to check if a dependency exists
        """
        stack = []
        stack.append({root_package: root_version})
        while len(stack) != 0:
            package, version = list(stack.pop().items())[0]
            if package is not None and dependency_exists(package, self.provider, self.session):
                if self.check:
                    self.check_email(package)
                deps = recover_dependencies(package, version, self.provider, self.session)
                self.already_done[package] = version
                if deps is not None and deps.status_code == 200:
                    deps = deps.json()
                    if deps.get("dependencyCount") and deps["dependencyCount"] > 0:
                        for dep in deps["dependencies"][1:]:
                            subpackage = dep["package"]["name"]
                            subpackage_version = dep["version"]
                            if (
                                subpackage not in self.already_done
                                and subpackage not in [list(x.keys())[0] for x in stack]
                            ):
                                stack.append({subpackage: subpackage_version})
            else:
                self.already_done[package] = version
                if package not in self.takeover:
                    self.takeover[package] = version
                if self.print_takeover:
                    if package is not None:
                        if "@" in package:
                            print(
                                f"""[DEBUG] {package} is not declared but cannot be taken over because it belongs to an external organization\nYou might have to check manually if the organization exists."""
                            )
                        else:
                            print(f"[DEBUG] {package}:{version} might be taken over !")

    def analyze_dependencies(self):
        """
        Method used to iterate over all dependencies
        """
        for key, val in self.dependencies.items():
            if key in self.already_done:
                continue
            self.already_done[key] = val
            self.check_dependency(key, val)

    def check_email(self, package):
        """
        Method used to check if an email exists
        """
        ec = EmailChecker(self.provider, package)
        res = ec.check_email()
        if len(res) > 0:
            for r in res:
                if r[0] not in self.email_takeover:
                    self.email_takeover.append(r[0])
                    print(
                        f"""The account associated to dependency {package} is : {r[1]} and the domain {r[0]} might be purchased !"""
                    )

    def run(self):
        """
        Main method to run analysis
        """
        print(f"[+] Starting analysis for {self.provider}...")
        self.analyze_dependencies()
        if len(self.takeover) > 0:
            if self.output is not None:
                with open(self.output, "w", encoding="utf-8") as fd:
                    for package, version in self.takeover.items():
                        fd.write(f"{package}:{version}\n")
                print(f"Results saved to {self.output} !")
            else:
                for package, version in self.takeover.items():
                    if package is not None:
                        if "@" in package:
                            print(
                                f"""[+] {package} is not declared but cannot be taken over because it belongs to an external organization\nYou might have to check manually if the organization exists."""
                            )
                        else:
                            print(f"[+] {package}:{version} might be taken over !")
        else:
            print("[+] No package can be taken over !")
