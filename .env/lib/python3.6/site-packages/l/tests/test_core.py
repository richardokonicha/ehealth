from io import BytesIO
from textwrap import dedent
from unittest import TestCase

from bp.memory import MemoryFS, MemoryPath

from l import core, cli


class TestOutputters(TestCase):
    def setUp(self):
        self.fs = MemoryFS()
        self.root = MemoryPath(fs=self.fs, path=("test-dir",))
        self.root.createDirectory()

    def assertOutputs(self, result, **kwargs):
        stdout = BytesIO()
        cli.run(stdout=stdout, **kwargs)
        self.assertEqual(stdout.getvalue(), dedent(result))

    def children(self, *new, **kwargs):
        of = kwargs.pop("of", self.root)
        assert not kwargs

        of.createDirectory()
        for child in new:
            path = of.child(child)
            path.setContent("")
            yield path

    def test_it_lists_directories(self):
        foo, bar = self.children("foo", "bar")
        self.assertOutputs(
            output=core.columnized,
            paths=[self.root],
            result="bar  foo\n",
        )

    def test_it_lists_multiple_directories(self):
        one = self.root.child("one")
        two, four = self.children("two", "four", of=one)

        three, = self.children("three")

        self.assertOutputs(
            output=core.columnized,
            paths=[self.root, one],
            result="""\
            /mem/test-dir:
            one  three

            /mem/test-dir/one:
            four  two
            """,
        )


    def test_group_directories_first(self):
        self.root.child("one").createDirectory()
        self.root.child("two").createDirectory()
        three, four = self.children("three", "four")

        self.assertOutputs(
            output=core.columnized,
            sort_by=core.group_directories_first,
            paths=[self.root],
            result="one  two  four  three\n",
        )

    def test_group_directories_first_one_per_line(self):
        self.root.child("one").createDirectory()
        self.root.child("two").createDirectory()
        three, four = self.children("three", "four")

        self.assertOutputs(
            output=core.one_per_line,
            sort_by=core.group_directories_first,
            paths=[self.root],
            result="""\
            one
            two
            four
            three
            """,
        )

    def test_group_directories_first_multiple_one_per_line(self):
        one = self.root.child("one")
        self.root.child("two").createDirectory()
        three, four = self.children("three", "four")
        five, six = self.children("five", "six", of=one)
        one.child("seven").createDirectory()

        self.assertOutputs(
            output=core.one_per_line,
            sort_by=core.group_directories_first,
            paths=[self.root, one],
            result="""\
            /mem/test-dir/one
            /mem/test-dir/one/seven
            /mem/test-dir/two
            /mem/test-dir/four
            /mem/test-dir/one/five
            /mem/test-dir/one/six
            /mem/test-dir/three
            """,
        )

    def test_it_ignores_hidden_files_by_default(self):
        foo, hidden = self.children("foo", ".hidden")
        self.assertOutputs(
            output=core.columnized,
            paths=[self.root],
            result="foo\n",
        )

    def test_it_ignores_hidden_files_by_default_for_multiple_directories(self):
        one = self.root.child("one")
        two, four = self.children(".two", "four", of=one)

        three, = self.children(".three")

        self.assertOutputs(
            output=core.columnized,
            paths=[self.root, one],
            result="""\
            /mem/test-dir:
            one

            /mem/test-dir/one:
            four
            """,
        )

    def test_it_can_list_almost_everything(self):
        one = self.root.child("one")
        two, four = self.children(".two", "four", of=one)

        three, = self.children(".three")

        self.assertOutputs(
            ls=core.ls_almost_all,
            output=core.columnized,
            paths=[self.root, one],
            result="""\
            /mem/test-dir:
            .three  one

            /mem/test-dir/one:
            .two  four
            """,
        )

    def test_it_can_list_everything(self):
        one = self.root.child("one")
        two, four = self.children(".two", "four", of=one)

        three, = self.children(".three")

        self.assertOutputs(
            ls=core.ls_all,
            output=core.columnized,
            paths=[self.root, one],
            result="""\
            /mem/test-dir:
            .  ..  .three  one

            /mem/test-dir/one:
            .  ..  .two  four
            """,
        )

    def test_it_can_list_everything_recursively(self):
        one = self.root.child("one")
        two, four = self.children(".two", "four", of=one)

        three, = self.children(".three")

        self.assertOutputs(
            ls=core.ls_all,
            output=core.columnized,
            recurse=core.recurse,
            paths=[self.root],
            result="""\
            /mem/test-dir:
            .  ..  .three  one

            /mem/test-dir/one:
            .  ..  .two  four
            """,
        )

    def test_it_lists_directories_one_per_line(self):
        foo, bar = self.children("foo", "bar")
        self.assertOutputs(
            output=core.one_per_line,
            paths=[self.root],
            result="bar\nfoo\n",
        )

    def test_it_lists_multiple_absolute_directories_one_per_line(self):
        one = self.root.child("one")
        two, four = self.children("two", "four", of=one)

        three, = self.children("three")

        self.assertOutputs(
            output=core.one_per_line,
            paths=[self.root, one],
            result="""\
            /mem/test-dir/one
            /mem/test-dir/one/four
            /mem/test-dir/one/two
            /mem/test-dir/three
            """,
        )

    def test_it_lists_directories_recursively(self):
        one = self.root.child("one")
        two, four = self.children("two", "four", of=one)

        three, = self.children("three")
        self.assertOutputs(
            output=core.columnized,
            recurse=core.recurse,
            paths=[self.root],
            result="""\
            /mem/test-dir:
            one  three

            /mem/test-dir/one:
            four  two
            """,
        )

    def test_it_lists_directories_recursively_one_per_line(self):
        one = self.root.child("one")
        two, four = self.children("two", "four", of=one)

        three, = self.children("three")
        self.assertOutputs(
            output=core.one_per_line,
            recurse=core.recurse,
            paths=[self.root],
            result="""\
            /mem/test-dir/one
            /mem/test-dir/one/four
            /mem/test-dir/one/two
            /mem/test-dir/three
            """,
        )

    def test_it_lists_nested_trees(self):
        one, two = self.root.child("one"), self.root.child("two")
        foo, bar = self.children("foo", "bar", of=one)
        two.createDirectory()
        two.child("quux").setContent("")
        two.child("baz").createDirectory()
        two.child("baz").child("spam").setContent("")

        self.assertOutputs(
            output=core.as_tree,
            paths=[self.root],
            result="""\
            /mem/test-dir
            ├── one
            │   ├── bar
            │   └── foo
            └── two
                ├── baz
                │   └── spam
                └── quux
            """,
        )

    def test_it_lists_flat_trees(self):
        foo, bar = self.children("foo", "bar")
        self.assertOutputs(
            output=core.as_tree,
            paths=[self.root],
            result="""\
            /mem/test-dir
            ├── bar
            └── foo
            """,
        )

    def test_it_lists_multiple_flat_directories_as_trees(self):
        one, two = self.root.child("one"), self.root.child("two")
        foo, bar = self.children("foo", "bar", of=one)
        baz, quux = self.children("baz", "quux", of=two)

        self.assertOutputs(
            output=core.as_tree,
            paths=[one, two],
            result="""\
            /mem/test-dir/one
            ├── bar
            └── foo
            /mem/test-dir/two
            ├── baz
            └── quux
            """,
        )

    def test_group_directories_first_as_tree(self):
        self.root.child("one").createDirectory()
        self.root.child("two").createDirectory()
        three, four = self.children("three", "four")

        self.assertOutputs(
            output=core.as_tree,
            sort_by=core.group_directories_first,
            paths=[self.root],
            result="""\
            /mem/test-dir
            ├── one
            ├── two
            ├── four
            └── three
            """,
        )

    def test_it_lists_empty_directories(self):
        self.assertOutputs(
            output=core.columnized,
            paths=[self.root],
            result="",
        )

    def test_it_lists_empty_directories_one_per_line(self):
        self.assertOutputs(
            output=core.one_per_line,
            paths=[self.root],
            result="",
        )

    def test_it_lists_empty_directories_as_tree(self):
        self.assertOutputs(
            output=core.as_tree,
            paths=[self.root],
            result="/mem/test-dir\n",
        )

    def test_it_lists_multiple_empty_directories(self):
        self.assertOutputs(
            output=core.columnized,
            paths=[self.root, self.root],
            result="/mem/test-dir:\n\n\n/mem/test-dir:\n\n",
        )

    def test_it_lists_multiple_empty_directories_one_per_line(self):
        self.assertOutputs(
            output=core.one_per_line,
            paths=[self.root, self.root],
            result="",
        )

    def test_it_lists_multiple_empty_directories_as_tree(self):
        self.assertOutputs(
            output=core.as_tree,
            paths=[self.root, self.root],
            result="/mem/test-dir\n" * 2,
        )

    def test_it_ignores_leading_punctuation_when_sorting_as_tree(self):
        one, two, three = self.children("[]one", "two", ".three")
        self.assertOutputs(
            output=core.as_tree,
            paths=[self.root],
            result="""\
            /mem/test-dir
            ├── []one
            ├── .three
            └── two
            """,
        )

    def test_it_ignores_case_when_sorting_as_tree(self):
        one, two, three = self.children("one", "TWO", "thrEE")
        self.assertOutputs(
            output=core.as_tree,
            paths=[self.root],
            result="""\
            /mem/test-dir
            ├── one
            ├── thrEE
            └── TWO
            """,
        )
