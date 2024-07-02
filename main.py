"""
Main script to analyze dependencies of a github organization
"""
import argparse
from pyfiglet import Figlet
from utils.recover_dependencies import RecoverDependencies
from utils.analyze_dependencies import AnalyzeDependencies

def main():
    """
    Main method to launch the analysis
    """
    f = Figlet(font='doom')
    print(f.renderText('DepFuzzer'))
    parser = argparse.ArgumentParser(prog='main.py', description='Dependency checker')
    parser.add_argument('--provider',
                        choices=["npm","pypi","cargo","go","all"],
                        required=True,
                        type=str)

    args_group = parser.add_mutually_exclusive_group(required=True)
    args_group.add_argument('--path',
                        help="Path to folder(s) to analyze",
                        required=False,
                        type=str)
    args_group.add_argument('--dependency',
                        help='''Specify the name of one dependency to check.
                        If you specify the version, please use ':' to separate name and version.''',
                        required=False,
                        type=str)

    parser.add_argument('--print-takeover',
                        help="Don't wait the end of the script to display takeoverable modules",
                        default=False,
                        type=bool)
    parser.add_argument('--output-file',
                        help="File where results will be stored",
                        default=None,
                        type=str)
    parser.add_argument('--check-email',
                        help="Check if the email's owner of the dependency exists. Might be longer to analyze.",
                        default=False,
                        type=bool)

    args = parser.parse_args()

    dependencies_to_check = {}
    if args.path is not None:
        if args.provider != "all":
            rd = RecoverDependencies(args.path, args.provider)
            rd.run()
            dependencies_to_check = rd.dependencies
    else:
        if ":" in args.dependency:
            splitted = args.dependency.split(":")
            name = splitted[0]
            version = splitted[1].strip()
        else:
            name = args.dependency.strip()
            version = ""
        dependencies_to_check = {name: version}

    if args.provider == "all":
        providers = ["npm","pypi","cargo","go"]
        for provider in providers:
            rd = RecoverDependencies(args.path, provider)
            rd.run()
            dependencies_to_check = rd.dependencies
            if len(dependencies_to_check) > 0:
                analyze = AnalyzeDependencies(provider,
                dependencies_to_check,
                args.print_takeover,
                args.output_file,
                args.check_email)
                analyze.run()
            else:
                print(f"[-] No package for {provider} found.")
    else:
        if len(dependencies_to_check) > 0:
            analyze = AnalyzeDependencies(args.provider,
                                        dependencies_to_check,
                                        args.print_takeover,
                                        args.output_file,
                                        args.check_email)
            analyze.run()
        else:
            print(f"[-] No package for {args.provider} found.")

if __name__ == "__main__":
    main()
