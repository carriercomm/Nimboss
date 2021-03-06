import hashlib

from libcloud.compute.base import NodeImage

from nimboss.nimbus import NimbusClusterDocument

class Cluster(object):
    """A collection of Nodes.

    All Nodes of a given Cluster instance
    are defined in a given "cluster document" that
    contains Node details, and inter-Node relationships.
    """

    def __init__(self, id, driver, cluster_type=None, name=None):
        self.id = id # id is actually a context URI
        self.driver = driver
        self.cluster_type = cluster_type
        self.name = name or ''
        self.uuid = self.get_uuid()
        self.nodes = {} 

    def add_node(self, node):
        """Add a Node to this Cluster's "nodes" attribute.

        The "nodes" attribute exists only for the lifetime
        of the Cluster instance, and is not persisted in 
        any way.
        """
        if isinstance(node, (list, tuple)):
            for n in node:
                self.nodes[n.uuid] = n
        else:
            self.nodes[node.uuid] = node

    def get_uuid(self):
        """Unique id, created by hashing Cluster id, and the Node Driver type.
        """
        return hashlib.sha1("%s" % (self.id)).hexdigest() #FIXME
    
    def get_status(self):
        """Cluster status, as return by the Context Broker.
        """
        resp = self.driver.broker_client.get_status(self.id)
        return resp

    def destroy(self):
        """Terminate all Nodes in this Cluster.
        """
        self.driver.destroy_cluster(self)

    def __repr__(self):
        args = (self.uuid, self.name, len(self.nodes.keys()))
        return "Cluster: uuid=%s, name=%s, total nodes=%d" % args


class ClusterDriver(object):
    """Logic to manage resource that make up a Cluster.

    Contains references to the Broker Client,
    and the Node Driver.
    """

    def __init__(self, broker_client=None, node_driver=None):
        self.broker_client = broker_client
        self.node_driver = node_driver

    def create_cluster(self, clusterdoc, context=None, **kwargs):
        """Create a new cluster of nodes

        @keyword    keyname: The name of the key pair
        @type       keyname: C{str}

        @keyword    securitygroup: Name of security group
        @type       securitygroup: C{str}
        """
        
        if isinstance(clusterdoc, str):
            clusterdoc = NimbusClusterDocument(clusterdoc)
        
        if context is None:
            context = self.broker_client.create_context()
        nodes_specs = clusterdoc.build_specs(context)

        cluster = self.new_bare_cluster(id=context.uri)

        for spec in nodes_specs:
            cluster.add_node(self.launch_node_spec(spec, self.node_driver,
                **kwargs))
        
        return cluster

    def new_bare_cluster(self, id):
        return Cluster(id, driver=self)

    def launch_node_spec(self, spec, driver, **kwargs):
        """Launches a single node group.

        Returns a single Node or a list of Nodes.
        """
        node_data = self._create_node_data(spec, driver, **kwargs)
        node = driver.create_node(**node_data)

        if isinstance(node, (list, tuple)):
            for n in node:
                n.ctx_name = spec.name
        else:
            node.ctx_name = spec.name

        return node

    def _create_node_data(self, spec, driver, **kwargs):
        """Utility to get correct form of data to create a Node.
        """
        image = NodeImage(spec.image, spec.name, driver)

        sizes = driver.list_sizes()
        size = None
        for asize in sizes:
            if asize.id == spec.size:
                size = asize
                break
        if size is None:
            raise KeyError("Node size %s not found for driver %s" %
                    (spec.size, self.node_driver))

        node_data = {
            'name':spec.name,
            'size':size,
            'image':image, 
            'ex_mincount':str(spec.count), 
            'ex_maxcount':str(spec.count), 
            'ex_userdata':spec.userdata,
            'ex_keyname':spec.keyname,
        }
        
        node_data.update(kwargs)
        # libcloud doesn't like args with None values
        return dict(pair for pair in node_data.iteritems() if pair[1] is not None)

    def destroy_cluster(self, cluster):
        """Terminate all Nodes from this Cluster.

        """
        for (id, node) in cluster.nodes.iteritems():
            node.destroy()

    def reboot_cluster(self, cluster):
        """Reboot all Nodes from this Cluster.

        """
        for (id, node) in cluster.nodes.iteritems():
            node.destroy()
