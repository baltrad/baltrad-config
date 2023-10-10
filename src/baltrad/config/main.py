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
import logging
import logging.handlers
import os
import sys
import argparse
import socket
import string
import subprocess
import shutil
import pwd, grp

from baltrad.config import propertyhandler
from baltrad.config import database

from baltradcrypto.crypto import keyczarcrypto

if sys.version_info < (3,):
  import urlparse
else:
  import urllib.parse as urlparse

def read_input(msg, defaultvalue=None):
  if defaultvalue != None:
    msg = msg + " [default: %s]: "%defaultvalue
  if sys.version_info < (3,):
    d = raw_input(msg)
  else:
    d = input(msg)
  if len(d)==0 and defaultvalue != None:
    d = defaultvalue

  return d

logger = logging.getLogger("baltrad.config")

SYSLOG_ADDRESS = "/dev/log"
SYSLOG_FACILITY = "local3"

def excepthook(*exc_info):
  logger.error("unhandled exception", exc_info=exc_info)
  sys.exit(1)

def create_argparse(descr):
  return argparse.ArgumentParser(description=descr)

##
# Checks if the provided dir exists and if not creates it
# @param dir: the dir name
def createdir(dir):
  if not os.path.exists(dir):
    os.mkdir(dir)
  elif not os.path.isdir(dir):
    raise Exception("%s exists but is not a directory"%dir)

# This method uses the linux command keytool    
def create_keystore(keystore, kpwd=None, dname=None):
  while kpwd == None:
    kpwd=read_input("Keystore password: ")
    if len(kpwd) < 1:
      print("Must specify a keystore password")
      kpwd = None

  args = ["keytool", "-genkey", "-alias", "baltrad", "-keyalg", "RSA", "-validity", "3650", "-keypass", kpwd, "-storepass", kpwd, "-keystore", keystore]
  if dname is not None:
    args.append("-dname")
    args.append(dname)
    
  ocode = subprocess.call(args)
  if ocode != 0:
    raise Exception("keytool command failed for keystore creation")
  return kpwd

# Code snippet from baltrad-exchange/src/bexchange/client/cfgcmd.py
def create_priv_pub_keys(keys_root, nodename):
  priv_nodekey = "%s/%s.priv"%(keys_root, nodename)
  pub_nodekey = "%s/%s.pub"%(keys_root, nodename)
  if not os.path.exists(priv_nodekey):
    os.makedirs(priv_nodekey)

  if not os.path.exists(pub_nodekey):
    os.makedirs(pub_nodekey)

    keyczar_signer = keyczarcrypto.create_keyczar_key()
    keyczar_verifier = keyczarcrypto.keyczar_verifier(keyczar_signer._key)
        
    keyczar_signer.export(priv_nodekey, nodename)
    keyczar_verifier.export(pub_nodekey, nodename)

    print("Created: ")
    print("  Private key: %s"%priv_nodekey)
    print("  Public  key: %s"%pub_nodekey)               

def create_initial_config(args):
  a=propertyhandler.propertyhandler()
  
  if args.questions:
    a.nodename = read_input("Node name", socket.gethostname())
    a.db_dbname = read_input("Database name", "baltrad")
    a.db_username = read_input("Database username", "baltrad")
    a.db_password = read_input("Database password", "baltrad")
    a.db_hostname = read_input("Database hostname", "localhost")

  a.write_config_file(args.conf)  

def execute_createkeys(args):
  a=propertyhandler.propertyhandler()
  a.open_config_file(args.conf)
  
  if args.keys_root is not None:
    a.keystore_root = args.keys_root
  if args.keystore_jks is not None:
    a.keystore_jks = args.keystore_jks
  if not os.path.exists(a.keystore_root):
    os.makedirs(a.keystore_root)
    if get_current_user() == "root":
      baltrad_uid = pwd.getpwnam(a.baltrad_user).pw_uid
      baltrad_gid = grp.getgrnam(a.baltrad_group).gr_gid
      os.chown(a.keystore_root, baltrad_uid, baltrad_gid)

  if os.path.exists(a.keystore_jks):
    x = read_input("%s already exists, overwrite (y/n)?"%a.keystore_jks, "n")
    if x=="y":
      os.unlink(a.keystore_jks)

  forced_storage = False
  if not os.path.exists(a.keystore_jks):
    a.keystore_pwd = create_keystore(a.keystore_jks, args.keystore_pwd, args.dname)
    forced_storage = True

  do_unlink_pub = False
    
  if os.path.exists("%s/%s.priv"%(a.keystore_root, a.nodename)):
    x = read_input("%s/%s.priv already exists, overwrite (y/n)?"%(a.keystore_root, a.nodename))
    if x=="y":
      shutil.rmtree("%s/%s.priv"%(a.keystore_root, a.nodename), True)
      do_unlink_pub = True

  if os.path.exists("%s/%s.pub"%(a.keystore_root, a.nodename)):
    if do_unlink_pub:
      x="y"
    else: 
      x = read_input("%s/%s.pub already exists, overwrite (y/n)?"%(a.keystore_root, a.nodename))
    if x=="y":
      shutil.rmtree("%s/%s.pub"%(a.keystore_root, a.nodename), True)

  create_priv_pub_keys(a.keystore_root, a.nodename)
    
  if args.keystore_jks is not None or args.keys_root is not None:
    x = read_input("Specified keystore root and/or keystore file as argument. Update property file %s  (y/n)? "%args.conf)
    if x == "y":
      a.write_config_file(args.conf)
  elif forced_storage:
    a.write_config_file(args.conf)

def get_current_user():
  return pwd.getpwuid(os.getuid())[0]

def change_mod(fname, mod):
  f_uid = os.stat(fname).st_uid
  c_uid = os.getuid()
  if c_uid == 0 or f_uid == c_uid:
    os.chown(fname, mod)

def execute_post_config(args):
  a=propertyhandler.propertyhandler()
  a.open_config_file(args.conf)
  
  a.write_bltnode_properties(args.bltnodefile)
  a.write_dex_properties(args.dexfile)
  a.write_dex_db_properties(args.dexdbfile)
  a.write_dex_fc_properties(args.dexfcfile)
  a.write_dex_beast_properties(args.dexbeastfile)
  a.write_tomcat_server_file(args.tomcatserverfile)
  a.update_application_context(args.appcontextfile)
  if not args.no_rave_config:
    a.update_rave_defines(args.ravedefinesfile, args.bltnodefile)

  # Change owner to root:baltrad
  uid = pwd.getpwnam("root").pw_uid
  baltrad_uid = pwd.getpwnam(a.baltrad_user).pw_uid
  baltrad_gid = grp.getgrnam(a.baltrad_group).gr_gid
  if get_current_user() == "root":
    os.chown(args.bltnodefile, baltrad_uid, baltrad_gid)
    os.chown(args.dexfile, baltrad_uid, baltrad_gid)
    os.chown(args.dexdbfile, baltrad_uid, baltrad_gid)
    os.chown(args.dexfcfile, baltrad_uid, baltrad_gid)
    os.chown(args.dexbeastfile, baltrad_uid, baltrad_gid)
    os.chown(args.tomcatserverfile, baltrad_uid, baltrad_gid)
    os.chown(args.appcontextfile, baltrad_uid, baltrad_gid)
    
    if not args.no_rave_config:
      os.chown(args.ravedefinesfile, baltrad_uid, baltrad_gid)

  else:
    print("WARNING! Could not change ownership of configuration files:")
    print("%s"%args.bltnodefile)
    print("%s"%args.dexfile)
    print("%s"%args.dexdbfile)
    print("%s"%args.dexfcfile)
    print("%s"%args.dexbeastfile)
    print("%s"%args.tomcatserverfile)
    print("%s"%args.appcontextfile)
    if not args.no_rave_config:
      print("%s"%args.ravedefinesfile)

  os.chmod(args.bltnodefile, 0o660)
  os.chmod(args.dexfile, 0o660)
  os.chmod(args.dexdbfile, 0o660)
  os.chmod(args.dexfcfile, 0o660)
  os.chmod(args.dexbeastfile, 0o660)
  os.chmod(args.tomcatserverfile, 0o660)
  os.chmod(args.appcontextfile, 0o660)

  if not args.no_rave_config:
    os.chmod(args.ravedefinesfile, 0o664)
  
  if args.install_database or args.update_database:
    db = database.baltrad_database(args.bltnodefile, a.db_hostname, a.db_dbname, a.db_username, a.db_password, a.bdb_binaries, a.beast_sql_file_dir, a.dex_sql_file_dir)
    if args.install_database:
      db.create()
    if args.update_database:
      db.upgrade()

  if args.run_scripts:
    execute_post_config_scripts(a, args.conf)
  
def execute_post_config_scripts(ph, configfile):
  for script in ph.post_config_scripts:
    code = subprocess.call([sys.executable, script, configfile])
    if code != 0:
      print("Failed to run post script: %s"%script)

def run():
  parser = create_argparse("Creates initial configuration for the baltrad node packages")

  subparsers = parser.add_subparsers(help='the allowed commands')
  
  parser_init = subparsers.add_parser('init', help='creates initial configuration')
  parser_createkeys = subparsers.add_parser('create_keys', help='creates the key structure')
  parser_setup = subparsers.add_parser('setup', help='runs the setup of a node')

  parser_init.add_argument(
    "--conf=", dest="conf", default="/etc/baltrad/localhost.properties", help="the name of the configuration file to be created"
  )

  parser_init.add_argument(
    "--questions", dest="questions", action="store_true", help="if a number of questions should be asked, otherwise default values will be set at most places",
  )

  parser_setup.add_argument(
    "--conf=", dest="conf", default="/etc/baltrad/localhost.properties", help="the name of the configuration file to be read"
  )

  parser_setup.add_argument(
    "--bltnodefile=", dest="bltnodefile", default="/etc/baltrad/bltnode.properties", help="Where the properties for bltnode should be written"
  )

  parser_setup.add_argument(
    "--dexfile=", dest="dexfile", default="/etc/baltrad/dex.properties", help="Where the properties for dex should be written"
  )

  parser_setup.add_argument(
    "--dexdbfile=", dest="dexdbfile", default="/etc/baltrad/db.properties", help="Where the properties for dex db should be written"
  )

  parser_setup.add_argument(
    "--dexfcfile=", dest="dexfcfile", default="/etc/baltrad/dex.fc.properties", help="Where the properties for dex fc should be written"
  )

  parser_setup.add_argument(
    "--dexbeastfile=", dest="dexbeastfile", default="/etc/baltrad/dex.beast.properties", help="Where the properties for dex beast should be written"
  )
  
  parser_setup.add_argument(
    "--ravedefinesfile=", dest="ravedefinesfile", default="/etc/baltrad/rave/Lib/rave_defines.py", help="Where rave_defines.py is located"
  )
  
  parser_setup.add_argument(
    "--tomcatserverfile=", dest="tomcatserverfile", default="/etc/baltrad/baltrad-node-tomcat/server.xml", help="Where the tomcat server.xml file is located"
  )
  
  parser_setup.add_argument(
    "--appcontextfile=", dest="appcontextfile", default="/var/lib/baltrad/baltrad-node-tomcat/webapps/BaltradDex/WEB-INF/applicationContext.xml", help="Where the application context file is located"
  )
  
  parser_setup.add_argument(
    "--no-rave-config", dest="no_rave_config", action="store_true", help="if rave defines file should be updated",
  )
  
  parser_setup.add_argument(
    "--install-database", dest="install_database", action="store_true", help="if the database install routines should be executed"
  )

  parser_setup.add_argument(
    "--upgrade-database", dest="update_database", action="store_true", help="if the database upgrade routines should be executed"
  )
  
  parser_setup.add_argument(
    "--runscripts", dest="run_scripts", action="store_true", help="if the scripts should be executed")
  
  
  parser_createkeys.add_argument(
    "--conf=", dest="conf", default="/etc/baltrad/localhost.properties", help="the name of the configuration file to be created"
  )
  
  parser_createkeys.add_argument(
    "--keys-root=", dest="keys_root", default=None, help="location of all keys used during exchange"
  )
    
  parser_createkeys.add_argument(
    "--keystore=", dest="keystore_jks", default=None, help="location of the keystore"
  )

  parser_createkeys.add_argument(
    "--password=", dest="keystore_pwd", default=None, help="password for the keystore"
  )
  
  parser_createkeys.add_argument(
    "--dname=", dest="dname", default=None, help="Distinguished name for the keystore")
  
  parser_init.set_defaults(func=create_initial_config)
  parser_setup.set_defaults(func=execute_post_config)
  parser_createkeys.set_defaults(func=execute_createkeys)
  
  args = parser.parse_args()
  
  args.func(args)
  

if __name__=="__main__":
  run()

