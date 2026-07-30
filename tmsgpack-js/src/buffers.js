import { TMsgpackError } from "./exceptions.js"

export class EncodeBuffer {
    constructor(initialSize, maxByteLength) {
        this.buffer     = new ArrayBuffer(initialSize, {maxByteLength});
        this.data_view  = new DataView(this.buffer);
        this.uint8Array = new Uint8Array(this.buffer);
        this.pos        = 0;
        this.max_pos    = initialSize;

        this.textEncoder = new TextEncoder()
        this.collator = new Intl.Collator('en', {
            sensitivity: 'base',
            numeric: false,
            caseFirst: 'false'
        });
    }

    wr(method, n, value, setUint8Array=false) {
        const old_pos = this.pos;
        this.pos += n;

        if (this.pos > this.max_pos) {
            // Calculate new size - double until it's large enough
            let new_size = this.max_pos;
            while (new_size < this.pos) { new_size *= 2; }
            this.buffer.resize(new_size)
            this.max_pos    = new_size;
            this.data_view  = new DataView(this.buffer);
            this.uint8Array = new Uint8Array(this.buffer);
        }

        if(setUint8Array) {
          this.uint8Array[method](value, old_pos)       // method should be 'set'
        } else {
          this.data_view[method](old_pos, value, true)     // true means little-endian
        }
        return this
    }

    // 'bytes' means: Uint8Array
    wr_bytes(value)  { return this.wr('set', value.length, value, true) }

    wr_int1(value)   { return this.wr('setInt8',      1, value) }
    wr_int2(value)   { return this.wr('setInt16',     2, value) }
    wr_int4(value)   { return this.wr('setInt32',     4, value) }
    wr_int8(value)   { return this.wr('setBigInt64',  8, BigInt(value)) }

    wr_uint1(value)  { return this.wr('setUint8',     1, value) }
    wr_uint2(value)  { return this.wr('setUint16',    2, value) }
    wr_uint4(value)  { return this.wr('setUint32',    4, value) }
    wr_uint8(value)  { return this.wr('setBigUint64', 8, BigInt(value)) }

    wr_float4(value) { return this.wr('setFloat32',   4, value) }
    wr_float8(value) { return this.wr('setFloat64',   8, value) }

    as_bytes() {
        // Copy buffer slice so that the result is not resizable!
        return new Uint8Array(this.buffer.slice(0, this.pos));
    } 
}

export class DecodeBuffer {
    constructor(bytes, start = 0, end = null) {
        this.buffer = bytes.buffer.slice(
            bytes.byteOffset, bytes.byteOffset + bytes.byteLength,
        );
        this.data_view   = new DataView(this.buffer);
        this.uint8Array  = new Uint8Array(this.buffer);
        this.pos         = start;
        this.end         = (end !== null) ? end : this.buffer.byteLength;
        this.textDecoder = new TextDecoder('utf-8');
    }

    rd(n, method) {
        const old_pos = this.pos;
        this.pos += n;

        if (this.pos > this.end) {
            throw new TMsgpackError('Not enough input data');
        }

        if(method === 'rdUint8Array') {
          return this.uint8Array.slice(old_pos, this.pos)
        } else {
          return this.data_view[method](old_pos, true)  // true means: little-endian
        }
    }

    rd_bytes(n) { return this.rd(n, 'rdUint8Array'); }
    rd_str(n)   { return this.textDecoder.decode(this.rd_bytes(n)); }
    rd_int1()   { return this.rd(1, 'getInt8'); }
    rd_int2()   { return this.rd(2, 'getInt16'); }
    rd_int4()   { return this.rd(4, 'getInt32'); }
    rd_int8()   { return Number(this.rd(8, 'getBigInt64')); }
    rd_uint1()  { return this.rd(1, 'getUint8'); }
    rd_uint2()  { return this.rd(2, 'getUint16'); }
    rd_uint4()  { return this.rd(4, 'getUint32'); }
    rd_uint8()  { return Number(this.rd(8, 'getBigUint64')); }
    rd_float8() { return this.rd(8, 'getFloat64'); }
}
