from src.compute_service.gensim_preprocessing import (
    strip_tags,
    strip_multiple_whitespaces,
    preprocess_string,
    strip_punctuation,
    strip_numeric,
    remove_stopwords,
    strip_short,
    deaccent,
)


def clean_text_common(text):
    return preprocess_string(
        text,
        filters=[strip_tags, strip_multiple_whitespaces],
    )


def clean_text_for_sparse(text):
    return preprocess_string(
        text,
        filters=[
            lambda x: x.lower(),
            strip_tags,
            strip_punctuation,
            strip_multiple_whitespaces,
            deaccent,
            strip_numeric,
            remove_stopwords,
            strip_short,
        ],
    )
