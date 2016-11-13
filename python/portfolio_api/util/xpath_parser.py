#!/usr/bin/python
# -*- coding: utf-8 -*-

import re

def html_escape(text):
    """Produce entities within text."""
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;"
    }

    return "".join(html_escape_table.get(c, c) for c in text)

def parse_htmlpage(html_src, is_broken=False):
    try:
        from lxml import html
        from lxml import etree

        if is_broken:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_src, 'html5lib')
            page_source = soup.prettify()

        detail_html = html.fromstring(html_src)
        page_tree = etree.ElementTree(detail_html)

        return page_tree
    except:
        return False

def get_elements_by_xpath(page_tree, target_xpath):
    try:
        if page_tree is not None and target_xpath is not None:
            target_value_list = page_tree.xpath(target_xpath)
            if target_value_list:
                return target_value_list
            else:
                return None
        else:
            return None
    except:
        return False

def get_value_by_xpath(page_tree, target_xpath, rex=None, use_escape=False):
    try:
        if page_tree is not None and target_xpath is not None:
            target_value_tmp = page_tree.xpath(target_xpath)
            if target_value_tmp:
                target_value = target_value_tmp[0]
                if rex:
                    target_value_tmp = re.search(rex, target_value)
                    if target_value_tmp:
                        target_value = target_value_tmp.group(1)
                    else:
                        return None
                if use_escape:
                    target_value = html_escape(target_value.strip())
                else:
                    target_value = target_value.strip()
                return target_value
            else:
                return None
        else:
            return None
    except:
        return False
