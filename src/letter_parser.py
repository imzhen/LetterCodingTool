from lxml import etree
import codecs
import os
import re
from functools import reduce
from itertools import chain
import nltk
import subprocess
from unidecode import unidecode
import pandas as pd


class LetterParser:

    def __init__(self, filepath, filename):
        """
        This function initializes the file structure, based on the given filename, filepath and
        header list.

        The procedure is:
        file_preprocess: PDF file --> XML parsed Texts
        refine_extractor: XML parsed Texts --> Refined Texts, with only contents that are useful
        remove_special_character: Texts --> Texts, with removed special ones and prepare for paragraph process
        parse_paragraph: Texts --> Texts, with paragraph structure added
        get_contents: Texts --> texts contents
        get_department: Texts --> Department metadata

        :param filepath:
        :param filename:
        """
        self.filepath = filepath
        self.filename = filename
        self.texts, self.ocr_flag, self.file_raw = self.file_preprocess()
        if self.ocr_flag:
            self.header_list, self.contents = self.ocr_parser()
        else:
            self.texts = self.text_preprocess()
            self.refined_id, self.texts_refined = self.refine_extractor()
            self.special_identifier = self.remove_special_character()
            self.texts_with_paragraph = self.parse_paragraph()
            self.header_list, self.contents = self.get_contents()
        self.department = self.get_metadata_wrapper(self.get_department)
        self.university = self.get_metadata_wrapper(self.get_university)
        self.file_postprocess()

    def file_preprocess(self):
        """
        Preprocess the file into xml, remove <b> and <i> tag and invalid tokens with Exception Checking

        :return: Texts Object
        """
        file_pdf = os.path.join(self.filepath, self.filename)
        file_raw = re.sub(r'(.*)(?:\.pdf)$', r'\1', file_pdf)
        file_xml = re.sub(r'(.*)(?:\.pdf)$', r'\1.xml', file_pdf)
        subprocess.call('src/xml_pre_process.sh %s' % file_raw, shell=True)
        parser = etree.XMLParser(ns_clean=True, recover=True)

        try:
            tree = etree.parse(codecs.open(file_xml, encoding='utf-8'), parser=parser)
        except:
            tree = etree.parse(codecs.open(file_xml, encoding='ISO-8859-1'), parser=parser)

        etree.strip_tags(tree, *['b', 'i', 'a'])
        root = tree.getroot()
        texts = root.findall(".//text")
        if len(texts) == 0:
            ocr_flag = True
        else:
            ocr_flag = False
        return texts, ocr_flag, file_raw

    def file_postprocess(self):
        subprocess.call('src/xml_post_process.sh %s' % self.file_raw, shell=True)

    def text_preprocess(self):
        texts = [text for text in self.texts if text.text]
        pre_pos = 0
        for pos, text in enumerate(texts[1:]):
            pos += 1
            top_diff = int(texts[pos].get('top')) - int(texts[pre_pos].get('top'))
            texts[pos].text = re.sub(r'^\s*', '', texts[pos].text)
            if re.sub(r'^\s+$', '', text.text) != '':
                if -15 < int(texts[pos].get('top')) - int(texts[pre_pos].get('top')) < 15:
                    if abs(int(texts[pre_pos].get('left')) - int(text.get('left'))) < 110:
                        if len(texts[pre_pos].text) == 1 or texts[pos-1].get('width') == '0':
                            texts[pre_pos].text += text.text
                        else:
                            texts[pre_pos].text += ' ' + text.text
                        if len(text.text) == 1:
                            text.set('width', '0')
                        texts[pos].text = ''
                        texts[pre_pos].set('width', str(int(text.get('width')) + int(texts[pre_pos].get('width'))))
                    else:
                        pre_pos = pos
                elif top_diff <= -15:
                    texts[pre_pos - 1].text += ' ' + texts[pre_pos].text
                    texts[pre_pos].text = ''
                    pre_pos = pos
                else:
                    pre_pos = pos
        for text in texts:
            text.text = re.sub(r'\s{2,}', r' ', text.text)
            text.text = unidecode(text.text)
        return texts

    def refine_extractor(self):
        """
        Use refine methods to extract the text from Texts. They are used one by one, and have no priority
        upon the others.

        Each refine method will return a list indicating which position in the Texts it thinks are reasonable
        to get the text. So the intersections between all of them is what we are looking for. But when they
        are not overlapped, only trust the width_refine method. It is the most robust one.

        At last, only return the texts that are not empty.

        :return: Refined Texts
        """
        refine_methods = [self.font_refine, self.height_refine, self.width_refine]
        refined_id_list = [f(self.texts) for f in refine_methods]
        refined_id = reduce(lambda x, y: list(set(x).intersection(y)), refined_id_list)
        if not refined_id:
            refined_id = self.width_refine(self.texts)
        texts_refined = [val for pos, val in enumerate(self.texts) if val.text and
                         pos in refined_id and re.sub(r' ', '', val.text) != '']
        return refined_id, texts_refined

    def remove_special_character(self):
        """
        It first removes special character "\t\n \xa0". This character is important since it will influence
        paragraph parsing, so if it is indeed found, it will be handled differently when doing paragraph
        parsing.

        Attention: On the Unix server it may behave differently. I will come back when I configured and run
         my script on Unix.

        :return: Remove special character and return whether it has this special one.
        """
        special_identifier = False
        for text in self.texts_refined:
            if re.search(r'\t\n \xa0', text.text):
                text.text = re.sub(r'\t\n \xa0', ' ', text.text)
                special_identifier = True
        return special_identifier

    def parse_paragraph(self):
        """
        If it has the special identifier, top para parser is enough.

        It is does not, I will first use top para parser. But if no paragraph structure is found, the
        left para parser is used.

        :return: Paragraph parsed Texts
        """
        if not self.special_identifier:
            insert_counter, texts = self.top_paragraph_parser(self.texts_refined)
            if insert_counter == 0:
                texts = self.left_paragraph_parser(texts)
        else:
            _, texts = self.top_paragraph_parser(self.texts_refined)
            for pos, val in enumerate(texts):
                if val.text == ' ':
                    texts[pos - 1].text += '\n\n'
        return texts

    def get_contents(self):
        """
        Get the final texts.

        :return: letter texts.
        """
        contents = reduce(lambda x, y: x + y, [val.text for val in self.texts_with_paragraph])
        header_list = [val.text for pos, val in enumerate(self.texts) if pos not in self.refined_id]
        # if not contents:
        #     raise ValueError('No result, please check refine methods for file %s\n' % self.filename)
        return header_list, contents

    def get_metadata_wrapper(self, func):
        first_level = func(self.header_list)
        if first_level:
            return first_level.title()

        if not self.ocr_flag:
            self.ocr_flag = True
            header_list, _ = self.ocr_parser()
            second_level = func(header_list)
            if second_level:
                return second_level.title()

        return "None Found"

    @staticmethod
    def get_department(header_list):
        header_list = list(chain.from_iterable(re.split(r'[.,:]', val) for val in header_list))
        header_list.reverse()
        departments = [re.sub(r'\W+', ' ', val) for val in header_list
                       if val if re.findall(r'department[s]?\W+of', val, re.IGNORECASE)]
        if departments:
            return re.findall(r'department[a-zA-Z& ]+', departments[0], re.IGNORECASE)[0].strip()

        other_strings = ['department\s*', 'Dept\.', 'center']
        for string in other_strings:
            string_text = [val for val in header_list
                           if val if re.findall(r'%s' % string, val, re.IGNORECASE)]
            if string_text:
                return re.findall(r'[a-zA-Z& ]*%s[a-zA-Z& ]*' % string, string_text[0], re.IGNORECASE)[0].strip()

        professor = [re.sub(r'\W+', ' ', val) for val in header_list
                     if val if re.findall(r'(?:Professor|Prof\.)\s{,2}of', val, re.IGNORECASE)]
        if professor:
            return re.sub(r'(?:Professor|Prof)\s{,2}of([a-zA-Z& ]+)', r'Department of\1',
                          professor[0], flags=re.I).strip()

        other_strings = ['lab', 'institu', 'school', 'college']
        for string in other_strings:
            string_text = [val for val in header_list
                           if val if re.findall(r'%s' % string, val, re.IGNORECASE)]
            if string_text:
                return re.findall(r'[a-zA-Z& ]*%s[a-zA-Z& ]*' % string, string_text[0], re.IGNORECASE)[0].strip()

        return None

    @staticmethod
    def get_university(header_list):
        header_list = list(chain.from_iterable(re.split(r'[.:]', val) for val in header_list))
        header_list.reverse()
        universities = [re.sub(r'\W+', ' ', val) for val in header_list
                        if val if re.findall(r'university\W+of', val, re.IGNORECASE)]
        if universities:
            return re.findall(r'university[a-zA-Z& ]+', universities[0], re.IGNORECASE)[0].strip()

        other_strings = ['universi\s*', 'College', 'center', 'Univ\.', 'institut']
        for string in other_strings:
            string_text = [val for val in header_list
                           if val if re.findall(r'%s' % string, val, re.IGNORECASE)]
            if string_text:
                return re.findall(r'[a-zA-Z& ]*%s[a-zA-Z& ]*' % string, string_text[0], re.IGNORECASE)[0].strip()

        return None

    def font_refine(self, texts):
        """
        Here I think only the texts with the most emerged font is reasonable, so only keep it. But doing
        one unclear match means it allows for one line to stay away and back, but not two lines. It will
        preserve the structure of paragraphs at the most benefit, since these type of lines are always
        paragraph separated lines.

        :param texts: Texts object
        :return: Id list refined
        """
        font_freq = nltk.FreqDist(text.get('font') for text in texts)
        font_target = font_freq.most_common(1)[0][0]
        font_refined_list = [pos for pos, text in enumerate(texts) if text.get('font') == font_target]
        return self.one_unclear_match(font_refined_list)

    def height_refine(self, texts):
        """
        The same logic as for font_refine.

        :param texts: Texts object
        :return: Id list refined
        """
        height_freq = nltk.FreqDist(text.get('height') for text in texts)
        height_target = height_freq.most_common(1)[0][0]
        height_refined_list = [pos for pos, text in enumerate(texts) if text.get('height') == height_target]
        return self.one_unclear_match(height_refined_list)

    def width_refine(self, texts, width_threshold=480):
        """
        To extract the width attribute, it is different from what is done with font and height. To
        extract blocks, it will first set flag to true, and when it sees a true, it will become false,
        and record the value, and when it sees a false, it will become true, and record the value...

        The result list is just spanned list. Spanned list is a definition I defined: it will form a long
        list by two numbers a group to specify the begin and the end for a sub-list.

        :param texts: Texts object
        :param width_threshold: Width to be confident to be a normal line for a paragraph. Maybe platform dependent.
        :return: Spanned list
        """
        width_flag_list = [int(text.get('width')) > width_threshold for text in texts]
        width_refined_list = []
        add_flag = True
        for pos, width_flag in enumerate(width_flag_list):
            if width_flag == add_flag:
                width_refined_list.append(pos)
                add_flag = not add_flag
        return self.two_bigrams_span(width_refined_list)

    def one_unclear_match(self, refined_id, threshold=2):
        """
        It is the main function doing unclear matching. Typically we match exactly, but given a list,
        it is allowed only one is missing. So for example, [1, 2, 4, 5] will be filled with [1, 2, 3, 4, 5],
        but [1, 2, 5, 6] will not be filled. It will work with two_bigrams_span to return the final
        list.

        This function is intended to be written generally, so can be two unclear match, three... But
        I only use one here.

        :param refined_id: Ids that match a specific criterion
        :param threshold: Missing filled threshold
        :return: Spanned list
        """
        refined_id_diff = [x[0] - x[1] for x in zip(refined_id[1:], refined_id[:-1])]
        refined_span_id = [(pos, pos + 1) for pos, val in enumerate(refined_id_diff) if val > threshold]
        span_id_cross = [(refined_id[a], refined_id[b]) for (a, b) in refined_span_id]
        if len(span_id_cross) != 0:
            span_id_all = (refined_id[0], ) + reduce(lambda x, y: x + y, span_id_cross) + (refined_id[-1], )
        else:
            span_id_all = (refined_id[0], refined_id[-1])
        return self.two_bigrams_span(span_id_all)

    @staticmethod
    def two_bigrams_span(span_id_all):
        """
        Given a list like [1, 3, 7, 19], it will return [1:3, 7:19]. In other words, two numbers
        to form a continuous group.

        :param span_id_all: Spanned ids
        :return: Refined list
        """
        span_id = [val for pos, val in enumerate(nltk.bigrams(span_id_all)) if pos % 2 == 0]
        span_list = reduce(lambda x, y: x + y, [list(range(a, b + 1)) for a, b in span_id])
        return span_list

    @staticmethod
    def top_paragraph_parser(texts):
        """
        For most texts in the pdf, they should have consistent line distance. So Significant larger distance
        should form a paragraph structure. It will look at the distance for each line (First line is treated
        specially) and see the distances, insert the line break, count the number of breaks inserted.

        :param texts: Texts object
        :return: number of breaks inserted, Texts object
        """
        top_list = [int(val.get('top')) for val in texts]
        top_diff = [x[0] - x[1] for x in zip(top_list[1:], top_list[:-1])]
        top_most = nltk.FreqDist(x for x in chain(top_diff, [x-1 for x in top_diff],
                                                  [x+1 for x in top_diff])).most_common()[0][0]
        insert_counter = 0
        for pos, diff in enumerate(top_diff):
            if top_most + 2 < diff:
                if pos == 0:
                    texts[0].text += '\n\n'
                    insert_counter += 1
                elif top_diff[pos] > top_most + 8 and re.search(r'(?:\.\s*)', texts[pos].text):
                    texts[pos].text += '\n\n'
                    insert_counter += 1
        return insert_counter, texts

    @staticmethod
    def left_paragraph_parser(texts):
        """
        If the number of breaks inserted is too small, it will look at the left attribute (indention).
        This is not the most robust one compared to top attribute, but it will fix some issues that
        encountered in top para parser.

        :param texts: Texts object
        :return: Texts object
        """
        left_freq = nltk.FreqDist(int(val.get('left')) for val in texts)
        if len(left_freq) > 1:
            left_identifier = left_freq.most_common(2)[-1][0]
            for pos, val in enumerate(texts):
                if int(val.get('left')) == left_identifier:
                    if pos != 0:
                        texts[pos-1].text += '\n\n'
        return texts

    @staticmethod
    def content_parser(contents):
        words = nltk.word_tokenize(contents)
        sents = nltk.sent_tokenize(contents)
        paras = re.split(r'\n', contents)
        return words, sents, paras

    def ocr_parser(self):
        string_list = self.ocr_process()
        header_list = list(chain.from_iterable(re.split('\n\n|\n', val) for val in string_list
                                               if len(val) < 500))
        contents_list = re.split('\n\n', ''.join(re.sub(r'\n\n \n\n$', r'\n\n', val)
                                                 for val in string_list if len(val) >= 500))
        contents = ''
        for val in contents_list:
            val_list = re.split(r'\n', val)
            val_list_width_avg = sum(len(va) for va in val_list) / len(val_list)
            if val_list_width_avg > 75:
                contents += val
                if re.findall(r'[.?:!]$', val):
                    contents += '\n\n'
                else:
                    contents += '\n'
            else:
                header_list += val_list
        return header_list, contents

    def ocr_process(self):
        file_base = os.path.basename(self.file_raw)
        pic_output = subprocess.check_output('find %s -name "%s*.png" -o -name "%s*.jpg"'
                                             % (self.filepath, file_base, file_base), shell=True)
        pic_list = re.split(r'\n', pic_output.decode())
        string_list = [subprocess.check_output('tesseract %s stdout 2> /dev/null' % pic, shell=True).decode()
                       for pic in pic_list if pic]
        return string_list

    def get_dataframe(self):
        df = pd.DataFrame.from_dict({
            "contents": [self.contents],
            "department": [self.department],
            "filename": [self.filename],
            "university": [self.university]
        })
        return df
