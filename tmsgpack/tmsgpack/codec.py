from base64 import urlsafe_b64encode
from dataclasses import dataclass, field, fields, is_dataclass, replace
from typing import Any, Protocol
from semifun.caching.cached_property import cached_property

import enum
from .api import EncodeDecode


class DependencyInjectorProtocol(Protocol):
    @staticmethod
    def injected_type(annotation: Any) -> type | None: ...
    def with_seed_data(self, seed_data: dict) -> "DependencyInjectorProtocol": ...
    def sync_call_with_args(self, *, fn: Any, args: tuple, kwargs: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class NoDependencyInjector:
    @staticmethod
    def injected_type(annotation):
        return None
    def with_seed_data(self, seed_data):
        raise TypeError("Dependency injection is not supported without a DependencyInjector")
    def sync_call_with_args(self, *, fn, args, kwargs):
        raise TypeError("Dependency injection is not supported without a DependencyInjector")


@dataclass(frozen=True)
class TmsgpackCodec(EncodeDecode):
    sort_keys: bool
    di: DependencyInjectorProtocol
    # Memoization only: init=False keeps them out of the constructor.
    # `replace()` re-runs default_factory, giving each derived codec fresh caches.
    encoder_cache: dict = field(default_factory=dict, init=False, repr=False)
    decoder_cache: dict = field(default_factory=dict, init=False, repr=False)
    plugin_feature_type: str

    def with_seed_data(self, seed_data):
        return replace(self, di=self.di.with_seed_data(seed_data))

    def prep_encode(self, value, target): return [None, self, value]

    def decode_codec(self, codec_type, source):
        if codec_type is None: return self
        raise NotImplementedError(f'Unsupported codec_type: {codec_type}')

    def encode_value(self, ectx):
        _type = type(ectx.value)
        if _type not in self.encoder_cache:
            type_name = self.type_to_type_name(_type=_type)
            codec_spec = self.type_name_to_codec_spec(type_name=type_name)
            codec_handler = self.codec_spec_to_codec_handler(codec_spec=codec_spec, type_name=type_name)
            self.encoder_cache[_type] = codec_handler
        codec_handler = self.encoder_cache[_type]
        codec_handler.encode_ectx(ectx=ectx)

    def decode_from_list(self, dctx):
        type_name = dctx._type
        if type_name not in self.decoder_cache:
            codec_spec = self.type_name_to_codec_spec(type_name=type_name)
            codec_handler = self.codec_spec_to_codec_handler(codec_spec=codec_spec, type_name=type_name)
            self.decoder_cache[type_name] = codec_handler
        codec_handler = self.decoder_cache[type_name]
        return codec_handler.decode_dctx(dctx=dctx)

    def decode_from_bytes(self, dctx):
        raise NotImplementedError(f'No bytes extension defined: {dctx._type}')

    @cached_property
    def feature_map(self):
        from semifun.plugins.registry import get_cached_feature_map
        return get_cached_feature_map(feature_type=self.plugin_feature_type)

    def type_to_type_name(self, _type):
        return _type.__name__

    def type_name_to_codec_spec(self, type_name):
        return self.feature_map(feature=type_name)

    def codec_spec_to_codec_handler(self, codec_spec, type_name):
        if isinstance(codec_spec, enum.EnumType):
            return CodecHandler(type_name=type_name, attributes=('value',), constructor=codec_spec)
        if is_dataclass(codec_spec):
            all_fields = fields(codec_spec)
            injected_type = self.di.injected_type
            passthrough = tuple(f.name for f in all_fields if not injected_type(f.type))
            has_injected = len(passthrough) < len(all_fields)
            if has_injected:
                return CodecHandlerDI(type_name=type_name, attributes=passthrough, constructor=codec_spec, di=self.di)
            else:
                return CodecHandler(type_name=type_name, attributes=passthrough, constructor=codec_spec)
        raise ValueError(f'Cannot encode this type: {codec_spec}')


@dataclass(frozen=True)
class CodecHandler:
    type_name: str
    attributes: tuple[str, ...]
    constructor: callable

    def encode_ectx(self, ectx):
        value = ectx.value
        data = {attr: getattr(value, attr) for attr in self.attributes}
        ectx.put_dict(self.type_name, data)

    def decode_dctx(self, dctx):
        return self.constructor(**dctx.take_dict())


@dataclass(frozen=True)
class CodecHandlerDI(CodecHandler):
    di: DependencyInjectorProtocol

    def decode_dctx(self, dctx):
        return self.di.sync_call_with_args(
            fn=self.constructor,
            args=(),
            kwargs=dctx.take_dict(),
        )
