"""Lossless XML payload adapter.

The adapter converts :class:`xml.etree.ElementTree.Element` trees into
plain dictionaries without making backend-specific decisions. It is
used by XML-speaking backends such as ANN, while semantic handling
stays in the backend rich-model layer.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union
from xml.etree import ElementTree

from animedex.models.common import ApiError


XmlInput = Union[str, bytes]

TAG_KEY = "_tag"
ATTRS_KEY = "_attrs"
TEXT_KEY = "_text"
TAIL_KEY = "_tail"
CHILDREN_KEY = "_children"
CHILDREN_BY_TAG_KEY = "_children_by_tag"


def element_to_dict(element: ElementTree.Element) -> Dict[str, Any]:
    """Convert an ElementTree element into a lossless dictionary.

    The returned shape preserves element name, attributes, direct
    text, tail text, ordered children, and grouped children by tag.
    The ordered child list is authoritative; the grouped map is a
    convenience index that always stores lists, even for tags that
    appear once.

    :param element: Parsed XML element.
    :type element: xml.etree.ElementTree.Element
    :return: Lossless dictionary representation of ``element``.
    :rtype: dict
    """
    children = [element_to_dict(child) for child in list(element)]
    grouped: Dict[str, list] = {}
    for child in children:
        grouped.setdefault(child[TAG_KEY], []).append(child)

    out: Dict[str, Any] = {
        TAG_KEY: element.tag,
        ATTRS_KEY: dict(element.attrib),
        CHILDREN_KEY: children,
        CHILDREN_BY_TAG_KEY: grouped,
    }
    if element.text is not None:
        out[TEXT_KEY] = element.text
    if element.tail is not None:
        out[TAIL_KEY] = element.tail
    return out


def xml_text_to_dict(xml: XmlInput) -> Dict[str, Any]:
    """Parse an XML string or bytes payload and convert it to a dict.

    XML parse errors are wrapped as :class:`ApiError` with
    ``reason="upstream-decode"`` so backend callers can surface a
    stable error vocabulary.

    :param xml: XML text or bytes.
    :type xml: str or bytes
    :return: Lossless dictionary representation of the root element.
    :rtype: dict
    :raises ApiError: When ``xml`` is not well-formed XML.
    """
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ApiError(f"XML parse failed: {exc}", reason="upstream-decode") from exc
    return element_to_dict(root)


def children_by_tag(node: Dict[str, Any], tag: str) -> list:
    """Return grouped child nodes for ``tag`` from an adapted node.

    :param node: Node produced by :func:`element_to_dict`.
    :type node: dict
    :param tag: Child element name.
    :type tag: str
    :return: Child nodes with matching tag, in original order.
    :rtype: list
    """
    grouped = node.get(CHILDREN_BY_TAG_KEY) or {}
    return list(grouped.get(tag) or [])


def node_text(node: Dict[str, Any]) -> Optional[str]:
    """Return the node's direct text content when present.

    :param node: Node produced by :func:`element_to_dict`.
    :type node: dict
    :return: Direct text content, or ``None``.
    :rtype: str or None
    """
    text = node.get(TEXT_KEY)
    return text if isinstance(text, str) else None


def selftest() -> bool:
    """Smoke-test the XML adapter.

    Parses a representative mixed-content document and verifies tag,
    attribute, text, child-order, and repeated-child preservation.

    :return: ``True`` on success.
    :rtype: bool
    """
    root = xml_text_to_dict('<root a="1">lead<x>one</x><x b="2" />tail<warning>none</warning></root>')
    assert root[TAG_KEY] == "root"
    assert root[ATTRS_KEY] == {"a": "1"}
    assert root[TEXT_KEY] == "lead"
    assert [child[TAG_KEY] for child in root[CHILDREN_KEY]] == ["x", "x", "warning"]
    assert len(children_by_tag(root, "x")) == 2
    assert node_text(children_by_tag(root, "warning")[0]) == "none"
    return True
