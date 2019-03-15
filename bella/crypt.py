"""
Created on 2015.12.17

@author: ZoeAllen
"""
import os
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex

env_key = os.environ.get('BELLA_CRYPT_KEY', None)


class PrpCrypt:
    def __init__(self, key=None):
        self.key = key or env_key
        if env_key is None:
            raise ValueError("You must specify a key throught"
                             " `key` argument or `BELLA_CRYPT_KEY`"
                             " environment")
        self.mode = AES.MODE_CBC

    def encrypt(self, text: str):
        crypt = AES.new(self.key, self.mode, self.key)
        length = 16
        count = len(text)
        add = length - (count % length)
        text += '\0' * add
        cipher_text = crypt.encrypt(text)
        return b2a_hex(cipher_text)

    def decrypt(self, text) -> str:
        crypt = AES.new(self.key, self.mode, self.key)
        plain_text = crypt.decrypt(a2b_hex(text))
        return plain_text.rstrip(b'\0')
