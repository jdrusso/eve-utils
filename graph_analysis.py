# Just some stuff playing with a graph theory analysis of systems and
#   connections between them.


# Probably need to generate a list of systems with their sec status and connections
#   or something to start with.


# Pull all the systems in Placid
# For each system, get everything it's connected to
# Build a dict of "system": "adjacent"

import requests_cache, redis
from graph_tool.all import *
from eve_utils import requests_retry_session

def find_adjacent(system_id):


    system_info = requests_retry_session().get(\
        ('https://esi.evetech.net/latest/universe/'
        'systems/{0}/'
        '?datasource=tranquility&language=en-us').format(system_id),
        timeout=15).json()

    system_name = system_info['name']



    try:
        gates = system_info["stargates"]
    except KeyError: # usually means this is a Jovian system
        # print(system_info)
        # print("ERROR")
        return -1


    out_systems = []

    for gate in gates:

        gate_info = requests_retry_session().get(
            ('https://esi.evetech.net/latest/universe/'
            'stargates/{0}/'
            '?datasource=tranquility').format(gate),
            timeout=15).json()

        out_system = gate_info["destination"]["system_id"]

        out_info = requests_retry_session().get(\
            ('https://esi.evetech.net/latest/universe/'
            'systems/{0}/'
            '?datasource=tranquility&language=en-us').format(out_system),
            timeout=15).json()


        sec = out_info["security_status"]

        out_systems += [out_system]

    print(out_systems)

    return system_name, out_systems



if __name__=="__main__":


    requests_cache.install_cache('graph_cache', backend="redis")

    region_ids = ["10000048"]

    systems = []

    for region_id in region_ids:

        r_request = requests_retry_session().get(
            ('https://esi.evetech.net/latest/'
            'universe/regions/{region}/'
            '?datasource=tranquility&language=en-us')
            .format(region=region_id))

        constellations = r_request.json()['constellations']

        systems_list = []

        for constellation in constellations:

            c_request = requests_retry_session().get(
                ('https://esi.evetech.net/latest'
                '/universe/constellations/{constellation}'
                '/?datasource=tranquility&language=en-us')
                .format(constellation=constellation))

            systems_list += c_request.json()['systems']

        # Make a list of all systems in the region
        systems = [[system] for system in systems_list]

        print("Obtained %d systems" % len(systems))


        # Build a list of [systems, [adjacent systems]]
        for i in range(len(systems)):

            print("Parsing system %d / %d" % (i+1, len(systems)), end='\r')

            name, adjacent = find_adjacent(systems[i][0])
            # print(adjacent)
            systems[i].append(name)
            systems[i].append(adjacent)

        print([system for system in systems])

        print("\n\n Done parsing systems...")

    # At this point, I have a list of all the systems in a region.
    # Go through them, find connections

    # TODO: Do this earlier
    # Build the dict of systems
    sdict = dict()
    for system in systems:
        sdict[system[0]] = {'adjacent': system[2], 'name': system[1]}

    # Build the graph
    print("Generating graph.")

    graph = Graph()

    # Add all the vertices
    # vertices = [graph.add_vertex() for system in systems]
    vprop_names = graph.new_vertex_property("string")
    for system in sdict.keys():
        sdict[system]['vertex'] = graph.add_vertex()
        vprop_systemname[sdict[system]['vertex']] = sdict[system]['name']


    # Add edges
    for system in sdict.keys():
        for adjacent in sdict[system]['adjacent']:
            try:
                graph.add_edge(sdict[system]['vertex'], sdict[adjacent]['vertex'])
            except KeyError:
                pass
            # adjacent is the system ID of the adjacent

    print(graph.list_properties())

    # Draw graph
    graph_draw(graph, vertex_text=vprop_names, vertex_font_size=18,
        output_size=(2048,2048), output="two-nodes.png")
