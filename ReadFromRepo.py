import json
import re
import networkx as nx
import matplotlib.pyplot as plt
import requests

class ReadFromRepo:
    def __init__(self, owner, repo, path, fetch_data=True):
        self.owner = owner
        self.repo = repo
        self.path = path
        self.repo_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        self.data = {}
        if fetch_data:

            self.get_files(self.repo_url)
            print(self.data)
            self.save_data()

    def get_files(self, url):
        headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        response = requests.get(url, headers=headers)

        # print eror message if the request fails
        if response.status_code != 200:
            print(f"Error fetching data from {url}: {response.status_code}")
            
            return
        if response.status_code == 200:
            data = response.json()
            print(f"Fetching data from {url}")
            for item in data:
                if item['type'] == 'dir':
                    self.get_files(item['url'])
                elif item['type'] == 'file':
                    self.data[item['name']] = item['download_url']

    def save_data(self):
        """Store the json data in a file"""
        file_name = f'{self.owner}_{self.repo}_{self.path}.json'
        with open(file_name, 'w') as f:
            json.dump(self.data, f)
        print("Data saved to", file_name)


    def import_from_line(self, line):
        """
        Extract the import from a line of code
        We assume that the import is in the form of "import module", "from module import" or "import module; import module"
        """

        try:
            # check if the line is a comment
            if line.startswith("#"):
                return None
            
            # cehck if multiple imports are in the same line
            if ";" in line:
                # split the line by semicolon
                parts = line.split(";")
                # check if the first part is "import"
                for part in parts:
                    if "import" in part:
                        # split the line by spaces
                        parts = part.split(" ")
                        # check if the first part is "import"
                        if parts[0] == "import":
                            # return the module name
                            return parts[1].split(",")[0].strip()
                        elif parts[0] == "from":
                            # return the module name
                            return parts[1].strip()
                return None

            # check if the line is an import statement
            if "import" in line:
                # split the line by spaces
                parts = line.split(" ")
                # check if the first part is "import"
                if parts[0] == "import":
                    # return the module name
                    return parts[1].split(",")[0].strip()
                elif parts[0] == "from":
                    # return the module name
                    return parts[1].strip()
            else:
                return None
        except:
            return None
        

    def read_file(self, path):
        response = requests.get(path)
        if response.status_code == 200:
            return response.text.splitlines()
        else:
            print(f"Error fetching file {path}: {response.status_code}")
            return None
        
    def imports_from_file(self, path):
        """Read the file and return the imports"""
        lines = self.read_file(path)
        nr_lines = len(lines)
        if lines is None:
            return []
        imports = []
        for line in lines:
            imp = self.import_from_line(line)
            if imp is not None:
                imports.append(imp)
        return imports, nr_lines
    
    def module_name_from_file_path(self, full_path):

        file_name = full_path.split("master/")[1]
        file_name = file_name.replace("/__init__.py","")
        file_name = file_name.replace("/",".")
        file_name = file_name.replace(".py","")
        return file_name
    
    def top_level_package(self, module_name, depth=1):
        components = module_name.split(".")
        return ".".join(components[:depth])
    
    def get_commits(self):
        data = []
        
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits"
        more_pages = True
        page = 1
        while more_pages:
            headers = {
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
                'per_page': '100',
                'page': str(page),
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:


                for commit in response.json():
                    response_commit = requests.get(commit['url'], headers=headers)
                    if response_commit.status_code != 200:
                        print(f"Error fetching commit data: {response_commit.status_code}")
                        return None
                    commit_data = response_commit.json()
                    files = []
                    for file in commit_data['files']:
                        files.append(file['filename'])

                    # save auther name, commit message, date and files changed
                    commit_data = {
                        'author': commit['commit']['author']['name'],
                        'message': commit['commit']['message'],
                        'date': commit['commit']['author']['date'],
                        'files_changed': files
                    }

                    data.append(commit_data)

                # check if there are more pages
                if 'Link' in response.headers:
                    links = response.headers['Link']
                    if 'rel="next"' in links:
                        page += 1
                    else:
                        more_pages = False



            # store the commits in a file
            with open(f"{self.owner}_{self.repo}_commits.json", 'w') as f:
                json.dump(data, f)
        else:
            print(f"Error fetching commits: {response.status_code}")
            return None
        
    def print_out_commit_details(self):

        # check if the file exists
        try:
            with open(f"{self.owner}_{self.repo}_commits.json", 'r') as f:
                commits = json.load(f)
        except FileNotFoundError:
            print(f"File {self.owner}_{self.repo}_commits.json does not exist, generating it...")
            self.get_commits()
            with open(f"{self.owner}_{self.repo}_commits.json", 'r') as f:
                commits = json.load(f)

        for commit in commits:
            print(commit)
            # for each in commit.modified_files:
            #     print(f"{commit.author.name} {each.change_type} {each.filename}\n -{each.old_path}\n -{each.new_path}")
