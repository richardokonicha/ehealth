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
from bp.memory import MemoryFS, MemoryPath, format_memory_path
from bp.tests.test_paths import AbstractFilePathTestCase


def heads(t):
    for i in range(len(t)):
        yield t[:i]


class MemoryPathTestCase(AbstractFilePathTestCase):

    def subdir(self, *dirname):
        for head in heads(dirname):
            self.fs._dirs.add(head)
        self.fs._dirs.add(dirname)

    def subfile(self, *dirname):
        for head in heads(dirname):
            self.fs._dirs.add(head)
        return self.fs.open(dirname)

    def setUp(self):
        self.fs = MemoryFS()

        AbstractFilePathTestCase.setUp(self)

        self.path = MemoryPath(self.fs)
        self.root = self.path
        self.all = self.fs._dirs | set(self.fs._store.keys())
        self.all = set(format_memory_path(p, "/") for p in self.all)
