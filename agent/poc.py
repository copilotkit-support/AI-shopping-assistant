import nltk

# Run these once in your environment (not every time in code):
# nltk.download("punkt")
# nltk.download("averaged_perceptron_tagger")

def reformat_query(query: str) -> str:
    """
    Extracts the core product noun from a query
    and returns a structured string like:
    'Product search on smartphones'
    """
    # Normalize
    query = query.lower().strip()

    # Tokenize & Part-of-Speech tagging
    tokens = nltk.word_tokenize(query)
    tagged = nltk.pos_tag(tokens)

    # Extract last noun (singular/plural) → product
    product = None
    for word, tag in reversed(tagged):
        if tag in ("NN", "NNS"):  # noun or plural noun
            product = word
            break

    # Fallback in case no noun is found
    if not product:
        product = query

    return f"Product search on {product}"


print(reformat_query("Get me some good smartphones"))
# -> Product search on smartphones

print(reformat_query("Get me some good budget smartphones"))
# -> Product search on smartphones

print(reformat_query("Find me the best budget-friendly 5G laptops under 300 dollars"))
# -> Product search on laptops