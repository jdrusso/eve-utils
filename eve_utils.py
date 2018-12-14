import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session



# This return the result of a GET to the given endpoint, with the necessary
#   url added before and after
def get_endpoint(endpoint):

    request_string = \
        ('https://esi.evetech.net/latest'
        '{endpoint}'
        '/?datasource=tranquility&language=en-us').format(endpoint=endpoint)

    c_request = requests_retry_session().get(request_string)

    return c_request.json()


def get_name(system_id):

    system_info = get_endpoint('/universe/systems/{0}'.format(system_id))
    system_name = system_info['name']

    return system_name


def get_adjacent(system_id):

    system_info = get_endpoint('/universe/systems/{0}'.format(system_id))
    system_name = system_info['name']

    try:
        gates = system_info["stargates"]
    except KeyError: # usually means this is a Jovian system
        # print(system_info)
        # print("ERROR")
        return []

    out_systems = []

    for gate in gates:

        gate_info = get_endpoint('/universe/stargates/{0}'.format(gate))
        out_system = gate_info["destination"]["system_id"]

        out_info = get_endpoint('/universe/systems/{0}'.format(out_system))
        sec = out_info["security_status"]

        out_systems += [out_system]

    return out_systems
