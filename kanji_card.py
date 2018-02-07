#/usr/bin/env python2
# -*- coding: utf-8 -*-

#from aqt import mw
#from aqt.utils import showInfo
#from aqt.qt import *

import re
import anki.stdmodels
import aqt

class AnnotatedTextBlock(object):
    def __init__(self, text, annotation):
        self.text = text
        self.annotation = annotation

    def html(self):
        return u"<ruby>{0}<rt>{1}</ruby>".format(self.text, self.annotation)


class PlainTextBlock(object):
    def __init__(self, text):
        self.text = text

    def html(self):
        return self.text


class Text(object):
    def __init__(self):
        self.blocks = []

    def add_plain_text(self, text):
        self.blocks.append(PlainTextBlock(text))

    def add_annotated_text(self, text, annotation):
        self.blocks.append(AnnotatedTextBlock(text, annotation))

    def html(self):
        block_strings = []
        for block in self.blocks:
            block_strings.append(block.html())
        return u"".join(block_strings)


class ReadingExample(object):
    def __init__(self, word, translation):
        self.word = word
        self.translation = translation

    def html(self):
        return self.word.html() + u"&emsp;" + self.translation.html()


class ReadingWithExamples(object):
    def __init__(self, reading):
        self.reading = reading
        self.examples = []

    def add_example(self, word, translation):
        self.examples.append(ReadingExample(word, translation))

    def html(self):
        if not self.examples:
            self.examples.append(ReadingExample(u"", u""))

        strings = []
        def write_table_row(first, second):
            strings.append(u"  <tr>")
            strings.append(u"    <td>{}</td>".format(first))
            strings.append(u"    <td>{}</td>".format(second))
            strings.append(u"  </tr>")

        write_table_row(self.reading, self.examples[0].html())

        for example in self.examples[1:]:
            write_table_row(u"", example.html())

        return u"\n".join(strings)


def parse_text(source):
    text = Text()

    while True:
        first_annotation_index = source.find(u"[")
        if first_annotation_index == -1:
            text.add_plain_text(source)
            break

        if first_annotation_index > 0:
            text.add_plain_text(source[:first_annotation_index])
            source = source[first_annotation_index:]
            continue

        separator_index = source.find(u"|")
        end_index = source.find(u"]")
        if not (separator_index > 0 and end_index > separator_index):
            raise RuntimeError(
                "bad annotation: {}".format(source.encode("utf-8")))

        plain_text = source[1:separator_index]
        annotation = source[separator_index+1:end_index]
        text.add_annotated_text(plain_text, annotation)
        source = source[end_index+1:]

    return text


class ReadingsBuilder(object):
    def __init__(self):
        self.readings = []
        self.current_reading = None

    def set_reading(self, reading):
        if self.current_reading:
            self.readings.append(self.current_reading)
        self.current_reading = ReadingWithExamples(reading)

    def add_example(self, word, translation):
        if self.current_reading is None:
            raise RuntimeError(
                "ReadingsBuilder: add_example called before set_reading")

        word_text = parse_text(word)
        translation_text = parse_text(translation)
        self.current_reading.add_example(word_text, translation_text)

    def html(self):
        if self.current_reading is not None:
            self.readings.append(self.current_reading)

        strings = []
        strings.append(u"<table>")
        for reading in self.readings:
            strings.append(reading.html())
        strings.append(u"</table>")
        return u"\n".join(strings)


def replace_html(string):
    open_tag_re = ur"<[^>]*>"
    close_tag_re = ur"</[^>]*>"

    string = re.sub(open_tag_re, u"\n", string)
    string = re.sub(close_tag_re, u"", string)
    return string


def convert(source):
    lines = source.splitlines()

    builder = ReadingsBuilder()
    for line in lines:
        line = line.rstrip()

        # Skip empty lines
        match = re.match(ur"^\s*$", line)
        if match:
            continue

        match = re.match(ur"^\s*(.*\S+)\s*:\s*$", line)
        if match:
            builder.set_reading(match.group(1))
            continue

        match = re.match(ur"^\s*\*\s*(.*\S+)\s*-\s*(.*\S+)\s*$", line)
        if match:
            word, translation = match.group(1), match.group(2)
            builder.add_example(word, translation)
            continue

        raise RuntimeError("unexpected line: {}".format(line.encode("utf-8")))

    return builder.html()


def add_kanji_card_model(col):
    models = col.models
    kanji_card_model = models.new(u"Kanji Card")

    models.addField(kanji_card_model, models.newField(u"Kanji"))
    models.addField(kanji_card_model, models.newField(u"Meaning"))
    models.addField(kanji_card_model, models.newField(u"Readings"))
    models.addField(kanji_card_model, models.newField(u"ProcessedReadings"))

    kanji_card_model["css"] += u"""\
.jp { font-size: 30px }
.win .jp { font-family: "MS Mincho", "ＭＳ 明朝"; }
.mac .jp { font-family: "Hiragino Mincho Pro", "ヒラギノ明朝 Pro"; }
.linux .jp { font-family: "Kochi Mincho", "東風明朝"; }
.mobile .jp { font-family: "Hiragino Mincho ProN"; }"""

    template = models.newTemplate(u"Recognition")
    template["qfmt"] = u"""\
<div class=jp> {{Kanji}} </div>"""
    template["afmt"] = u"""\
{{FrontSide}}

<hr id=answer>

<div>
    {{ProcessedReadings}}
</div>"""
    models.addTemplate(kanji_card_model, template)

    models.add(kanji_card_model)

    return kanji_card_model


def focus_lost_hook(flag, note, field_index):
    source_field = u"Readings"
    target_field = u"ProcessedReadings"

    # Check necessary fields are present
    fields = aqt.mw.col.models.fieldNames(note.model())
    if source_field not in fields or target_field not in fields:
        return flag

    # Check that source field lost focus
    if fields[field_index] != source_field:
        return flag

    source_text = note[source_field]
    raw_text = replace_html(source_text)
    target_text = convert(raw_text)

    note[target_field] = target_text
    return True    


anki.stdmodels.models.append(("Kanji Card", add_kanji_card_model))
anki.hooks.addHook("editFocusLost", focus_lost_hook)
