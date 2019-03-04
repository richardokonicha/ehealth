# Copyright (C) 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from base64 import b64decode
import os.path
from zlib import decompress

from bp.iso import ISOPath
from bp.memory import MemoryFS, MemoryPath
from bp.tests.test_paths import AbstractFilePathTestCase


iso = decompress(b64decode("""
eJzt28FOE0EcB+CpNqSJiRc1UOCw9mDQaNltEUI41bKUYmlNWxJ4AE1MPPloPhFvot1dGoNISxQB
9fvSZqazv27nsOk/M+2GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACU2rtxnJRCr9s/
Oo4u194dDg5nHJ+e78u5ZsbnTh7ZM1QqoVYM1R59P/wkHwiLxavFUMmaSvhcuv/46drpven7Z0yI
G9BJ+93RoHvY6qTRpBNtb27G6/t7o2iv20tHJ6Nxehi1h2lrPBhGa+3nUbK93YzS+sngqN/ZbfXS
6eDWq0Ycb0YH9Xdpazga9NcP6qP2frc3uSo7eSY7nGW2sgvxbXccjdPWrMvxz2jEyUacxBuN5us4
c3phIP5BuJAohRufNnfKdXxtw7X4elb/AQAAgH9XKd9jz9b/5bCU90ZHb5JyqE77zdudHwAAAPD7
8l/+F7OmnPWWQqlY/09U8771PwAAAPz15t9jNzdRehGWi8TyQtEunCVCkahkd4Ml9Z0kPMv/YxCy
fYafnqucbT5MUtUiVb08ZVsCAH5dbU5Fvlr9XykSKzPqfyOr/wDAXVCbs9a+Sv1/GVaLxOr0rOfr
/4Os/jfr6fF4J4nnZB/m2TiOi3i4aj45ywMA8334+Ol9pGwCwH8lr/+N254FAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AADM9g1BnfEm
"""))


class ISOPathTestCase(AbstractFilePathTestCase):

    def _mkpath(self, *p):
        self.all.append("/".join(p))
        x = os.path.abspath(os.path.join(self.cmn, *p))
        return x

    def setUp(self):
        fs = MemoryFS()
        fp = MemoryPath(fs).child("test.iso")
        fp.setContent(iso)

        AbstractFilePathTestCase.setUp(self)

        self.path = ISOPath(fp)
        self.root = self.path

    def test_createDirectory(self):
        """
        createDirectory() cannot create new directories on a read-only file
        path.
        """

        self.assertRaises(Exception,
                          self.path.child(b"directory").createDirectory)

    def test_walk(self):
        AbstractFilePathTestCase.test_walk(self)

    test_walk.todo = "Joliet/Rock Ridge names need to be allowed"
