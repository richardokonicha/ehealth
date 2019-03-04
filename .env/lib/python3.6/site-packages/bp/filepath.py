# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
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

"""
Object-oriented filesystem path representation.
"""

from __future__ import division, absolute_import

from collections import namedtuple
import base64
import errno
from hashlib import sha1
import os

from os.path import isabs, exists, normpath, abspath, splitext
from os.path import basename, dirname
from os.path import join as joinpath
from os import sep as slash
from os import listdir, utime, stat

from stat import S_ISREG, S_ISDIR, S_IMODE, S_ISBLK, S_ISSOCK
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from stat import S_IRGRP, S_IWGRP, S_IXGRP
from stat import S_IROTH, S_IWOTH, S_IXOTH

from zope.interface import implementer

# Please keep this as light as possible on other Twisted imports; many, many
# things import this module, and it would be good if it could easily be
# modified for inclusion in the standard library.  --glyph

from bp.abstract import IFilePath
from bp.errors import LinkError, UnlistableError
from bp.generic import (genericChildren, genericDescendant, genericGetContent,
                        genericParents, genericSegmentsFrom, genericSibling,
                        genericWalk)
from bp.win32 import (ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND,
                      ERROR_INVALID_NAME, ERROR_DIRECTORY, O_BINARY,
                      isWindows, WindowsError)


_CREATE_FLAGS = (os.O_EXCL |
                 os.O_CREAT |
                 os.O_RDWR |
                 O_BINARY)


def _stub_islink(path):
    """
    Always return C{False} if the operating system does not support symlinks.

    @param path: A path string.
    @type path: L{str}

    :return: C{False}
    :rtype: L{bool}
    """
    return False


islink = getattr(os.path, 'islink', _stub_islink)
randomBytes = os.urandom
armor = base64.urlsafe_b64encode


class InsecurePath(Exception):
    """
    Error that is raised when the path provided to :py:class:`FilePath` is invalid.
    """


def _secureEnoughString():
    """
    Compute a string usable as a new, temporary filename.

    :return: A pseudorandom, 16 byte string for use in secure filenames.
    :rtype: C{bytes}
    """
    return armor(sha1(randomBytes(64)).digest())[:16]


class RWX(namedtuple("RWX", "read, write, execute")):
    """
    A class representing read/write/execute permissions for a single user
    category (i.e. user/owner, group, or other/world).  Instantiate with
    three boolean values: readable? writable? executable?.

    @type read: C{bool}
    @ivar read: Whether permission to read is given

    @type write: C{bool}
    @ivar write: Whether permission to write is given

    @type execute: C{bool}
    @ivar execute: Whether permission to execute is given
    """

    def shorthand(self):
        """
        Returns a short string representing the permission bits.  Looks like
        part of what is printed by command line utilities such as 'ls -l'
        (e.g. 'rwx')

        :return: The shorthand string.
        :rtype: L{str}
        """
        returnval = ['r', 'w', 'x']
        i = 0
        for val in (self.read, self.write, self.execute):
            if not val:
                returnval[i] = '-'
            i += 1
        return ''.join(returnval)


class Permissions(namedtuple("Permissions", "user, group, other")):
    """
    A class representing read/write/execute permissions.  Instantiate with any
    portion of the file's mode that includes the permission bits.

    @type user: L{RWX}
    @ivar user: User/Owner permissions

    @type group: L{RWX}
    @ivar group: Group permissions

    @type other: L{RWX}
    @ivar other: Other/World permissions
    """

    @classmethod
    def fromStat(cls, statModeInt):
        user, group, other = (
            [RWX(*[statModeInt & bit > 0 for bit in bitGroup]) for bitGroup in
             [[S_IRUSR, S_IWUSR, S_IXUSR],
              [S_IRGRP, S_IWGRP, S_IXGRP],
              [S_IROTH, S_IWOTH, S_IXOTH]]]
        )

        return cls(user, group, other)

    def shorthand(self):
        """
        Returns a short string representing the permission bits.  Looks like
        what is printed by command line utilities such as 'ls -l'
        (e.g. 'rwx-wx--x')

        :return: The shorthand string.
        :rtype: L{str}
        """
        return "".join(
            [x.shorthand() for x in (self.user, self.group, self.other)])


@implementer(IFilePath)
class FilePath(object):
    """
    I am a path on the filesystem that only permits "downwards" access.

    Instantiate me with a pathname, e.g.
    FilePath('/home/myuser/public_html'), and I will attempt to only provide
    access to files which reside inside that path.  I may be a path to a file,
    a directory, or a file which does not exist.

    The correct way to use me is to instantiate me, and then do *all*
    filesystem access through me.  In other words, do not import the ``os``
    module; if you need to open a file, call my :py:meth:`.open` method.  If
    you need to list a directory, call my :py:meth:`.listdir` method.

    Even if you pass me a relative path, I will convert that to an absolute
    path internally.

    Note: although time-related methods do return floating-point results, they
    may still be only second resolution depending on the platform and the last
    value passed to ``os.stat_float_times``.  If you want greater-than-second
    precision, call ``os.stat_float_times(True)``, or use Python 2.5.
    Greater-than-second precision is only available in Windows on Python 2.5
    and later.

    On both Python 2 and Python 3, paths can only be bytes.

    :ivar bool alwaysCreate: When opening this file, only succeed if the file
                             does not already exist.

    :ivar bytes path: The path from which "downward" traversal is permitted.

    :ivar os.stat_result statinfo: The currently cached status information
                                   about the file on the filesystem that this
                                   :py:class:`FilePath` points to.  This
                                   attribute is C{None} if the file is in an
                                   indeterminate state (either this
                                   :py:class:`FilePath` has not yet had cause
                                   to call C{stat()} yet or
                                   L{FilePath.changed} indicated that new
                                   information is required), 0 if C{stat()}
                                   was called and returned an error (i.e. the
                                   path did not exist when C{stat()} was
                                   called), or a C{stat_result} object that
                                   describes the last known status of the
                                   underlying file (or directory, as the case
                                   may be).  Trust me when I tell you that you
                                   do not want to use this attribute. Instead,
                                   use the methods on :py:class:`FilePath`
                                   which give you information about it, like
                                   C{getsize()}, C{isdir()},
                                   C{getModificationTime()}, and so on.


    .. warning:: Do not use ``statinfo``. Trust me when I tell you that you do
                 not want to use this attribute.
    """

    statinfo = None
    path = None

    sep = slash.encode("ascii")

    children = genericChildren
    descendant = genericDescendant
    getContent = genericGetContent
    parents = genericParents
    segmentsFrom = genericSegmentsFrom
    sibling = genericSibling
    walk = genericWalk

    def __init__(self, path, alwaysCreate=False):
        """
        Convert a path string to an absolute path if necessary and initialize
        the :py:class:`FilePath` with the result.
        """
        self.path = abspath(path)
        self.alwaysCreate = alwaysCreate

    def __getstate__(self):
        """
        Support serialization by discarding cached :py:func:`os.stat` results
        and returning everything else.
        """
        d = self.__dict__.copy()
        if 'statinfo' in d:
            del d['statinfo']
        return d

    def __hash__(self):
        """
        Hash the same as another :py:class:`FilePath` with the same path as
        mine.
        """
        return hash((FilePath, self.path))

    def child(self, path):
        """
        Create and return a new :py:class:`FilePath` representing a path
        contained by this path.

        :param bytes path: The base name of the new :py:class:`FilePath`. If
                           it contains directory separators or parent
                           references, it will be rejected.

        :raises InsecurePath: If the result of combining this path with the
                              given path would result in a path which is not a
                              direct child of this path.

        :return: The child path
        :rtype: :py:class:`FilePath`
        """

        # Catch paths like C:blah that don't have a slash. This is
        # Windows-only.
        if isWindows and path.count(b":"):
            raise InsecurePath(
                "Colons not permitted in Windows: %r" % (path,))

        # Catch paths with separators like "./".
        if self.sep in path:
            raise InsecurePath(
                "%r contains directory separators" % (path,))

        norm = normpath(path)
        if self.sep in norm:
            raise InsecurePath(
                "%r (normalized) contains directory separators" % (norm,))

        # Catch attempted traversals above this location. Also catch paths
        # like "." or "" which don't traverse anywhere besides the current
        # path. See Twisted #6728.
        newpath = abspath(joinpath(self.path, norm))
        if newpath == self.path or not newpath.startswith(self.path):
            raise InsecurePath(
                "%r is not a child of %s" % (newpath, self.path))

        return self.clonePath(newpath)

    def preauthChild(self, path):
        """
        Use me if C{path} might have slashes in it, but you know they're safe.

        :param bytes path: A relative path (ie, a path not starting with
                           C{"/"}) which will be interpreted as a child or
                           descendant of this path.

        :return: The child path.
        :rtype: :py:class:`FilePath`
        """
        newpath = abspath(joinpath(self.path, normpath(path)))
        if not newpath.startswith(self.path):
            raise InsecurePath(
                "%s is not a child of %s" % (newpath, self.path))
        return self.clonePath(newpath)

    def childSearchPreauth(self, *paths):
        """
        Return my first existing child with a name in C{paths}.

        C{paths} is expected to be a list of *pre-secured* path fragments;
        in most cases this will be specified by a system administrator and not
        an arbitrary user.

        If no appropriately-named children exist, this will return C{None}.

        :return: C{None} or the child path.
        :rtype: L{types.NoneType} or :py:class:`FilePath`
        """
        p = self.path
        for child in paths:
            jp = joinpath(p, child)
            if exists(jp):
                return self.clonePath(jp)

    def siblingExtensionSearch(self, *exts):
        """
        Attempt to return a path with my name, given multiple possible
        extensions.

        Each extension in C{exts} will be tested and the first path which
        exists will be returned.  If no path exists, C{None} will be returned.
        If C{''} is in C{exts}, then if the file referred to by this path
        exists, C{self} will be returned.

        The extension '*' has a magic meaning, which means "any path that
        begins with C{self.path + '.'} is acceptable".
        """
        p = self.path
        for ext in exts:
            if not ext and self.exists():
                return self
            if ext == b'*':
                basedot = basename(p) + b'.'
                for fn in listdir(dirname(p)):
                    if fn.startswith(basedot):
                        return self.clonePath(joinpath(dirname(p), fn))
            p2 = p + ext
            if exists(p2):
                return self.clonePath(p2)

    def realpath(self):
        """
        Returns the absolute target as a :py:class:`FilePath` if self is a
        link, self otherwise.

        The absolute link is the ultimate file or directory the
        link refers to (for instance, if the link refers to another link, and
        another...).  If the filesystem does not support symlinks, or
        if the link is cyclical, raises a :py:class:`LinkError`.

        :return: :py:class:`FilePath` of the target path.
        :rtype: :py:class:`FilePath`
        :raises LinkError: if links are not supported or links are cyclical.
        """
        result = os.path.realpath(self.path)

        if result == self.path:
            if self.islink():
                raise LinkError("Cyclical link - will loop forever")
            else:
                # We were already correctly unaliased.
                return self
        else:
            return self.clonePath(result)

    def siblingExtension(self, ext):
        """
        Attempt to return a path with my name, given the extension at C{ext}.

        :param str ext: File-extension to search for.

        :return: The sibling path.
        :rtype: :py:class:`FilePath`
        """
        return self.clonePath(self.path + ext)

    def linkTo(self, linkFilePath):
        """
        Creates a symlink to self to at the path in the :py:class:`FilePath`
        C{linkFilePath}.

        Only works on posix systems due to its dependence on
        L{os.symlink}.  Propagates L{OSError}s up from L{os.symlink} if
        C{linkFilePath.parent()} does not exist, or C{linkFilePath} already
        exists.

        :param FilePath linkFilePath: the link to be created.
        """
        os.symlink(self.path, linkFilePath.path)

    def open(self, mode='r'):
        """
        Open this file using C{mode} or for writing if C{alwaysCreate} is
        C{True}.

        In all cases the file is opened in binary mode, so it is not necessary
        to include C{"b"} in C{mode}.

        :param str mode: The mode to open the file in.  Default is C{"r"}.
        :raises AssertionError: If C{"a"} is included in the mode and
                                C{alwaysCreate} is C{True}.
        :rtype: L{file}
        :return: An open L{file} object.
        """
        if self.alwaysCreate:
            # XXX assertions? In my code?
            assert 'a' not in mode, ("Appending not supported when "
                                     "alwaysCreate == True")
            return self.create()
        # This hack is necessary because of a bug in Python 2.7 on Windows:
        # http://bugs.python.org/issue7686
        mode = mode.replace('b', '')
        return open(self.path, mode + 'b')

    # stat methods below

    def restat(self, reraise=True):
        """
        Re-calculate cached effects of 'stat'.  To refresh information on this
        path after you know the filesystem may have changed, call this method.

        :param bool reraise: If true, re-raise exceptions from
                             :py:func:`os.stat`; otherwise, mark this path as
                             not existing, and remove any cached stat
                             information.

        :raise Exception: If C{reraise} is C{True} and an exception occurs
                          while reloading metadata.

        .. note:: Please do not use this method.

        .. deprecated:: 0.2
        """
        try:
            self.statinfo = stat(self.path)
        except OSError:
            self.statinfo = 0
            if reraise:
                raise

    def changed(self):
        """
        Clear any cached information about the state of this path on disk.
        """

        self.statinfo = None

    def chmod(self, mode):
        """
        Changes the permissions on self, if possible.  Propagates errors from
        L{os.chmod} up.

        :param int mode: the new permissions desired (same as the command line
                         chmod)
        """
        os.chmod(self.path, mode)

    def getsize(self):
        """
        Retrieve the size of this file in bytes.

        :return: The size of the file at this file path in bytes.
        :raise Exception: if the size cannot be obtained.
        :rtype: int
        """
        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return st.st_size

    def getModificationTime(self):
        """
        Retrieve the time of last access from this file.

        :return: a number of seconds from the epoch.
        :rtype: float
        """
        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return float(st.st_mtime)

    def getStatusChangeTime(self):
        """
        Retrieve the time of the last status change for this file.

        :return: a number of seconds from the epoch.
        :rtype: float
        """
        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return float(st.st_ctime)

    def getAccessTime(self):
        """
        Retrieve the time that this file was last accessed.

        :return: a number of seconds from the epoch.
        :rtype: float
        """
        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return float(st.st_atime)

    def getInodeNumber(self):
        """
        Retrieve the file serial number, also called inode number, which
        distinguishes this file from all other files on the same device.

        :raise NotImplementedError: if the platform is Windows, since the
                                    inode number would be a dummy value for
                                    all files in Windows

        :return: a number representing the file serial number
        :rtype: int
        """
        if isWindows:
            raise NotImplementedError

        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return st.st_ino

    def getDevice(self):
        """
        Retrieves the device containing the file.  The inode number and device
        number together uniquely identify the file, but the device number is
        not necessarily consistent across reboots or system crashes.

        :raise NotImplementedError: if the platform is Windows, since the
                                    device number would be 0 for all
                                    partitions on a Windows platform
        :return: a number representing the device
        :rtype: int
        """
        if isWindows:
            raise NotImplementedError

        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return st.st_dev

    def getNumberOfHardLinks(self):
        """
        Retrieves the number of hard links to the file.

        This count keeps track of how many directories have entries for this
        file. If the count is ever decremented to zero then the file itself is
        discarded as soon as no process still holds it open.  Symbolic links
        are not counted in the total.

        :raise NotImplementedError: if the platform is Windows, since Windows
                                    doesn't maintain a link count for
                                    directories, and :py:func:`os.stat` does
                                    not set C{st_nlink} on Windows anyway.
        :return: the number of hard links to the file
        :rtype: int
        """
        if isWindows:
            raise NotImplementedError

        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return st.st_nlink

    def getUserID(self):
        """
        Returns the user ID of the file's owner.

        :raise NotImplementedError: if the platform is Windows, since the UID
                                    is always 0 on Windows
        :return: the user ID of the file's owner
        :rtype: L{int}
        """
        if isWindows:
            raise NotImplementedError

        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return st.st_uid

    def getGroupID(self):
        """
        Returns the group ID of the file.

        :raise NotImplementedError: if the platform is Windows, since the GID
                                    is always 0 on windows
        :return: the group ID of the file
        :rtype: int
        """
        if isWindows:
            raise NotImplementedError

        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return st.st_gid

    def getPermissions(self):
        """
        Returns the permissions of the file.  Should also work on Windows;
        however, those permissions may not be what is expected in Windows.

        :return: the permissions for the file
        :rtype: :py:class:`Permissions`
        """
        st = self.statinfo
        if not st:
            self.restat()
            st = self.statinfo
        return Permissions.fromStat(S_IMODE(st.st_mode))

    def exists(self):
        """
        Check if this :py:class:`FilePath` exists.

        :return: Whether this path definitely exists.
        :rtype: bool
        """
        if self.statinfo:
            return True
        else:
            self.restat(False)
            if self.statinfo:
                return True
            else:
                return False

    def isdir(self):
        """
        Check if this :py:class:`FilePath` refers to a directory.

        :return: Whether this :py:class:`FilePath` refers to a directory
        :rtype: bool
        """
        st = self.statinfo
        if not st:
            self.restat(False)
            st = self.statinfo
            if not st:
                return False
        return S_ISDIR(st.st_mode)

    def isfile(self):
        """
        Check if this file path refers to a regular file.

        :return: C{True} if this :py:class:`FilePath` points to a regular file
                 (not a directory, socket, named pipe, etc), C{False}
                 otherwise.
        :rtype: L{bool}
        """
        st = self.statinfo
        if not st:
            self.restat(False)
            st = self.statinfo
            if not st:
                return False
        return S_ISREG(st.st_mode)

    def isBlockDevice(self):
        """
        Returns whether the underlying path is a block device.

        :return: C{True} if it is a block device, C{False} otherwise
        :rtype: L{bool}
        """
        st = self.statinfo
        if not st:
            self.restat(False)
            st = self.statinfo
            if not st:
                return False
        return S_ISBLK(st.st_mode)

    def isSocket(self):
        """
        Returns whether the underlying path is a socket.

        :return: C{True} if it is a socket, C{False} otherwise
        :rtype: L{bool}
        """
        st = self.statinfo
        if not st:
            self.restat(False)
            st = self.statinfo
            if not st:
                return False
        return S_ISSOCK(st.st_mode)

    def islink(self):
        """
        Check if this :py:class:`FilePath` points to a symbolic link.

        :return: C{True} if this :py:class:`FilePath` points to a symbolic
                 link, C{False} otherwise.
        :rtype: L{bool}
        """
        # We can't use cached stat results here, because that is the stat of
        # the destination - (see #1773) which in *every case* but this one is
        # the right thing to use.  We could call lstat here and use that, but
        # it seems unlikely we'd actually save any work that way.  -glyph
        return islink(self.path)

    def isabs(self):
        """
        Check if this :py:class:`FilePath` refers to an absolute path.

        .. deprecated:: 0.2
           This method always returns True. To replace this method, simply
           replace its usage in code with ``True`` and then simplify as
           needed.

        :return: True
        :rtype: bool
        """
        return isabs(self.path)

    def listdir(self):
        """
        List the base names of the direct children of this :py:class:`FilePath`.

        :return: A L{list} of L{bytes} giving the names of the contents of the
                 directory this :py:class:`FilePath` refers to.  These names
                 are relative to this :py:class:`FilePath`.
        :rtype: L{list}

        :raise OSError: If an error occurs while listing the directory.  If
                        the error is 'serious', meaning that the operation
                        failed due to an access violation, exhaustion of some
                        kind of resource (file descriptors or memory), OSError
                        or a platform-specific variant will be raised.

        :raise UnlistableError: If the inability to list the directory is due
                                to this path not existing or not being a
                                directory, the more specific OSError subclass
                                L{UnlistableError} is raised instead.

        :raise: Anything the platform L{os.listdir} implementation might raise
                (typically L{OSError}).
        """
        try:
            subnames = listdir(self.path)
        except WindowsError as winErrObj:
            # WindowsError is an OSError subclass, so if not for this clause
            # the OSError clause below would be handling these.  Windows error
            # codes aren't the same as POSIX error codes, so we need to handle
            # them differently.

            # Under Python 2.5 on Windows, WindowsError has a winerror
            # attribute and an errno attribute.  The winerror attribute is
            # bound to the Windows error code while the errno attribute is
            # bound to a translation of that code to a perhaps equivalent POSIX
            # error number.

            # Under Python 2.4 on Windows, WindowsError only has an errno
            # attribute.  It is bound to the Windows error code.

            # For simplicity of code and to keep the number of paths through
            # this suite minimal, we grab the Windows error code under either
            # version.

            # Furthermore, attempting to use os.listdir on a non-existent path
            # in Python 2.4 will result in a Windows error code of
            # ERROR_PATH_NOT_FOUND.  However, in Python 2.5,
            # ERROR_FILE_NOT_FOUND results instead. -exarkun
            winerror = getattr(winErrObj, 'winerror', winErrObj.errno)
            if winerror not in (ERROR_PATH_NOT_FOUND,
                                ERROR_FILE_NOT_FOUND,
                                ERROR_INVALID_NAME,
                                ERROR_DIRECTORY):
                raise
            raise UnlistableError(winErrObj)
        except OSError as ose:
            if ose.errno not in (errno.ENOENT, errno.ENOTDIR):
                # Other possible errors here, according to linux manpages:
                # EACCES, EMIFLE, ENFILE, ENOMEM.  None of these seem like the
                # sort of thing which should be handled normally. -glyph
                raise
            raise UnlistableError(ose)
        return subnames

    def splitext(self):
        """
        Split the file path into a pair C{(root, ext)} such that
        C{root + ext == path}.

        :return: Tuple where the first item is the filename and second item is
            the file extension. See Python docs for L{os.path.splitext}.
        :rtype: L{tuple}
        """
        return splitext(self.path)

    def __repr__(self):
        return 'FilePath(%r)' % (self.path,)

    def touch(self):
        """
        Updates the access and last modification times of the file at this
        file path to the current time. Also creates the file if it does not
        already exist.

        @raise Exception: if unable to create or modify the last modification
            time of the file.
        """
        try:
            self.open('a').close()
        except IOError:
            pass
        utime(self.path, None)

    def remove(self):
        """
        Removes the file or directory that is represented by self.  If
        C{self.path} is a directory, recursively remove all its children
        before removing the directory. If it's a file or link, just delete it.
        """
        if self.isdir() and not self.islink():
            for child in self.children():
                child.remove()
            os.rmdir(self.path)
        else:
            os.remove(self.path)
        self.changed()

    def makedirs(self):
        """
        Create all directories not yet existing in C{path} segments, using
        L{os.makedirs}.

        :return: C{None}
        """
        return os.makedirs(self.path)

    def globChildren(self, pattern):
        """
        Assuming I am representing a directory, return a list of FilePaths
        representing my children that match the given pattern.

        @param pattern: A glob pattern to use to match child paths.
        @type pattern: L{bytes}

        :return: A L{list} of matching children.
        :rtype: L{list}
        """
        import glob
        path = self.path[-1] == b'/' and self.path + pattern or self.sep.join(
            [self.path, pattern])
        return map(self.clonePath, glob.glob(path))

    def basename(self):
        """
        Retrieve the final component of the file path's path (everything
        after the final path separator).

        :return: The final component of the :py:class:`FilePath`'s path (Everything
            after the final path separator).
        :rtype: L{bytes}
        """
        return basename(self.path)

    def dirname(self):
        """
        Retrieve all of the components of the :py:class:`FilePath`'s path except the
        last one (everything up to the final path separator).

        :return: All of the components of the :py:class:`FilePath`'s path except the
            last one (everything up to the final path separator).
        :rtype: L{bytes}
        """
        return dirname(self.path)

    def parent(self):
        """
        A file path for the directory containing the file at this file path.

        :return: A :py:class:`FilePath` representing the path which directly contains
            this :py:class:`FilePath`.
        :rtype: :py:class:`FilePath`
        """
        return self.clonePath(self.dirname())

    def setContent(self, content, ext=b'.new'):
        """
        Replace the file at this path with a new file that contains the given
        bytes, trying to avoid data-loss in the meanwhile.

        On UNIX-like platforms, this method does its best to ensure that by
        the time this method returns, either the old contents *or* the new
        contents of the file will be present at this path for subsequent
        readers regardless of premature device removal, program crash, or
        power loss, making the following assumptions:

            - your filesystem is journaled (i.e. your filesystem will not
              I{itself} lose data due to power loss)

            - your filesystem's C{rename()} is atomic

            - your filesystem will not discard new data while preserving new
              metadata (see U{http://mjg59.livejournal.com/108257.html} for
              more detail)

        On most versions of Windows there is no atomic C{rename()} (see
        U{http://bit.ly/win32-overwrite} for more information), so this method
        is slightly less helpful.  There is a small window where the file at
        this path may be deleted before the new file is moved to replace it:
        however, the new file will be fully written and flushed beforehand so
        in the unlikely event that there is a crash at that point, it should
        be possible for the user to manually recover the new version of their
        data.  In the future, Twisted will support atomic file moves on those
        versions of Windows which *do* support them: see U{Twisted ticket
        3004<http://twistedmatrix.com/trac/ticket/3004>}.

        This method should be safe for use by multiple concurrent processes,
        but note that it is not easy to predict which process's contents will
        ultimately end up on disk if they invoke this method at close to the
        same time.

        :param bytes content: The desired contents of the file at this path.

        :param bytes ext: An extension to append to the temporary filename
                          used to store the bytes while they are being
                          written.  This can be used to make sure that
                          temporary files can be identified by their suffix,
                          for cleanup in case of crashes.
        """
        sib = self.temporarySibling(ext)
        f = sib.open('w')
        try:
            f.write(content)
        finally:
            f.close()
        if isWindows and exists(self.path):
            os.unlink(self.path)
        os.rename(sib.path, self.path)

    def __cmp__(self, other):
        if not isinstance(other, FilePath):
            return NotImplemented
        return cmp(self.path, other.path)

    def createDirectory(self):
        """
        Create the directory the :py:class:`FilePath` refers to.

        @see: L{makedirs}

        :raise OSError: If the directory cannot be created.
        """
        os.mkdir(self.path)

    def requireCreate(self, val=True):
        """
        Sets the C{alwaysCreate} variable.

        :param bool val: C{True} or C{False}, indicating whether opening this
                         path will be required to create the file or not.
        """

        self.alwaysCreate = val

    def create(self):
        """
        Exclusively create a file, only if this file previously did not exist.

        :return: A file-like object opened from this path.
        """
        fdint = os.open(self.path, _CREATE_FLAGS)

        # XXX TODO: 'name' attribute of returned files is not mutable or
        # settable via fdopen, so this file is slighly less functional than the
        # one returned from 'open' by default.  send a patch to Python...

        return os.fdopen(fdint, 'w+b')

    def temporarySibling(self, extension=b""):
        """
        Construct a path referring to a sibling of this path.

        The resulting path will be unpredictable, so that other subprocesses
        should neither accidentally attempt to refer to the same path before
        it is created, nor they should other processes be able to guess its
        name in advance.

        :param bytes extension: A suffix to append to the created filename.
                                (Note that if you want an extension with a '.'
                                you must include the '.' yourself.)

        :return: A FilePath with the given extension suffix and with
                 C{alwaysCreate} set to True.

        :rtype: :py:class:`FilePath`
        """
        sib = self.sibling(_secureEnoughString() + self.basename() + extension)
        sib.requireCreate()
        return sib

    _chunkSize = 2 ** 2 ** 2 ** 2

    def copyTo(self, destination, followLinks=True):
        """
        Copies self to destination.

        If self doesn't exist, an OSError is raised.

        If self is a directory, this method copies its children (but not
        itself) recursively to destination - if destination does not exist as
        a directory, this method creates it.  If destination is a file, an
        IOError will be raised.

        If self is a file, this method copies it to destination.  If
        destination is a file, this method overwrites it.  If destination is a
        directory, an IOError will be raised.

        If self is a link (and followLinks is False), self will be copied over
        as a new symlink with the same target as returned by os.readlink.
        That means that if it is absolute, both the old and new symlink will
        link to the same thing.  If it's relative, then perhaps not (and it's
        also possible that this relative link will be broken).

        File/directory permissions and ownership will NOT be copied over.

        If followLinks is True, symlinks are followed so that they're treated
        as their targets.  In other words, if self is a link, the link's
        target will be copied.  If destination is a link, self will be copied
        to the destination's target (the actual destination will be
        destination's target).  Symlinks under self (if self is a directory)
        will be followed and its target's children be copied recursively.

        If followLinks is False, symlinks will be copied over as symlinks.

        :param FilePath destination: the destination (a FilePath) to which
                                     self should be copied
        :param bool followLinks: whether symlinks in self should be treated as
                                 links or as their targets
        """
        if self.islink() and not followLinks:
            os.symlink(os.readlink(self.path), destination.path)
            return
        # XXX TODO: *thorough* audit and documentation of the exact desired
        # semantics of this code.  Right now the behavior of existent
        # destination symlinks is convenient, and quite possibly correct, but
        # its security properties need to be explained.
        if self.isdir():
            if not destination.exists():
                destination.createDirectory()
            for child in self.children():
                destChild = destination.child(child.basename())
                child.copyTo(destChild, followLinks)
        elif self.isfile():
            writefile = destination.open('w')
            try:
                readfile = self.open()
                try:
                    while True:
                        # XXX TODO: optionally use os.open, os.read and
                        # O_DIRECT and use os.fstatvfs to determine chunk
                        # sizes and make *****sure**** copy is page-atomic;
                        # the following is good enough for 99.9% of everybody
                        # and won't take a week to audit though.
                        chunk = readfile.read(self._chunkSize)
                        writefile.write(chunk)
                        if len(chunk) < self._chunkSize:
                            break
                finally:
                    readfile.close()
            finally:
                writefile.close()
        elif not self.exists():
            raise OSError(errno.ENOENT, "No such file or directory")
        else:
            # If you see the following message because you want to copy
            # symlinks, fifos, block devices, character devices, or unix
            # sockets, please feel free to add support to do sensible things in
            # reaction to those types!
            raise NotImplementedError(
                "Only copying of files and directories supported")

    def moveTo(self, destination, followLinks=True):
        """
        Move self to destination - basically renaming self to whatever
        destination is named.

        If destination is an already-existing directory,
        moves all children to destination if destination is empty.  If
        destination is a non-empty directory, or destination is a file, an
        OSError will be raised.

        If moving between filesystems, self needs to be copied, and everything
        that applies to copyTo applies to moveTo.

        @param destination: the destination (a FilePath) to which self
            should be copied
        @param followLinks: whether symlinks in self should be treated as links
            or as their targets (only applicable when moving between
            filesystems)
        """
        try:
            os.rename(self.path, destination.path)
        except OSError as ose:
            if ose.errno == errno.EXDEV:
                # man 2 rename, ubuntu linux 5.10 "breezy":

                #   oldpath and newpath are not on the same mounted filesystem.
                #   (Linux permits a filesystem to be mounted at multiple
                #   points, but rename(2) does not work across different mount
                #   points, even if the same filesystem is mounted on both.)

                # that means it's time to copy trees of directories!
                secsib = destination.temporarySibling()
                # Slow...
                self.copyTo(secsib, followLinks)
                # Visible.
                secsib.moveTo(destination, followLinks)

                # done creating new stuff.  let's clean me up.
                mysecsib = self.temporarySibling()
                # Visible...
                self.moveTo(mysecsib, followLinks)
                # Slow.
                mysecsib.remove()
            else:
                raise
        else:
            self.changed()
            destination.changed()


FilePath.clonePath = FilePath
