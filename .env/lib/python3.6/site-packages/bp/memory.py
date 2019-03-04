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
from itertools import chain
from StringIO import StringIO

from zope.interface import implementer

from bp.abstract import IFilePath
from bp.errors import UnlistableError
from bp.generic import (genericChildren, genericParents, genericSegmentsFrom,
                        genericSibling, genericWalk)

DIR = object()
FILE = object()


class MemoryFile(StringIO):
    """
    A file-like object that saves itself to an external mapping when closed.
    """

    def __init__(self, store, key, buf=""):
        StringIO.__init__(self, buf)
        self._target = store, key

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        buf = self.getvalue()
        store, key = self._target
        store[key] = buf
        StringIO.close(self)


class MemoryFS(object):
    """
    An in-memory filesystem.
    """

    def __init__(self):
        self._store = {}
        self._dirs = set()

    def open(self, path):
        if path in self._dirs:
            raise Exception("Directories cannot be opened")
        elif path in self._store:
            return MemoryFile(self._store, path, self._store[path])
        else:
            return MemoryFile(self._store, path)


def format_memory_path(path, sep):
    return sep.join(("/mem",) + path)


@implementer(IFilePath)
class MemoryPath(object):
    """
    An IFilePath which shows a view into a MemoryFS.
    """

    sep = "/"

    def __init__(self, fs, path=()):
        """
        Create a new path in memory.
        """

        self._fs = fs
        self._path = path

    def __eq__(self, other):
        return self._fs == other._fs and self._path == other._path

    def __hash__(self):
        return hash((MemoryPath, self._fs, self._path))

    @property
    def path(self):
        return format_memory_path(self._path, self.sep)

    def listdir(self):
        """
        Pretend that we are a directory and get a listing of child names.
        """

        if self._path not in self._fs._dirs:
            raise UnlistableError()

        i = chain(self._fs._dirs, self._fs._store.iterkeys())

        # Linear-time search. Could be better.
        p = self._path
        l = len(p) + 1
        ks = [t[-1] for t in i if t[:-1] == p and len(t) == l]

        return ks

    # IFilePath generic methods

    children = genericChildren
    parents = genericParents
    segmentsFrom = genericSegmentsFrom
    sibling = genericSibling
    walk = genericWalk

    # IFilePath navigation

    def parent(self):
        if self._path:
            return MemoryPath(self._fs, self._path[:-1])
        else:
            return self

    def child(self, name):
        return MemoryPath(self._fs, self._path + (name,))

    def descendant(self, segments):
        return MemoryPath(self._fs, self._path + tuple(segments))

    # IFilePath writing and reading

    def open(self, mode="r"):
        return self._fs.open(self._path)

    def createDirectory(self):
        self._fs._dirs.add(self._path)

    def getContent(self):
        return self._fs._store[self._path]

    def setContent(self, content, ext=b".new"):
        self._fs._store[self._path] = content

    # IFilePath stat and other queries

    def changed(self):
        pass

    def isdir(self):
        return self._path in self._fs._dirs

    def isfile(self):
        return self._path in self._fs._store

    def islink(self):
        return False

    def exists(self):
        return self.isdir() or self.isfile()

    def basename(self):
        return self._path[-1] if self._path else ""

    def getsize(self):
        if self._path in self._fs._store:
            return len(self._fs._store[self._path])
        else:
            raise Exception("Non-file has no size")

    def getModificationTime(self):
        return 0.0

    def getStatusChangeTime(self):
        return 0.0

    def getAccessTime(self):
        return 0.0

    # IFilePath symlinks

    def realpath(self):
        return self
