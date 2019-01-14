from SimpleXMLRPCServer import SimpleXMLRPCServer
from os import path
import xml.etree.ElementTree as ET
import os


root = os.environ.get("REPO_SERVER_HOME") or path.expanduser("~/.cache/repo-server")
if not path.exists(root):
    os.makedirs(root)


def _get_unique_name(branch, target=None):
    return branch if target is None else "{}-{}".format(branch, target)


def _make_new_rev(branch, target=None):
    filename = path.join(root, _get_unique_name(branch, target) + ".rev")
    try:
        with open(filename) as f:
            rev = int(f.read())+1
    except:
        rev = 1
    with open(filename, "w") as f:
        f.write(str(rev))
    return rev


def publish_manifest(manifest, branch, target=None):
    et = ET.fromstring(manifest)
    rev = _make_new_rev(branch, target)
    filename = path.join(root, _get_unique_name(branch, target) +  "-{}.xml".format(rev))
    with open(filename, "w") as f:
        f.write(ET.tostring(et))
    symlink = path.join(root, _get_unique_name(branch, target) + "-latest.xml")
    try:
        os.unlink(symlink)
    except:
        pass
    os.symlink(filename, symlink)
    return True, rev


def get_approved_manifest(branch, target=None):
    print("Serving manifest for {}".format(branch))
    filename = path.join(root, _get_unique_name(branch, target) + "-latest.xml")
    with open(filename) as f:
        return True, f.read()
    return False, ""


def make_revision(branch, target=None):
    return 0


server = SimpleXMLRPCServer(("", 9123))
server.register_function(get_approved_manifest, 'GetApprovedManifest')
server.register_function(publish_manifest, 'PublishManifest')
server.serve_forever()
