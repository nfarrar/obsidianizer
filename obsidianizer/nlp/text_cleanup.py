"""Utilities to process and clean sentences. Especially coming from journal entries"""
import datetime as dt
import itertools
import re
import string
from collections import Counter
from typing import List, Optional, Union

import nltk
import pandas as pd
import spacy
from nltk import ngrams
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import word_tokenize


def _compute_stop_words() -> List[str]:
    """Computes the stopwords from nltk, gensim and spacy"""
    sp_en = spacy.load("en_core_web_md")
    spacy_stopwords_en = sp_en.Defaults.stop_words
    # nltk.download("stopwords")
    stopwords_nltk = stopwords.words("english")

    total_stopwords = list(set([*spacy_stopwords_en, *stopwords_nltk]))
    return total_stopwords


STOPWORDS = _compute_stop_words()


def remove_special_characters(sentence: str) -> str:
    return re.sub(r"[^\w\s]", "", sentence)


def tokenize_sentences(entry_text: str) -> List[str]:
    """Splits a string into its sentences. A sentence is independent when:
    - It starts with \\-
    - It is separated by "\n\n" due to how the drafts are saved into disk from gmail.
    - TODO: Maybe in the future differentiate between paragraph and sentence.
    """

    # Make sure that the bullet point get transformed as new sentences.
    entry_text = entry_text.replace("\\-", "\n\n\\-")
    sentences = entry_text.split("\n\n")

    sentences = [
        clean_sentence_email_draft(sent)
        for sent in sentences
        if is_raw_sentence_not_empty(sent)
    ]
    return sentences


def is_raw_sentence_not_empty(sent: str) -> bool:
    """Detect if the sentence is not empty"""
    return len(sent) > 0 and sent != "\n"


def clean_sentence_email_draft(sentence: str) -> str:
    """Cleans a sentence given the idiosyncracies of how the drafts are saved to disk"""
    sentence = sentence.replace("\n", " ")
    sentence = sentence.strip()
    return sentence


def word_count(sentences: List[str]) -> int:
    """Counts the number of words"""
    total_word_count = 0
    for paragraph in sentences:
        words = len(paragraph.split())
        total_word_count = words + total_word_count
    return total_word_count


def lematize_sentences(sentences: List[str]) -> List[List[str]]:
    """Returns all lemmas in the list of sentences provided"""
    lemmatizer = WordNetLemmatizer()
    all_lemmas = []
    for sentence in sentences:
        words = word_tokenize(sentence)
        lemmas = [lemmatizer.lemmatize(word) for word in words]
        all_lemmas.append(lemmas)

    return all_lemmas


def stem_sentences(sentences: List[str]) -> List[List[str]]:
    """Returns all stems in the list of sentences provided"""
    porter_stemmer = PorterStemmer()
    all_stems = []
    for sentence in sentences:
        words = word_tokenize(sentence)
        stems = [porter_stemmer.stem(word) for word in words]
        all_stems.append(stems)

    return all_stems


def n_grams_function(
    journal_df: pd.DataFrame, column: str = "", n: int = 2
) -> pd.DataFrame:
    """Returns the n_grams of the dataframe containing the jouranl entries"""
    grams_list = []
    for _, row in journal_df.iterrows():
        for sentence in row[column]:
            sentence = remove_special_characters(sentence)
            tokenized_sentence = nltk.word_tokenize(str.lower(sentence))
            grammed_sentence = ngrams(tokenized_sentence, n)
            for gram in grammed_sentence:
                grams_list.append(gram)

    n_gram_combined_list = []
    test = pd.DataFrame(grams_list)
    for i, row in test.iterrows():
        n_gram = ""
        for word_position in range(0, n):
            word = row.iloc[word_position]
            n_gram = n_gram + " " + word
        n_gram_combined_list.append(n_gram)

    n_grams_dataframe = pd.DataFrame(n_gram_combined_list, columns=[f"{n}_grams"])
    counted_ngrams = (
        n_grams_dataframe.reset_index()
        .groupby(f"{n}_grams")
        .count()
        .sort_values("index", ascending=False)
    )
    return counted_ngrams


def join_list_of_lists_of_strings(words_series: pd.Series) -> str:
    joined_tokens = words_series.apply(lambda x_list: [" ".join(x) for x in x_list])
    joined_sentences = joined_tokens.apply(lambda x: " ".join(x))

    all_joined_text = " ".join(joined_sentences)
    all_joined_text = all_joined_text.strip()
    return all_joined_text


def get_most_used_words(
    sentences_series: pd.Series, remove_stopwords: bool = True
) -> pd.Series:
    """It returns a list of the most used words in the column passed as argument.
    Each element of the argument is a sentence string"""

    def get_tokenized_words(sentence: Union[str, List[str]]):
        if isinstance(sentence, list):
            sentence = itertools.chain.from_iterable(sentence)
        return sentence

    # Join all sentences in the same string
    all_concatenated_sentences = " ".join(sentences_series.apply(get_tokenized_words))
    all_tokenized_words = remove_stop_words_en(all_concatenated_sentences)

    words_series = pd.Series(Counter(all_tokenized_words)).sort_values(ascending=False)
    return words_series


def remove_stop_words_en(sentence: str) -> str:
    """Removes the stopwords"""
    # Remove punctuation
    regex = re.compile("[%s]" % re.escape(string.punctuation))
    sentence = regex.sub("", sentence)

    text_tokens = word_tokenize(sentence)
    text_without_stopword = [
        word for word in text_tokens if word.lower() not in STOPWORDS
    ]
    return text_without_stopword


def filter_entries_by_languages(
    journal_df: pd.DataFrame,
    languages: List[str],
    mode: str = "any",
) -> pd.DataFrame:
    """It filters out the entries that do not contain the languages in languages"""
    if mode == "any":
        # Keep entries with at least one sentence with the valid language
        journal_df_languages = journal_df[
            journal_df["languages"].apply(
                lambda x: len(set(languages).intersection(x)) == 1
            )
        ]
    elif mode == "all":
        # Only keep entries where all sentences are of the valid language
        journal_df_languages = journal_df[
            journal_df["languages"].apply(
                lambda x: len([lang for lang in x if lang in languages]) == len(x)
            )
        ]
    else:
        return journal_df
    return journal_df_languages


def filter_entries_by_date(
    journal_df: pd.DataFrame,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
) -> pd.DataFrame:
    """ Filters out the entries not included in the selected time range"""
    if start_date:
        journal_df = journal_df[journal_df["date"] >= start_date]
    if end_date:
        journal_df = journal_df[journal_df["date"] <= end_date]
    return journal_df
