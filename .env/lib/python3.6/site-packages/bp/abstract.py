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
from zope.interface import Interface, Attribute


class IFilePath(Interface):
    """
    File path object.

    A file path represents a location for a file-like-object and can be
    organized into a hierarchy; a file path can can children which are
    themselves file paths.

    A file path has a name which uniquely identifies it in the context of its
    parent, if it has one; a file path can not have two children with the same
    name.  This name is referred to as the file path's "base name".

    A series of such names can be used to locate nested children of a file
    path; such a series is referred to as the child's "path", relative to the
    parent.  In this case, each name in the path is referred to as a "path
    segment"; the child's base name is the segment in the path.

    When representing a file path as a string, a "path separator" is used to
    delimit the path segments within the string.  For a file system path, that
    would be C{os.sep}.

    Note that the values of child names may be restricted.  For example, a file
    system path will not allow the use of the path separator in a name, and
    certain names (eg. C{"."} and C{".."}) may be reserved or have special
    meanings.

    Note that, in the presence of symlinks, two file paths may differ in
    equality but address the same data; this is called "aliasing" and is
    completely legal.
    """

    sep = Attribute("The path separator to use in string representations")
    path = Attribute("A string representation of the path")

    # Navigation

    def parent():
        """
        A file path for the directory containing the file at this file path.

        As a special case, the file path representing the root is its own
        parent; this invariant must always be preserved.
        """

    def sibling(name):
        """
        A file path for the directory containing the file at this file path.

        @param name: the name of a sibling of this path. C{name} must be a
            direct sibling of this path and may not contain a path separator.

        @return: a sibling file path of this one.
        """

    def child(name):
        """
        Obtain a direct child of this file path.  The child may or may not
        exist.

        @param name: the name of a child of this path. C{name} must be a direct
            child of this path and may not contain a path separator.
        @return: the child of this path with the given C{name}.
        @raise InsecurePath: if C{name} describes a file path that is not a
            direct child of this file path.
        """

    def children():
        """
        List the children of this path object.

        @return: a sequence of the children of the directory at this file path.
        @raise Exception: if the file at this file path is not a directory.
        """

    # Segments

    def basename():
        """
        Retrieve the final component of the file path's path (everything
        after the final path separator).

        @return: the base name of this file path.
        @rtype: L{str}
        """

    # Writing and reading

    def open(mode="r"):
        """
        Opens this file path with the given mode.

        @return: a file-like object.
        @raise Exception: if this file path cannot be opened.
        """

    def createDirectory():
        """
        Create this file path as a directory.

        @raise Exception: If the directory cannot be created.
        """

    def getContent():
        """
        Retrieve the bytes located at this file path.
        """

    def setContent(content, ext=b'.new'):
        """
        Replace or create the file at this path with a new file that contains
        the given bytes.

        This method should attempt to be as atomic as possible.

        @param content: The desired contents of the file at this path.
        @type content: L{bytes}

        @param ext: An extension to append to the temporary filename used to
            store the bytes while they are being written.  This can be used to
            make sure that temporary files can be identified by their suffix,
            for cleanup in case of crashes.
        @type ext: L{bytes}
        """

    # Stat and other queries

    def changed():
        """
        Clear any cached information about the state of this path on disk.
        """

    def getsize():
        """
        Retrieve the size of this file in bytes.

        @return: the size of the file at this file path in bytes.
        @raise Exception: if the size cannot be obtained.
        """

    def getModificationTime():
        """
        Retrieve the time of last access from this file.

        @return: a number of seconds from the epoch.
        @rtype: L{float}
        """

    def getStatusChangeTime():
        """
        Retrieve the time of the last status change for this file.

        @return: a number of seconds from the epoch.
        @rtype: L{float}
        """

    def getAccessTime():
        """
        Retrieve the time that this file was last accessed.

        @return: a number of seconds from the epoch.
        @rtype: L{float}
        """

    def exists():
        """
        Check if this file path exists.

        @return: C{True} if the file at this file path exists, C{False}
            otherwise.
        @rtype: L{bool}
        """

    def isdir():
        """
        Check if this file path refers to a directory.

        @return: C{True} if the file at this file path is a directory, C{False}
            otherwise.
        """

    def isfile():
        """
        Check if this file path refers to a regular file.

        @return: C{True} if the file at this file path is a regular file,
            C{False} otherwise.
        """

    def islink():
        """
        Check if this file path refers to a symbolic ("soft") link.

        @return: C{True} if the file at this file path is a symbolic link, or
            C{False} otherwise.
        """

    # Symlinks

    def realpath():
        """
        A symbolic-link-free file path that is alias-equivalent to this file
        path.

        @return: a file path.
        """
