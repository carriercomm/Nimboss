import hashlib

from libcloud.base import NodeImage, NodeSize
from libcloud.drivers import ec2

from nimboss.nimbus import NimbusClusterDocument
from nimboss.node import NimbusNodeDriver, EC2NodeDriver

class Cluster(object):
    """A Cluster is a collection of Nodes.
    """

    def __init__(self, id, driver, cluster_type=None, name=None):
        self.id = id # id is actually a context URI
        self.driver = driver
        self.cluster_type = cluster_type
        self.name = name or ''
        self.uuid = self.get_uuid()
        self.nodes = {} 

    def add_node(self, node):
        if isinstance(node, (list, tuple)):
            for n in node:
                self.nodes[n.uuid] = n
        else:
            self.nodes[node.uuid] = node

    def create_cluster(self, clusterdoc, context=None):
        self.driver.create_cluster(clusterdoc, context)

    def get_uuid(self):
        return hashlib.sha1("%s:%d" % (self.id, self.driver.node_driver.type)).hexdigest() #FIXME
    
    def get_status(self):
        # this doesn't feel right..
        resp = self.driver.broker_client.get_status(self.id)
        return resp

    def __repr__(self):
        args = (self.uuid, self.name, len(self.nodes.keys()))
        return "Cluster: uuid=%s, name=%s, total nodes=%d" % args


class ClusterDriver(object):
    """Logic to manage a Cluster.

    Key parts:
        - 'BrokerClient' instance.
    """

    def __init__(self, broker_client, node_driver):
        self.broker_client = broker_client
        self.node_driver = node_driver

    def create_cluster(self, clusterdoc, context=None, **kwargs):
        """Create a new cluster of nodes

        @keyword    keyname: The name of the key pair
        @type       keyname: C{str}

        @keyword    securitygroup: Name of security group
        @type       securitygroup: C{str}
        """
        
        nimbuscd = NimbusClusterDocument(clusterdoc) 
        if context is None:
            context = self.broker_client.create_context()
        nodes_specs = nimbuscd.build_specs(context)

        cluster = Cluster(id=context.uri, driver=self)

        for spec in nodes_specs:
            node_data = self._create_node_data(spec, **kwargs)
            new_node = self.node_driver.create_node(**node_data)
            cluster.add_node(new_node)
        
        return cluster 

    def _create_node_data(self, spec, **kwargs):
        image = NodeImage(spec.image, spec.name, self.node_driver)
        sz = ec2.EC2_INSTANCE_TYPES[spec.size] #XXX generalize (for Nimbus, etc)
        size = NodeSize(sz['id'], sz['name'], sz['ram'], sz['disk'], sz['bandwidth'], sz['price'], self.node_driver)
        node_data = {
            'name':spec.name,
            'size':size,
            'image':image, 
            'mincount':str(spec.count), 
            'maxcount':str(spec.count), 
            'userdata':spec.userdata
        }
        node_data.update(kwargs)
        return node_data

    def destroy_cluster(self, cluster):
        for (id, node) in cluster.nodes.iteritems():
            node.destroy()

    def reboot_cluster(self, cluster):
        for (id, node) in cluster.nodes.iteritems():
            node.destroy()


# hmmmm, needed? :
class NimbusClusterDriver(ClusterDriver):
    nodeDriver = NimbusNodeDriver
    create_node = nodeDriver.create_node
    destroy_node = nodeDriver.destroy_node


class EC2ClusterDriver(ClusterDriver):
    nodeDriver = EC2NodeDriver
    create_node = nodeDriver.create_node
    destroy_node = nodeDriver.destroy_node
