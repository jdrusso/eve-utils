# Just some stuff playing with a graph theory analysis of systems and
#   connections between them.


# Probably need to generate a list of systems with their sec status and connections
#   or something to start with.


# Pull all the systems in Placid
# For each system, get everything it's connected to
# Build a dict of "system": "adjacent"

import requests_cache, redis
from graph_tool.all import *
from eve_utils import *


if __name__=="__main__":


    requests_cache.install_cache('graph_cache', backend="redis")

    region_ids = ["10000048"] # Placid

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


    # Build the graph
    print("Generating graph.")

    graph = Graph(directed=False)

    # Add all the vertices
    # vertices = [graph.add_vertex() for system in systems]
    vprop_names = graph.new_vertex_property("string")
    vprop_sec = graph.new_vertex_property("float")
    vprop_kills = graph.new_vertex_property("int")
    vprop_jumps = graph.new_vertex_property("int")
    for system in sdict.keys():

        # If system is highsec:
        if sdict[system]['sec'] >= 0.45:
            continue

        sdict[system]['vertex'] = graph.add_vertex()
        vprop_names[sdict[system]['vertex']] = sdict[system]['name']
        vprop_sec[sdict[system]['vertex']] = sdict[system]['sec']
        vprop_kills[sdict[system]['vertex']] = sdict[system]['ship_kills']
        vprop_jumps[sdict[system]['vertex']] = sdict[system]['ship_jumps']


    vprop_size = prop_to_size(vprop_kills, mi=0, ma=5)



    # Add edges
    for system in sdict.keys():
        for adjacent in sdict[system]['adjacent']:
            try:
                graph.add_edge(sdict[system]['vertex'], sdict[adjacent]['vertex'])
            except KeyError:
                pass
            # adjacent is the system ID of the adjacent

    # Draw graph
    # graph_draw(graph,
    #     vertex_text=vprop_names,
    #     vertex_size=vprop_size,
    #     vertex_font_size=10,
    #     output_size=(1200,768),
    #     edge_pen_width=24,
    #     output="graph.png")
    graphviz_draw(graph,
        # vertex_text=vprop_names,
        vsize=vprop_size,
        size=(100,100),
        overlap="prism",
        ratio='fill',
        # vertex_font_size=10,
        # output_size=(1200,768),
        # edge_pen_width=24,
        vprops={'label':vprop_names},
        vcolor=prop_to_size(vprop_jumps, ma=1),
        # sep=1,
        output="graph.png")
