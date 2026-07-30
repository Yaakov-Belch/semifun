from typing import Any
from dataclasses import dataclass
from tmsgpack.core import EncodeBuffer, DecodeBuffer
from tmsgpack.core import ebuf_put_value, dbuf_take_value
from tmsgpack.core import TMsgpackError

class EncodeDecode:
    def encode(self, value, target=None):
        codec_type, new_codec, new_value = self.prep_encode(value, target)
        ebuf = EncodeBuffer()
        self.ebuf_put_value(ebuf, codec_type)
        if new_codec is None: ebuf.wr_bytes(new_value)
        else:                 new_codec.ebuf_put_value(ebuf, new_value)
        return ebuf.as_bytes()

    def ebuf_put_value(self, ebuf, value): ebuf_put_value(self, ebuf, value)

    def decode(self, msg, source=None):
        dbuf       = DecodeBuffer(msg=msg, start=0, end=len(msg))
        codec_type = self.dbuf_take_value(dbuf)
        new_codec  = self.decode_codec(codec_type, source)
        value      = new_codec.dbuf_take_value(dbuf)
        return value

    def dbuf_take_value(self, dbuf): return dbuf_take_value(self, dbuf)

    def hash_to_bytes(self, value) -> bytes: # 16 bytes
        import xxhash
        assert self.sort_keys, 'hash_to_bytes: sort_keys is false --> unstable hash.'
        return xxhash.xxh3_128_digest(self.encode(value))

    def hash_to_str(self, value) -> str:     # 22 chars
        from base64 import urlsafe_b64encode
        return urlsafe_b64encode(self.hash_to_bytes(value)).rstrip(b'=').decode('ascii')



@dataclass(frozen=True)
class BasicCodec(EncodeDecode):
    sort_keys = True
    def prep_encode(self, value, target): return [None, self, value]

    def decode_codec(self, codec_type, source):
        if codec_type is None: return self
        raise TMsgpackError(f'Unsupported codec_type: {codec_type}')

    def encode_value(self, ectx):
        raise TMsgpackError(f'Unsupported value: {ectx.value}')

    def decode_from_bytes(self, dctx):
        raise TMsgpackError(f'No bytes extension defined: {dctx._type}')

    def decode_from_list(self, dctx):
        raise TMsgpackError(f'No tuple extension defined: {dctx._type}')


basic_codec = BasicCodec()
