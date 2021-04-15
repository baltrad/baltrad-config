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
import requests
import json
import os
import base64
import datetime
from keyczar import keyczar 

DEFAULT_HOST="http://localhost:8080"
DEFAULT_URI="%s/BaltradDex/administrator.htm"%DEFAULT_HOST
DEFAULT_NODE_NAME=socket.gethostname()
DEFAULT_PRIVATE_KEY="/etc/baltrad/bltnode-keys/%s.priv"%DEFAULT_NODE_NAME

try:
  from rave_defines import DEX_SPOE
  DEFAULT_HOST = DEX_SPOE.replace("/BaltradDex","")
except:
  pass

try:
  DEFAULT_URI = "%s/BaltradDex/administrator.htm"%DEFAULT_HOST
except:
  pass

try:
  from rave_defines import DEX_NODENAME
  DEFAULT_NODE_NAME = DEX_NODENAME
except:
  pass

try:
  from rave_defines import DEX_PRIVATEKEY
  DEFAULT_PRIVATE_KEY = DEX_PRIVATEKEY
except:
  pass

logger = logging.getLogger("baltrad.bltcmd")

SYSLOG_ADDRESS = "/dev/log"
SYSLOG_FACILITY = "local3"

def excepthook(*exc_info):
  logger.error("unhandled exception", exc_info=exc_info)
  sys.exit(1)

def create_argparse(descr):
  return argparse.ArgumentParser(description=descr)

# The mainclass used for handling a baltrad command.
#
class bltcmd(object):
  def __init__(self, nodename, privatekey, uri):
    self._uri = uri
    self._nodename = nodename
    self._privatekey=privatekey
    self._signer = keyczar.Signer.Read(self._privatekey)
      
  def _generate_headers(self, message):
    d = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    signature = self._signer.Sign(d + ":" + message)
    headers = {
      "Node-Name": self._nodename, 
      "Content-Type":"application/json",
      "Date": d,
      "Signature": signature
    }
    return headers


  def send_command(self, command, content):
    message="""
{"command":"%s",
 "arguments":%s
}
"""%(command, content)
    #print("MESSAGE=%s"%message)
    headers = self._generate_headers(message)
    return requests.post(self._uri, data=message, headers=headers)  

def run_command(args, unknown_args):
  nodename = args.nodename
  privatekey = DEFAULT_PRIVATE_KEY
  uri = "%s/BaltradDex/administrator.htm"%args.host
  
  if args.uri is not None:
    uri = args.uri

  if args.privatekey is not None:
    privatekey = args.privatekey
  
  cmd = bltcmd(nodename, privatekey, uri)
  
  content = args.data
  if args.fname is not None and os.path.exists(args.fname):
    content = open(args.fname).read()

  extra_args=None
  if content is None:
    if len(unknown_args) > 1:
      if unknown_args[0] == "help":
        content="{\"command\":\"%s\"}"%unknown_args[1]
      else:
        extra_args=unknown_args[1:]
        content = "{%s}"%(",".join(extra_args))
  if content is None:
    content="{}"

  resp = cmd.send_command(unknown_args[0], content)
  
  if unknown_args[0] == "help" and resp.status_code==200:
    print(json.loads(resp.content)["help"]["description"].replace("\\n","\n").replace("\\\"","\""))
    if "commands" in json.loads(resp.content)["help"]:
      for s in json.loads(resp.content)["help"]["commands"]:
        print(" -   %s"%s)
  elif resp.status_code == 200:
    print(json.dumps(json.loads(resp.content), indent=2))
  else:
    print("Failed to handle operation , error code: %d"%resp.status_code)

def run():
  parser = create_argparse("Used for communicating with the dex/beast engine")

  parser.add_argument("--nodename=", dest="nodename", default=DEFAULT_NODE_NAME, help="The name of the node we should present us with.")

  parser.add_argument("--privatekey=", dest="privatekey", default=None, help="The name of the folder where the private key is located")

  parser.add_argument(
    "--host=", dest="host", default=DEFAULT_HOST, help="The hostname uri. E.g. http://localhost:8080. /BaltradDex/administrator.htm will be appended."
  )

  parser.add_argument(
    "--uri=", dest="uri", default=None, help="The full uri where command should be sent. E.g. http://localhost:8080/BaltradDex/administrator.htm."
  )

  parser.add_argument(
    "--file=", dest="fname", default=None, help="The filename containing the data."
  )

  parser.add_argument(
    "--data=", dest="data", default=None, help="Can be used instead of --file to specify data."
  )

  parser.set_defaults(func=run_command)
  
  args, unknown_args = parser.parse_known_args()
  
  args.func(args, unknown_args)
  

if __name__=="__main__":
  run()
