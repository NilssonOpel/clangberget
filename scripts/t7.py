# Download libclang from from
# https://github.com/llvm/llvm-project/releases/tag/llvmorg-11.0.1,
# e.g.
# https://github.com/llvm/llvm-project/releases/download/llvmorg-11.0.1/LLVM-11.0.1-win64.exe
# https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.1/LLVM-14.0.1-win64.exe
# Run and install at e.g. D:\LLVM\11.0.1
#
# For more
# https://pypi.org/project/libclang/
# https://sudonull.com/post/907-An-example-of-parsing-C-code-using-libclang-in-Python


import argparse
import my_python_bindings.cindex as clang
import json
import os
from pprint import pprint
import sys
import textwrap

MY_NAME = os.path.basename(__file__)

DESCRIPTION = f"""
Make a source index of a c or c++ file
"""
USAGE_EXAMPLE = f"""
Example:
> {MY_NAME} -D YES=1 -I my_include_dir --source_file a.c --out_file a.c.indx
"""

#-------------------------------------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(
        MY_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(DESCRIPTION),
        epilog=textwrap.dedent(USAGE_EXAMPLE)
    )
    add = parser.add_argument
    add('-d', '--dependency_file', type=str,
        help='Output file for dependencies')
    add('-D', '--define', type=str, action='append',
        help='Define a macro')
    add('-I', '--include', type=str, action='append',
        help='Add include directory')
    add('-std', '--std', type=str,
        help='Language standard - to see them type\nclang(++) -std=blaj a.c')

    add('-s', '--source_file', required=True, help='Input file')
    add('-o', '--output_file', help='Name of output file')

    options = parser.parse_args()
    if options.define is None:
        options.define = []
    if options.include is None:
        options.include = []
    if options.output_file is None:
        output_file = os.path.basename(options.source_file)
        output_file += '.indx'
        options.output_file = output_file
    return options

#-------------------------------------------------------------------------------
def load_json_data(file):
    data = {}
    with open(file) as fp:
        try:
            data = json.load(fp)
        except json.decoder.JSONDecodeError:
            print('loading json went wrong')

    return data

#-------------------------------------------------------------------------------
def store_json_data(file, data):
    try:
        with open(file, 'w') as fp:
            json.dump(data, fp, indent=2)
    except json.decoder.JSONDecodeError:
        print('saving json went wrong')

#-------------------------------------------------------------------------------
def run(tu, the_tree):
    recurse(tu.cursor, the_tree)

#-------------------------------------------------------------------------------
def print_location(loc, iter):
    filename = None
    if loc.file:
        filename = loc.file.name
    indent = ' ' * iter
    print(f'{indent}{filename}, line: {loc.line}, {loc.column}')

#-------------------------------------------------------------------------------
def get_location(loc):
    location = {}
    filename = None
    if loc.file:
        filename = loc.file.name
    location['filename'] = filename
    location['line'] = loc.line
    location['column']= loc.column
    return location

#-------------------------------------------------------------------------------
def cursorIsReference(kind):
    if (kind >= clang.CursorKind.FIRST_REF and
        kind <= clang.CursorKind.LAST_REF):
        return True
    if (kind >= clang.CursorKind.DECL_REF_EXPR and
        kind <= clang.CursorKind.CALL_EXPR):
        return True
    if kind == clang.CursorKind.MACRO_INSTANTIATION:
        return True

    return False

#-------------------------------------------------------------------------------
def cursorIsDeclaration(kind):
    if (kind >= clang.CursorKind.STRUCT_DECL and
        kind <= clang.CursorKind.OBJC_DYNAMIC_DECL):
        return True
    if (kind == clang.CursorKind.LABEL_STMT):
        return True
    return False

#-------------------------------------------------------------------------------
def cursorIsDefinition(cursor):
    if (cursor.is_definition() or
        cursor.kind == clang.CursorKind.MACRO_DEFINITION):
        return True
    return False

#-------------------------------------------------------------------------------
def wanted_cursor(cursor):
    the_kind = cursor.kind
    if cursorIsDefinition(cursor):
        return True
    if cursorIsDeclaration(the_kind):
        return True
    if cursorIsReference(the_kind):
        return True
    if the_kind.is_preprocessing():
        return True
    return False

#-------------------------------------------------------------------------------
def get_cursorUSR(cursor):
    usr = cursor.get_usr()
    if usr is not None and len(usr):
        return usr

    # See if the cursors' reference can give something
    try:
        if ref := clang.conf.lib.clang_getCursorReferenced(cursor):
            if usr := ref.get_usr():
                if len(usr):
                    return usr
    except TypeError:
        print(f' - not referenceable {cursor.kind}')

    # See if we can get to its definition cursor
    if definition_cursor := cursor.get_definition():
        if usr := definition_cursor.get_usr():
            if len(usr):
                return usr

    return None

#-------------------------------------------------------------------------------
def get_cursorName(cursor):
    name = cursor.spelling
    if name is not None and len(name):
        return name
    return "unknown name"

#-------------------------------------------------------------------------------
def handle_cursor(cursor, the_tree):
    # Get the USR and use as key
    usr = get_cursorUSR(cursor)
    if usr is None:
        usr = get_cursorName(cursor)
        if usr is None:
            print(f'No usr on {cursor.kind}')
            return

    # Prepare contents
    content = {}
    content['reference'] = []
    content['declaration'] = []
    content['definition'] = []

    # Current source position
    src_pos = {}
    src_pos['location'] = get_location(cursor.location)
    src_pos['cursor']  = f'{cursor.kind}'
    try:
        src_pos['storage_class'] = str(cursor.storage_class)
    except Exception as err:
        src_pos['storage_class'] = 'Threw an exception!'
#    src_pos['linkage_kind'] = str(cursor.linkage)

    # A definition is also a declaration - so need to nag
    ref_type = 'UnKnown'
    if cursorIsDefinition(cursor):
        ref_type = 'Definition'
        content['definition'].append(src_pos)
    elif cursorIsDeclaration(cursor.kind):
        ref_type = 'Declaration'
        content['declaration'].append(src_pos)
    if cursorIsReference(cursor.kind):
        ref_type = 'Reference'
        content['reference'].append(src_pos)

    displayname = cursor.displayname
    if displayname is None or len(displayname) == 0:
        displayname = '-No name-'

    if usr not in the_tree:
        content['displayname'] = displayname
        the_tree[usr] = content
        return

    curr_content = the_tree[usr]
    if ref_type == 'Defintion':
        if src_pos not in curr_content['definition']:
            curr_content['definition'].append(src_pos)
    if ref_type == 'Declaration':
        if src_pos not in curr_content['declaration']:
            curr_content['declaration'].append(src_pos)
    if ref_type == 'Reference':
        if src_pos not in curr_content['reference']:
            curr_content['reference'].append(src_pos)
    if 'displayname' in curr_content:
        if displayname != curr_content['displayname']:
#            print (f'Funny spelling: {displayname} - {curr_content["displayname"]}')
            if len(displayname) > len(curr_content['displayname']):
                curr_content['displayname'] = displayname
    else:
        curr_content['displayname'] = displayname

#-------------------------------------------------------------------------------
def recurse(cursor, the_tree):
    if wanted_cursor(cursor):
#        print(f'Cursor: {cursor.kind}')
#        print_location(cursor.location, 2)
        handle_cursor(cursor, the_tree)
    else:
#        print(f'Skip:   {cursor.kind}')
#        print_location(cursor.location, 2)
        pass

    for child in cursor.get_children():
        recurse(child, the_tree)

#-------------------------------------------------------------------------------
def make_command_line(inputs):
#    print(20*'=')
    arguments = ""
    for the_define in inputs.define:
        arguments += f'-D {the_define} '
    for include_dir in inputs.include:
        arguments += f'-I \"{include_dir}\" '

    return inputs.source_file, arguments

#-------------------------------------------------------------------------------
def escape_dep(instring):
    outstring = ""
    instring = instring.strip()

    index = 0
    while index < len(instring):
        ch = instring[index]
        index += 1
        if ch == ' ':
            outstring += "\ "
        elif ch == '$':
            outstring += "$$"
        else:
            outstring += ch

    return outstring

#-------------------------------------------------------------------------------
def add_unique_clang_includes(raw_clang_includes, include_set):
    for clang_include in raw_clang_includes:
        # Filter on system includes ???
        include_name = clang_include.name()
        include_set.add(include_name)

#-------------------------------------------------------------------------------
def generate_dependency_file(options, translation_unit):
    # The source file is included in get_includes()
    raw_includes = translation_unit.get_includes()
    the_inputs = set()
    add_unique_clang_includes(raw_includes, the_inputs)

    target = options.output_file
    dep_file = options.dependency_file
    with open(dep_file, 'w') as fp:
        try:
            output = escape_dep(target) + ':\\\n'
            fp.write(output)
            for the_input in the_inputs:
                output = '  ' + escape_dep(the_input) + '\\\n'
                fp. write(output)

        except Exception as err:
            print(f'Could not generate dependency file {dep_file}')
            print(f'{err = }')

#-------------------------------------------------------------------------------
def main():
    inputs = parse_arguments()
    src_file, arguments = make_command_line(inputs)

#    print(f'{src_file = }\n{arguments = }')
    if not os.path.exists(src_file):
        print(f'Cannot open file "{src_file}"')
        sys.exit(3)

    clang.Config.set_library_path('C:/LLVM/18.1.7/bin')

    exclude_local_declarations = True
    index = clang.Index.create(exclude_local_declarations)
    translation_unit = index.parse(src_file, args=[arguments],
        options=clang.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
#    pprint(translation_unit.cursor)
    the_tree = {}
    run(translation_unit, the_tree)
    if inputs.dependency_file:
        generate_dependency_file(inputs, translation_unit)

    save_file_name = inputs.output_file
    store_json_data(save_file_name, the_tree)
#    print(f'Output saved as {save_file_name}')
    return 0

#-------------------------------------------------------------------------------
#
#-------------------------------------------------------------------------------
sys.exit(main())
