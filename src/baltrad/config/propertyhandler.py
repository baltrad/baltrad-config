import socket
import jprops
import tempfile
import re
import os
import shutil

class propertyhandler(object):
  def __init__(self):
    super(propertyhandler, self).__init__()
    self.baltrad_user = "baltrad"
    self.baltrad_group = "baltrad" 
    self.db_username="baltrad"
    self.db_password="baltrad"
    self.db_hostname="localhost"
    self.db_dbname="baltrad"
    self.nodename=socket.gethostname()
    self.nodeaddress="http://127.0.0.1:8080"
    self.keystore_root="/etc/baltrad/bltnode-keys"
    self.keystore_jks="%s/keystore.jks"%self.keystore_root
    self.with_rave = True
    self.dex_uri = "http://localhost:8080/BaltradDex/post_file.htm"
    self.prepare_threshold = -1
    self.bdb_binaries = "/usr/bin"
    self.beast_sql_file_dir = "/usr/share/baltrad/baltrad-beast/sql"
    self.dex_sql_file_dir = "/usr/share/baltrad/baltrad-dex/sql"
    self.bdb_server_type = "cherrypy"
    self.bdb_server_cherrypy_threads = 10
    self.bdb_server_cherrypy_backlog = 5
    self.bdb_server_cherrypy_timeout = 10
    self.bdb_server_uri = "http://localhost:8090"
    self.bdb_server_backend_type = "sqla"
    self.bdb_server_backend_sqla_pool_size = 10
    self.bdb_server_log_level = "INFO"
    self.bdb_server_log_type = "logfile"
    self.bdb_server_log_file = "/var/log/baltrad/baltrad-bdb-server.log"
    self.bdb_server_log_id = "baltrad-bdb-server"
    self.bdb_server_backend_sqla_storage_type = "db"
    self.bdb_server_backend_sqla_storage_fs_path = "/var/lib/baltrad/bdb_storage"
    self.bdb_server_auth_providers = "noauth, keyczar"
    self.baltrad_framepublisher_min_poolsize = 1
    self.baltrad_framepublisher_max_poolsize = 5
    self.baltrad_framepublisher_queuesize = 100
    self.rave_ctpath = ""
    self.rave_pgfs = "4"
    self.rave_loglevel = "info"
    self.rave_logid = "'PGF[rave.%s]'"%self.nodename
    
    self.post_config_scripts = []
    
  def _load_properties(self, cfile):
    with open(cfile, "r") as fp:
      return jprops.load_properties(fp)
    
  def write_config_file(self, config_file):
    with open(config_file, "w") as fp:
      fp.write(str(self))
    os.chmod(config_file,0o600)

  def open_config_file(self, config_file):
    properties = self._load_properties(config_file)
    self.with_rave = properties["baltrad.with.rave"] == "true"
    if "baltrad.user" in properties:
      self.baltrad_user = properties["baltrad.user"]
    if "baltrad.group" in properties:
      self.baltrad_group = properties["baltrad.group"]

    self.db_username = properties["baltrad.db.username"]
    self.db_password = properties["baltrad.db.password"]
    self.db_hostname = properties["baltrad.db.hostname"]
    self.db_dbname = properties["baltrad.db.dbname"]
    
    self.nodename = properties["baltrad.node.name"]
    self.nodeaddress = properties["baltrad.node.address"]
    self.keystore_root = properties["baltrad.keyczar.root"]
    self.keystore_jks = properties["baltrad.keystore.jks"]
    self.dex_uri = properties["baltrad.dex.uri"]
    self.prepare_threshold = int(properties["baltrad.db.jdbc.prepare_threshold"])

    self.bdb_binaries = properties["bdb.binaries"]
    self.beast_sql_file_dir = properties["beast.sql.file.dir"]
    self.dex_sql_file_dir = properties["dex.sql.file.dir"]
    
    self.bdb_server_type = properties["baltrad.bdb.server.type"]
    self.bdb_server_cherrypy_threads = int(properties["baltrad.bdb.server.cherrypy.threads"])
    self.bdb_server_cherrypy_backlog = int(properties["baltrad.bdb.server.cherrypy.backlog"])
    self.bdb_server_cherrypy_timeout = int(properties["baltrad.bdb.server.cherrypy.timeout"])
    self.bdb_server_uri = properties["baltrad.bdb.server.uri"]
    self.bdb_server_backend_type = properties["baltrad.bdb.server.backend.type"]
    self.bdb_server_backend_sqla_pool_size = int(properties["baltrad.bdb.server.backend.sqla.pool_size"])
    self.bdb_server_log_level = properties["baltrad.bdb.server.log.level"]
    self.bdb_server_log_type = properties["baltrad.bdb.server.log.type"]
    self.bdb_server_log_file = properties["baltrad.bdb.server.log.file"]
    self.bdb_server_log_id = properties["baltrad.bdb.server.log.id"]
    self.bdb_server_backend_sqla_storage_type = properties["baltrad.bdb.server.backend.sqla.storage.type"]
    self.bdb_server_backend_sqla_storage_fs_path = properties["baltrad.bdb.server.backend.sqla.storage.fs.path"]
    self.bdb_server_auth_providers = properties["baltrad.bdb.server.auth.providers"]
    
    if "baltrad.framepublisher.min_poolsize" in properties:
      self.baltrad_framepublisher_min_poolsize = int(properties["baltrad.framepublisher.min_poolsize"])
    if "baltrad.framepublisher.max_poolsize" in properties:
      self.baltrad_framepublisher_max_poolsize = int(properties["baltrad.framepublisher.max_poolsize"])
    if "baltrad.framepublisher.queuesize" in properties:
      self.baltrad_framepublisher_queuesize = int(properties["baltrad.framepublisher.queuesize"])
    
    if "rave.ctpath" in properties:
      self.rave_ctpath = properties["rave.ctpath"]
    if "rave.pgfs" in properties:
      self.rave_pgfs = properties["rave.pgfs"]
    if "rave.loglevel" in properties:
      self.rave_loglevel = properties["rave.loglevel"]
    if "rave.logid" in properties:
      self.rave_logid = properties["rave.logid"]
    
    index = 1
    self.post_config_scripts=[]
    while "baltrad.post.config.script.%d"%index in properties:
      self.post_config_scripts.append(properties["baltrad.post.config.script.%d"%index])

  def __str__(self):
    s = "\n# General configuration settings\n"
    s += "# Specifies if rave is installed or not (true, false).\n"
    s += "# Used to know if rave_defines.py should be configured or not.\n"
    s += "baltrad.with.rave = %s\n"%"true" if self.with_rave else "false"
    s += "\n"
    s += "baltrad.user = %s\n"%self.baltrad_user
    s += "baltrad.group = %s\n"%self.baltrad_group
    s += "\n"
    s += "\n# postgres database specifics\n"
    s += "baltrad.db.username = %s\n"%self.db_username
    s += "baltrad.db.password = %s\n"%self.db_password
    s += "baltrad.db.hostname = %s\n"%self.db_hostname
    s += "baltrad.db.dbname = %s\n"%self.db_dbname
    s += "\n"
    s += "baltrad.node.name = %s\n"%self.nodename
    s += "baltrad.node.address = %s\n"%self.nodeaddress
    s += "baltrad.keyczar.root = %s\n"%self.keystore_root
    s += "baltrad.keystore.jks = %s\n"%self.keystore_jks
    s += "baltrad.dex.uri = %s\n"%self.dex_uri
    s += "baltrad.db.jdbc.prepare_threshold = %d\n"%self.prepare_threshold
    s += "\n# dex & beast database script locations\n"
    s += "beast.sql.file.dir=%s\n"%self.beast_sql_file_dir
    s += "dex.sql.file.dir=%s\n"%self.dex_sql_file_dir
    s += "bdb.binaries=%s\n"%self.bdb_binaries
    s += "\n\n"
    s += "#BDB settings\n"
    s += "#baltrad.bdb.server.type = werkzeug\n"
    s += "baltrad.bdb.server.type = %s\n"%self.bdb_server_type
    s += "baltrad.bdb.server.cherrypy.threads = %d\n"%self.bdb_server_cherrypy_threads
    s += "baltrad.bdb.server.cherrypy.backlog = %d\n"%self.bdb_server_cherrypy_backlog
    s += "baltrad.bdb.server.cherrypy.timeout = %d\n"%self.bdb_server_cherrypy_timeout
    s += "baltrad.bdb.server.uri = %s\n"%self.bdb_server_uri
    s += "baltrad.bdb.server.backend.type = %s\n"%self.bdb_server_backend_type
    s += "baltrad.bdb.server.backend.sqla.pool_size = %d\n"%self.bdb_server_backend_sqla_pool_size
    s += "baltrad.bdb.server.log.level = %s\n"%self.bdb_server_log_level
    s += "baltrad.bdb.server.log.type = %s\n"%self.bdb_server_log_type
    s += "baltrad.bdb.server.log.file = %s\n"%self.bdb_server_log_file
    s += "baltrad.bdb.server.log.id = %s\n"%self.bdb_server_log_id
    s += "#baltrad.bdb.server.backend.sqla.storage.type = fs\n"
    s += "baltrad.bdb.server.backend.sqla.storage.type = %s\n"%self.bdb_server_backend_sqla_storage_type
    s += "baltrad.bdb.server.backend.sqla.storage.fs.path = %s\n"%self.bdb_server_backend_sqla_storage_fs_path
    s += "baltrad.bdb.server.auth.providers = %s\n"%self.bdb_server_auth_providers
    s += "baltrad.framepublisher.min_poolsize = %s\n"%self.baltrad_framepublisher_min_poolsize
    s += "baltrad.framepublisher.max_poolsize = %s\n"%self.baltrad_framepublisher_max_poolsize
    s += "baltrad.framepublisher.queuesize = %s\n"%self.baltrad_framepublisher_queuesize
    s += "\n"
    s += "#rave.ctpath=%s\n"%self.rave_ctpath
    s += "rave.pgfs=%s\n"%self.rave_pgfs
    s += "rave.loglevel=%s\n"%self.rave_loglevel
    s += "rave.logid=%s\n"%self.rave_logid
    
    s += "\n\n"
    s += "# Additional post config scripts.\n"
    s += "# These scripts are called as python scripts with the only additional argument pointing at this\n"
    s += "# property file so you can specify more properties in addition to the ones above.\n"
    s += "# The naming of the post config script properties should be baltrad.post.config.script.<N> \n"
    s += "# where N is a sequential number running from 1, and upward (1,2,3....).\n"
    s += "#baltrad.post.config.script.1=..../xyz.py\n"
    s += "#baltrad.post.config.script.2=..../xyz2.py\n"
    for i in range(len(self.post_config_scripts)):
      s += "baltrad.post.config.script.%d = %s\n"%(i+1, self.post_config_scripts[i])    
    
    return s

  def write_bltnode_properties(self, bltnodefile):
    with open(bltnodefile, "w") as fp:
      fp.write("\n#BDB settings\n")
      fp.write("baltrad.bdb.server.type = %s\n"%self.bdb_server_type)
      fp.write("baltrad.bdb.server.cherrypy.threads = %d\n"%self.bdb_server_cherrypy_threads)
      fp.write("baltrad.bdb.server.cherrypy.backlog = %d\n"%self.bdb_server_cherrypy_backlog)
      fp.write("baltrad.bdb.server.cherrypy.timeout = %d\n"%self.bdb_server_cherrypy_timeout)
      fp.write("baltrad.bdb.server.uri = %s\n"%self.bdb_server_uri)
      fp.write("baltrad.bdb.server.backend.type = %s\n"%self.bdb_server_backend_type)
      fp.write("baltrad.bdb.server.backend.sqla.uri = postgresql://%s:%s@%s/%s\n"%(self.db_username,self.db_password,self.db_hostname,self.db_dbname))
      fp.write("baltrad.bdb.server.backend.sqla.pool_size = %d\n"%self.bdb_server_backend_sqla_pool_size)
      fp.write("baltrad.bdb.server.log.level = %s\n"%self.bdb_server_log_level)
      fp.write("baltrad.bdb.server.log.type = %s\n"%self.bdb_server_log_type)
      fp.write("baltrad.bdb.server.log.id = %s\n"%self.bdb_server_log_id)
      fp.write("baltrad.bdb.server.backend.sqla.storage.type = %s\n"%self.bdb_server_backend_sqla_storage_type)
      fp.write("baltrad.bdb.server.backend.sqla.storage.fs.path = %s\n"%self.bdb_server_backend_sqla_storage_fs_path)
      fp.write("baltrad.bdb.server.backend.sqla.storage.fs.layers = 3\n")
      fp.write("baltrad.bdb.server.auth.providers = %s\n"%self.bdb_server_auth_providers)

      fp.write("baltrad.bdb.server.auth.keyczar.keystore_root = %s\n"%self.keystore_root)
      fp.write("baltrad.bdb.server.auth.keyczar.keys.%s = %s.pub\n"%(self.nodename,self.nodename))
      fp.write("\n# BEAST PGF Specific values\n")
      
      fp.write("baltrad.beast.server.url = %s\n"%self.dex_uri)
      fp.write("baltrad.beast.pgf.nodename = %s\n"%self.nodename)
      fp.write("baltrad.beast.pgf.url = http://localhost\n")
      fp.write("baltrad.beast.pgf.key = %s/%s.priv\n"%(self.keystore_root,self.nodename))
      
      fp.write("\n# RAVE PGF Specific values\n")
      fp.write("rave.db.uri=postgresql://%s:%s@%s/%s\n"%(self.db_username,self.db_password,self.db_hostname,self.db_dbname))
    
  def write_dex_properties(self, dexfile):
    with open(dexfile) as fp:
      lines = fp.readlines()
    fp.close()
    (fd, fname) = tempfile.mkstemp()
    fp = os.fdopen(fd, "w")
    for l in lines:
      modline = l
      modline = re.sub("^\s*key.alias\s*=\s*.*","key.alias=%s"%self.nodename,modline)
      modline = re.sub("^\s*node.name\s*=\s*.*","node.name=%s"%self.nodename,modline)
      modline = re.sub("^\s*keystore.directory\s*=\s*.*","keystore.directory=%s"%self.keystore_root,modline)
      modline = re.sub("^\s*node.address\s*=\s*.*","node.address=%s"%self.nodeaddress,modline)
      modline = re.sub("^\s*framepublisher.min_poolsize\s*=\s*.*","framepublisher.min_poolsize=%s"%self.baltrad_framepublisher_min_poolsize,modline)
      modline = re.sub("^\s*framepublisher.max_poolsize\s*=\s*.*","framepublisher.max_poolsize=%s"%self.baltrad_framepublisher_max_poolsize,modline)
      modline = re.sub("^\s*framepublisher.queuesize\s*=\s*.*","framepublisher.queuesize=%s"%self.baltrad_framepublisher_queuesize,modline)
    
      fp.write("%s"%modline)
    fp.close()
 
    shutil.move(fname, dexfile)
    
  def write_dex_db_properties(self, dexdbfile):
    with open(dexdbfile, "w") as fp:
      fp.write("Autogenerated by post config script\n")
      fp.write("db.jar=postgresql-42.1.4.jre6.jar\n")
      fp.write("db.driver=org.postgresql.Driver\n")
      if self.prepare_threshold < 0:
        fp.write("db.url=jdbc:postgresql://%s/%s\n"%(self.db_hostname,self.db_dbname))
      else:
        fp.write("db.url=jdbc:postgresql://%s/%s?prepareThreshold=%i\n"%(self.db_hostname,self.db_dbname,self.prepare_threshold))
      fp.write("db.user=%s\n"%self.db_username)
      fp.write("db.pwd=%s\n"%self.db_password)
    fp.close()

  ##
  # Updates the dex.fc.properties file in the BaltradDex tomcat directory (baltrad.install.3p_root/....)
  # @param properties: the properties to be used
  #
  def write_dex_fc_properties(self, dexfcfile):
    with open(dexfcfile, "w") as fp:
      fp.write("# Autogenerated by install script\n")
      fp.write("database.uri=%s\n"%self.bdb_server_uri)
      fp.write("# File catalog data storage directory\n")
      fp.write("data.storage.folder=%s\n"%self.bdb_server_backend_sqla_storage_fs_path)
      fp.write("# Keyczar key to communicate with node\n")
      fp.write("database.keyczar.key=%s/%s.priv\n"%(self.keystore_root, self.nodename))
      fp.write("# Name of the node\n")
      fp.write("database.keyczar.name=%s\n"%self.nodename)
      
    fp.close()
    
  def update_rave_defines(self, ravedefinesfile, bltnodefile):
    fd = open(ravedefinesfile, "r")
    rows = fd.readlines()
    fd.close()
    nrows = []
    for row in rows:
      if row.startswith("DEX_SPOE"):
        row = "DEX_SPOE = \"%s\"\n"%self.dex_uri
      elif row.startswith("DEX_NODENAME"):
        row = "DEX_NODENAME = \"%s\"\n"%self.nodename
      elif row.startswith("DEX_PRIVATEKEY"):
        row = "DEX_PRIVATEKEY = \"%s/%s.priv\"\n"%(self.keystore_root,self.nodename)
      elif row.startswith("BDB_CONFIG_FILE"):
        row = "BDB_CONFIG_FILE = \"%s\"\n"%bltnodefile
      elif row.startswith("CTPATH") and self.rave_ctpath is not None:
        row = "CTPATH = \"%s\"\n"%self.rave_ctpath
      elif row.startswith("PGFs") and self.rave_pgfs is not None:
        row = "PGFs = %s\n"%self.rave_pgfs
      elif row.startswith("LOGLEVEL") and self.rave_loglevel is not None:
        row = "LOGLEVEL = \"%s\"\n"%self.rave_loglevel
      elif row.startswith("LOGID") and self.rave_logid is not None:
        row = "LOGID = %s\n"%self.rave_logid
      nrows.append(row)    
    fp = open(ravedefinesfile, "w")
    for row in nrows:
      fp.write(row)
    fp.close()
