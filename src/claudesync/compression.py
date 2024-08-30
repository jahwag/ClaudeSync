import json
import zlib
import bz2
import lzma
import base64
import brotli
from collections import Counter
import os
import io
import heapq


def compress_files(local_path, local_files, algorithm):
    packed_content = _pack_files(local_path, local_files)
    return compress_content(packed_content, algorithm)


def decompress_files(local_path, compressed_content, algorithm):
    decompressed_content = decompress_content(compressed_content, algorithm)
    _unpack_files(local_path, decompressed_content)


def _pack_files(local_path, local_files):
    packed_content = io.StringIO()
    for file_path, file_hash in local_files.items():
        full_path = os.path.join(local_path, file_path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        packed_content.write(f"--- BEGIN FILE: {file_path} ---\n")
        packed_content.write(content)
        packed_content.write(f"\n--- END FILE: {file_path} ---\n")
    return packed_content.getvalue()


def _unpack_files(local_path, decompressed_content):
    current_file = None
    current_content = io.StringIO()

    for line in decompressed_content.splitlines():
        if line.startswith("--- BEGIN FILE:"):
            if current_file:
                _write_file(local_path, current_file, current_content.getvalue())
                current_content = io.StringIO()
            current_file = line.split("--- BEGIN FILE:")[1].strip()
        elif line.startswith("--- END FILE:"):
            if current_file:
                _write_file(local_path, current_file, current_content.getvalue())
                current_file = None
                current_content = io.StringIO()
        else:
            current_content.write(line + "\n")

    if current_file:
        _write_file(local_path, current_file, current_content.getvalue())


def _write_file(local_path, file_path, content):
    full_path = os.path.join(local_path, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)


def compress_content(content, algorithm):
    compressors = {
        "zlib": zlib_compress,
        "bz2": bz2_compress,
        "lzma": lzma_compress,
        "brotli": brotli_compress,  # Add Brotli to compressors
        "dictionary": dictionary_compress,
        "rle": rle_compress,
        "huffman": huffman_compress,
        "lzw": lzw_compress,
        "pack": no_compress,
    }
    if algorithm in compressors:
        return compressors[algorithm](content)
    else:
        return content  # No compression


def decompress_content(compressed_content, algorithm):
    decompressors = {
        "zlib": zlib_decompress,
        "bz2": bz2_decompress,
        "lzma": lzma_decompress,
        "brotli": brotli_decompress,  # Add Brotli to decompressors
        "dictionary": dictionary_decompress,
        "rle": rle_decompress,
        "huffman": huffman_decompress,
        "lzw": lzw_decompress,
        "pack": no_decompress,
    }
    if algorithm in decompressors:
        return decompressors[algorithm](compressed_content)
    else:
        return compressed_content  # No decompression


# Pack compression
def no_compress(text):
    return text


def no_decompress(compressed_text):
    return compressed_text


# Brotli compression
def brotli_compress(text):
    compressed = brotli.compress(text.encode("utf-8"))
    return base64.b64encode(compressed).decode("ascii")


def brotli_decompress(compressed_text):
    decoded = base64.b64decode(compressed_text.encode("ascii"))
    return brotli.decompress(decoded).decode("utf-8")


# Zlib compression
def zlib_compress(text):
    compressed = zlib.compress(text.encode("utf-8"))
    return base64.b64encode(compressed).decode("ascii")


def zlib_decompress(compressed_text):
    decoded = base64.b64decode(compressed_text.encode("ascii"))
    return zlib.decompress(decoded).decode("utf-8")


# BZ2 compression
def bz2_compress(text):
    compressed = bz2.compress(text.encode("utf-8"))
    return base64.b64encode(compressed).decode("ascii")


def bz2_decompress(compressed_text):
    decoded = base64.b64decode(compressed_text.encode("ascii"))
    return bz2.decompress(decoded).decode("utf-8")


# LZMA compression
def lzma_compress(text):
    compressed = lzma.compress(text.encode("utf-8"))
    return base64.b64encode(compressed).decode("ascii")


def lzma_decompress(compressed_text):
    decoded = base64.b64decode(compressed_text.encode("ascii"))
    return lzma.decompress(decoded).decode("utf-8")


# Dictionary-based compression
def dictionary_compress(text):
    words = text.split()
    dictionary = {}
    compressed = []

    for word in words:
        if word not in dictionary:
            dictionary[word] = str(len(dictionary))
        compressed.append(dictionary[word])

    return json.dumps({"dict": dictionary, "compressed": " ".join(compressed)})


def dictionary_decompress(compressed_text):
    data = json.loads(compressed_text)
    dictionary = {v: k for k, v in data["dict"].items()}
    return " ".join(dictionary[token] for token in data["compressed"].split())


# Run-length encoding (RLE)
def rle_compress(text):
    compressed = []
    count = 1
    for i in range(1, len(text)):
        if text[i] == text[i - 1]:
            count += 1
        else:
            compressed.append((text[i - 1], count))
            count = 1
    compressed.append((text[-1], count))
    return json.dumps(compressed)


def rle_decompress(compressed_text):
    compressed = json.loads(compressed_text)
    return "".join(char * count for char, count in compressed)


# Huffman coding
class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


def huffman_compress(text):
    freq = Counter(text)
    heap = [HuffmanNode(char, freq) for char, freq in freq.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = HuffmanNode(None, left.freq + right.freq)
        merged.left = left
        merged.right = right
        heapq.heappush(heap, merged)

    root = heap[0]
    codes = {}

    def generate_codes(node, code):
        if node.char:
            codes[node.char] = code
            return
        generate_codes(node.left, code + "0")
        generate_codes(node.right, code + "1")

    generate_codes(root, "")

    encoded = "".join(codes[char] for char in text)
    padding = 8 - len(encoded) % 8
    encoded += "0" * padding

    compressed = bytearray()
    for i in range(0, len(encoded), 8):
        byte = encoded[i : i + 8]
        compressed.append(int(byte, 2))

    return json.dumps(
        {
            "tree": {char: code for char, code in codes.items()},
            "padding": padding,
            "data": base64.b64encode(compressed).decode("ascii"),
        }
    )


def huffman_decompress(compressed_text):
    data = json.loads(compressed_text)
    tree = {code: char for char, code in data["tree"].items()}
    padding = data["padding"]
    compressed = base64.b64decode(data["data"].encode("ascii"))

    binary = "".join(f"{byte:08b}" for byte in compressed)
    binary = binary[:-padding] if padding else binary

    decoded = ""
    code = ""
    for bit in binary:
        code += bit
        if code in tree:
            decoded += tree[code]
            code = ""

    return decoded


# LZW compression
def lzw_compress(text):
    dictionary = {chr(i): i for i in range(256)}
    result = []
    w = ""
    for c in text:
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            result.append(dictionary[w])
            dictionary[wc] = len(dictionary)
            w = c
    if w:
        result.append(dictionary[w])
    return base64.b64encode(bytes(result)).decode("ascii")


def lzw_decompress(compressed_text):
    compressed = base64.b64decode(compressed_text.encode("ascii"))
    dictionary = {i: chr(i) for i in range(256)}
    result = []
    w = chr(compressed[0])
    result.append(w)
    for i in range(1, len(compressed)):
        k = compressed[i]
        if k in dictionary:
            entry = dictionary[k]
        elif k == len(dictionary):
            entry = w + w[0]
        else:
            raise ValueError("Bad compressed k: %s" % k)
        result.append(entry)
        dictionary[len(dictionary)] = w + entry[0]
        w = entry
    return "".join(result)
