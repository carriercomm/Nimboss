import sys
import base64

import httplib2 # Not in standard library, change later if needed.
import httplib # for status codes

try: 
    import json
except: 
    import simplejson as json

Connection = httplib2.Http

class ContextClient(object):
    """Broker connection management and utility functionality.
    """
    def __init__(self, broker_uri, key, secret):
        self.broker_uri = broker_uri
        self.connection = Connection()
        self.connection.add_credentials(key, secret)

        # forcibly add basic auth header to get around Nimbus not
        # sending WWW-Authenticate header in 401 response, which
        # httplib2 relies on.
        auth = base64.b64encode(key + ":" + secret)
        self.headers = {'Authorization' : 'Basic ' + auth}

    def create_context(self):
        """Create a new context with Broker.

        @return: instance of type C{ContextResource}
        """

        # creating a new context is a POST to the base broker URI
        # context URI is returned in Location header and info for VMs
        # is returned in body
        try:
            (resp, body) = self.connection.request(self.broker_uri, 'POST', 
                    headers=self.headers)
        except Exception, e:
            trace = sys.exc_info()[2]
            raise BrokerError("Failed to contact broker: %s" % str(e)), None, trace

        if resp.status != httplib.CREATED:
            raise BrokerError("Failed to create new context")
        
        location = resp['location']
        body = json.loads(body)

        return _resource_from_response(location, body)

    def get_status(self, resource):
        """Status of a Context resource.

        Returns a ContextStatus object
        """
        
        try:
            (resp, body) = self.connection.request(str(resource), 'GET',
                    headers=self.headers)
        except Exception, e:
            trace = sys.exc_info()[2]
            raise BrokerError("Failed to contact broker: %s" % str(e)), None, trace
        
        if resp.status != httplib.OK:
            raise BrokerError("Failed to get status of context")
        try:
            response = json.loads(body)
            return _status_from_response(response)
        except:
            raise BrokerError("Failed to parse status response from broker")

class ContextResource(dict):
    """Context created on the broker. 

    Used in generation of userdata.
    """
    def __init__(self, **kwargs):
        for key,value in kwargs.iteritems():
            self[key] = value
        self.uri = self['uri']
        self.broker_uri = self['broker_uri']
        self.context_id = self['context_id']
        self.secret = self['secret']

    def __str__(self):
        return self.uri

def _resource_from_response(uri, response):
    dct = {'broker_uri' : response['brokerUri'], 
            'context_id' : response['contextId'],
            'secret' : response['secret'],
            'uri' : uri}
    return ContextResource(**dct)

def _status_from_response(response):
    res_nodes = response['nodes']
    nodes = []
    for n in res_nodes:
        ids = _identities_from_response_node(n)
        ok_occurred = n.get('okOccurred', False)
        error_occurred = n.get('errorOccurred', False)
        error_code = n.get('errorCode')
        error_message = n.get('errorMessage', None)
        node = ContextNode(ids, ok_occurred, error_occurred, error_code,
                error_message)
        nodes.append(node)

    complete = response.get('isComplete', False)
    error = response.get('errorOccurred', False)
    expected_count = response['expectedNodeCount']
    return ContextStatus(nodes, expected_count, complete, error)

def _identities_from_response_node(resp_node):
    ids = resp_node['identities']
    identities = []
    for id in ids:
        identity = ContextNodeIdentity(id['iface'], id['ip'], id['hostname'],
            id['pubkey']) 
        identities.append(identity)
    return identities

class ContextStatus(object):
    """Status information about a context
    """
    def __init__(self, nodes, expected_count, complete=False, error=False):
        self.nodes = nodes
        self.expected_count = expected_count
        self.complete = complete
        self.error = error

class ContextNode(object):
    """A single contextualization node, with one or more identities.
    """
    def __init__(self, identities, ok_occurred=False, error_occurred=False,
            error_code=None, error_message=None):
        self.identities = identities
        self.ok_occurred = ok_occurred
        self.error_occurred = error_occurred
        self.error_code = error_code
        self.error_message = error_message

class ContextNodeIdentity(object):
    """A single network identity for a node.
    """
    def __init__(self, interface, ip, hostname, pubkey):
        self.interface = interface
        self.ip = ip
        self.hostname = hostname
        self.pubkey = pubkey

class BrokerError(Exception):
    """Error response from Context Broker.
    """
    def __init(self, reason):
        self.reason = reason
        Exception.__init__(self, reason)

