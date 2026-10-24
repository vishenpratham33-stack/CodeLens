# How a search engine works (my notes)

An **inverted index** maps each word to the files that contain it, so a search
jumps straight to the answer. Multi-word queries intersect sorted posting lists
with two pointers. Results are ranked with **TF-IDF**: rare words count more.
A **trie** gives autocomplete, and **edit distance** fixes typos.
The best ten results are picked with a **min-heap** in O(n log k).
