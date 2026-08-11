import inspect
from dataclasses import dataclass

_MODES = ('dict', 'list', 'bytes')


class TmsgpackSpecial:
    """Base class for custom tmsgpack codec handlers.

    Subclass and define exactly one encode/decode pair:
        encode_dict / decode_dict  — wire format is key-value pairs
        encode_list / decode_list  — wire format is ordered sequence
        encode_bytes / decode_bytes — wire format is raw bytes

    Example (dict mode):
        class CodecBar(TmsgpackSpecial):
            def encode_dict(obj):
                return {'x': obj.x, 'y': obj.y}
            def decode_dict(*, x, y):
                return Bar(x=x, y=y)

    Example (bytes mode):
        class CodecPoint(TmsgpackSpecial):
            def encode_bytes(obj):
                return struct.pack('ff', obj.x, obj.y)
            def decode_bytes(data):
                x, y = struct.unpack('ff', data)
                return Point(x, y)

    Dependency injection on encode or decode:
        class CodecBig(TmsgpackSpecial):
            def encode_dict(obj, store: Inject[BlobStore]):
                blob_id = store.put(obj.data)
                return {'id': blob_id, 'name': obj.name}
            def decode_dict(*, id, name, store: Inject[BlobStore]):
                data = store.get(id)
                return Big(name=name, data=data)
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        encode_modes = [m for m in _MODES if hasattr(cls, f'encode_{m}')]
        decode_modes = [m for m in _MODES if hasattr(cls, f'decode_{m}')]
        if len(encode_modes) != 1:
            raise TypeError(
                f'{cls.__name__}: define exactly one of encode_dict, encode_list, encode_bytes'
                f' (found: {", ".join(f"encode_{m}" for m in encode_modes) or "none"})'
            )
        if len(decode_modes) != 1:
            raise TypeError(
                f'{cls.__name__}: define exactly one of decode_dict, decode_list, decode_bytes'
                f' (found: {", ".join(f"decode_{m}" for m in decode_modes) or "none"})'
            )
        if encode_modes[0] != decode_modes[0]:
            raise TypeError(
                f'{cls.__name__}: mode mismatch — encode_{encode_modes[0]} vs decode_{decode_modes[0]}'
            )


def _has_injected(fn, di):
    """Check whether any parameter of fn has an Inject[T] annotation."""
    sig = inspect.signature(fn)
    for param in sig.parameters.values():
        if param.annotation is not inspect.Parameter.empty:
            if di.injected_type(param.annotation):
                return True
    return False


@dataclass(frozen=True)
class CodecHandlerSpecial:
    type_name: str
    encode_fn: object
    decode_fn: object
    mode: str               # 'dict' | 'list' | 'bytes'
    encode_has_di: bool
    decode_has_di: bool
    di: object              # DependencyInjectorProtocol

    def encode_ectx(self, ectx):
        value = ectx.value
        if self.encode_has_di:
            data = self.di.sync_call_with_args(fn=self.encode_fn, args=(value,), kwargs={})
        else:
            data = self.encode_fn(value)
        mode = self.mode
        if   mode == 'dict':  ectx.put_dict(self.type_name, data)
        elif mode == 'list':  ectx.put_sequence(self.type_name, data)
        else:                 ectx.put_bytes(self.type_name, data)

    def decode_dctx(self, dctx):
        mode = self.mode
        if mode == 'dict':
            data = dctx.take_dict()
            if self.decode_has_di:
                return self.di.sync_call_with_args(fn=self.decode_fn, args=(), kwargs=data)
            return self.decode_fn(**data)
        elif mode == 'list':
            data = dctx.take_list()
            if self.decode_has_di:
                return self.di.sync_call_with_args(fn=self.decode_fn, args=tuple(data), kwargs={})
            return self.decode_fn(*data)
        else:
            data = dctx.take_bytes()
            if self.decode_has_di:
                return self.di.sync_call_with_args(fn=self.decode_fn, args=(data,), kwargs={})
            return self.decode_fn(data)


def make_codec_handler_special(codec_spec, type_name, di):
    """Create a CodecHandlerSpecial from a TmsgpackSpecial subclass."""
    for mode in _MODES:
        if hasattr(codec_spec, f'encode_{mode}'):
            break
    encode_fn = getattr(codec_spec, f'encode_{mode}')
    decode_fn = getattr(codec_spec, f'decode_{mode}')
    return CodecHandlerSpecial(
        type_name=type_name,
        encode_fn=encode_fn,
        decode_fn=decode_fn,
        mode=mode,
        encode_has_di=_has_injected(encode_fn, di),
        decode_has_di=_has_injected(decode_fn, di),
        di=di,
    )
