#!/usr/bin/env python3
'''
Copyright (C) 2021 - Swedish Meteorological and Hydrological Institute (SMHI)

This file is part of baltrad-config.

baltrad-config is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

baltrad-config is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with baltrad-config.  If not, see <http://www.gnu.org/licenses/>.

'''
import socket
import baltradutils.jprops
import tempfile
import re
import os
import shutil
import time
import difflib

class propertyhandler(object):
  def __init__(self):
    super(propertyhandler, self).__init__()
    self.baltrad_user = "baltrad"
    self.baltrad_group = "baltrad" 
    self.db_username="baltrad"
    self.db_password="baltrad"
    self.db_hostname="localhost"
    self.db_dbname="baltrad"
    self.db_pool_size=10

    self.nodename=socket.gethostname()
    self.nodeaddress="http://127.0.0.1:8080"
    self.keystore_root="/etc/baltrad/bltnode-keys"
    self.keystore_jks="%s/keystore.jks"%self.keystore_root
    self.keystore_pwd="secret"

    self.ajp_connector_enabled=False
    self.ajp_connector_secret_required=False
    self.ajp_connector_secret=""
    self.ajp_connector_address="::1"
    self.ajp_connector_port=8009
    self.ajp_connector_redirectPort=8443
    
    self.extra_fwd_port=""
    
    self.with_rave = True
    self.dex_uri = "http://localhost:8080/BaltradDex"
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
    self.bdb_server_backend_fs_layers = 3
    self.bdb_server_backend_cachesize = 5000
    self.bdb_server_backend_sqla_storage_fs_path = "/var/lib/baltrad/bdb_storage"
    self.bdb_server_auth_providers = "noauth, keyczar"
    self.bdb_client_rest_maxconnections = 20
    self.bdb_client_rest_cachesize = 7000
    self.baltrad_framepublisher_min_poolsize = 1
    self.baltrad_framepublisher_max_poolsize = 5
    self.baltrad_framepublisher_queuesize = 100
    
    self.beast_admin_mailer_enabled = False
    self.beast_admin_mailer_encoding = "UTF-8"
    self.beast_admin_mailer_host = "localhost"
    self.beast_admin_mailer_port = 25
    self.beast_admin_mailer_username = ""
    self.beast_admin_mailer_password = ""
    self.beast_admin_mailer_from = ""
    self.beast_admin_mailer_transport_protocol = "smtp"
    self.beast_admin_mailer_smtp_auth = False
    self.beast_admin_mailer_smtp_starttls_enable = False

    self.beast_cli_administration_enabled = False

    self.beast_pooled_publisher_pool_core_size = 1
    self.beast_pooled_publisher_pool_max_size = 5
    self.beast_pooled_publisher_queue_size = 100

    self.beast_manager_number_executors = 10

    self.rave_ctpath = ""
    self.rave_pgfs = "4"
    self.rave_pgf_tasks_per_worker = 100
    self.rave_loglevel = "info"
    self.rave_logid = "'PGF[rave.%s]'"%self.nodename
    self.rave_centerid="ORG:82"
    self.rave_qitotalmethod="minimum"
    self.rave_scansun_out_path = ""
    self.rave_pgf_compositing_use_lazy_loading = False
    self.rave_pgf_compositing_use_lazy_loading_preloads = False
    
    self.rave_pgf_tiledcompositing_nrprocesses = None
    self.rave_pgf_tiledcompositing_timeout = 290
    self.rave_pgf_tiledcompositing_allow_missing_tiles = False

    self.post_config_scripts = []
    
  def _load_properties(self, cfile):
    with open(cfile, "r") as fp:
      return baltradutils.jprops.load_properties(fp)
    
  def write_config_file(self, config_file):
    with open(config_file, "w") as fp:
      fp.write(str(self))
    os.chmod(config_file,0o600)

  def str_to_bool(self, s):
    if s is not None:
      if s.lower() in ["true", "1", "yes", "y", "t"]:
        return True
    return False 

  def str_to_int_or_none(self, s):
    try:
      return int(s)
    except:
      return None

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
    if "baltrad.db.pool.size" in properties:
      self.db_pool_size = int(properties["baltrad.db.pool.size"])

    self.nodename = properties["baltrad.node.name"]
    self.nodeaddress = properties["baltrad.node.address"]
    self.keystore_root = properties["baltrad.keyczar.root"]
    self.keystore_jks = properties["baltrad.keystore.jks"]
    if "baltrad.keystore.password" in properties:
      self.keystore_pwd = properties["baltrad.keystore.password"]

    if "baltrad.ajp.connector.enabled" in properties:
      self.ajp_connector_enabled = self.str_to_bool(properties["baltrad.ajp.connector.enabled"])

    if "baltrad.ajp.connector.secret_required" in properties:
      self.ajp_connector_secret_required = self.str_to_bool(properties["baltrad.ajp.connector.secret_required"])
      
    if "baltrad.ajp.connector.secret" in properties:
      self.ajp_connector_secret = properties["baltrad.ajp.connector.secret"]
    
    if "baltrad.ajp.connector.address" in properties:
      self.ajp_connector_address = properties["baltrad.ajp.connector.address"]

    if "baltrad.ajp.connector.port" in properties:
      self.ajp_connector_port = int(properties["baltrad.ajp.connector.port"])

    if "baltrad.ajp.connector.redirect_port" in properties:
      self.ajp_connector_redirectPort = int(properties["baltrad.ajp.connector.redirect_port"])
    
    if "baltrad.extra.fwd.port" in properties:
      self.extra_fwd_port = properties["baltrad.extra.fwd.port"]
    
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
    
    if "baltrad.bdb.server.log.file" in properties:
      self.bdb_server_log_file = properties["baltrad.bdb.server.log.file"]
    
    self.bdb_server_log_id = properties["baltrad.bdb.server.log.id"]
    self.bdb_server_backend_sqla_storage_type = properties["baltrad.bdb.server.backend.sqla.storage.type"]
    self.bdb_server_backend_sqla_storage_fs_path = properties["baltrad.bdb.server.backend.sqla.storage.fs.path"]
    if "baltrad.bdb.server.backend.sqla.storage.fs.layers" in properties:
      self.bdb_server_backend_fs_layers = int(properties["baltrad.bdb.server.backend.sqla.storage.fs.layers"])
    if "baltrad.bdb.server.backend.sqla.storage.db.cachesize" in properties:
      self.bdb_server_backend_cachesize = int(properties["baltrad.bdb.server.backend.sqla.storage.db.cachesize"])

    self.bdb_server_auth_providers = properties["baltrad.bdb.server.auth.providers"]

    if "baltrad.bdb.client.rest.maxconnections" in properties:
      self.bdb_client_rest_maxconnections = int(properties["baltrad.bdb.client.rest.maxconnections"])
    if "baltrad.bdb.client.rest.cachesize" in properties:
      self.bdb_client_rest_cachesize = int(properties["baltrad.bdb.client.rest.cachesize"])
    
    if "baltrad.framepublisher.min_poolsize" in properties:
      self.baltrad_framepublisher_min_poolsize = int(properties["baltrad.framepublisher.min_poolsize"])
    if "baltrad.framepublisher.max_poolsize" in properties:
      self.baltrad_framepublisher_max_poolsize = int(properties["baltrad.framepublisher.max_poolsize"])
    if "baltrad.framepublisher.queuesize" in properties:
      self.baltrad_framepublisher_queuesize = int(properties["baltrad.framepublisher.queuesize"])

    if "beast.admin.mailer.enabled" in properties:
      self.beast_admin_mailer_enabled = properties["beast.admin.mailer.enabled"] == "true"
    if "beast.admin.mailer.encoding" in properties:
      self.beast_admin_mailer_encoding = properties["beast.admin.mailer.encoding"]
    if "beast.admin.mailer.host" in properties:
      self.beast_admin_mailer_host = properties["beast.admin.mailer.host"]
    if "beast.admin.mailer.port" in properties:
      self.beast_admin_mailer_port = int(properties["beast.admin.mailer.port"])
    if "beast.admin.mailer.username" in properties:
      self.beast_admin_mailer_username = properties["beast.admin.mailer.username"]
    if "beast.admin.mailer.password" in properties:
      self.beast_admin_mailer_password = properties["beast.admin.mailer.password"]
    if "beast.admin.mailer.from" in properties:
      self.beast_admin_mailer_from = properties["beast.admin.mailer.from"]
    if "beast.admin.mailer.transport.protocol" in properties:
      self.beast_admin_mailer_transport_protocol = properties["beast.admin.mailer.transport.protocol"]
    if "beast.admin.mailer.smtp.auth" in properties:
      self.beast_admin_mailer_smtp_auth = properties["beast.admin.mailer.smtp.auth"] == "true"
    if "beast.admin.mailer.smtp.starttls.enable" in properties:
      self.beast_admin_mailer_smtp_starttls_enable = properties["beast.admin.mailer.smtp.starttls.enable"] == "true"

    if "beast.cli.administration.enabled" in properties:
      self.beast_cli_administration_enabled = properties["beast.cli.administration.enabled"] == "true"

    if "beast.pooled.publisher.pool.core.size" in properties:
      self.beast_pooled_publisher_pool_core_size = int(properties["beast.pooled.publisher.pool.core.size"])
    if "beast.pooled.publisher.pool.max.size" in properties:
      self.beast_pooled_publisher_pool_max_size = int(properties["beast.pooled.publisher.pool.max.size"])
    if "beast.pooled.publisher.queue.size" in properties:
      self.beast_pooled_publisher_queue_size = int(properties["beast.pooled.publisher.queue.size"])

    if "beast.manager.number.executors" in properties:
      self.beast_manager_number_executors = int(properties["beast.manager.number.executors"])

    if "rave.ctpath" in properties:
      self.rave_ctpath = properties["rave.ctpath"]
    if "rave.pgfs" in properties:
      self.rave_pgfs = properties["rave.pgfs"]
    if "rave.pgf.tasks.per.worker" in properties:
      self.rave_pgf_tasks_per_worker = int(properties["rave.pgf.tasks.per.worker"])
    if "rave.loglevel" in properties:
      self.rave_loglevel = properties["rave.loglevel"]
    if "rave.logid" in properties:
      self.rave_logid = properties["rave.logid"]
    if "rave.centerid" in properties:
      self.rave_centerid = properties["rave.centerid"]
    if "rave.qitotalmethod" in properties:
      self.rave_qitotalmethod = properties["rave.qitotalmethod"]
    if "rave.scansunout" in properties:
      self.rave_scansun_out_path = properties["rave.scansunout"]
    if "rave.pgf.compositing.use_lazy_loading" in properties:
      self.rave_pgf_compositing_use_lazy_loading = properties["rave.pgf.compositing.use_lazy_loading"]
    if "rave.pgf.compositing.use_lazy_loading_preloads" in properties:
      self.rave_pgf_compositing_use_lazy_loading_preloads = properties["rave.pgf.compositing.use_lazy_loading_preloads"]

    if "rave.pgf.tiledcompositing.nrprocesses" in properties:
      tmpstr = properties["rave.pgf.tiledcompositing.nrprocesses"]
      self.rave_pgf_tiledcompositing_nrprocesses = self.str_to_int_or_none(tmpstr)
    if "rave.pgf.tiledcompositing.timeout" in properties:
      self.rave_pgf_tiledcompositing_timeout = int(properties["rave.pgf.tiledcompositing.timeout"])
    if "rave.pgf.tiledcompositing.allow_missing_tiles" in properties:
      self.rave_pgf_tiledcompositing_allow_missing_tiles = self.str_to_bool(properties["rave.pgf.tiledcompositing.allow_missing_tiles"])

    index = 1
    self.post_config_scripts=[]
    while "baltrad.post.config.script.%d"%index in properties:
      self.post_config_scripts.append(properties["baltrad.post.config.script.%d"%index])
      index = index + 1

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
    s += "baltrad.db.pool.size = %d\n"%self.db_pool_size
    s += "\n"
    s += "baltrad.node.name = %s\n"%self.nodename
    s += "baltrad.node.address = %s\n"%self.nodeaddress
    s += "baltrad.keyczar.root = %s\n"%self.keystore_root
    s += "baltrad.keystore.jks = %s\n"%self.keystore_jks
    s += "baltrad.keystore.password = %s\n"%self.keystore_pwd
    
    s += "baltrad.ajp.connector.enabled = %s\n"%str(self.ajp_connector_enabled).lower()
    s += "baltrad.ajp.connector.secret_required = %s\n"%str(self.ajp_connector_secret_required).lower()
    s += "baltrad.ajp.connector.secret = %s\n"%self.ajp_connector_secret
    s += "baltrad.ajp.connector.address = %s\n"%self.ajp_connector_address
    s += "baltrad.ajp.connector.port = %d\n"%self.ajp_connector_port
    s += "baltrad.ajp.connector.redirect_port = %d\n"%self.ajp_connector_redirectPort

    s += "\n"
    s += "# If there is some sort of forwarding to the node which remaps for example port 80 to 8080 and 443 to 8443.\n"
    s += "# Then add, from-port and to port like baltrad.extra.fwd.port=80,443\n"
    s += "baltrad.extra.fwd.port=%s\n"%self.extra_fwd_port
    s += "\n"

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
    s += "baltrad.bdb.server.backend.sqla.storage.fs.layers = %d\n"%self.bdb_server_backend_fs_layers
    s += "baltrad.bdb.server.backend.sqla.storage.db.cachesize = %d\n"%self.bdb_server_backend_cachesize
    s += "baltrad.bdb.server.auth.providers = %s\n"%self.bdb_server_auth_providers
    s += "\n"
    s += "baltrad.bdb.client.rest.maxconnections = %d\n"%self.bdb_client_rest_maxconnections
    s += "baltrad.bdb.client.rest.cachesize = %d\n"%self.bdb_client_rest_cachesize
    s += "\n"
    s += "baltrad.framepublisher.min_poolsize = %s\n"%self.baltrad_framepublisher_min_poolsize
    s += "baltrad.framepublisher.max_poolsize = %s\n"%self.baltrad_framepublisher_max_poolsize
    s += "baltrad.framepublisher.queuesize = %s\n"%self.baltrad_framepublisher_queuesize
    s += "\n"
    s += "#BEAST settings\n"
    s += "beast.admin.mailer.enabled = %s\n"%("true" if self.beast_admin_mailer_enabled else "false")
    s += "beast.admin.mailer.encoding = %s\n"%self.beast_admin_mailer_encoding
    s += "beast.admin.mailer.host = %s\n"%self.beast_admin_mailer_host
    s += "beast.admin.mailer.port = %s\n"%self.beast_admin_mailer_port
    s += "beast.admin.mailer.username = %s\n"%self.beast_admin_mailer_username
    s += "beast.admin.mailer.password = %s\n"%self.beast_admin_mailer_password
    s += "beast.admin.mailer.from = %s\n"%self.beast_admin_mailer_from
    s += "beast.admin.mailer.transport.protocol = %s\n"%self.beast_admin_mailer_transport_protocol
    s += "beast.admin.mailer.smtp.auth = %s\n"%("true" if self.beast_admin_mailer_smtp_auth else "false")
    s += "beast.admin.mailer.smtp.starttls.enable = %s\n"%("true" if self.beast_admin_mailer_smtp_starttls_enable else "false")
    s += "\n"
    s += "beast.cli.administration.enabled = %s\n"%("true" if self.beast_cli_administration_enabled else "false")
    s += "\n"
    s += "#BEAST exchange pool settings\n"
    s += "beast.pooled.publisher.pool.core.size = %d\n"%self.beast_pooled_publisher_pool_core_size
    s += "beast.pooled.publisher.pool.max.size = %d\n"%self.beast_pooled_publisher_pool_max_size
    s += "beast.pooled.publisher.queue.size = %d\n"%self.beast_pooled_publisher_queue_size
    s += "\n"
    s += "#BEAST message manager settings\n"
    s += "beast.manager.number.executors = %d\n"%self.beast_manager_number_executors
    s += "\n"
    s += "#rave.ctpath=%s\n"%self.rave_ctpath
    s += "rave.pgfs=%s\n"%self.rave_pgfs
    s += "rave.pgf.tasks.per.worker=%d\n"%self.rave_pgf_tasks_per_worker
    s += "rave.loglevel=%s\n"%self.rave_loglevel
    s += "rave.logid=%s\n"%self.rave_logid
    s += "rave.centerid=%s\n"%self.rave_centerid
    s += "rave.qitotalmethod=%s\n"%self.rave_qitotalmethod
    if not self.rave_scansun_out_path:
      s += "rave.scansunout=\n"
    else:
      s += "rave.scansunout=%s\n"%self.rave_scansun_out_path
    s += "rave.pgf.compositing.use_lazy_loading=%s\n"%self.rave_pgf_compositing_use_lazy_loading
    s += "rave.pgf.compositing.use_lazy_loading_preloads=%s\n"%self.rave_pgf_compositing_use_lazy_loading_preloads
    if self.rave_pgf_tiledcompositing_nrprocesses is not None:
      s += "rave.pgf.tiledcompositing.nrprocesses=%d\n"%self.rave_pgf_tiledcompositing_nrprocesses
    else:
      s += "rave.pgf.tiledcompositing.nrprocesses=None\n"
    s += "rave.pgf.tiledcompositing.timeout=%d\n"%self.rave_pgf_tiledcompositing_timeout
    s += "rave.pgf.tiledcompositing.allow_missing_tiles=%s\n"%("true" if self.rave_pgf_tiledcompositing_allow_missing_tiles else "false")
    
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
      fp.write("baltrad.bdb.server.backend.sqla.storage.fs.layers = %d\n"%self.bdb_server_backend_fs_layers)
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
      fp.write("#Autogenerated by post config script\n")
      fp.write("db.jar=postgresql-42.1.4.jre6.jar\n")
      fp.write("db.driver=org.postgresql.Driver\n")
      if self.prepare_threshold < 0:
        fp.write("db.url=jdbc:postgresql://%s/%s\n"%(self.db_hostname,self.db_dbname))
      else:
        fp.write("db.url=jdbc:postgresql://%s/%s?prepareThreshold=%i\n"%(self.db_hostname,self.db_dbname,self.prepare_threshold))
      fp.write("db.user=%s\n"%self.db_username)
      fp.write("db.pwd=%s\n"%self.db_password)
      fp.write("db.pool.size=%d\n"%self.db_pool_size)

    fp.close()

  ##
  # Updates the dex.fc.properties file in the BaltradDex tomcat directory (baltrad.install.3p_root/....)
  # @param properties: the properties to be used
  #
  def write_dex_fc_properties(self, dexfcfile):
    with open(dexfcfile, "w") as fp:
      fp.write("# Autogenerated by install script\n")
      fp.write("database.uri=%s\n"%self.bdb_server_uri)
      fp.write("\n")
      fp.write("# What type of strategy should be used for storage\n")
      fp.write("data.storage.strategy=%s\n"%self.bdb_server_backend_sqla_storage_type)
      fp.write("\n")
      fp.write("# File catalog data storage directory\n")
      fp.write("data.storage.folder=%s\n"%self.bdb_server_backend_sqla_storage_fs_path)
      fp.write("\n")
      fp.write("# The number of layers used if using \"fs\" storage\n")
      fp.write("data.storage.number.layers=%d\n"%self.bdb_server_backend_fs_layers)
      fp.write("\n")
      fp.write("# Size of cache storage if using \"db\" storage since the \"fs\" storage itself is one huge cache.\n")
      fp.write("data.storage.cache.size=%d\n"%self.bdb_server_backend_cachesize)
      fp.write("\n")
      fp.write("# The rest clients max number of connections\n")
      fp.write("bdb.rest.client.maxconnections=%d\n"%self.bdb_client_rest_maxconnections)
      fp.write("\n")
      fp.write("# The rest clients max cache size\n")
      fp.write("bdb.rest.client.cachesize=%d\n"%self.bdb_client_rest_cachesize)
      fp.write("\n")
      fp.write("# Keyczar key to communicate with node\n")
      fp.write("database.keyczar.key=%s/%s.priv\n"%(self.keystore_root, self.nodename))
      fp.write("\n")
      fp.write("# Name of the node\n")
      fp.write("database.keyczar.name=%s\n"%self.nodename)
      fp.write("\n")
      
    fp.close()
    
  ##
  # Updates the dex.beast.properties file in the BaltradDex tomcat directory (baltrad.install.3p_root/....)
  # @param properties: the properties to be used
  #
  def write_dex_beast_properties(self, dexbeastfile):
    with open(dexbeastfile, "w") as fp:
      fp.write("# Autogenerated by install script\n")
      fp.write("# BEAST mailer specifics\n")
      fp.write("beast.admin.mailer.enabled=%s\n"%("true" if self.beast_admin_mailer_enabled else "false"))
      fp.write("beast.admin.mailer.encoding=%s\n"%self.beast_admin_mailer_encoding)
      fp.write("beast.admin.mailer.host=%s\n"%self.beast_admin_mailer_host)
      fp.write("beast.admin.mailer.port=%s\n"%self.beast_admin_mailer_port)
      fp.write("beast.admin.mailer.username=%s\n"%self.beast_admin_mailer_username)
      fp.write("beast.admin.mailer.password=%s\n"%self.beast_admin_mailer_password)
      fp.write("beast.admin.mailer.from=%s\n"%self.beast_admin_mailer_from)
      fp.write("beast.admin.mailer.transport.protocol=%s\n"%self.beast_admin_mailer_transport_protocol)
      fp.write("beast.admin.mailer.smtp.auth=%s\n"%("true" if self.beast_admin_mailer_smtp_auth else "false"))
      fp.write("beast.admin.mailer.smtp.starttls.enable=%s\n"%("true" if self.beast_admin_mailer_smtp_starttls_enable else "false"))

      fp.write("beast.cli.administration.enabled=%s\n"%("true" if self.beast_cli_administration_enabled else "false"))

      fp.write("\n")
      fp.write("# BEAST mailer specifics\n")
      fp.write("beast.admin.security.keyzcar.path=%s\n"%self.keystore_root)
      fp.write("\n")
      fp.write("# BEAST exchange pool settings\n")
      fp.write("beast.pooled.publisher.pool.core.size=%d\n"%self.beast_pooled_publisher_pool_core_size)
      fp.write("beast.pooled.publisher.pool.max.size=%d\n"%self.beast_pooled_publisher_pool_max_size)
      fp.write("beast.pooled.publisher.queue.size=%d\n"%self.beast_pooled_publisher_queue_size)
      fp.write("\n")
      
      fp.write("#BEAST message manager settings\n")
      fp.write("beast.manager.number.executors = %d\n"%self.beast_manager_number_executors)

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
      elif row.startswith("CENTER_ID") and self.rave_centerid is not None:
        row = "CENTER_ID = \"%s\"\n"%self.rave_centerid
      elif row.startswith("QITOTAL_METHOD") and self.rave_qitotalmethod is not None:
        row = "QITOTAL_METHOD = \"%s\"\n"%self.rave_qitotalmethod
      elif row.startswith("RAVESCANSUN_OUT"):
        if not self.rave_scansun_out_path:
          row = "RAVESCANSUN_OUT = None\n"
        else:
          row = "RAVESCANSUN_OUT = \"%s\"\n"%self.rave_scansun_out_path
      elif row.startswith("RAVE_PGF_COMPOSITING_USE_LAZY_LOADING_PRELOADS"):
        row = "RAVE_PGF_COMPOSITING_USE_LAZY_LOADING_PRELOADS=%s\n"%str(self.rave_pgf_compositing_use_lazy_loading_preloads)
      elif row.startswith("RAVE_PGF_COMPOSITING_USE_LAZY_LOADING"):
        row = "RAVE_PGF_COMPOSITING_USE_LAZY_LOADING=%s\n"%str(self.rave_pgf_compositing_use_lazy_loading)
      elif row.startswith("RAVE_MULTIPROCESSING_MAX_TASKS_PER_WORKER"):
        row = "RAVE_MULTIPROCESSING_MAX_TASKS_PER_WORKER: int = %d\n"%self.rave_pgf_tasks_per_worker
      elif row.startswith("RAVE_TILE_COMPOSITING_PROCESSES"):
        if self.rave_pgf_tiledcompositing_nrprocesses is not None:
          row = "RAVE_TILE_COMPOSITING_PROCESSES=%d\n"%self.rave_pgf_tiledcompositing_nrprocesses
        else:
          row = "RAVE_TILE_COMPOSITING_PROCESSES=None\n"
      elif row.startswith("RAVE_TILE_COMPOSITING_TIMEOUT"):
        row = "RAVE_TILE_COMPOSITING_TIMEOUT: int = %d\n"%self.rave_pgf_tiledcompositing_timeout
      elif row.startswith("RAVE_TILE_COMPOSITING_ALLOW_MISSING_TILES"):
        row = "RAVE_TILE_COMPOSITING_ALLOW_MISSING_TILES=%s\n"%("True" if self.rave_pgf_tiledcompositing_allow_missing_tiles else "False")

      nrows.append(row)
    fp = open(ravedefinesfile, "w")
    for row in nrows:
      fp.write(row)
    fp.close()
    
  def write_tomcat_server_file(self, tomcatserverfile):
    server_template_file = os.path.join(os.path.dirname(__file__),"server.xml.template")
    with open(server_template_file, "r") as fp:
      template = fp.read()
    template = template.replace("${baltrad.keystore.file}", self.keystore_jks)
    template = template.replace("${baltrad.keystore.password}", self.keystore_pwd)
    ajpconnector=""
    if self.ajp_connector_enabled:
      ajpconnector = ajpconnector + "    <Connector port=\"%d\"\n"%self.ajp_connector_port
      ajpconnector = ajpconnector + "               protocol=\"AJP/1.3\"\n"
      ajpconnector = ajpconnector + "               redirectPort=\"%d\"\n"%self.ajp_connector_redirectPort
      if self.ajp_connector_address:
        ajpconnector = ajpconnector + "               address=\"%s\"\n"%self.ajp_connector_address
      if self.ajp_connector_secret_required:
        ajpconnector = ajpconnector + "               secretRequired=\"true\"\n"
        ajpconnector = ajpconnector + "               secret=\"%s\" />\n"%self.ajp_connector_secret
      else:
        ajpconnector = ajpconnector + "               secretRequired=\"false\" />\n"
    template = template.replace("${baltrad.ajpconnector}", ajpconnector)

    with open(tomcatserverfile) as fp:
      original = fp.read()
    if template != original:
      backup_name="%s.%s"%(tomcatserverfile, time.strftime("%Y%m%d%H%M%S"))
      shutil.copy(tomcatserverfile, backup_name)
      with open(tomcatserverfile, "w") as fp:
        fp.write(template)
      print("WARNING! Tomcat server.xml has changed. Old file has been saved as %s"%backup_name)
      text1 = open(backup_name).readlines()
      text2 = open(tomcatserverfile).readlines()
      for line in difflib.unified_diff(text1, text2):
        print(line, end = '')

  def update_application_context(self, appcontextfile):
    STARTTAG="<security:port-mappings>"
    ENDTAG="</security:port-mappings>"
    newrows = []
    with open(appcontextfile, "r") as fp:
      rows = fp.readlines()
    
    ignore_lines=False
    for row in rows:
      if row.find(STARTTAG) >= 0:
        newrows.append("        " + STARTTAG + "\n")
        newrows.append("           <security:port-mapping http=\"8080\" https=\"8443\"/>\n")
        if self.extra_fwd_port:
          p=self.extra_fwd_port.split(",")
          p1=int(p[0])
          p2=int(p[1])
          newrows.append("           <security:port-mapping http=\"%d\" https=\"%d\"/>\n"%(p1,p2))
        ignore_lines=True
      elif row.find(ENDTAG) >= 0:
        newrows.append("        " + ENDTAG + "\n")
        ignore_lines=False
      elif ignore_lines:
        pass
      else:
        newrows.append(row)
        
    with open(appcontextfile, "w") as fp:
      for row in newrows:
        fp.write(row)
