import pathlib
import sys
import textwrap
import yaml
import dataclasses
import click
from functools import singledispatchmethod
from dataclasses import dataclass, Field
from typing import Any, get_args, get_origin, Union

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = type(Union[int, float])


@dataclass
class CommonFields:
    comment: str | None = None
    only_for: str | None = None
    not_for: str | None = None
    api: str | None = None
    doc: str | None = None
    emit: bool = True


def toplevel(cls):
    for f in dataclasses.fields(CommonFields):
        setattr(cls, f.name, f)
        cls.__annotations__[f.name] = CommonFields.__annotations__[f.name]
    return dataclass(cls)


@dataclass
class StructMember:
    name: str
    type: str


@toplevel
class Union:
    name: str
    members: list[StructMember] = dataclasses.field(default_factory=list)
    size: int | None = None


@toplevel
class Struct:
    name: str
    members: list[StructMember] = dataclasses.field(default_factory=list)
    size: int | None = None


@dataclass
class EnumMember:
    name: str
    value: int | None = None


@toplevel
class Enum:
    values: list[EnumMember]
    name: str | None = None


@toplevel
class Typedef:
    name: str
    type: str


@toplevel
class LowMem:
    name: str
    type: str
    address: int


@toplevel
class PyVerbatim:
    content: str | None = None
    typedef_content: str | None = None
    name: str | None = None


@toplevel
class Verbatim:
    verbatim: str


@dataclass
class Argument:
    name: str
    type: str


@toplevel
class Function:
    name: str
    trap: int | None = None
    args: list[Argument] = dataclasses.field(default_factory=list)
    executor: str | None = None
    return_: str | None = None


@toplevel
class FunPtr:
    name: str
    args: list[Argument] = dataclasses.field(default_factory=list)
    return_: str | None = None


yaml_types = {
    'function': Function,
    'funptr': FunPtr,
    'verbatim': Verbatim,
    'pyverbatim': PyVerbatim,
    'lowmem': LowMem,
    'typedef': Typedef,
    'enum': Enum,
    'struct': Struct,
    'union': Union,
}


def fix_key(k):
    k = k.replace('-', '_')
    if k == 'return':
        k += "_"
    return k


def identify(y):
    for k in y.keys():
        if r := yaml_types.get(k):
            result = dict(y)
            if k != 'verbatim':
                # Verbatim just has a str value, it's not a namespace
                result.update(result.pop(k, {}))
            return result, r
    raise RuntimeError(f"Could not identify field type for {y!r}")


def get_field_type(field: Field[Any] | type) -> Any:
    if isinstance(field, type):
        return field
    field_type = field.type
    if isinstance(field_type, str):
        raise RuntimeError("parameters dataclass may not use 'from __future__ import annotations")
    origin = get_origin(field_type)
    if origin in (Union, UnionType):
        for arg in get_args(field_type):
            if arg is not None:
                return arg
    if origin is list:
        return [get_field_type(get_args(field_type)[0])]
    return field_type


def yaml_to_type(y, t=None):
    if t is None:
        y, t = identify(y)
    if isinstance(y, t):
        return y
    try:
        kwargs = {}
        fields = {f.name: f for f in dataclasses.fields(t)}
        print(list(fields.keys()), list(y.keys()))
        for k, v in y.items():
            k1 = fix_key(k)
            print(f"{k=} {k1=} {fields=}")
            field = fields[k1]
            field_type = get_field_type(field)
            if isinstance(v, list):
                kwargs[k1] = [yaml_to_type(vi, field_type[0]) for vi in v]
            else:
                kwargs[k1] = yaml_to_type(v, field_type)
        return t(**kwargs)
    except (KeyError, TypeError) as e:
        raise TypeError(f"Converting node {y} to {t}") from e


def load_defs(path):
    with open(path) as f:
        defs = yaml.safe_load(f)
    return [yaml_to_type(d) for d in defs]


signed_integer_types = {'uint8_t', 'uint16_t', 'uint32_t'}
unsigned_integer_types = {'int8_t', 'int16_t', 'int32_t'}


class PointConverter:
    def emit_to_c(self, name_py, name_c):
        return f"Point {name_c} = Point_to_c({name_py});\n"

    def emit_to_py(self, name_c):
        return f"NEW_TUPLE({name_c}.x, {name_c}.y)"


converters = {
    'Point': PointConverter,
}


class SimpleConverter:
    def __init__(self, type_c, to_c, to_py):
        self.type_c = type_c
        self.to_c = to_c
        self.to_py = to_py

    def emit_decls(self):
        pass

    def emit_to_c(self, name_py, name_c):
        return f"{self.type_c} {name_c} = {self.to_c}({name_py});\n"

    def emit_to_py(self, name_c):
        return f"{self.to_py}({name_c})"


class PtrConverter:
    def __init__(self, type_c):
        self.type_c = type_c

    def emit_to_c(self, name_py, name_c):
        is_const = +self.type_c.startswith("const ")  # to get 0/1, not True/False
        return f"{self.type_c} {name_c} = to_c_helper({name_py}, sizeof(*{name_c}), {is_const});\n"

    def emit_to_py(self, name_c):
        is_signed_hint = not self.type_c.lower().startswith('u')
        return f"from_c_helper({name_c}, sizeof(*{name_c}), {+is_signed_hint})"


def make_converter(type_c):
    if converter := converters.get(type_c):
        return converter()
    if type_c in signed_integer_types:
        return SimpleConverter(type_c, "mp_obj_get_int", "mp_obj_new_int")
    if type_c in unsigned_integer_types:
        return SimpleConverter(type_c, "mp_obj_get_int_truncated", "mp_obj_new_int_from_uint")
    if type_c.endswith("*") or type_c.endswith("Handle") or type_c.endswith("Ptr"):
        return PtrConverter(type_c)
    raise ValueError(f"no converter possible for {type_c}")


class Processor:
    def __init__(self, modname):
        self.modname = modname
        self.decls = []
        self.body = []
        self.locals = []
        self.info = []
        self.unknowns = set()
        self.types = {}
        self.body_dedent("""
        #include "py/obj.h"
        #include "py/runtime.h"
        #include "extmod/moductypes.h"
        #include <Multiverse.h>

        // Relies on gcc Variadic Macros and Statement Expressions
        #define NEW_TUPLE(...) \
            ({mp_obj_t _z[] = {__VA_ARGS__}; mp_obj_new_tuple(MP_ARRAY_SIZE(_z), _z); })

        static void *to_c_helper(mp_obj_t obj, size_t objsize, bool is_const) {
            if (mp_obj_is_int(obj)) {
                return (void*)mp_obj_get_int_truncated(obj);
            }
            mp_buffer_info_t bufinfo = {0};
            mp_get_buffer_raise(obj, &bufinfo, is_const ? MP_BUFFER_READ : MP_BUFFER_READ | MP_BUFFER_WRITE);
            if (objsize > 1 && bufinfo.len != objsize) {
                mp_raise_ValueError(MP_ERROR_TEXT("buffer has wrong length"));
            }
            return bufinfo.buf;
        }

        Point Point_to_c(mp_obj_t obj) {
            Point result;
            if (mp_obj_len_maybe(obj) == MP_OBJ_NEW_SMALL_INT(2)) {
                result.h = mp_obj_get_int(mp_obj_subscr(obj, mp_obj_new_int(0), MP_OBJ_SENTINEL));
                result.v = mp_obj_get_int(mp_obj_subscr(obj, mp_obj_new_int(1), MP_OBJ_SENTINEL));
            } else {
                result = *(Point*)to_c_helper(obj, sizeof(Point), true);
            }
            return result;
        }

        mp_obj_t from_c_helper(void *buf, size_t objsize, bool is_signed_hint) {
            return mp_obj_new_int_from_uint(*(unsigned long*)buf);
        }

        mp_obj_t LMGet_common(long address, size_t objsize, mp_obj_t arg) {
            if (arg == mp_const_none) {
                return mp_obj_new_bytearray(objsize, (void*)address);
            }
            mp_buffer_info_t bufinfo = {0};
            mp_get_buffer_raise(arg, &bufinfo, MP_BUFFER_WRITE);
            if (bufinfo.len != objsize) {
                mp_raise_ValueError(MP_ERROR_TEXT("buffer has wrong length"));
            }
            memcpy(bufinfo.buf, (void*)address, objsize);
            return arg;
        }
        void LMSet_common(long address, size_t objsize, mp_obj_t arg) {
            mp_buffer_info_t bufinfo = {0};
            mp_get_buffer_raise(arg, &bufinfo, MP_BUFFER_READ);
            if (bufinfo.len != objsize) {
                mp_raise_ValueError(MP_ERROR_TEXT("buffer has wrong length"));
            }
            memcpy((void*)address, bufinfo.buf, objsize);
        }
        """)
        self.add_local("__name__", f"MP_ROM_QSTR(MP_QSTR_{self.modname})")

    def resolve_type(self, typename):
        print(f"resolve_type {typename!r}")
        typename = typename.strip()
        if typename.startswith("const "):
            return "const " + self.resolve_type(typename.removeprefix("const "))
        if typename.endswith("*"):
            return self.resolve_type(typename.removesuffix("*")) + "*"

        if typename in self.types:
            typename = self.resolve_type(self.types[typename])
        return typename

    def is_ptr(self, typename):
        return typename.endswith("*") or typename.endswith("Handle") or typename.endswith("Ptr")

    def is_const(self, typename):
        return typename.startswith("const ")

    def body_dedent(self, text):
        self.body.append(textwrap.dedent(text.rstrip()))

    def typedefs(self, defs):
        for d in defs:
            if isinstance(d, Typedef):
                self.types[d.name] = d.type
            if isinstance(d, Struct) and d.members:
                self.body_dedent(f"MP_DECLARE_CTYPES_STRUCT({d.name}_type_obj);")
            if isinstance(d, PyVerbatim) and d.typedef_content:
                self.body_dedent(d.typedef_content)

    def emit(self, defs):
        print(f"emitting {len(defs)} defs")
        for d in defs:
            print(d)
            self.emit_node(d)

    @singledispatchmethod
    def emit_node(self, node):
        if type(node) in self.unknowns:
            return
        self.unknowns.add(type(node))
        self.info.append(f"# Unknown {node!r:.68s}...")

    @emit_node.register
    def emit_enum(self, e: Enum):
        for v in e.values:
            if v.value is not None and v.name is not None:
                self.locals.append(f"{{ MP_ROM_QSTR(MP_QSTR_{v.name}), MP_ROM_INT({v.value}) }},")
            # else:
            # self.info.append(f"enumerant without value: {v['name']}")

    @emit_node.register
    def emit_lowmem(self, lm: LowMem):
        name = lm.name
        address = lm.address
        typename = lm.type
        self.body_dedent(f"""
            static mp_obj_t LMGet{name}_fn(size_t n_args, const mp_obj_t *args) {{
                return LMGet_common({address}, sizeof({typename}), n_args == 0 ? mp_const_none : args[0]);
            }}
            MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(LMGet{name}_obj, 0, 1, LMGet{name}_fn);

            static mp_obj_t LMSet{name}_fn(mp_obj_t value) {{
                LMSet_common({address}, sizeof({typename}), value);
                return mp_const_none;
            }}
            MP_DEFINE_CONST_FUN_OBJ_1(LMSet{name}_obj, LMSet{name}_fn);
            """)
        self.add_local(f"LMGet{name}")
        self.add_local(f"LMSet{name}")

    def add_local(self, name, value=...):
        if value is ...:
            value = f"MP_ROM_PTR(&{name}_obj)"
        self.locals.append(f"{{ MP_ROM_QSTR(MP_QSTR_{name}), {value} }},")

    @emit_node.register
    def emit_verbatim(self, v: Verbatim):
        pass  # Ignore verbatim blocks

    @emit_node.register
    def emit_pyverbatim(self, v: PyVerbatim):
        print(f"{v=!r}")
        if v.content:
            self.body.append(v.content)
        if v.name is not None:
            self.add_local(v.name)

    # {'args': [{'name': 'src_bitmap', 'type': 'BitMap*'},
    #          {'name': 'dst_bitmap', 'type': 'BitMap*'},
    #          {'name': 'src_rect', 'type': 'const Rect*'},
    #          {'name': 'dst_rect', 'type': 'const Rect*'},
    #          {'name': 'mode', 'type': 'INTEGER'},
    #          {'name': 'mask', 'type': 'RgnHandle'}],
    # 'executor': 'C_',
    # 'name': 'CopyBits',
    # 'trap': 43244}

    def fun_declare_args_enum(self, args):
        if args:
            args = ", ".join(f"ARG_{arg.name}" for arg in args)
            return f"enum {{ {args} }};"
        return ""

    @staticmethod
    def fun_declare_allowed_arg(arg):
        name = arg.name
        return f"{{ MP_QSTR_{name}, MP_ARG_OBJ | MP_ARG_REQUIRED, {{0}}, }},"

    def fun_parse_args(self, args):
        body = [
            self.fun_declare_args_enum(args),
            "static const mp_arg_t allowed_args[] = {",
            *(self.fun_declare_allowed_arg(a) for a in args),
            "};",
            "mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];",
            "mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);",
        ]
        return "\n".join(f"    {line}" for line in body)

    def make_converter(self, typename):
        typename = self.resolve_type(typename)
        return make_converter(typename)

    def fun_convert_arg(self, idx, arg):
        return self.make_converter(arg.type).emit_to_c(f"args[{idx}].u_obj", arg.name)

    def fun_convert_args(self, args):
        return "".join("    " + self.fun_convert_arg(i, a) for i, a in enumerate(args))

    def fun_call_fun(self, fun):
        return_type = fun.return_
        args = fun.args
        fun_args = ", ".join(arg.name for arg in args)
        funcall = f"{fun.name}({fun_args});"
        if return_type:
            funcall = f"{return_type} retval = {funcall}"
        return "    " + funcall

    def fun_convert_return(self, fun):
        return_type = fun.return_
        if return_type:
            converter = self.make_converter(return_type)
            return f"    return {converter.emit_to_py('retval')};// TODO"
        else:
            return "    return mp_const_none;"

    @emit_node.register
    def emit_function(self, node: Function):
        name = node.name
        args = node.args
        if node.api == 'carbon':
            return
        self.body_dedent(f"""
        mp_obj_t {name}_fn(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {{
             {self.fun_parse_args(args)}
             {self.fun_convert_args(args)}
             {self.fun_call_fun(node)}
             {self.fun_convert_return(node)}
        }}
        MP_DEFINE_CONST_FUN_OBJ_KW({name}_obj, {len(args)}, {name}_fn);
        """)
        self.add_local(name)

    @emit_node.register
    def emit_funptr(self, node: FunPtr):
        pass  # Ignore function pointers for now

    def make_output(self, target):
        print("make_output", target)

        def do_print(*args):
            print(*args, file=target)

        for row in self.decls:
            do_print(row)
        for row in self.body:
            do_print(row)
            do_print()
        do_print("static const mp_rom_map_elem_t module_globals_table[] = {")
        for row in self.locals:
            do_print(f"    {row}")
        do_print("};")
        do_print("static MP_DEFINE_CONST_DICT(module_globals, module_globals_table);")
        do_print(
            textwrap.dedent(f"""
            const mp_obj_module_t {self.modname}_module = {{
                .base = {{ &mp_type_module }},
                .globals = (mp_obj_dict_t *)&module_globals,
            }};

            MP_REGISTER_MODULE(MP_QSTR_{self.modname}, {self.modname}_module);""")
        )

        for row in self.info:
            print(row, file=sys.stderr)


@click.command
@click.argument("defs_files", type=click.Path(path_type=pathlib.Path, exists=True), nargs=-1)
@click.option("-o", "--output", type=click.Path(path_type=pathlib.Path), default=None)
@click.option(
    "-t", "--typedefs", multiple=True, type=click.Path(path_type=pathlib.Path, exists=True)
)
@click.option("-m", "--modname", type=str)
def main(defs_files, output, modname, typedefs):
    print(f"note: {typedefs=!r} {defs_files=!r}")
    if output is None:
        output = pathlib.Path(f"mod{modname}.c")
    # if pyoutput is None:
    # pyoutput = output.with_suffix(".py")
    processor = Processor(modname)

    for t in typedefs:
        defs = load_defs(t)
        processor.typedefs(defs)

    defs = []
    for f in defs_files:
        defs.extend(load_defs(f))
    print(len(defs))
    processor.typedefs(defs)
    processor.emit(defs)

    with open(output, "w") as f:
        processor.make_output(f)
    print(f"wrote to {output!r}")


if __name__ == '__main__':
    main()
