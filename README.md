# DepFuzzer

DepFuzzer is a tool used to find dependency confusion or project where owner's email can be takeover.


## Install the tool

/!\ This tool requires python >= 3.10 /!\

```sh
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip3 install -r requirements.txt
```

## Use the tool

The tool can be used to scan folders to search specific file where dependencies are declared, for example :

- `package.json`
- `requirements.txt`
- ...

`python3 main.py --provider pypi --path ~/Documents/Projets/MyProject/`

Moreover, this tool can be used to scan one specific dependency :

`python3 main.py --provider pypi --dependency requests:0.1.0`

Please note that the tool used a third-party called `deps.dev`, you might need to specify a proxy to reach it.

## All possible arguments

```
______          ______                      
|  _  \         |  ___|                     
| | | |___ _ __ | |_ _   _ ___________ _ __ 
| | | / _ \ '_ \|  _| | | |_  /_  / _ \ '__|
| |/ /  __/ |_) | | | |_| |/ / / /  __/ |   
|___/ \___| .__/\_|  \__,_/___/___\___|_|   
          | |                               
          |_|                               

usage: main.py [-h] --provider {npm,pypi,cargo,go,all} (--path PATH | --dependency DEPENDENCY) [--print-takeover PRINT_TAKEOVER] [--output-file OUTPUT_FILE] [--check-email CHECK_EMAIL]

Dependency checker

options:
  -h, --help            show this help message and exit
  --provider {npm,pypi,cargo,go,all}
  --path PATH           Path to folder(s) to analyze
  --dependency DEPENDENCY
                        Specify the name of one dependency to check. 
                        If you specify the version, please use ':' to separate name and version.
  --print-takeover PRINT_TAKEOVER
                        Don't wait the end of the script to display takeoverable modules
  --output-file OUTPUT_FILE
                        File where results will be stored
  --check-email CHECK_EMAIL
                        Check if the email's owner of the dependency exists. Might be longer to analyze.
```

## Found a bug or an idea ?

If you found a bug or have an idea, don't hesitate to open an issue on this project !