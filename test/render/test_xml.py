"""Tests for :mod:`animedex.render.xml`."""

from __future__ import annotations

from xml.etree import ElementTree

import pytest


pytestmark = pytest.mark.unittest


class TestElementToDict:
    def test_empty_element_preserves_tag_and_empty_containers(self):
        from animedex.render.xml import ATTRS_KEY, CHILDREN_BY_TAG_KEY, CHILDREN_KEY, TAG_KEY, element_to_dict

        node = element_to_dict(ElementTree.fromstring("<empty />"))

        assert node[TAG_KEY] == "empty"
        assert node[ATTRS_KEY] == {}
        assert node[CHILDREN_KEY] == []
        assert node[CHILDREN_BY_TAG_KEY] == {}

    def test_attribute_only_element_preserves_attrs(self):
        from animedex.render.xml import ATTRS_KEY, element_to_dict

        node = element_to_dict(ElementTree.fromstring('<item id="1" type="anime" />'))

        assert node[ATTRS_KEY] == {"id": "1", "type": "anime"}

    def test_text_element_preserves_text(self):
        from animedex.render.xml import TEXT_KEY, element_to_dict

        node = element_to_dict(ElementTree.fromstring("<warning>no result</warning>"))

        assert node[TEXT_KEY] == "no result"

    def test_repeated_children_are_grouped_as_lists(self):
        from animedex.render.xml import CHILDREN_BY_TAG_KEY, CHILDREN_KEY, TAG_KEY, element_to_dict

        node = element_to_dict(ElementTree.fromstring("<root><info>A</info><info>B</info><staff>C</staff></root>"))

        assert [child[TAG_KEY] for child in node[CHILDREN_KEY]] == ["info", "info", "staff"]
        assert len(node[CHILDREN_BY_TAG_KEY]["info"]) == 2
        assert len(node[CHILDREN_BY_TAG_KEY]["staff"]) == 1

    def test_mixed_content_preserves_text_and_tail(self):
        from animedex.render.xml import CHILDREN_KEY, TAIL_KEY, TEXT_KEY, element_to_dict

        node = element_to_dict(ElementTree.fromstring("<root>lead<b>bold</b>tail<i>italic</i></root>"))

        assert node[TEXT_KEY] == "lead"
        assert node[CHILDREN_KEY][0][TEXT_KEY] == "bold"
        assert node[CHILDREN_KEY][0][TAIL_KEY] == "tail"
        assert node[CHILDREN_KEY][1][TEXT_KEY] == "italic"

    def test_whitespace_text_and_tail_are_preserved(self):
        from animedex.render.xml import CHILDREN_KEY, TAIL_KEY, TEXT_KEY, element_to_dict

        node = element_to_dict(ElementTree.fromstring("<root> <empty />\n</root>"))

        assert node[TEXT_KEY] == " "
        assert node[CHILDREN_KEY][0][TAIL_KEY] == "\n"


class TestXmlTextToDict:
    def test_accepts_bytes(self):
        from animedex.render.xml import TAG_KEY, xml_text_to_dict

        assert xml_text_to_dict(b"<ann><warning>x</warning></ann>")[TAG_KEY] == "ann"

    def test_wraps_parse_errors_as_api_error(self):
        from animedex.models.common import ApiError
        from animedex.render.xml import xml_text_to_dict

        with pytest.raises(ApiError) as ei:
            xml_text_to_dict("<ann>")

        assert ei.value.reason == "upstream-decode"

    def test_ann_warning_shape(self):
        from animedex.render.xml import children_by_tag, node_text, xml_text_to_dict

        root = xml_text_to_dict("<ann><warning>no result for anime=30</warning></ann>")

        warnings = children_by_tag(root, "warning")
        assert [node_text(w) for w in warnings] == ["no result for anime=30"]


class TestSelftest:
    def test_selftest_runs(self):
        from animedex.render import xml

        assert xml.selftest() is True
