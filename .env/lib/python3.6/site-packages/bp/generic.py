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
from bp.errors import LinkError


def genericParents(path):
    """
    Retrieve an iterator of all the ancestors of the given path.

    :return: An iterator of all the ancestors of the given path, from the most
             recent (its immediate parent) to the root of its filesystem.
    :rtype: iterator
    """

    parent = path.parent()
    # root.parent() == root, so this means "are we the root"
    while path != parent:
        yield parent
        path = parent
        parent = parent.parent()


def genericSibling(path, segment):
    """
    Return an L{IFilePath} with the same directory as the given path, but with
    a basename of C{segment}.

    :param str segment: The basename of the L{IFilePath} to return.

    :return: The sibling path.
    :rtype: L{IFilePath}
    """

    return path.parent().child(segment)


def genericChildren(path):
    """
    List the children of the given path.

    :return: an iterable of all currently-existing children of the path.
    :rtype: iterable
    """

    return map(path.child, path.listdir())


def genericWalk(path, descend=None):
    """
    Yield a path, then each of its children, and each of those children's
    children in turn.

    :param callable descend: A one-argument callable that will return True for
                             FilePaths that should be traversed and False
                             otherwise. It will be called with each path for
                             which :py:meth:`.isdir` returns True. If omitted,
                             all directories will be traversed, including
                             symbolic links.

    :raises LinkError: A cycle of symbolic links was found

    :return: a generator yielding FilePath-like objects
    :rtype: generator
    """

    # Note that we already agreed to yield this path.
    yield path

    if path.isdir():
        for c in path.children():
            # we should first see if it's what we want, then we
            # can walk through the directory
            pred = descend is None or (c.isdir() and descend(c))
            if pred:
                for subc in c.walk(descend):
                    # Check for symlink loops.
                    rsubc = subc.realpath()
                    rself = path.realpath()
                    if rsubc == rself or rsubc in rself.parents():
                        raise LinkError("Cycle in file graph.")
                    yield subc
            else:
                yield c


def genericDescendant(path, segments):
    """
    Retrieve a child or child's child of the given path.

    :param iterable segments: A sequence of path segments as L{str} instances.

    :return: A L{FilePath} constructed by looking up the C{segments[0]} child
             of this path, the C{segments[1]} child of that path, and so on.
    """

    for name in segments:
        path = path.child(name)
    return path


def genericSegmentsFrom(path, ancestor):
    """
    Return a list of segments between a child and its ancestor.

    For example, in the case of a path X representing /a/b/c/d and a path Y
    representing /a/b, C{Y.segmentsFrom(X)} will return C{['c', 'd']}.

    :param ancestor: an instance of the same class as self, ostensibly an
                     ancestor of self.

    :raise ValueError: When the 'ancestor' parameter is not actually an
                       ancestor, i.e. a path for /x/y/z is passed as an
                       ancestor for /a/b/c/d.

    :return: a list of segments
    :rtype: list
    """

    # The original author alludes to an "obvious fast implementation". I
    # cannot envision an obvious fast implementation which behaves
    # correctly on arbitrary IFilePaths, so I will leave this here for the
    # next brave hacker. ~ C.
    f = path
    p = f.parent()
    segments = []
    while f != ancestor and f != p:
        segments.append(f.basename())
        f, p = p, p.parent()
    if f == ancestor and segments:
        segments.reverse()
        return segments
    raise ValueError("%r not parent of %r" % (ancestor, path))


def genericGetContent(path):
    """
    Retrieve the data from a given file path.
    """

    # We are not currently willing to use a with-statement here, for backwards
    # compatibility.
    fp = path.open()
    try:
        return fp.read()
    finally:
        fp.close()
