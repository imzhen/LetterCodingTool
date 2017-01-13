#!/usr/bin/env python
import os
import codecs
import sys
import re
import argparse
from datetime import datetime
import shutil
import logging
import json
import time

sys.path.insert(0, os.path.abspath(".."))
from LetterCodingTool.src.letter_parser import LetterParser
# Xinyan please comment the above line and use the line below
# from LetterCodingTool.src.letter_parser_no_ocr import LetterParser


class Manager:
    def __init__(self, config, dev, directory):
        self.config = config
        self.dev = self.config[dev]
        self.directory = directory
        self.header = "department,filename,name,university"

    def run(self):
        dirs = self.directory or self.dev['dir']
        identifier = '%s_%s' % (datetime.today().strftime('%Y%m%d%H%M%S'), os.path.split(dirs)[1])
        logging.basicConfig(format='%(levelname)s - %(name)s - %(message)s', filename='results/log/%s.log' % identifier,
                            level=logging.DEBUG)
        if self.dev['destination'] == 'file':
            sys.stdout = codecs.open("results/parsed/%s.csv" % identifier, 'w+', "utf-8")

        elif self.dev['destination'] == 'remote':
            sys.stdout = open("/home/research/ucrecruit/stem_letters/results/%s.csv" % identifier, 'w+')
            #sys.stdout = open("/Users/gsr/Documents/test/%s.csv" % identifier, 'w+')

        print(self.header)

        for root, _, files in os.walk(dirs):
            if files:
                for file in files:
                    if re.search(r'^(?!\.).*(?:\.pdf)$', file):
                        self.writer(root, file)

    # This is used by Xinyan
    # def writer(self, root, file):
    #     try:
    #         sTime = time.time()
    #         letter_csv = LetterParser(root, file).get_dataframe()
    #         logging.debug('File: %s, Finished in %s' % (file, time.time()-sTime))
    #         #letter_csv.to_csv(sys.stdout, header=False, index=False, mode='a')
    #         sys.stdout.write(letter_csv.to_csv(header=False, index=False))
    #     except Exception as e:
    #         logging.info('File: %s, Exception: %s' % (file, e))
    #         if not self.dev['fail_no_copy']:
    #             shutil.copyfile(os.path.join(root, file), os.path.join('data/fail', file))

    #  This is used by Zhen
    def writer(self, root, file):
        writer_kwargs = {"header": False, "index": False}
        try:
            sys.stdout.write(LetterParser(root, file).get_dataframe().to_csv(**writer_kwargs))
        except Exception as e:
            logging.error('%s, %s' % (file, e))
            if not self.dev['fail_no_copy']:
                shutil.copyfile(os.path.join(root, file), os.path.join('results/failed', file))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', action='store', dest='dev')
    parser.add_argument('--dir', action='store', dest='directory')
    parsed = parser.parse_args()

    with open('config.json', 'r') as f:
        config = json.load(f)

    manager = Manager(config, parsed.dev, parsed.directory)
    manager.run()
