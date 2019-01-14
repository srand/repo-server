#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import os
import sys
import netrc
import socket
from StringIO import StringIO
from git_refs import R_HEADS, HEAD

from pyversion import is_python3
if is_python3():
  import http.cookiejar as cookielib
  import urllib.error
  import urllib.parse
  import urllib.request
  import xmlrpc.client
else:
  import cookielib
  import imp
  import urllib2
  import urlparse
  import xmlrpclib
  urllib = imp.new_module('urllib')
  urllib.error = urllib2
  urllib.parse = urlparse
  urllib.request = urllib2
  xmlrpc = imp.new_module('xmlrpc')
  xmlrpc.client = xmlrpclib

from command import Command
from subcmds.sync import PersistentTransport

class Smartpublish(Command):
  common = True
  helpSummary = "Publish current manifest as the latest known good revision"

  def _Options(self, p, show_smart=True):
    p.add_option('-q', '--quiet',
                 dest='quiet', action='store_true',
                 help='be more quiet')
    p.add_option('-u', '--manifest-server-username', action='store',
                 dest='manifest_server_username',
                 help='username to authenticate with the manifest server')
    p.add_option('-p', '--manifest-server-password', action='store',
                 dest='manifest_server_password',
                 help='password to authenticate with the manifest server')

  def Execute(self, opt, args):
    if not self.manifest.manifest_server:
      print('error: cannot smart sync: no manifest server defined in '
            'manifest', file=sys.stderr)
      sys.exit(1)

    manifest_server = self.manifest.manifest_server
    if not opt.quiet:
      print('Using manifest server %s' % manifest_server)

    if not '@' in manifest_server:
      username = None
      password = None
      if opt.manifest_server_username and opt.manifest_server_password:
        username = opt.manifest_server_username
        password = opt.manifest_server_password
      else:
        try:
          info = netrc.netrc()
        except IOError:
          # .netrc file does not exist or could not be opened
          pass
        else:
          try:
            parse_result = urllib.parse.urlparse(manifest_server)
            if parse_result.hostname:
              auth = info.authenticators(parse_result.hostname)
              if auth:
                username, _account, password = auth
              else:
                print('No credentials found for %s in .netrc'
                      % parse_result.hostname, file=sys.stderr)
          except netrc.NetrcParseError as e:
            print('Error parsing .netrc file: %s' % e, file=sys.stderr)

      if (username and password):
        manifest_server = manifest_server.replace('://', '://%s:%s@' %
                                                  (username, password),
                                                  1)

    transport = PersistentTransport(manifest_server)
    if manifest_server.startswith('persistent-'):
      manifest_server = manifest_server[len('persistent-'):]

    try:
      server = xmlrpc.client.Server(manifest_server, transport=transport)

      p = self.manifest.manifestProject
      b = p.GetBranch(p.CurrentBranch)
      branch = b.merge
      if branch.startswith(R_HEADS):
        branch = branch[len(R_HEADS):]

      manifest = StringIO()
      self.manifest.Save(
        manifest,
        peg_rev = True,
        peg_rev_upstream = False)
      manifest = manifest.getvalue()

      env = os.environ.copy()
      if 'SYNC_TARGET' in env:
        target = env['SYNC_TARGET']
        [success, manifest_rev] = server.PublishManifest(manifest, branch, target)
      elif 'TARGET_PRODUCT' in env and 'TARGET_BUILD_VARIANT' in env:
        target = '%s-%s' % (env['TARGET_PRODUCT'],
                            env['TARGET_BUILD_VARIANT'])
        [success, manifest_rev] = server.PublishManifest(manifest, branch, target)
      else:
        [success, manifest_rev] = server.PublishManifest(manifest, branch)
        print("published as revision {}".format(manifest_rev))
    except (socket.error, IOError, xmlrpc.client.Fault) as e:
      print('error: cannot connect to manifest server %s:\n%s'
            % (self.manifest.manifest_server, e), file=sys.stderr)
      sys.exit(1)
    except xmlrpc.client.ProtocolError as e:
      print('error: cannot connect to manifest server %s:\n%d %s'
            % (self.manifest.manifest_server, e.errcode, e.errmsg),
            file=sys.stderr)
      sys.exit(1)
