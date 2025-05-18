from ReadFromRepo import ReadFromRepo
import os
import json
import networkx as nx
import matplotlib.pyplot as plt

class DrawGraphs(ReadFromRepo):
    def __init__(self, owner, repo, path, fetch_data=True, list_of_relevant_modules=None):
        super().__init__(owner, repo, path, fetch_data)
        self.list_of_relevant_modules = list_of_relevant_modules


    # a function to draw a graph
    def draw_graph(self, G, size, **args):
        plt.figure(figsize=size)
        pos = nx.shell_layout(G)
            # Draw edge labels to show weights
        edge_labels = nx.get_edge_attributes(G, 'weight')

        nx.draw(G, pos, with_labels=True, **args)
    
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, label_pos=0.75)
        plt.show()

    def store_modules_with_imports(self):
        # get files from json if they exist
        if os.path.exists(f"{self.owner}_{self.repo}_{self.path}.json"):
            with open(f"{self.owner}_{self.repo}_{self.path}.json", 'r') as f:
                data = json.load(f)        
        else:
            Exception(f"File {self.owner}_{self.repo}_{self.path}.json does not exist")
            return
        
        modules = {}

        for file_name, file_url in data.items():
            # check if .py file
            if not file_name.endswith('.py'):
                continue

            module_name = super().module_name_from_file_path(file_url)
            modules[module_name] = super().imports_from_file(file_url)

        with open(f"{self.owner}_{self.repo}_{self.path}_modules.json", 'w') as f:
            json.dump(modules, f)

    def dependencies_graph(self):
        if not os.path.exists(f"{self.owner}_{self.repo}_{self.path}_modules.json"):
            print(f"File {self.owner}_{self.repo}_{self.path}_modules.json does not exist, generating it...")
            self.store_modules_with_imports()

        with open(f"{self.owner}_{self.repo}_{self.path}_modules.json", 'r') as f:
            data = json.load(f)

        G = nx.Graph()
        for module_name, (imports, _) in data.items():
            if module_name not in G.nodes:
                G.add_node(module_name)
            for each in imports:
                if self.relevant_module(each):

                    if G.has_edge(module_name, each):
                        G[module_name][each]['weight'] += 1
                    else:
                        G.add_edge(module_name, each, weight=1)
        return G
    
    def relevant_module(self, module_name):

        if "test" in module_name:
            return False

        if module_name.startswith(self.path):
            if self.list_of_relevant_modules is not None:
                for rel_module in self.list_of_relevant_modules:
                    if module_name.startswith(rel_module):
                        return True
                else:
                    return False
            return True


        return False
    
    def dependencies_digraph(self):

        if not os.path.exists(f"{self.owner}_{self.repo}_{self.path}_modules.json"):
            print(f"File {self.owner}_{self.repo}_{self.path}_modules.json does not exist, generating it...")
            self.store_modules_with_imports()

        with open(f"{self.owner}_{self.repo}_{self.path}_modules.json", 'r') as f:
            data = json.load(f)

        G = nx.DiGraph()
        for module_name, (imports, _) in data.items():
            # ignore if module is not relevant
            if not self.relevant_module(module_name):
                continue
            # add node if not exists
            G.add_node(module_name)

            # add edges
            for target_module in imports:
                if self.relevant_module(target_module):
                    if G.has_edge(module_name, target_module):
                        G[module_name][target_module]['weight'] += 1
                    else:
                        G.add_edge(module_name, target_module, weight=1)

        return G
    
    def abstracted_to_top_level(self, G, depth=1):
        aG = nx.DiGraph()
        for each in G.edges():
            src = super().top_level_package(each[0], depth)
            dst = super().top_level_package(each[1], depth)

            if src != dst:
                if aG.has_edge(src, dst):
                    aG[src][dst]['weight'] += 1
                else:
                    aG.add_edge(src, dst, weight=1)

        return aG
    
    def draw_with_package_activity(self, G, depth=1, cutoff=0, graphSize=(8,8), clean_name=None, multiplier=1):
        if not os.path.exists(f"top_level_packages_{depth}.json"):
            print(f"File top_level_packages_{depth}.json does not exist")
            return
        with open(f"top_level_packages_{depth}.json", 'r') as f:
            package_activity = json.load(f)
        
        sizes = []
        
        to_remove = []

        for n in G.nodes():
            activity = 0
            if n  in package_activity:
                activity = package_activity[n]
            if activity >= cutoff:
                sizes.append(package_activity[n] * multiplier)
            else:
                to_remove.append(n)

        for n in to_remove:
            G.remove_node(n)

        if not clean_name is None:
            mapping = {}
            for n in G.nodes():
                if n.startswith(clean_name):
                    mapping[n] = n.replace(clean_name, "")
            print(f"Mapping: {mapping}")
            G = nx.relabel_nodes(G, mapping)


        self.draw_graph(G, graphSize, node_size=sizes)

    def draw_with_line_count(self, G, depth=1, clean_name=None):
        if not os.path.exists(f"{self.owner}_{self.repo}_{self.path}_modules.json"):
            print(f"File {self.owner}_{self.repo}_{self.path}_modules.json does not exist")
            return
        with open(f"{self.owner}_{self.repo}_{self.path}_modules.json", 'r') as f:
            data = json.load(f)

        data_with_lines = {}

        for module_name, (imports, nr_lines) in data.items():
            abstracted_module_name = super().top_level_package(module_name, depth)
            if abstracted_module_name not in data_with_lines:
                data_with_lines[abstracted_module_name] = 0
            data_with_lines[abstracted_module_name] += nr_lines


        print(data_with_lines)
        sizes = []
        
        for n in G.nodes():
            if n not in data_with_lines:
                sizes.append(0)
            else:
                sizes.append(data_with_lines[n])
        
        if not clean_name is None:
            mapping = {}
            for n in G.nodes():
                if n.startswith(clean_name):
                    mapping[n] = n.replace(clean_name, "")
            print(f"Mapping: {mapping}")
            G = nx.relabel_nodes(G, mapping)

        self.draw_graph(G, (12, 12), node_size=sizes)