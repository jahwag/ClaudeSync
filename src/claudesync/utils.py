import hashlib

def calculate_checksum(content):
    normalized_content = content.replace('\r\n', '\n').replace('\r', '\n').strip()
    return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()