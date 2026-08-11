# THIS FILE IS AUTOMATICALLY CREATED BY build_pyx.py
# DON'T EDIT THIS FILE.  EDIT THE SOURCES, INSTEAD: tmsgpack/src-parts/*

__version__ = "0.3.13"

from libc.stdint cimport int8_t, int16_t, int32_t, int64_t
from libc.stdint cimport uint8_t, uint16_t, uint32_t, uint64_t
from cpython.long cimport PyLong_AsLongLong
from cpython.tuple cimport PyTuple_New, PyTuple_SetItem

ctypedef double float64_t

import struct
import sys

# Integer limits
cdef int64_t i1_max = 2**7
cdef int64_t i2_max = 2**15
cdef int64_t i4_max = 2**31

cdef uint64_t ui1_max = 2**8
cdef uint64_t ui2_max = 2**16

# Opcode constants
cdef uint8_t FixInt2 = 129
cdef uint8_t FixInt4 = 130
cdef uint8_t FixInt8 = 131

cdef uint8_t FixFloat8 = 132

cdef uint8_t FixStr0 = 133

cdef uint8_t VarStr1 = 149
cdef uint8_t VarStr2 = 150
cdef uint8_t VarStr8 = 151

cdef uint8_t FixBytes0 = 152
cdef uint8_t FixBytes1 = 153
cdef uint8_t FixBytes2 = 154
cdef uint8_t FixBytes4 = 155
cdef uint8_t FixBytes8 = 156
cdef uint8_t FixBytes16 = 157
cdef uint8_t FixBytes20 = 158
cdef uint8_t FixBytes32 = 159

cdef uint8_t VarBytes1 = 160
cdef uint8_t VarBytes2 = 161
cdef uint8_t VarBytes8 = 162

cdef uint8_t FixTuple0 = 163

cdef uint8_t VarTuple1 = 180
cdef uint8_t VarTuple2 = 181
cdef uint8_t VarTuple8 = 182

cdef uint8_t ConstValStart = 183
cdef uint8_t ConstValTrue = 183
cdef uint8_t ConstValFalse = 184
cdef uint8_t ConstValNone = 185

cdef uint8_t NotUsed = 186
cdef uint8_t ConstNegInt = 192

cdef int64_t min_ConstNegInt = ConstNegInt - ui1_max  # This is -64

# For Python interop, also define the type
NoneType = type(None)

# We may want to optimize codec access in the future:
ctypedef object TMsgpackCodec

cdef class EncodeCtx:

    # Warning: This object is mutable and shared.
    # The self.value changes whenever new values are written.
    # Copy early and use the copy.

    cdef readonly TMsgpackCodec codec
    cdef BaseEncodeBuffer       ebuf
    cdef readonly object        value
    cdef bint                   _used
    cdef readonly bint          sort_keys

    def __cinit__(self, TMsgpackCodec codec, BaseEncodeBuffer ebuf):
        self.codec     = codec
        self.ebuf      = ebuf
        self.value     = None
        self._used     = True    # Set to False directly before use.
        self.sort_keys = codec.sort_keys

    cdef _v(self, value):
        self.value = value
        self._used = False
        return self

    cdef _mark_use(self, bint expect_used):
        if expect_used is not self._used:
            if expect_used: raise TMsgpackError('ectx was not used.')
            else:           raise TMsgpackError('ectx used twice.')
        self._used = True
        if expect_used: self.value = None

    cpdef put_str(self, object _type, str value):
        self.put_bytes(_type, value.encode('utf-8'))

    cpdef put_bytes(self, object _type, object value):
        cdef BaseEncodeBuffer ebuf = self.ebuf
        cdef uint64_t         _len
        self._mark_use(False)
        if type(value) is not bytes: raise TMsgpackError(f'not bytes: {value}')

        bytes_val = <bytes>value
        _len = <uint64_t>len(bytes_val)

        if   _len ==  0:     ebuf.wr_uint1(FixBytes0)
        elif _len ==  1:     ebuf.wr_uint1(FixBytes1)
        elif _len ==  2:     ebuf.wr_uint1(FixBytes2)
        elif _len ==  4:     ebuf.wr_uint1(FixBytes4)
        elif _len ==  8:     ebuf.wr_uint1(FixBytes8)
        elif _len == 16:     ebuf.wr_uint1(FixBytes16)
        elif _len == 20:     ebuf.wr_uint1(FixBytes20)
        elif _len == 32:     ebuf.wr_uint1(FixBytes32)
        elif _len < ui1_max: ebuf.wr_uint1(VarBytes1).wr_uint1(<uint8_t>_len)
        elif _len < ui2_max: ebuf.wr_uint1(VarBytes2).wr_uint2(<uint16_t>_len)
        else:                ebuf.wr_uint1(VarBytes8).wr_uint8(<uint64_t>_len)

        ectx_put_value(self, _type)
        ebuf.wr_bytes(bytes_val)

    cpdef put_sequence(self, object _type, object value):
        cdef uint64_t _len = <uint64_t>len(value)
        self._mark_use(False)

        _tuple_header(self.ebuf, _len)
        ectx_put_value(self, _type)

        for v in value: ectx_put_value(self, v)

    cpdef put_dict(self, object _type, object value, bint sort=False):
        cdef object   pairs = value.items()
        cdef uint64_t _len  = <uint64_t>(2 * len(pairs))
        if sort: pairs = sorted(pairs)

        self._mark_use(False)
        _tuple_header(self.ebuf, _len)
        ectx_put_value(self, _type)

        for k, v in pairs:
            ectx_put_value(self, k)
            ectx_put_value(self, v)

    cpdef put_value(self, object value):
        ectx_put_value(self, value)

cdef bint _tuple_header(BaseEncodeBuffer ebuf, uint64_t _len):
    if   _len < 17:      ebuf.wr_uint1(<uint8_t>(FixTuple0 + _len))
    elif _len < ui1_max: ebuf.wr_uint1(VarTuple1).wr_uint1(<uint8_t>_len)
    elif _len < ui2_max: ebuf.wr_uint1(VarTuple2).wr_uint2(<uint16_t>_len)
    else:                ebuf.wr_uint1(VarTuple8).wr_uint8(<uint64_t>_len)

cpdef BaseEncodeBuffer ebuf_put_value(
    TMsgpackCodec codec, BaseEncodeBuffer ebuf, object value
):
    """Encode value to a msg and put it into ebuf."""
    return ectx_put_value(EncodeCtx(codec, ebuf), value)

cdef ectx_put_value(EncodeCtx ectx, object value):
    cdef TMsgpackCodec    codec = ectx.codec
    cdef BaseEncodeBuffer ebuf  = ectx.ebuf
    cdef int64_t int_val
    cdef bytes str_bytes
    cdef uint64_t _len
    cdef bint bool_val

    cdef object t = type(value)

    if t is int:
        # Cast to C int64_t for efficient comparisons and arithmetic
        int_val = PyLong_AsLongLong(value)

        if min_ConstNegInt <= int_val < 0:
            return ebuf.wr_uint1(<uint8_t>(int_val + ui1_max))
        if 0 <= int_val < FixInt2:
            return ebuf.wr_uint1(<uint8_t>int_val)

        if -i2_max <= int_val < i2_max:
            return ebuf.wr_uint1(FixInt2).wr_int2(<int16_t>int_val)
        if -i4_max <= int_val < i4_max:
            return ebuf.wr_uint1(FixInt4).wr_int4(<int32_t>int_val)
        else:
            return ebuf.wr_uint1(FixInt8).wr_int8(<int64_t>int_val)

    if t is float:
        return ebuf.wr_uint1(FixFloat8).wr_float8(<float64_t>value)

    if t is str:
        str_bytes = (<str>value).encode('utf8')
        _len = <uint64_t>len(str_bytes)

        # Str length header -- followed by string characters.
        if   _len < 16:      ebuf.wr_uint1(<uint8_t>(FixStr0 + _len))
        elif _len < ui1_max: ebuf.wr_uint1(VarStr1).wr_uint1(<uint8_t>_len)
        elif _len < ui2_max: ebuf.wr_uint1(VarStr2).wr_uint2(<uint16_t>_len)
        else:                ebuf.wr_uint1(VarStr8).wr_uint8(<uint64_t>_len)

        return ebuf.wr_bytes(str_bytes)

    if t is bool:
        bool_val = <bint>value
        if bool_val is True:  return ebuf.wr_uint1(ConstValTrue)
        if bool_val is False: return ebuf.wr_uint1(ConstValFalse)
        raise TMsgpackError(f'Illegal boolean value: {value}')

    if t is NoneType: return ebuf.wr_uint1(ConstValNone)

    if   t is bytes: ectx._v(None).put_bytes(True, value)
    elif t is tuple: ectx._v(None).put_sequence(True, value)
    elif t is list:  ectx._v(None).put_sequence(False, value)
    elif t is dict:  ectx._v(None).put_dict(None, value, codec.sort_keys)
    else:            codec.encode_value(ectx._v(value)); ectx._mark_use(True)

cdef class DecodeCtx:

    # Warning: This object is mutable and shared.
    # The values self._len, self._type, self._bytes change whenever new values are read.
    # Copy early and use the copies!

    cdef readonly TMsgpackCodec  codec
    cdef BaseDecodeBuffer        dbuf
    cdef readonly uint64_t       _len
    cdef readonly object         _type
    cdef readonly bint           _bytes
    cdef bint                    _used

    def __cinit__(self, TMsgpackCodec codec, BaseDecodeBuffer dbuf):
        self.codec  = codec
        self.dbuf   = dbuf
        self._len   = 0
        self._type  = None
        self._bytes = False
        self._used  = True    # Set to False directly before use.

    cdef _ltb(self, _len, _type, _bytes):
        self._len   = _len
        self._type  = _type
        self._used  = False
        self._bytes = _bytes
        return self

    cdef _mark_use(self, bint expect_used):
        if expect_used is not self._used:
            if expect_used: raise TMsgpackError('dctx was not used.')
            else:           raise TMsgpackError('dctx used twice.')
        self._used = True
        if expect_used: self._len=0; self._type=None; self._bytes=False

    cpdef list take_list(self):
        if self._bytes: raise TMsgpackError('take_list called for bytes')
        self._mark_use(False)

        _list = []
        for i in range(self._len): _list.append(dctx_take_value(self))
        return _list

    cpdef tuple take_tuple(self): return tuple(self.take_list())

    cpdef dict take_dict(self):
        if self._bytes: raise TMsgpackError('take_dict called for bytes')
        self._mark_use(False)

        _dict = {}
        for i in range(self._len // 2):
            k = dctx_take_value(self)
            v = dctx_take_value(self)
            _dict[k] = v
        return _dict

    cpdef bytes take_bytes(self):
        if not self._bytes: raise TMsgpackError('take_bytes called for list')
        self._mark_use(False)
        return self.dbuf.rd_bytes(self._len)

    cpdef str take_str(self):
        if not self._bytes: raise TMsgpackError('take_str called for list')
        self._mark_use(False)
        return self.dbuf.rd_str(self._len)

cpdef object dbuf_take_value(TMsgpackCodec codec, BaseDecodeBuffer dbuf):
    """Take one msg out of dbuf and return the decoded value."""
    return dctx_take_value(DecodeCtx(codec, dbuf))

cdef dctx_take_value(DecodeCtx dctx):
    cdef TMsgpackCodec    codec = dctx.codec
    cdef BaseDecodeBuffer dbuf  = dctx.dbuf
    cdef uint64_t _len
    cdef object   _type

    cdef uint8_t  opcode = dbuf.rd_uint1()

    if not (0 <= opcode < ui1_max):
        raise TMsgpackError(f'Opcode out of range 0-255: {opcode}')

    # Note: Reverse stacked ranges.
    # Every range is bounded above by the range right before it.
    # This is intentional and consistent with the format definition.
    # It provides correct upper bounds for opcodes in each range.

    if ConstNegInt <= opcode: return <int64_t>(opcode - ui1_max)  # negative integer

    if NotUsed <= opcode: raise TMsgpackError(f'Undefined opcode: {opcode}')
    if ConstValStart <= opcode: return _map_consts[opcode - ConstValStart]

    if FixTuple0 <= opcode:
        if   opcode == VarTuple1: _len = <uint64_t>dbuf.rd_uint1()
        elif opcode == VarTuple2: _len = <uint64_t>dbuf.rd_uint2()
        elif opcode == VarTuple8: _len = <uint64_t>dbuf.rd_uint8()
        else:                     _len = <uint64_t>(opcode - FixTuple0)
        # The else branch handles FixTuple0, ..., FixTuple16

        _type = dbuf_take_value(codec, dbuf)

        if _type is True:  return dctx._ltb(_len, _type, False).take_tuple()
        if _type is False: return dctx._ltb(_len, _type, False).take_list()
        if _type is None:  return dctx._ltb(_len, _type, False).take_dict()
        result = codec.decode_from_list(dctx._ltb(_len, _type, False))
        dctx._mark_use(True)
        return result

    if FixBytes0 <= opcode:
        if   opcode == VarBytes1: _len = <uint64_t>dbuf.rd_uint1()
        elif opcode == VarBytes2: _len = <uint64_t>dbuf.rd_uint2()
        elif opcode == VarBytes8: _len = dbuf.rd_uint8()
        else:                     _len = <uint64_t>_map_01248_16_20_32[opcode - FixBytes0]
        # The else branch catches FixBytes0/1/2/4/8/16/20/32

        _type = dbuf_take_value(codec, dbuf)

        if _type is True: return dctx._ltb(_len, _type, True).take_bytes()
        result = codec.decode_from_bytes(dctx._ltb(_len, _type, True))
        dctx._mark_use(True)
        return result

    if FixStr0 <= opcode:
        if opcode == VarStr1: return dbuf.rd_str(<int>dbuf.rd_uint1())
        if opcode == VarStr2: return dbuf.rd_str(<int>dbuf.rd_uint2())
        if opcode == VarStr8: return dbuf.rd_str(<int>dbuf.rd_uint8())
        else:                 return dbuf.rd_str(<int>(opcode - FixStr0))
        # The else branch catches FixStr0, ..., FixStr15

    if FixFloat8 <= opcode:   return dbuf.rd_float8()
    if FixInt2   <= opcode:
        if opcode == FixInt2: return <int64_t>dbuf.rd_int2()
        if opcode == FixInt4: return <int64_t>dbuf.rd_int4()
        if opcode == FixInt8: return dbuf.rd_int8()

    if 0         <= opcode:   return <int64_t>opcode  # const integer


cdef list _map_consts = [True, False, None]  # ConstValTrue, ConstValFalse, ConstValNone
cdef list _map_01248_16_20_32 = [0, 1, 2, 4, 8, 16, 20, 32]  # FixBytes0-FixBytes32

# BaseEncodeBuffer is correct only on little-endian architectures.
# Most modern architectures are little-endian.
# See SafeEncodeBuffer and EncodeBuffer.

cdef class BaseEncodeBuffer:
    cdef bytearray barray

    def __init__(self):
        self.barray = bytearray()

    cdef BaseEncodeBuffer _add_bytes(self, const char* data, size_t length):
        """Internal method that extends barray with raw bytes"""
        self.barray.extend(data[:length])
        return self

    # Bytes and strings
    cpdef BaseEncodeBuffer wr_bytes(self, bytes value):
        """Takes length from the value argument"""
        return self._add_bytes(value, len(value))

    cpdef BaseEncodeBuffer wr_str(self, str value):
        cdef bytes encoded = value.encode('utf-8')
        return self._add_bytes(encoded, len(encoded))

    # Signed integers
    cpdef BaseEncodeBuffer wr_int1(self, int value):
        cdef int8_t val = value
        return self._add_bytes(<char*>&val, sizeof(int8_t))

    cpdef BaseEncodeBuffer wr_int2(self, int value):
        cdef int16_t val = value
        return self._add_bytes(<char*>&val, sizeof(int16_t))

    cpdef BaseEncodeBuffer wr_int4(self, int value):
        cdef int32_t val = value
        return self._add_bytes(<char*>&val, sizeof(int32_t))

    cpdef BaseEncodeBuffer wr_int8(self, long value):
        cdef int64_t val = value
        return self._add_bytes(<char*>&val, sizeof(int64_t))

    # Unsigned integers
    cpdef BaseEncodeBuffer wr_uint1(self, int value):
        cdef uint8_t val = value
        return self._add_bytes(<char*>&val, sizeof(uint8_t))

    cpdef BaseEncodeBuffer wr_uint2(self, int value):
        cdef uint16_t val = value
        return self._add_bytes(<char*>&val, sizeof(uint16_t))

    cpdef BaseEncodeBuffer wr_uint4(self, int value):
        cdef uint32_t val = value
        return self._add_bytes(<char*>&val, sizeof(uint32_t))

    cpdef BaseEncodeBuffer wr_uint8(self, long value):
        cdef uint64_t val = value
        return self._add_bytes(<char*>&val, sizeof(uint64_t))

    # Float
    cpdef BaseEncodeBuffer wr_float8(self, float64_t value):
        return self._add_bytes(<char*>&value, sizeof(float64_t))

    # Get the result.
    cpdef bytes as_bytes(self):
        return bytes(self.barray)

# BaseDecodeBuffer is correct only on little-endian architectures.
# Most modern architectures are little-endian.
# See SafeDecodeBuffer and DecodeBuffer.

cdef class BaseDecodeBuffer:
    cdef bytes msg
    cdef int start
    cdef int end

    def __init__(self, bytes msg, int start, int end):
        self.msg   = msg
        self.start = start
        self.end   = end

    cdef const char* _pull_bytes(self, int n) except NULL:
        """Internal method that returns pointer to n bytes and advances start"""
        cdef int new_start = self.start + n
        if new_start > self.end:
            raise TMsgpackError('Not enough input data')
        cdef const char* result = <const char*>self.msg + self.start
        self.start = new_start
        return result

    # Bytes and strings
    cpdef bytes rd_bytes(self, int n):
        """Takes n bytes and returns them as bytes object"""
        cdef int old_start = self.start
        self._pull_bytes(n)  # Advances self.start and validates bounds
        return self.msg[old_start:self.start]

    cpdef str rd_str(self, int n):
        return self.rd_bytes(n).decode('utf-8')

    # Signed integers
    cpdef int rd_int1(self):
        cdef const char* data = self._pull_bytes(sizeof(int8_t))
        return (<int8_t*>data)[0]

    cpdef int rd_int2(self):
        cdef const char* data = self._pull_bytes(sizeof(int16_t))
        return (<int16_t*>data)[0]

    cpdef int rd_int4(self):
        cdef const char* data = self._pull_bytes(sizeof(int32_t))
        return (<int32_t*>data)[0]

    cpdef long rd_int8(self):
        cdef const char* data = self._pull_bytes(sizeof(int64_t))
        return (<int64_t*>data)[0]

    # Unsigned integers
    cpdef int rd_uint1(self):
        cdef const char* data = self._pull_bytes(sizeof(uint8_t))
        return (<uint8_t*>data)[0]

    cpdef int rd_uint2(self):
        cdef const char* data = self._pull_bytes(sizeof(uint16_t))
        return (<uint16_t*>data)[0]

    cpdef long rd_uint4(self):
        cdef const char* data = self._pull_bytes(sizeof(uint32_t))
        return (<uint32_t*>data)[0]

    cpdef long rd_uint8(self):
        cdef const char* data = self._pull_bytes(sizeof(uint64_t))
        return (<uint64_t*>data)[0]

    # Float
    cpdef float64_t rd_float8(self):
        cdef const char* data = self._pull_bytes(sizeof(float64_t))
        return (<float64_t*>data)[0]

cdef class SafeEncodeBuffer(BaseEncodeBuffer):
    """BaseEncodeBuffer that always encodes to little-endian regardless of platform"""

    # Signed integers - override to use struct.pack
    cpdef BaseEncodeBuffer wr_int1(self, int value):
        return self.wr_bytes(struct.pack('<b', value))

    cpdef BaseEncodeBuffer wr_int2(self, int value):
        return self.wr_bytes(struct.pack('<h', value))

    cpdef BaseEncodeBuffer wr_int4(self, int value):
        return self.wr_bytes(struct.pack('<i', value))

    cpdef BaseEncodeBuffer wr_int8(self, long value):
        return self.wr_bytes(struct.pack('<q', value))

    # Unsigned integers
    cpdef BaseEncodeBuffer wr_uint1(self, int value):
        return self.wr_bytes(struct.pack('<B', value))

    cpdef BaseEncodeBuffer wr_uint2(self, int value):
        return self.wr_bytes(struct.pack('<H', value))

    cpdef BaseEncodeBuffer wr_uint4(self, int value):
        return self.wr_bytes(struct.pack('<I', value))

    cpdef BaseEncodeBuffer wr_uint8(self, long value):
        return self.wr_bytes(struct.pack('<Q', value))

    # Float
    cpdef BaseEncodeBuffer wr_float8(self, float64_t value):
        return self.wr_bytes(struct.pack('<d', value))

cdef class SafeDecodeBuffer(BaseDecodeBuffer):
    """BaseDecodeBuffer that always decodes from little-endian regardless of platform"""

    # Signed integers - override to use struct.unpack
    cpdef int rd_int1(self):
        return struct.unpack('<b', self.rd_bytes(1))[0]

    cpdef int rd_int2(self):
        return struct.unpack('<h', self.rd_bytes(2))[0]

    cpdef int rd_int4(self):
        return struct.unpack('<i', self.rd_bytes(4))[0]

    cpdef long rd_int8(self):
        return struct.unpack('<q', self.rd_bytes(8))[0]

    # Unsigned integers
    cpdef int rd_uint1(self):
        return struct.unpack('<B', self.rd_bytes(1))[0]

    cpdef int rd_uint2(self):
        return struct.unpack('<H', self.rd_bytes(2))[0]

    cpdef long rd_uint4(self):
        return struct.unpack('<I', self.rd_bytes(4))[0]

    cpdef long rd_uint8(self):
        return struct.unpack('<Q', self.rd_bytes(8))[0]

    # Float
    cpdef float64_t rd_float8(self):
        return struct.unpack('<d', self.rd_bytes(8))[0]


# Choose the appropriate implementation based on platform endianness
EncodeBuffer = BaseEncodeBuffer if sys.byteorder == 'little' else SafeEncodeBuffer
DecodeBuffer = BaseDecodeBuffer if sys.byteorder == 'little' else SafeDecodeBuffer
class TMsgpackError(Exception): pass
