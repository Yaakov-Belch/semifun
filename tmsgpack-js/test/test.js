import {basic_codec, EncodeDecode, TMsgpackError} from "../index.js"

function tmsgpack_test() {
    check_round_trip([[[[1, 2]]]], '._len bug fixed');
    check_round_trip(range(-2000, 2000), 'small integers');

    check_round_trip([
        ...(() => {
            const results = [];
            for (let e = 0; e < 63; e++) {
                for (let d = -10; d < 10; d++) {
                    for (const s of [-1, 1]) {
                        results.push(s * (2**e + d));
                    }
                }
            }
            return results;
        })()
    ], 'integers');

    check_round_trip([3.1415926], 'float');

    check_round_trip([
        ...(() => {
            const results = [];
            for (let e = 0; e < 8; e++) {         // 18
                for (let d = -2; d < 2; d++) {
                    for (const f of [1, 1/3]) {
                        const n = Math.max(1, Math.floor(f * 2**e + d));
                        results.push(
                            "*".repeat(n),
                            new Uint8Array(n).fill(42), // "*" as byte 42
                            new Array(n).fill(12),
                            new Array(n).fill(12), // JavaScript doesn't distinguish tuple/list
                            (() => {
                                const obj = {};
                                for (let m = 0; m < n; m++) {
                                    obj[m] = 3*m + 1;
                                }
                                return obj;
                            })()
                        );
                    }
                }
            }
            return results;
        })()
    ], 'strings, bytes, lists, tuples, dicts');

    check_round_trip([true, false, null], 'constants: true false null');

    check_round_trip([[
        1, 2, 3, 4, {'a': 'hello', 'b': ['world', 5, 6, 7]}
    ]], 'nested value');

    check_round_trip([1760628047033313535], 'large integer')

    const codec = new MyCodec({Foo})
    check_round_trip([new Foo(1,2), new Foo(2,3)], 'Foo', codec)
}

export class MyCodec extends EncodeDecode {
    constructor(types) {
        super(); this.sort_keys=true; this.types=types;
        this.encode_cache={}; this.decode_cache={};
    }

    prep_encode(value, target) { return [null, this, value]; }

    decode_codec(codec_type, source) {
        if (codec_type === null) return this;
        throw new TMsgpackError(`Unsupported codec_type: ${codec_type}`);
    }

    encode_value(ectx) {
        const type_name   = this.value_to_type_name(ectx.value)
        if(!(type_name in this.encode_cache)) {
            const constructor = this.name_to_constructor(type_name)
            const attrs       = this.constructor_to_attrs(constructor)
            this.encode_cache[type_name] = (ectx) => {
                const value = ectx.value
                ectx.put_sequence(type_name, attrs.flatMap((attr) => [attr, value[attr]]))
            }
        }
        this.encode_cache[type_name](ectx)
    }

    decode_from_bytes(dctx) {
        throw new TMsgpackError(`No bytes extension defined: obj_type=${dctx._type}`);
    }

    decode_from_list(dctx) {
        const _type = dctx._type
        if(!(_type in this.decode_cache)) {
            const constructor = this.name_to_constructor(_type)
            const attrs       = this.constructor_to_attrs(constructor)
            this.decode_cache[_type] = (dctx) => {
                const kwargs = dctx.take_dict()
                return new constructor(...attrs.map(attr=>kwargs[attr]))
            }
        }
        return this.decode_cache[_type](dctx)
    }

    value_to_type_name(value) { return value.constructor.class_name }
    name_to_constructor(name) {
        const res = this.types[name]
        if(res) { return res }
        else    { throw new TMsgpackError(`Unsupported type: ${name}`) }
    }
    constructor_to_attrs(constructor) { return constructor.class_attrs }

}

class Foo {
    static class_name  = 'Foo'
    static class_attrs = ['x', 'y']
    constructor(x, y) { this.x=x; this.y=y; }
}

function check_round_trip(values, comment = '', codec=basic_codec) {
    let ok = 0;
    let not_ok = 0;

    for (const value of values) {
        const msg = codec.encode(value);
        const new_value = codec.decode(msg);

        if (deep_equal(new_value, value)) {
            ok++;
        } else {
            not_ok++;
            console.log(value);
            console.log(new_value);
            console.log('-----------------------');
        }
    }

    console.log(`ok=${ok} not_ok=${not_ok} ${comment}`);
}

// This test function is currently not used.
function check_not_supported(values, comment='', codec=basic_codec) {
    let ok = 0;
    let notOk = 0;

    for (const value of values) {
        try {
            codec.encode(value);
            notOk++;
            console.log(`MISSING ERROR: ${value}`);
        } catch (error) {
            if (error instanceof TMsgpackError) { ok++ }
            else                                { throw error }
        }
    }
    console.log(`ok=${ok} notOk=${notOk} ${comment}`);
}
// Helper functions
function range(start, stop) {
    const result = [];
    for (let i = start; i < stop; i++) {
        result.push(i);
    }
    return result;
}

function deep_equal(a, b) {
    if (a === b) return true;

    if (a instanceof Uint8Array && b instanceof Uint8Array) {
        if (a.length !== b.length) return false;
        for (let i = 0; i < a.length; i++) {
            if (a[i] !== b[i]) return false;
        }
        return true;
    }

    if (Array.isArray(a) && Array.isArray(b)) {
        if (a.length !== b.length) return false;
        for (let i = 0; i < a.length; i++) {
            if (!deep_equal(a[i], b[i])) return false;
        }
        return true;
    }

    if (typeof a === 'object' && typeof b === 'object' && a !== null && b !== null) {
        const keysA = Object.keys(a);
        const keysB = Object.keys(b);
        if (keysA.length !== keysB.length) return false;
        for (const key of keysA) {
            if (!keysB.includes(key) || !deep_equal(a[key], b[key])) return false;
        }
        return true;
    }

    return false;
}


tmsgpack_test()
