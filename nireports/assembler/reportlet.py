# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# Copyright 2023 The NiPreps Developers <nipreps@gmail.com>
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
#
# We support and encourage derived works from this project, please read
# about our expectations at
#
#     https://www.nipreps.org/community/licensing/
#
# STATEMENT OF CHANGES: This file was ported carrying over full git history from niworkflows,
# another NiPreps project licensed under the Apache-2.0 terms, and has been changed since.
"""The reporting visualization unit or *reportlet*."""
from pathlib import Path
from nipype.utils.filemanip import copyfile
from nireports.assembler.misc import SVG_SNIPPET, Element


class Reportlet(Element):
    """
    A reportlet has title, description and a list of components with either an
    HTML fragment or a path to an SVG file, and possibly a caption. This is a
    factory class to generate Reportlets reusing the layout from a ``Report``
    object.

    .. testsetup::

    >>> from pkg_resources import resource_filename
    >>> from shutil import copytree
    >>> from bids.layout import BIDSLayout
    >>> test_data_path = resource_filename('nireports', 'assembler/data/tests/work')
    >>> testdir = Path(tmpdir)
    >>> data_dir = copytree(test_data_path, str(testdir / 'work'))
    >>> out_figs = testdir / 'out' / 'fmriprep'
    >>> bl = BIDSLayout(str(testdir / 'work' / 'reportlets'),
    ...                 config='figures', validate=False)

    .. doctest::

    >>> bl.get(subject='01', desc='reconall')[0]._path.as_posix() # doctest: +ELLIPSIS
    '.../nireports/sub-01/figures/sub-01_desc-reconall_T1w.svg'

    >>> len(bl.get(subject='01', space='.*', regex_search=True))
    2

    >>> r = Reportlet(bl, out_figs, config={
    ...     'title': 'Some Title', 'bids': {'datatype': 'figures', 'desc': 'reconall'},
    ...     'description': 'Some description'})
    >>> r.name
    'datatype-figures_desc-reconall'

    >>> r.components[0][0].startswith('<img')
    True

    >>> r = Reportlet(bl, out_figs, config={
    ...     'title': 'Some Title', 'bids': {'datatype': 'figures', 'desc': 'reconall'},
    ...     'description': 'Some description', 'static': False})
    >>> r.name
    'datatype-figures_desc-reconall'

    >>> r.components[0][0].startswith('<object')
    True

    >>> r = Reportlet(bl, out_figs, config={
    ...     'title': 'Some Title', 'bids': {'datatype': 'figures', 'desc': 'summary'},
    ...     'description': 'Some description'})

    >>> r.components[0][0].startswith('<h3')
    True

    >>> r.components[0][1] is None
    True

    >>> r = Reportlet(bl, out_figs, config={
    ...     'title': 'Some Title',
    ...     'bids': {'datatype': 'figures', 'space': '.*', 'regex_search': True},
    ...     'caption': 'Some description {space}'})
    >>> sorted(r.components)[0][1]
    'Some description MNI152NLin2009cAsym'

    >>> sorted(r.components)[1][1]
    'Some description MNI152NLin6Asym'


    >>> r = Reportlet(bl, out_figs, config={
    ...     'title': 'Some Title',
    ...     'bids': {'datatype': 'fmap', 'space': '.*', 'regex_search': True},
    ...     'caption': 'Some description {space}'})
    >>> r.is_empty()
    True

    """

    def __init__(self, layout, out_dir, config=None):
        if not config:
            raise RuntimeError("Reportlet must have a config object")

        self.title = config.get("title")
        self.subtitle = config.get("subtitle")
        self.description = config.get("description")
        self.components = []

        # Determine whether this is a "BIDS-type" reportlet (typically, an SVG file)
        if bidsquery := config.get("bids", {}):
            self.name = config.get(
                "name",
                "_".join("%s-%s" % i for i in sorted(bidsquery.items())),
            )

            # Query the BIDS layout of reportlets
            files = layout.get(**bidsquery)

            for bidsfile in files:
                src = Path(bidsfile.path)
                ext = "".join(src.suffixes)
                desc_text = config.get("caption")

                contents = None
                if ext == ".html":
                    contents = src.read_text().strip()
                elif ext == ".svg":
                    entities = dict(bidsfile.entities)
                    if desc_text:
                        desc_text = desc_text.format(**entities)

                    try:
                        html_anchor = src.relative_to(out_dir)
                    except ValueError:
                        html_anchor = src.relative_to(Path(layout.root).parent)
                        dst = out_dir / html_anchor
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        copyfile(src, dst, copy=True, use_hardlink=True)

                    contents = SVG_SNIPPET[config.get("static", True)].format(html_anchor)

                    # Our current implementations of dynamic reportlets do this themselves,
                    # however I'll leave the code here since this is potentially something we
                    # will want to transfer from every figure generator to this location.
                    # The following code misses setting preserveAspecRatio="xMidYMid meet"
                    # if not is_static:
                    #     # Remove height and width attributes from initial <svg> tag
                    #     svglines = out_file.read_text().splitlines()
                    #     expr = re.compile(r' (height|width)=["\'][0-9]+(\.[0-9]*)?[a-z]*["\']')
                    #     for l, line in enumerate(svglines[:6]):
                    #         if line.strip().startswith('<svg'):
                    #             newline = expr.sub('', line)
                    #             svglines[l] = newline
                    #             out_file.write_text('\n'.join(svglines))
                    #             break

                if contents:
                    self.components.append((contents, desc_text))

    def is_empty(self):
        return len(self.components) == 0
