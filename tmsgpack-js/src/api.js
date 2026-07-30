import { EncodeBuffer, DecodeBuffer }      from "./buffers.js"
import { ebuf_put_value, dbuf_take_value } from "./engine.js"
import { TMsgpackError } from "./exceptions.js"

export class EncodeDecode {
    encode(value, target = null) {
        const [codec_type, new_codec, new_value] = this.prep_encode(value, target);
        const ebuf = new EncodeBuffer(1024, 2**31-2);  // Unlimited encoding space

        this.ebuf_put_value(ebuf, codec_type);

        if (new_codec === null) { ebuf.wr_bytes(new_value); }
        else                    { new_codec.ebuf_put_value(ebuf, new_value); }

        return ebuf.as_bytes();
    }

    decode(msg, source = null) {
        const dbuf       = new DecodeBuffer(msg, 0, msg.length);
        const codec_type = this.dbuf_take_value(dbuf);
        const new_codec  = this.decode_codec(codec_type, source);
        const value      = new_codec.dbuf_take_value(dbuf);
        return value;
    }

    ebuf_put_value(ebuf, value) { return ebuf_put_value(this, ebuf, value); }
    dbuf_take_value(dbuf)       { return dbuf_take_value(this, dbuf);       }
}

export class BasicCodec extends EncodeDecode {
    constructor() { super(); this.sort_keys = true; }

    prep_encode(value, target) { return [null, this, value]; }

    decode_codec(codec_type, source) {
        if (codec_type === null) return this;
        throw new TMsgpackError(`Unsupported codec_type: ${codec_type}`);
    }

    encode_value(ectx) {
        throw new TMsgpackError(`Unsupported value: ${ectx.value}`);
    }

    decode_from_bytes(dctx) {
        throw new TMsgpackError(
            `No bytes extension defined: obj_type=${dctx._type}`,
        );
    }

    decode_from_list(dctx) {
        throw new TMsgpackError(
            `No list extension defined: obj_type=${dctx._type}`
        );
    }
}

export const basic_codec = new BasicCodec();
