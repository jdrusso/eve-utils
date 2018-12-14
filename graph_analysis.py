# Just some stuff playing with a graph theory analysis of systems and
#   connections between them.


# Probably need to generate a list of systems with their sec status and connections
#   or something to start with.


# Pull all the systems in Placid
# For each system, get everything it's connected to
# Build a dict of "system": "adjacent"

import requests_cache, redis, sys
from graph_tool.all import *
from eve_utils import *


class VisitorExample(DFSVisitor):

    def __init__(self, name):
        self.name = name
        self.visited = []
        self.depth = 0
        self.backtracking = False

    # def start_vertex(self, u):
    #     self.visited.append(u)

    def back_edge(self, e):
        # print("Back edge")
        # print([self.name[x] for x in self.visited])
        print("Found back edge from %s to %s" % (self.name[e.source()], self.name[e.target()]))
        # if not self.backtracking:
        #     visited = [self.name[x] for x in self.visited]
        #     print("\nCurrent cycle was: %s \n" % visited)
        self.backtracking = True
        # #
        # print("Popping %s" % [self.name[x] for x in self.visited][-1])
        # self.visited.pop()
        # self.backtracking = True

    def discover_vertex(self, u):
        print("-->", self.name[u], "has been discovered!")
        if self.name[u] == 'Gare': #####DEBUGGING ########
            sys.exit(-1)
        self.visited.append(u)
        self.depth += 1
        self.backtracking = False

        # self.backtracking = False


    def examine_edge(self, e):
        print("\n%s -> %s" % (self.name[e.source()], self.name[e.target()]))
        pass
        # if self.backtracking == True:
            # self.visited.pop()
        # print("\n")
        print([self.name[x] for x in self.visited])


        # if len(self.visited) > 1 and e.target() == self.visited[-2]:
        #     if self.backtracking == False:
        #         print("Retracing, current cycle was %s" % ([self.name[x] for x in self.visited]))
        #     self.visited.pop()
        #     self.depth -= 1
        #     self.backtracking=True
        #
        # print("Appending %s" % self.name[e.source()])
        # self.visited.append(e.source())

    def tree_edge(self, e):
        print("Tress")
        pass
        # print("Tree...")# % \
            #(self.name[e.source()], self.name[e.target()]))


        # print("Appending %s" % self.name[e.target()])
        # self.visited.append(e.source())

        # print([self.name[x] for x in self.visited])


if __name__=="__main__":

    osti_id = 30003792

    requests_cache.install_cache('graph_cache', backend="redis")

    region_ids = ["10000048"]#, "10000051", "10000041", "10000023", "10000069", "10000064", "10000068"] # Placid

    systems = []

    sdict = dict()

    for region_id in region_ids:

        r_request = get_endpoint('/universe/regions/{0}'.format(region_id))

        constellations = r_request['constellations']

        systems_list = []

        for constellation in constellations:

            c_request = get_endpoint('/universe/constellations/{0}'.format(constellation))

            systems_list += c_request['systems']

        # Make a list of all systems in the region
        systems = [[system] for system in systems_list]

        for system in systems_list:
            sdict[system] = {}

        print("Obtained %d systems" % len(systems))

        kill_data = get_endpoint('/universe/system_kills')
        for kill in kill_data:
            if kill['system_id'] in systems_list:
                sdict[kill['system_id']]['npc_kills'] = int(kill['npc_kills'])
                sdict[kill['system_id']]['ship_kills'] = int(kill['ship_kills'])

        jump_data = get_endpoint('/universe/system_jumps')
        for jump in jump_data:
            if jump['system_id'] in systems_list:
                sdict[jump['system_id']]['ship_jumps'] = int(jump['ship_jumps'])


        for system in sdict.keys():
            if 'npc_kills' not in sdict[system].keys():
                sdict[system]['npc_kills'] = 0
                sdict[system]['ship_kills'] = 0
            if 'ship_jumps' not in sdict[system].keys():
                sdict[system]['ship_jumps'] = 0

        print("Gathered system kill and jump data")


        # Build a list of [systems, [adjacent systems]]
        for i in range(len(systems)):

            print("Parsing system %d / %d" % (i+1, len(systems)), end='\r')

            id = systems[i][0]

            adjacent = get_adjacent(id)
            name = get_name(id)

            sec = get_endpoint('/universe/systems/{0}'.format(id))['security_status']

            sdict[id]['adjacent'] = adjacent
            sdict[id]['name'] = name
            sdict[id]['sec'] = float(sec)


        # print([system for system in systems])

        print("\nDone parsing systems...")

    # At this point, I have a list of all the systems in a region.
    # Go through them, find connections

    # Remove highsec
    sdict = {x:sdict[x] for x in sdict.keys() if sdict[x]['sec'] < 0.45}


    # Build the graph
    print("Generating graph.")
    graph = Graph(directed=False)


    # Add all the vertices with properties
    vprop_names = graph.new_vertex_property("string")
    vprop_sec = graph.new_vertex_property("float")
    vprop_kills = graph.new_vertex_property("int")
    vprop_jumps = graph.new_vertex_property("int")
    for system in sdict.keys():

        sdict[system]['vertex'] = graph.add_vertex()
        vprop_names[sdict[system]['vertex']] = sdict[system]['name']
        vprop_sec[sdict[system]['vertex']] = sdict[system]['sec']
        vprop_kills[sdict[system]['vertex']] = sdict[system]['ship_kills']
        vprop_jumps[sdict[system]['vertex']] = sdict[system]['ship_jumps']


    vprop_size = prop_to_size(vprop_kills, mi=0, ma=5)



    # Add edges
    for system in sdict.keys():
        source = sdict[system]['vertex']

        for adjacent in sdict[system]['adjacent']:
            try:
                target = sdict[adjacent]['vertex']
            except KeyError:
                continue # Not in the selected regions

            if (graph.edge(source, target) == None) and (graph.edge(target,source) == None):
                graph.add_edge(source, target)

    time = graph.new_vertex_property('int')
    pred = graph.new_vertex_property('int64_t')
    visitor = VisitorExample(vprop_names)

    # Do search:
    dfs_search(graph, source=sdict[osti_id]['vertex'], visitor=visitor)

    # Draw graph
    graphviz_draw(graph,
        vsize=vprop_size,
        size=(100,100),
        overlap="prism",
        ratio='fill',
        vprops={'label':vprop_names},
        vcolor=prop_to_size(vprop_jumps, ma=1),
        output="graph.png")
