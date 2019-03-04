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
from calendar import timegm
from collections import namedtuple
from datetime import datetime
from StringIO import StringIO
from struct import unpack

from zope.interface import implementer

from bp.abstract import IFilePath
from bp.errors import UnlistableError
from bp.generic import (genericChildren, genericParents, genericSegmentsFrom,
                        genericSibling, genericWalk)
from bp.util import modeIsWriting


PRIMARYVD = 0x01
FINALVD = 0xff

DIRMASK = 0x02


def thawPrimaryDate(s):
    year = int(s[0:4])
    month = int(s[4:6])
    day = int(s[6:8])
    hour = int(s[8:10])
    minute = int(s[10:12])
    second = int(s[12:14])
    microsecond = int(s[14:16]) * 10 * 1000
    # Fuck timezones.

    return datetime(year, month, day, hour, minute, second, microsecond)


def thawRecordDate(s):
    year = ord(s[0]) + 1900
    month = ord(s[1])
    day = ord(s[2])
    hour = ord(s[3])
    minute = ord(s[4])
    second = ord(s[5])
    # Fuck timezones.

    return datetime(year, month, day, hour, minute, second)


class Record(
        namedtuple("Record", "extent, size, time, isdir, name")):

    @classmethod
    def fromEntry(cls, data):
        data_len = ord(data[0])
        if data_len > len(data):
            raise ValueError("Not enough data for record")
        extent, = unpack("<I", data[2:2 + 4])
        size, = unpack("<I", data[10:10 + 4])
        time = thawRecordDate(data[18:18 + 6])
        flags = ord(data[25])
        isdir = bool(flags & DIRMASK)
        name_len = ord(data[32])
        name = data[33:33 + name_len].lower()

        return cls(extent, size, time, isdir, name)


class Primary(
        namedtuple("Primary", "identifier, root, creator, ctime, mtime")):

    @classmethod
    def fromEntry(cls, data):
        identifier = data[33:33 + 32].strip()

        root = Record.fromEntry(data[149:183])

        creator = data[439:439 + 128].strip()

        ctime = thawPrimaryDate(data[806:806 + 17])
        mtime = thawPrimaryDate(data[823:823 + 17])

        return cls(identifier, root, creator, ctime, mtime)


def fixName(name):
    name = name.rsplit(";", 1)[0]
    if name.endswith("."):
        name = name.rstrip(".")
    return name


class ISO(object):

    primary = None

    def __init__(self, path):
        self._path = path
        self._dirs = {}

    def readVDs(self):
        with self._path.open("rb") as handle:
            handle.seek(32 * 1024)

            while True:
                vd = handle.read(2048)
                vdtype = ord(vd[0])
                if vdtype == FINALVD:
                    break
                elif vdtype == PRIMARYVD:
                    data = vd[7:]
                    self.primary = Primary.fromEntry(data)
                    self._dirs[()] = self.primary.root.extent

    def readExtent(self, extent, size):
        with self._path.open("rb") as handle:
            handle.seek(extent * 2048)
            return handle.read(size)

    def readRecords(self, extent, segments):
        offset = extent * 2048

        with self._path.open("rb") as handle:
            while True:
                handle.seek(offset)
                data = handle.read(256)
                size = ord(data[0])

                if offset // 2048 < (offset + size) // 2048:
                    # Next record would cross a boundary; move forward and try
                    # again.
                    offset = (offset + 2047) & ~2047

                    data = handle.read(256)
                    size = ord(data[0])

                if size == 0:
                    # No more records.
                    return

                offset += size

                record = Record.fromEntry(data)

                if record.isdir and record.name in ("\x00", "\x01"):
                    continue

                if record.isdir:
                    t = segments + (record.name,)
                    self._dirs[t] = record.extent
                else:
                    record = record._replace(name=fixName(record.name))
                yield record

    def findDir(self, segments):
        t = segments
        ts = [segments]
        while t not in self._dirs:
            t = t[:-1]
            ts.append(t)

        for t in reversed(ts):
            if t not in self._dirs:
                # Not a directory; return None.
                return None

            for r in self.readRecords(self._dirs[t], t):
                pass

        return self._dirs.get(segments)

    def findRecord(self, segments):
        if not segments:
            return self.primary.root

        parent = segments[:-1]
        name = segments[-1]

        extent = self.findDir(parent)

        if extent is None:
            return None

        for record in self.readRecords(extent, parent):
            if record.name == name:
                return record
        else:
            return None


@implementer(IFilePath)
class ISOPath(object):
    """
    An IFilePath which provides access to an ISO 9660 filesystem image.
    """

    sep = "/"

    _extent = None

    def __init__(self, fp=None, path=()):
        """
        View an ISO image.

        :param FilePath fp: An IFilePath for an ISO image.
        :param tuple path: An optional tuple of path segments.
        """

        if fp is not None:
            self._iso = ISO(fp)
            self._iso.readVDs()
        self._path = path

    @classmethod
    def withISO(cls, iso, path=()):
        """
        Pre-wrap the ISO-bearing FilePath in an ISO object.

        Useful for sharing the ISO object's caches amongst all ISOPaths
        accessing it.
        """

        self = cls(path=path)
        self._iso = iso
        return self

    def __eq__(self, other):
        return self._iso == other._iso and self._path == other._path

    def __hash__(self):
        return hash((ISOPath, self._iso, self._path))

    @property
    def path(self):
        return self.sep.join(self._path)

    def listdir(self):
        extent = self._iso.findDir(self._path)

        if extent is None:
            raise UnlistableError()

        return [r.name for r in self._iso.readRecords(extent, self._path)]

    # IFilePath generic methods

    children = genericChildren
    parents = genericParents
    segmentsFrom = genericSegmentsFrom
    sibling = genericSibling
    walk = genericWalk

    # IFilePath navigation

    def parent(self):
        if self._path:
            return ISOPath.withISO(self._iso, self._path[:-1])
        else:
            return self

    def child(self, name):
        return ISOPath.withISO(self._iso, self._path + (name,))

    def descendant(self, segments):
        return ISOPath.withISO(self._iso, self._path + tuple(segments))

    # IFilePath writing and reading

    def open(self, mode="r"):
        if modeIsWriting(mode):
            raise Exception("ISOs are read-only")

        return StringIO(self.getContent())

    def createDirectory(self):
        raise Exception("ISOs are read-only")

    def getContent(self):
        record = self._iso.findRecord(self._path)
        if record is None:
            raise Exception("I don't exist")

        data = self._iso.readExtent(record.extent, record.size)
        return data

    def setContent(self, content, ext=b".new"):
        raise Exception("ISOs are read-only")

    # IFilePath stat and other queries

    def changed(self):
        pass

    def isdir(self):
        return self._iso.findDir(self._path) is not None

    def isfile(self):
        record = self._iso.findRecord(self._path)
        return record is not None and record.isdir == False

    def islink(self):
        return False

    def exists(self):
        return self.isdir() or self.isfile()

    def basename(self):
        return self._path[-1] if self._path else ""

    def getsize(self):
        record = self._iso.findRecord(self._path)
        if record is None:
            raise Exception("I don't exist")

        return record.size

    def getModificationTime(self):
        record = self._iso.findRecord(self._path)
        if record is None:
            raise Exception("I don't exist")

        return float(timegm(record.time.timetuple()))

    getStatusChangeTime = getModificationTime
    getAccessTime = getModificationTime

    # IFilePath symlinks

    def realpath(self):
        return self
