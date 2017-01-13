# This snippet of code comes from http://streamhacker.com/2010/06/16/
# text-classification-sentiment-analysis-eliminate-low-information-features/

import collections, itertools
import nltk.classify.util, nltk.metrics
from nltk.classify import NaiveBayesClassifier
from nltk.corpus import movie_reviews, stopwords
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures
from nltk.probability import FreqDist, ConditionalFreqDist


def evaluate_classifier(featx):
    negids = movie_reviews.fileids('neg')
    posids = movie_reviews.fileids('pos')
    # file level / review level feature builds, feature selection or mechanism
    # can differ, and is the main point
    negfeats = [(featx(movie_reviews.words(fileids=[f])), 'neg') for f in negids]
    posfeats = [(featx(movie_reviews.words(fileids=[f])), 'pos') for f in posids]
    # train/test split, split rate differs
    negcutoff = len(negfeats)*3/4
    poscutoff = len(posfeats)*3/4

    trainfeats = negfeats[:negcutoff] + posfeats[:poscutoff]
    testfeats = negfeats[negcutoff:] + posfeats[poscutoff:]
    # training algorithm, here is bayesian, but can use maximum entropy, svm,
    # or other algorithms
    classifier = NaiveBayesClassifier.train(trainfeats)
    refsets = collections.defaultdict(set)
    testsets = collections.defaultdict(set)
    # precision-recall analysis
    for i, (feats, label) in enumerate(testfeats):
            refsets[label].add(i)
            observed = classifier.classify(feats)
            testsets[observed].add(i)

    print('accuracy:', nltk.classify.util.accuracy(classifier, testfeats))
    print('pos precision:', nltk.metrics.precision(refsets['pos'], testsets['pos']))
    print('pos recall:', nltk.metrics.recall(refsets['pos'], testsets['pos']))
    print('neg precision:', nltk.metrics.precision(refsets['neg'], testsets['neg']))
    print('neg recall:', nltk.metrics.recall(refsets['neg'], testsets['neg']))
    classifier.show_most_informative_features()


# use each word as a feature, and is the simplest method
def word_feats(words):
    # return {word: True for word in words}
    return dict([(word, True) for word in words])

print('evaluating single word features')
evaluate_classifier(word_feats)

# The next part is totally a new story. It aims to select the most informative
# words manually and only use them as the features.

# These lines of codes are not good. Here is my implementation:
# pos_words = [(word, 'pos') for word in movie_reviews.words(categories='pos')]
# neg_words = [(word, 'neg') for word in movie_reviews.words(categories='neg')]
# total_words = pos_words + neg_words
# word_fd = nltk.FreqDist(word for word, label in total_words)
# label_word_fd = nltk.ConditionalFreqDist((label, word) for word, label in total_words)
word_fd = FreqDist()
label_word_fd = ConditionalFreqDist()

for word in movie_reviews.words(categories=['pos']):
    word_fd.inc(word.lower())
    label_word_fd['pos'].inc(word.lower())

for word in movie_reviews.words(categories=['neg']):
    word_fd.inc(word.lower())
    label_word_fd['neg'].inc(word.lower())

# These lines are just an explanation for BigramAssocMeasures.chi_sq function
# It is well worth reading and see what each of them represents
# n_ii = label_word_fd[label][word]
# n_ix = word_fd[word]
# n_xi = label_word_fd[label].N()
# n_xx = label_word_fd.N()

pos_word_count = label_word_fd['pos'].N()
neg_word_count = label_word_fd['neg'].N()
total_word_count = pos_word_count + neg_word_count

word_scores = {}

for word, freq in word_fd.iteritems():
    pos_score = BigramAssocMeasures.chi_sq(label_word_fd['pos'][word],
        (freq, pos_word_count), total_word_count)
    neg_score = BigramAssocMeasures.chi_sq(label_word_fd['neg'][word],
        (freq, neg_word_count), total_word_count)
    word_scores[word] = pos_score + neg_score

# Now we can use the score criterion to get the most informative words
best = sorted(word_scores.items(), key=lambda w, s: s, reverse=True)[:10000]
bestwords = set([w for w, s in best])


def best_word_feats(words):
    return dict([(word, True) for word in words if word in bestwords])

print('evaluating best word features')
evaluate_classifier(best_word_feats)


# The subsequent function can be a guideline of how to use bigrams/trigrams
def best_bigram_word_feats(words, score_fn=BigramAssocMeasures.chi_sq, n=200):
    bigram_finder = BigramCollocationFinder.from_words(words)
    bigrams = bigram_finder.nbest(score_fn, n)
    d = dict([(bigram, True) for bigram in bigrams])
    d.update(best_word_feats(words))
    return d

print('evaluating best words + bigram chi_sq word features')
evaluate_classifier(best_bigram_word_feats)

# Indeed, there are some ways that can improve the accuracy:
# 1, Adding different feature selection mechanisms
# 2, Pre-processing the text to get rid of unimportant words (stopwords) or punctuation
# 3, Doing deeper analysis of the sentences as a whole
# 4, Trying a different classifier than the Naive Bayes Classifier (I have specified)

# Procedures:
# Preprocess text (build data) --> filter words needed (filter out stopwords, punctuation) -->
# build features (mechanisms) --> select classification algorithms

with open('/Users/Elliott/Desktop/test/department.txt', 'w+') as f:
    for file in os.listdir('data/files'):
        if re.search(r'^(?!\.).*(?:\.pdf)$', file):
            try:
                f.write('\n')
                f.write(file)
                f.write('\n')
                f.write(LetterParser('data/files', file).department)
                f.write('\n')
                f.write('\n')
            except:
                pass

