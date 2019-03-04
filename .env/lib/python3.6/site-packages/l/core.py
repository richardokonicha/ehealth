_CENTRAL = "├── "
_LAST = "└── "
_VERTICAL = "│   "


class _FakeFilePath(object):
    """
    A thing that isn't really a path but which we trick outputting for.

    """

    # XXX: A nasty hack for sorting
    _always_sorts_first = True

    def __init__(self, path):
        self.path = path

    def __lt__(self, other):
        if not isinstance(other, self.__class__) or other.path not in "..":
            raise TypeError(other)
        return self.path <= other.path

    def basename(self):
        return self.path

    def isdir(self):
        return False


def ls(path):
    return [
        child for child in ls_almost_all(path=path)
        if not child.basename().startswith(".")
    ]


def ls_almost_all(path):
    return path.children()


def ls_all(path):
    return [_FakeFilePath("."), _FakeFilePath("..")] + path.children()


def columnized(paths, sort_by):
    if len(paths) == 1:
        (_, children), = paths
        if children:
            yield _tabularized(children, sort_by=sort_by)
        return

    labelled = _labelled(sorted(paths), sort_by=sort_by)
    label, contents = next(labelled)
    yield label
    yield contents
    for label, contents in labelled:
        yield ""
        yield label
        yield contents


def _labelled(parents_and_children, sort_by):
    for parent, children in parents_and_children:
        yield parent.path + ":", _tabularized(children, sort_by=sort_by)


def _tabularized(children, sort_by):
    return "  ".join(
        child.basename() for child in sorted(children, key=sort_by)
    )


def one_per_line(parents_and_children, sort_by):
    if len(parents_and_children) == 1:
        return (
            child.basename()
            for _, children in parents_and_children
            for child in sorted(children, key=sort_by)
        )
    paths = sorted(
        (
            child
            for _, children in parents_and_children
            for child in children
        ),
        key=sort_by,
    )
    return (child.path for child in paths)


def as_tree(parents_and_children, sort_by):
    for root, _ in parents_and_children:
        yield root.path
        for line in _as_tree(node=root, sort_by=sort_by, prefix="") :
            yield line


def _as_tree(node, sort_by, prefix):
    children = node.children()
    if children:
        children.sort(key=sort_by)
        for child in children[:-1]:
            yield prefix + "├── " + child.basename()
            if child.isdir():
                for line in _as_tree(child, sort_by, prefix + _VERTICAL):
                    yield line
        child = children[-1]
        yield prefix + "└── " + child.basename()
        if child.isdir():
            for line in _as_tree(child, sort_by, prefix + "    "):
                yield line


def recurse(path, ls):
    working = [path]
    while working:
        path = working.pop()
        children = ls(path=path)
        yield path, children
        working.extend(child for child in children if child.isdir())


def flat(path, ls):
    return [(path, ls(path=path))]


def group_directories_first(child):
    return not child.isdir(), child
