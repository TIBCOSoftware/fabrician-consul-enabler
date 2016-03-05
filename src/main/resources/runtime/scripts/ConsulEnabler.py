import os
import time
import sys
import os.path
import stat
import re
import ast
from subprocess import call
from subprocess import call, Popen, PIPE

from java.lang import Boolean

from com.datasynapse.fabric.util import ContainerUtils
from com.datasynapse.fabric.common import RuntimeContextVariable
from com.datasynapse.fabric.common import ActivationInfo


class Consul:
    
    def __init__(self, additionalVariables):
        " initialize consul cluster member"
        
        self.__clusterConfigDir = getVariableValue("CLUSTER_CONFIG_DIR")
        
        if not self.__clusterConfigDir:
            raise Exception("CLUSTER_CONFIG_DIR variable is required")
        
        componentName = proxy.container.currentDomain.name
        self.__clusterConfigDir = os.path.join(self.__clusterConfigDir, componentName)
       
        self.__listenAddress = getVariableValue("LISTEN_ADDRESS")
        self.__nodeName = getVariableValue("NODE_NAME_PREFIX", "node-") + self.__listenAddress.replace('.', '-') + "-"+ getVariableValue("ENGINE_INSTANCE")
        additionalVariables.add(RuntimeContextVariable("NODE_NAME", self.__nodeName, RuntimeContextVariable.STRING_TYPE, "Consul node name", False, RuntimeContextVariable.NO_INCREMENT))
        
        self.__workDir = getVariableValue("CONTAINER_WORK_DIR")
        changePermissions(self.__workDir)
        
        self.__rpcAddr = self.__listenAddress + ":" + getVariableValue("CLI_RPC_PORT")
        self.__serfAddr = self.__listenAddress + ":" + getVariableValue("SERF_LAN_PORT")
        self.__httpAddr = self.__listenAddress + ":" + getVariableValue("HTTP_PORT")
        self.__dnsAddr = self.__listenAddress + ":" + getVariableValue("DNS_SERVER_PORT")
        
        self.__lockExpire = int(getVariableValue("LOCK_EXPIRE", "300000"))
        self.__lockWait = int(getVariableValue("LOCK_WAIT", "30000"))
        self.__staleWait = int(getVariableValue("STALE_CONFIG_WAIT", "300"))
        
        self.__lock()
        mkdir_p(self.__clusterConfigDir)
        self.__unlock()
        
        additionalVariables.add(RuntimeContextVariable("CONSUL_HTTP_ADDRESS", "http://"+self.__httpAddr, RuntimeContextVariable.STRING_TYPE, "Consul Http address", True, RuntimeContextVariable.NO_INCREMENT))
        keyFile = getVariableValue("KEY_FILE")
        certFile = getVariableValue("CERT_FILE")
        self.__httpsAddr = None
        if keyFile and certFile:
            self.__httpsAddr = self.__listenAddress + ":" + getVariableValue("HTTPS_PORT")
            additionalVariables.add(RuntimeContextVariable("CONSUL_HTTPS_ADDRESS", "https://"+self.__httpsAddr, RuntimeContextVariable.STRING_TYPE, "Consul Https address", True, RuntimeContextVariable.NO_INCREMENT))
        
        additionalVariables.add(RuntimeContextVariable("CONSUL_DNS_ADDRESS", self.__dnsAddr, RuntimeContextVariable.STRING_TYPE, "Consul DNS address", True, RuntimeContextVariable.NO_INCREMENT))
        additionalVariables.add(RuntimeContextVariable("CONSUL_ADDRESS", "consul://" + self.__httpAddr, RuntimeContextVariable.STRING_TYPE, "Consul  address", True, RuntimeContextVariable.NO_INCREMENT))
    
    def __isNodeUp(self):
        file = None
        alive = False
        
        try:
            path = os.path.join(self.__workDir , "curl.out")
            file2 = open(path, "w")
        
            path = os.path.join(self.__workDir , "node.out")
            file = open(path, "w")
            
            cmdList = ["curl", "http://" + self.__httpAddr + "/v1/agent/self"]
      
            retcode = call(cmdList, stdout=file, stderr=file2)
            file.close()
            file = open(path, "r")
            lines = file.readlines()
           
            if lines and len(lines) >0:
                json = lines[0]
                map=parseJson(json)
                map = map["Config"]
                alive = (self.__nodeName == map["NodeName"])
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("isNodeAlive error:" + `value`)
        finally:
            if file:
                file.close()
                
        return alive
    
    def __getMembers(self):
        file = None
        members=[]
        
        try:
            path = os.path.join(self.__workDir , "curl.out")
            file2 = open(path, "w")
        
            path = os.path.join(self.__workDir , "agent.out")
            file = open(path, "w")
            
            cmdList = ["curl", "http://" + self.__httpAddr + "/v1/agent/members"]
      
            retcode = call(cmdList, stdout=file, stderr=file2)
            file.close()
            file = open(path, "r")
            lines = file.readlines()
           
            if lines and len(lines) >0:
                json = lines[0]
                memberList=parseJson(json)
                for member in memberList:
                    members.append(member["Addr"] + ":"+ str(member["Port"]))
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("getMembers error:" + `value`)
        finally:
            if file:
                file.close()
                
        return members
    
    def __join(self, serfAddr):
        try:
            cmd = os.path.join(self.__workDir, "consul")
            cmdlist = [cmd, "join", "-rpc-addr", self.__rpcAddr, serfAddr]
            logger.info("Executing:" + list2str(cmdlist))
            retcode = call(cmdlist)
            logger.info("Return code:" + `retcode`)
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("join error:" + `value`)
            
    def __leave(self):
        try:
            cmd = os.path.join(self.__workDir, "consul")
            cmdlist = [cmd, "leave", "-rpc-addr", self.__rpcAddr]
            logger.info("Executing:" + list2str(cmdlist))
            retcode = call(cmdlist)
            logger.info("Return code:" + `retcode`)
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("leave error:" + `value`)
    
    def __readConfig(self, path):
        "read server id information from file"
        file = None
        config = None
        try:
            if os.path.isfile(path):
                file = open(path, "r")
                lines = file.readlines()
                for line in lines:
                    config = line.strip()
                    break;
        finally:
            if file:
                file.close()
                
        return config
    
    def __writeConfig(self, path, config):
        "write  config"
        
        file = None
        try:
            file = open(path, "w")
            file.write(config + "\n")
        finally:
            if file:
                file.close()
                
    def __getConsulCluster(self):
        "get consul cluster address"
        
        consulCluster = []
                
        list = os.listdir(self.__clusterConfigDir)
        for name in list:
            path = os.path.join(self.__clusterConfigDir, name)
                
            if name[:5] == "serf.":
                if time.time() - os.path.getmtime(path) > self.__staleWait:
                    logger.info("Removing stale consul configuration file:" + path)
                    os.remove(path)
                else:
                    logger.fine('Reading consul configuration:' + path)
                    serverConfig = self.__readConfig(path)
                    
                    if serverConfig:
                        consulCluster.append(serverConfig)
        
        logger.fine("Expected Consul cluster:" + str(consulCluster))
        return consulCluster
        
    def __lock(self):
        "get global lock"
        self.__locked = ContainerUtils.acquireGlobalLock(self.__clusterConfigDir, self.__lockExpire, self.__lockWait)
        if not self.__locked:
            raise Exception("Unable to acquire global lock:" + self.__clusterConfigDir)
    
    def __unlock(self):
        "unlock global lock"
        if self.__locked:
            ContainerUtils.releaseGlobalLock(self.__clusterConfigDir)
            self.__locked = None
            
    def isNodeRunning(self):
        " is node running"
        
        running = False
        try:
            self.__lock()
            running = self.__isNodeUp()
                
            if running:
                path = os.path.join(self.__clusterConfigDir, "serf." + self.__nodeName)
                self.__writeConfig(path, self.__serfAddr)
                path = os.path.join(self.__clusterConfigDir, "http." + self.__nodeName)
                self.__writeConfig(path, self.__httpAddr)
                
                if self.__httpsAddr:
                    path = os.path.join(self.__clusterConfigDir, "https." + self.__nodeName)
                    self.__writeConfig(path, self.__httpsAddr)
                    
                cluster = self.__getConsulCluster()
                members = self.__getMembers()
                for serfAddr in cluster:
                    if not (serfAddr in members):
                        self.__join(serfAddr)
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("isNodeRunning error:" + `value`)
        finally:
            self.__unlock()
     
        return running
                    
    def hasNodeStarted(self):
        " has node started"
        return self.isNodeRunning()

    def cleanup(self):
        try:
            path = os.path.join(self.__clusterConfigDir, "serf." + self.__nodeName)
            if os.path.isfile(path):
                os.remove(path)
                
            path = os.path.join(self.__clusterConfigDir, "http." + self.__nodeName)
            if os.path.isfile(path):
                os.remove(path)
                
            path = os.path.join(self.__clusterConfigDir, "https." + self.__nodeName)
            if os.path.isfile(path):
                os.remove(path)
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("cleanup error:" + `value`)
            
    def shutdownNode(self):
        "shutdown node"
        try:
            self.__leave()
        finally:
            proxy.doShutdown()
    
    def startNode(self):
        "start node"
        try:
            self.__lock()
            if not self.__isNodeUp():
                cmd = os.path.join(self.__workDir, "consul")
                configFile = getVariableValue("CONFIG_FILE")
                consulDomain = getVariableValue("CONSUL_DOMAIN")
            
                activationInfo = proxy.container.getActivationInfo()
                componentInstance = int(activationInfo.getProperty(ActivationInfo.COMPONENT_INSTANCE))
                
                if componentInstance == 0:
                    cmdlist = [cmd, "agent", "-server", "--bootstrap-expect", "1", "-config-file", configFile, "-ui", "-domain", consulDomain]
                else:
                    cmdlist = [cmd, "agent", "-server",  "-config-file", configFile, "-ui", "-domain", consulDomain]
                logger.info("Executing:" + list2str(cmdlist))
                Popen(cmdlist)
            else:
                logger.info("Not starting node because it is already alive!")
        finally:
            self.__unlock()
            
    def installActivationInfo(self, info):
        "install activation info"

        host = getVariableValue("ENGINE_USERNAME")
        
        if self.__httpAddr:
            httpEndpoint = "http://" + self.__httpAddr.replace(self.__listenAddress, host) + "/v1/"
            info.setProperty("ConsulAPIHttpEndpoint", httpEndpoint)
            httpEndpoint = "http://" + self.__httpAddr.replace(self.__listenAddress, host) + "/ui"
            info.setProperty("ConsulUIHttpEndpoint", httpEndpoint)
        
        if self.__httpsAddr:
            httpsEndpoint = "https://" + self.__httpsAddr.replace(self.__listenAddress, host) + "/v1/"
            info.setProperty("ConsulAPIHttpsEndpoint", httpsEndpoint)
            httpsEndpoint = "https://" + self.__httpsAddr.replace(self.__listenAddress, host) + "/ui"
            info.setProperty("ConsulUIHttpsEndpoint", httpsEndpoint)
            
        dnsAddr = self.__dnsAddr.replace(self.__listenAddress, host) 
        info.setProperty("ConsulDnsAddress", httpEndpoint)
            
def parseJson(json):
    json=json.replace('null','None')
    json=json.replace('false','False')
    json=json.replace('true','True')
    jsonObject=ast.literal_eval(json.strip())
    return jsonObject
    
def parseJsonDictionary(map, select, output):
    for key,value in map.iteritems():
        if key == select:
            output.append(value)
        elif type(value) is dict:
            parseJsonDictionary(value,select, output)
        elif type(value) is list:
            parseJsonList(value, select, output)

def parseJsonList(itemlist, select, output):
    for item in itemlist:
        if type(item) is dict:
            parseJsonDictionary(item, select, output)
        elif type(item) is list:
            parseJsonList(item, select, output)
            
def list2str(list):
    content = str(list).strip('[]')
    content = content.replace(",", " ")
    content = content.replace("u'", "")
    content = content.replace("'", "")
    return content

def mkdir_p(path, mode=0700):
    if not os.path.isdir(path):
        logger.info("Creating directory:" + path)
        os.makedirs(path, mode)
                    
def copyContainerEnvironment():
    count = runtimeContext.variableCount
    for i in range(0, count, 1):
        rtv = runtimeContext.getVariable(i)
        if rtv.type == "Environment":
            os.environ[rtv.name] = rtv.value
    
    os.unsetenv("LD_LIBRARY_PATH")
    os.unsetenv("LD_PRELOAD")
              
def getVariableValue(name, value=None):
    "get runtime variable value"
    var = runtimeContext.getVariable(name)
    if var != None:
        value = var.value
    
    return value

def changePermissions(dir):
    logger.info("chmod:" + dir)
    os.chmod(dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
      
    for dirpath, dirnames, filenames in os.walk(dir):
        for dirname in dirnames:
            dpath = os.path.join(dirpath, dirname)
            os.chmod(dpath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
           
        for filename in filenames:
               filePath = os.path.join(dirpath, filename)
               os.chmod(filePath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                
def doInit(additionalVariables):
    "do init"
    consul = Consul(additionalVariables)
    consulRcv = RuntimeContextVariable("CONSUL_OBJECT", consul, RuntimeContextVariable.OBJECT_TYPE)
    runtimeContext.addVariable(consulRcv)

def doShutdown():
    "do shutdown"
    logger.info("Enter ConsulEnabler:doShutdown")
    try:
        consul = getVariableValue("CONSUL_OBJECT")
        if consul:
            consul.shutdownNode()
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("ConsulEnabler:doShutdown:" + `value`)
    
    logger.info("Exit ConsulEnabler:doShutdown")
    
def doStart():
    "do start"
    logger.info("Enter ConsulEnabler:doStart")
    
    consul = getVariableValue("CONSUL_OBJECT")
    if consul:
        consul.startNode()
    
    logger.info("Exit ConsulEnabler:doStart")

def hasContainerStarted():
    logger.info("Enter ConsulEnabler:hasContainerStarted")
    started = False
    try:
        consul = getVariableValue("CONSUL_OBJECT")
        
        if consul:
            started = consul.hasNodeStarted()
            
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in ConsulEnabler:hasContainerStarted:" + `value`)
    logger.info("Exit ConsulEnabler:hasContainerStarted")
    return started
    
def isContainerRunning():
    running = False
    try:
        consul = getVariableValue("CONSUL_OBJECT")
        if consul:
            running = consul.isNodeRunning()
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in ConsulEnabler:isContainerRunning:" + `value`)
    
    return running

def doInstall(info):
    " do install of activation info"

    logger.info("doInstall:Enter")
    try:
        consul = getVariableValue("CONSUL_OBJECT")
        if consul:
            consul.installActivationInfo(info)
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in ConsulEnabller:doInstall:" + `value`)
    finally:
        proxy.doInstall(info)
        
    logger.info("doInstall:Exit")

def cleanupContainer():
    try:
        consul = getVariableValue("CONSUL_OBJECT")
        if consul:
            consul.cleanup()
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in ConsulEnabler:cleanup:" + `value`)
    finally:
        proxy.cleanupContainer()
        

def getContainerStartConditionPollPeriod():
    poll = getVariableValue("START_POLL_PERIOD", "10000")
    return int(poll)
    
def getContainerRunningConditionPollPeriod():
    poll = getVariableValue("RUNNING_POLL_PERIOD", "60000")
    return int(poll)

