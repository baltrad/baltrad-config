import getpass
import os
import sys
import argparse
import json

def create_argparse(descr):
  return argparse.ArgumentParser(description=descr)
  
def run_command(args):
  sactive = "true"
  if not args.active:
    sactive = "false"

  result = """
{
  "groovy-script": {
    "name":"%s",
    "author":"%s",
    "description":"%s",
    "active":%s,
    "script":%s
  }
}
"""%(args.name, args.author, args.description, sactive, json.dumps(open(args.scriptname).read()))
  print(result)

  
def run():
  parser = create_argparse("Creates a groovy-route from a groovy script and attributes.")

  parser.add_argument("--name=", dest="name", default="", help="The name of the route.")
  
  parser.add_argument("--author=", dest="author", default=getpass.getuser(), help="The name of the author.")

  parser.add_argument("--description=", dest="description", default="", help="The description.")

  parser.add_argument("--active=", dest="active", default=True, type=bool, help="If route should be active or not.")

  parser.add_argument("scriptname", default=None, help="If route should be active or not.")

  parser.set_defaults(func=run_command)

  args= parser.parse_args()
  
  args.func(args)
  
if __name__=="__main__":
  run()

