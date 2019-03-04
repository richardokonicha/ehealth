from unittest import TestCase

from bp.abstract import IFilePath
from bp.memory import MemoryFS, MemoryPath
from testscenarios import with_scenarios
from zope.interface import verify

from l import project


class TestProjectDetection(TestCase):
    def setUp(self):
        self.fs = MemoryFS()
        self.root = MemoryPath(fs=self.fs, path=("test-dir",))
        self.root.createDirectory()

    def test_it_detects_git_repositories(self):
        self.root.child(".git").createDirectory()
        self.assertEqual(
            project.from_path(self.root),
            project.GitPath(
                git_dir=self.root.child(".git"),
                path=self.root,
            ),
        )

    def test_it_detects_hg_repositories(self):
        self.root.child(".hg").createDirectory()
        self.assertEqual(
            project.from_path(self.root),
            project.HgPath(
                hg_dir=self.root.child(".hg"),
                path=self.root,
            ),
        )

    def test_it_detects_normal_directories(self):
        self.assertEqual(project.from_path(self.root), self.root)


@with_scenarios()
class TestAreFilePaths(TestCase):

    scenarios = [
        (cls.__name__, {"Path": cls})
        for cls in [project.GitPath, project.HgPath]
    ]

    def test_are_IFilePaths(self):
        verify.verifyClass(IFilePath, self.Path)

    def test_parent(self):
        parent = self.Path(path=MemoryPath(fs=MemoryFS()))
        child = parent.child("child")
        self.assertEqual(child.parent(), parent)

    def test_parent_outside_repo(self):
        repo = self.Path(path=MemoryPath(fs=MemoryFS(), path=("repo",)))
        self.assertEqual(repo.parent(), repo)

    def test_segmentsFrom(self):
        parent = self.Path(path=MemoryPath(fs=MemoryFS()))
        child = parent.child("child").child("another")
        self.assertEqual(child.segmentsFrom(parent), ["child", "another"])
