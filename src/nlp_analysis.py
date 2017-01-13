import nltk
import pandas as pd
from collections import defaultdict


class Analysis:
    def __init__(self, texts):
        self.texts = texts
        self.texts_tokenized = nltk.word_tokenize(self.texts)
        self.texts_tagged = self.tag()

    def tag(self, subset=None):
        codebook = pd.read_csv("resources/codebook/letter_codebook.csv")
        tag_to_word = defaultdict(lambda: [])
        for pos, row in codebook.iterrows():
            tag_to_word[row.Tag].append(row.Word)
        word_to_tag = defaultdict(lambda: [])

        if not subset:
            for key, val in tag_to_word.items():
                for va in val:
                    word_to_tag[va].append(key)
        else:
            for key, val in tag_to_word.items():
                if key not in subset:
                    continue
                for va in val:
                    word_to_tag[va].append(key)

        def tagging(word):
            result = []
            for t_key, t_val in word_to_tag.items():
                if t_key.endswith("*"):
                    if word.startswith(t_key[:-1]):
                        result += t_val
                else:
                    if word == t_key:
                        result += t_val
            return result

        texts_tagged = [(word, tagging(word)) for word in self.texts_tokenized]
        return texts_tagged


if __name__ == "__main__":
    texts = "Recently, Cora has made other important findings on how fear learning and extinction affect synaptic " \
            "structural remodeling in the auditory cortex. She has also developed a technique to perform in vivo " \
            "calcium imaging of individual synapses and dendrites in awake animals in response to fear " \
            "conditioning-related stimuli. In addition to her own projects, Cora has been involved in three " \
            "collaborative projects in the lab. In all the projects that she was involved, Cora showed a very strong " \
            "dedication to the work and her contributions to the projects were extremely invaluable. I expect Cora " \
            "to be the first author on two other papers and co-authors in three more papers when these studies are " \
            "published in the near future. The incredible productivity over the last few years speaks for Cora's " \
            "strong drive and work ethics. She is one of the most efficient and productive postdoctoral fellows in " \
            "my lab in the past 13 years."
    print(Analysis(texts).texts_tagged)
