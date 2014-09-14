import zlib, struct, base64, hmac, hashlib, os
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

IV = 16 * '\x00'

class CheckSumError(Exception):
    pass

def _padsecret(secret, blocksize=32, padding='}'):
    """pad secret if not legal AES block size (16, 24, 32)"""
    if not len(secret) in (16, 24, 32):
        return secret + (blocksize - len(secret)) * padding
    return secret

def encrypt(plaintext, secret, lazy=True, checksum=True):
    secret = _padsecret(secret) if lazy else secret
    encobj = AES.new(secret, AES.MODE_CFB, IV)

    if checksum:
        plaintext += struct.pack("i", zlib.crc32(plaintext))

    return base64.b64encode(encobj.encrypt(plaintext))

def decrypt(ciphertext, secret, lazy=True, checksum=True):
    secret = _padsecret(secret) if lazy else secret
    encobj = AES.new(secret, AES.MODE_CFB, IV)
    plaintext = encobj.decrypt(base64.b64decode(ciphertext))

    if checksum:
        crc, plaintext = (plaintext[-4:], plaintext[:-4])
        if not crc == struct.pack("i", zlib.crc32(plaintext)):
            raise CheckSumError("checksum mismatch")

    return plaintext

def signstr(s, k):
    h = hmac.new(k, s, hashlib.sha1)
    return base64.b64encode(h.digest())

def ssh_keygen(size=2048):
    rsa_key = RSA.generate(size, os.urandom)
    public_key = rsa_key.publickey().exportKey(format='OpenSSH')
    private_key = rsa_key.exportKey()
    return (public_key, private_key)
