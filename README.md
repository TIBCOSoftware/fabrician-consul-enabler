### Consul Enabler User Guide

### Introduction
--------------------------------------
`Consul Enabler` is used with `TIBCO Silver Fabric` to manage a Consul cluster. 
This enabler was developed and tested with Consul version 0.6.3.

This enabler automatically configures a Consul cluster using a shared configuration directory. 
See [Consul] for details about Consul.

### Building the Enabler and Distribution
---------------------------------------------------
This enabler project builds a `Silver Fabric Enabler Grid Library`. It also optionally builds a `Silver Fabric Distribution Grid Library` for Consul database. 
The Silver Fabric Grid Libraries can be built by executing Maven `install`. After a successful build, the Enabler and Distribution Grid Library files 
can be found under project `target` folder. 

To build both the Enabler and Distribution Grid Libraries:

* Download Consul release for 64 bit linux from `https://www.consul.io/downloads.html`. For example,  download v0.6.3 `consul_0.6.3_linux_amd64.zip` to /tmp.
* Run Maven `install` target with Java system property `distribution.location` pointing to the location of down loaded compressed tar file. For example, `-Ddistribution.location=/tmp/consul_0.6.3_linux_amd64.zip`

If you want to build the Enabler Grid LIbrary without building Distribution Grid Library:

* Run Maven `install` target without defining `distribution.location` Java system property

### Installing the Enabler and Distribution
----------------------------------------------------
Installation of the Consul Enabler and Distribution is done by copying the Consul Enabler and Distribution Grid Libraries from the `target` project folder to the 
`SF_HOME/webapps/livecluster/deploy/resources/gridlib` folder on the Silver Fabric Broker. 

### Enabler Features
-------------------------------------------
This Enabler supports following Silver Fabric Features:

* Application Logging Support

### Enabler Statistics
-------------------------------------
This enabler supports no statistics.

### Runtime Context Variables
---------------------------------------
Silver Fabric Components using this enabler can configure following Enabler Runtime Context variables. 

### Runtime Context Variable List:
--------------------------------------------

|Variable Name|Default Value|Type|Description|Export|Auto Increment|
|---|---|---|---|---|---|
|`DATACENTER`|datacenter1|String| Data center name.|false|None|
|`CLUSTER_CONFIG_DIR`||String| Consul cluster configuration shared directory. This is the only variable that is required. .|false|None|
|`NODE_NAME_PREFIX`|node-|String| Consul node name prefix.|false|None|
|`DATA_DIR`|${CONTAINER_WORK_DIR}/consul.data|String| Path to the Consul data directory. Default value is non-persistent across restart.|false|None|
|`CONFIG_FILE`|${CONTAINER_WORK_DIR}/consul.d/config.json|String| Path to the configuration file.|false|None|
|`DEV_MODE`|false|String| Enable development server mode..|false|None|
|`LOG_LEVEL`|INFO|String| Consul log levell.|false|None|
|`HTTP_PORT`|8500|String| This is used by clients to talk to the HTTP API. TCP only..|false|Numeric|
|`HTTPS_PORT`|8543|String| This is used by clients to talk to the HTTP API over SSL. TCP only.|false|Numeric|
|`CLI_RPC_PORT`|8400|String|This is used by all agents to handle RPC from the CLI. TCP only.|false|Numeric|
|`SERVER_RPC_PORT`|8300|String|This is used by servers to handle incoming requests from other agents. TCP only.|false|Numeric|
|`SERF_LAN_PORT`|8330|String|This is used to handle gossip in the LAN. Required by all agents. TCP and UDP..|false|Numeric|
|`SERF_WAN_PORT`|8360|String|This is used by servers to gossip over the WAN to other servers. TCP and UDP.|false|Numeric|
|`DNS_SERVER_PORT`|8600|String|Used to resolve DNS queries. TCP and UDP.|false|Numeric|
|`ENABLE_DEBUG`|false|String|Enable debug.|false|None|
|`ENABLE_SYSLOG`|false|String|Enable syslog.|false|None|
|`ENCRYPT`|false|String|Base 64 encoded 16 byte encryption key used by Consul cluster nodes to encrypt internal network communications.|false|None|
|`CA_FILE`||String|This provides a file path to a PEM-encoded certificate authority.|false|None|
|`CERT_FILE`||String|This provides a file path to a PEM-encoded certificate. Must be used with KEY_FILE.|false|None|
|`KEY_FILE`||String|This provides a the file path to a PEM-encoded private key.|false|None|
|`REAP`|true|String|If this is set to true or false, then it controls reaping regardless of Consul's PID.|false|None|
|`VERIFY_INCOMING`|false|String|If set to true, Consul requires that all incoming connections make use of TLS and that the client provides a certificate signed by the Certificate Authority.|false|None|
|`VERIFY_OUTGOING`|false|String|If set to true, Consul requires that all outgoing connections make use of TLS and that the server provides a certificate that is signed by the Certificate Authority.|false|None|
|`VERIFY_SERVER_HOSTNAME`|false|String|If set to true, Consul verifies for all outgoing connections that the TLS certificate presented by the servers matches server host name.|false|None|
|`CONSUL_DOMAIN`|consul.|String|Consul DNS domain name.|false|None|
|`RECURSOR_DNS_SERVERS`|8.8.8.8|String|This flag provides addresses of upstream DNS servers that are used to recursively resolve queries if they are not inside the service domain for consul.|false|None|
|`ALLOW_STALE`|true|String|Enables a stale query for DNS information. This allows any Consul server, rather than only the leader, to service the request.|false|None|
|`MAX_STALE`|5s|String|This is used to limit how stale DNS results are allowed to be.|false|None|

Following variables are automatically defined and exported by the Enabler :

* `CONSUL_HTTP_ADDRESS` This is the HTTP address of the consul node. The format is http://<host:port>
* `CONSUL_HTTPS_ADDRESS` This is the HTTPS address of consul node. The format is https://<host:port>
* `CONSUL_ADDRESS` This is the consul address of the node. The format is consul://<host:port>
* `CONSUL_DNS_ADDRESS` This is the DNS server address of the node. The format is <host:port>

### Component and Stack Examples
-----------------------------------------------
Below is a screenshot image from an example Consul cluster Component defined in Silver Fabric. 

* [Consul Cluster Component] (images/consul-cluster-component.png)

Below is a screenshot image from an example Consul cluster Stack defined in Silver Fabric. 
This example defines a cluster of size 1. The cluster size is specified in the Stack. 

It is best to run no more than one Consul node on a single host. This is configured in the Component and the Stack. In the Component it is 
configured by specifying `Maximum Instances Per Host` option and in the Stack this is using through a resource preference
rule for a specific Silver Fabric Engine Instance, for example, 0.

* [Consul Cluster Stack] (images/consul-cluster-stack.png)


[Consul]:<https://www.consul.io/intro/index.html> 