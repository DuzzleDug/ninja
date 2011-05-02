#!/usr/bin/python
#
# Copyright 2001 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script that generates the build.ninja for ninja itself.

Projects that use ninja themselves should either write a similar script
or use a meta-build system that supports Ninja output."""

import os
import sys
sys.path.insert(0, 'misc')

import ninja

n = ninja.Writer(sys.stdout)
n.comment('This file is used to build ninja itself.')
n.comment('It is generated by ' + os.path.basename(__file__) + '.')
n.newline()

def src(filename):
    return os.path.join('src', filename)
def built(filename):
    return os.path.join('$builddir', filename)
def cxx(name, **kwargs):
    return n.build(built(name + '.o'), 'cxx', src(name + '.cc'), **kwargs)

n.variable('builddir', 'build')
n.variable('cxx', os.environ.get('CC', 'g++'))
cflags = ('-O2 -g -Wall -Wno-deprecated -fno-exceptions -fvisibility=hidden '
          '-pipe')
if 'CFLAGS' in os.environ:
    cflags += ' ' + os.environ['CFLAGS']
n.variable('cflags', cflags)
n.variable('ldflags', os.environ.get('LDFLAGS', ''))
n.newline()

n.rule('cxx',
       command='$cxx -MMD -MF $out.d $cflags -c $in -o $out',
       depfile='$out.d',
       description='CC $out')
n.newline()

n.rule('ar',
       command='ar crs $out $in',
       description='AR $out')
n.newline()

n.rule('link',
       command='$cxx $ldflags -o $out $in',
       description='LINK $out')
n.newline()

n.comment('browse_py.h is used to inline browse.py.')
n.rule('inline',
       command='src/inline.sh $varname < $in > $out',
       description='INLINE $out')
n.build(built('browse_py.h'), 'inline', src('browse.py'),
        variables=[('varname', 'kBrowsePy')])
n.newline()

objs = []

n.comment("TODO: this shouldn't need to depend on inline.sh.")
objs += cxx('browse',
            implicit='src/inline.sh',
            order_only=built('browse_py.h'))
n.newline()

n.comment('Core source files all build into ninja library.')
for name in ['build', 'build_log', 'clean', 'eval_env', 'graph', 'graphviz',
             'parsers', 'subprocess', 'util',
             'ninja_jumble']:
    objs += cxx(name)
ninja_lib = n.build(built('ninja.a'), 'ar', objs)
n.newline()

n.comment('Main executable is library plus main() function.')
objs = cxx('ninja')
n.build('ninja', 'link', objs + ninja_lib)

n.comment('Tests all build into ninja_test executable.')
objs = []
for name in ['build_test', 'build_log_test', 'graph_test', 'ninja_test',
             'parsers_test', 'subprocess_test', 'util_test',
             'test']:
    objs += cxx(name)
ldflags = '-lgtest -lgtest_main -lpthread'
if 'LDFLAGS' in os.environ:
    ldflags += ' ' + os.environ.get('LDFLAGS')
n.build('ninja_test', 'link',
        objs + ninja_lib,
        variables=[('ldflags', ldflags)])
n.newline()

n.comment('Generate a graph using the "graph" tool.')
n.rule('gendot',
       command='./ninja -t graph > $out')
n.rule('gengraph',
       command='dot -Tpng $in > $out')
dot = n.build(built('graph.dot'), 'gendot', ['ninja', 'build.ninja'])
n.build('graph.png', 'gengraph', dot)
n.newline()

n.comment('Generate the manual using asciidoc.')
n.rule('asciidoc',
       command='asciidoc -a toc $in',
       description='ASCIIDOC $in')
n.build('manual.html', 'asciidoc', 'manual.asciidoc')
n.build('manual', 'phony',
        order_only='manual.html')
n.newline()

n.comment('Generate Doxygen.')
n.rule('doxygen',
       command='doxygen $in',
       description='DOXYGEN $in')
n.variable('doxygen_mainpage_generator',
           './gen_doxygen_mainpage.sh')
n.rule('doxygen_mainpage',
       command='$doxygen_mainpage_generator $in > $out',
       description='DOXYGEN_MAINPAGE $out')
mainpage = n.build(built('doxygen_mainpage'), 'doxygen_mainpage',
                   ['README', 'HACKING', 'COPYING'],
                   implicit=['$doxygen_mainpage_generator'])
n.build('doxygen', 'doxygen', 'doxygen.config',
        implicit=mainpage,
        order_only=mainpage)
n.newline()

n.comment('Regenerate build files if build script changes.')
n.rule('gen-build-file',
       command='./gen-build-file.py > $out')
n.build('build.ninja', 'gen-build-file',
        implicit='gen-build-file.py')
