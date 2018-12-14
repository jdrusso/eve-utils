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
        self.routes = []
        self.visited = []
        self.current = None


    # If you've found a loop, record the stack
    def back_edge(self, e):

        self.routes.append(self.visited)

    # If I've found a new vertex, add it to the stack
    def discover_vertex(self, u):
        # print("-->", self.name[u], "has been discovered!")
        self.visited.append(u)
        self.current = u

    # Upon looking along a new edge
    def examine_edge(self, e):

        # If I've moved...
        if not e.source() == self.current:

            self.current = e.source()

            # If I've already visited this vertex, pop everything past it from
            #   the stack.
            if e.source() in self.visited:
                idx = self.visited.index(e.source())
                self.visited = self.visited[:idx]
            # If I haven't, add it to the stack.
            else:
                self.visited.append(e.source())


if __name__=="__main__":

    osti_id = 30003792

    requests_cache.install_cache('graph_cache', backend="redis")

    region_ids = ["10000048", "10000051", "10000041", "10000023", "10000069", "10000064", "10000068"] # Placid

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
        # if sdict[system]['name'] == "Covryn":
        #
        #     print("\nanalyzing system %s" % sdict[system]['name'])
        #     print("Adjacent are %s" % sdict[system]['adjacent'])

        source = sdict[system]['vertex']

        for adjacent in sdict[system]['adjacent']:
            # if debug:
            #     print(sdict[adjacent][])
            try:
                target = sdict[adjacent]['vertex']
            except KeyError:
                continue # Not in the selected regions

            # if sdict[system]['name'] == "Covryn":
            #     print("making edge to %s" % vprop_names[target])

            if (graph.edge(source, target) == None) and (graph.edge(target,source) == None):
                graph.add_edge(source, target)

    visitor = VisitorExample(vprop_names)

    # Do search to obtain all cycles
    dfs_search(graph, source=sdict[osti_id]['vertex'], visitor=visitor)
    routes = visitor.routes

    # Clean up routes to make sure they all have the right starting location
    #   TODO: Why does my search sometimes not include the starting location?
    for route in routes:
        if route == []:
            continue
        if not route[0] == sdict[osti_id]['vertex']:
            route.insert(0,sdict[osti_id]['vertex'])

    # Make sure only unique paths are stored.
    #   I apologize sincerely for this set comprehension. I did it because:
    #   - Casting a list to a set is a nice way to ensure that only unique
    #     elements are kept
    #   - "routes" is a list of lists -- list are mutable, and so unhashable.
    #   - A set must be constructed of hashable elements
    # So, the solution is to cast each of the sub-lists to a tuple, and then
    #   build the set from that.
    routes = set(tuple(route) for route in routes)
    print("Found %d unique paths" % len(routes))

    # Now analyze the cycles, and calculate the node weights for each
    best_route = []
    max_kills = 0
    for route in routes:

        route_names = [vprop_names[s] for s in route]
        route_kills = sum([vprop_kills[s] for s in route])
        route_jumps = sum([vprop_jumps[s] for s in route])

        # print("Route: %s \n\t Total kills: %d \n\t Total jumps: %d" % \
        #     (route_names, route_kills, route_jumps))

        if route_kills > max_kills:
            best_route = route
            max_kills = route_kills

    print("Most active route was: %s \n\t with %d kills and %d jumps " %
        ([vprop_names[s] for s in best_route],
        max_kills,
        sum([vprop_jumps[s] for s in best_route])))

    # vprop_onroute = graph.new_vertex_property("bool")
    # for v in graph.vertices():
    #     if v in best_route:
    #         vprop_onroute[v] = True
    #     else:
    #         vprop_onroute[v] = False

    eprop_onroute = graph.new_edge_property("bool")
    # Detect which edges are along the route
    for e in graph.edges():
        if e.source() in best_route and e.target() in best_route:
            eprop_onroute[e] = 6
        else:
            eprop_onroute[e] = 1

    # Draw the route
    # graph.set_edge_filter(eprop_onroute)



    # Draw graph
    graphviz_draw(graph,
        vsize=vprop_size,
        size=(100,100),
        overlap="prism",
        ratio='fill',
        vprops={'label':vprop_names},
        penwidth=eprop_onroute,
        vcolor=prop_to_size(vprop_jumps, ma=1),
        output="graph.png")
