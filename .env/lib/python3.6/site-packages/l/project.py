import errno
import os
import subprocess

from bp import abstract, generic
from bp.filepath import FilePath
from characteristic import Attribute, attributes
from zope.interface import implementer


def from_path(path):
    git_dir = path.child(".git")
    if git_dir.isdir():
        return GitPath(git_dir=git_dir, path=path)

    try:
        git = subprocess.Popen(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=path.path,
        )
    except OSError as error:
        # The cwd didn't exist
        if error.errno != errno.ENOENT:
            raise
    else:
        stdout, _ = git.communicate()
        if stdout == "true\n":
            return GitPath(path=path)

    hg_dir = path.child(".hg")
    if hg_dir.isdir():
        return HgPath(hg_dir=hg_dir, path=path)  # XXX

    return path


# TODO: Really betterpath should have a separate interface for like,
#       file systems, or listable things.
@implementer(abstract.IFilePath)
@attributes(
    [
        Attribute(name="_git_dir", default_value=None, exclude_from_repr=True),
        Attribute(name="_path", exclude_from_repr=True),
        Attribute(name="path", exclude_from_init=True),
    ],
)
class GitPath(object):

    children = generic.genericChildren
    segmentsFrom = generic.genericSegmentsFrom
    walk = generic.genericWalk

    def clonePath(self, path):
        return GitPath(git_dir=self._git_dir, path=path)

    def child(self, name):
        child = self._path.child(name)
        return GitPath(git_dir=self._git_dir, path=child)

    def parent(self):
        if self._path == self._git_dir:
            return self
        return self.clonePath(path=self._path.parent())

    def listdir(self):
        argv = ["git"]
        if self._git_dir is not None:
            argv.extend(["--git-dir", self._git_dir.path])
        path = self.path + "/" if self.isdir() else ""
        argv.extend(["ls-tree", "--name-only", "HEAD", path])
        listdir = subprocess.check_output(argv).splitlines()
        return [outputted.rpartition("/")[2] for outputted in listdir]


@implementer(abstract.IFilePath)
@attributes(
    [
        Attribute(name="_hg_dir", default_value=None, exclude_from_repr=True),
        Attribute(name="_path", exclude_from_repr=True),
        Attribute(name="path", exclude_from_init=True),
    ],
)
class HgPath(object):

    children = generic.genericChildren
    segmentsFrom = generic.genericSegmentsFrom
    walk = generic.genericWalk

    def __init__(self):
        if self._hg_dir is None:
            self._hg_dir = self._path

    def clonePath(self, path):
        return HgPath(hg_dir=self._hg_dir, path=path)

    def child(self, name):
        return self.clonePath(path=self._path.child(name))

    def parent(self):
        if self._path == self._hg_dir:
            return self
        return self.clonePath(path=self._path.parent())

    def listdir(self):
        paths = subprocess.check_output(
            [
                "hg", "--repository", self.path,
                "files", "--include", "*", "--exclude", "*/*",
            ],
        )
        return (os.path.basename(path) for path in paths.splitlines())


def _proxy_for_attribute(name):
    return property(lambda self: getattr(self._path, name))


for attribute in [
    "basename",
    "changed",
    "createDirectory",
    "exists",
    "getAccessTime",
    "getContent",
    "getModificationTime",
    "getStatusChangeTime",
    "getsize",
    "isdir",
    "isfile",
    "islink",
    "open",
    "path",
    "realpath",
    "remove",
    "sep",  # Apparently not in IFilePath
    "setContent",
    "sibling",
]:
    proxy = _proxy_for_attribute(name=attribute)
    setattr(GitPath, attribute, proxy)
    setattr(HgPath, attribute, proxy)
