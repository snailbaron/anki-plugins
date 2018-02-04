#/usr/bin/env python2
# -*- coding: utf-8 -*-

#from aqt import mw
#from aqt.utils import showInfo
#from aqt.qt import *

import re

class AnnotatedTextBlock(object):
    def __init__(self, text, annotation):
        self.text = text
        self.annotation = annotation

    def html(self):
        return '<ruby>{0}<rt>{1}</ruby>'.format(self.text, self.annotation)


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
        return ''.join(block_strings)


class ReadingExample(object):
    def __init__(self, word, translation):
        self.word = word
        self.translation = translation

    def html(self):
        return self.word.html() + '&emsp;' + self.translation.html()


class ReadingWithExamples(object):
    def __init__(self, reading):
        self.reading = reading
        self.examples = []

    def add_example(self, word, translation):
        self.examples.append(ReadingExample(word, translation))

    def html(self):
        if not self.examples:
            self.examples.append(ReadingExample('', ''))

        strings = []
        def write_table_row(first, second):
            strings.append('  <tr>')
            strings.append('    <td>{}</td>'.format(first))
            strings.append('    <td>{}</td>'.format(second))
            strings.append('  </tr>')

        write_table_row(self.reading, self.examples[0].html())

        for example in self.examples[1:]:
            write_table_row('', example.html())

        return '\n'.join(strings)


def parse_text(source):
    text = Text()

    while True:
        first_annotation_index = source.find('[')
        if first_annotation_index == -1:
            text.add_plain_text(source)
            break

        if first_annotation_index > 0:
            text.add_plain_text(source[:first_annotation_index])
            source = source[first_annotation_index:]
            continue

        separator_index = source.find('|')
        end_index = source.find(']')
        if not (separator_index > 0 and end_index > separator_index):
            raise RuntimeError('bad annotation: {}'.format(source))

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
                'ReadingsBuilder: add_example called before set_reading')

        word_text = parse_text(word)
        translation_text = parse_text(translation)
        self.current_reading.add_example(word_text, translation_text)

    def html(self):
        if self.current_reading is not None:
            self.readings.append(self.current_reading)

        strings = []
        strings.append('<table>')
        for reading in self.readings:
            strings.append(reading.html())
        strings.append('</table>')
        return '\n'.join(strings)


def convert(source):
    lines = source.splitlines()

    builder = ReadingsBuilder()
    for line in lines:
        match = re.match(r'^\s*(.*\S+)\s*:\s*$', line)
        if match:
            builder.set_reading(match.group(1))
            continue

        match = re.match(r'^\s*\*\s*(.*\S+)\s*-\s*(.*\S+)\s*$', line)
        if match:
            word, translation = match.group(1), match.group(2)
            builder.add_example(word, translation)
            continue

        raise RuntimeError('unexpected line: {}'.format(line))

    return builder.html()




if __name__ == '__main__':
    input_unicode_string = u"""ジョ :
* [女|じょ][性|せい] - женщина
* [彼女|かのじょ] - она
おんな :
* [女|おんな] - женщина
* [女|おんな]の[子|こ] - девочка
"""
    input_raw_string = input_unicode_string.encode('utf-8')

    print(convert(input_raw_string))
