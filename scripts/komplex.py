# Download libclang from from e.g.
# https://github.com/llvm/llvm-project/releases/,
# e.g.
# https://github.com/llvm/llvm-project/releases/download/llvmorg-18.1.7/LLVM-18.1.7-win64.exe
# Run and install at e.g. D:\LLVM\18.1.7
#
# For more
# https://pypi.org/project/libclang/
# https://sudonull.com/post/907-An-example-of-parsing-C-code-using-libclang-in-Python


import argparse
import os
from pprint import pprint
import re
import shlex
import subprocess
import sys
import textwrap
import yaml

MY_NAME = os.path.basename(__file__)

DESCRIPTION = f"""
Run clang-tidy on a c or c++ file
"""
USAGE_EXAMPLE = f"""
Example:
> {MY_NAME} -D YES=1 -I my_include_dir --source_file a.c
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
        output_file += '.complex'
        options.output_file = output_file
    return options

#-------------------------------------------------------------------------------
def save_as_yaml(file_name, content):
    try:
        with open(file_name, 'w', encoding='utf-8') as file:
            yaml.dump(content, file)
    except yaml.YAMLError as exc:
        print(f"Error in saving yaml: {exc}")

#-------------------------------------------------------------------------------
def do_the_setup(arguments):
    basic_config = {
        "Checks" : "-*,readability-function-cognitive-complexity",
        "CheckOptions" :
            {"readability-function-cognitive-complexity.DescribeBasicIncrements" : "false"},
        "FormatStyle" : "llvm",
        }
    basic_config['ExtraArgs'] = arguments

    return basic_config

#-------------------------------------------------------------------------------
def make_llvm_command_line(inputs):
#    print(20*'=')
    arguments = []
    for the_define in inputs.define:
        arguments.append(f'-D {the_define}')
    for include_dir in inputs.include:
        arguments.append(f'-I \"{include_dir}\"')

    return inputs.source_file, arguments

#-------------------------------------------------------------------------------
def ccp():
    '''Get current code page'''
    try:
        return ccp.codepage
    except AttributeError:
        reply = os.popen('cmd /c CHCP').read()
        cp = re.match(r'^.*:\s+(\d*)$', reply)
        if cp:
            ccp.codepage = cp.group(1)
        else:
            ccp.codepage = 'utf-8'
        return ccp.codepage

#----------------------------------------------------------------------
def _to_cmdline(cmd):
    if isinstance(cmd, str):
        return cmd
    else:
        return ' '.join(shlex.quote(arg) for arg in cmd)

#-------------------------------------------------------------------------------
def run_process(command, do_check, extra_dir=os.getcwd(), as_text=True):
    exit_code = 0
    try:
        encoding_used = None
        if as_text:
            encoding_used = ccp()

        status = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=as_text,
                                shell=True,
                                encoding=encoding_used,  # See https://bugs.python.org/issue27179
                                check=do_check)
        if status.returncode == 0:
            reply = status.stdout
        else:
            reply = status.stdout
            reply += status.stderr
        exit_code = status.returncode

    except Exception as e:
        reply = '\n-start of exception-\n'
        reply += f'The command\n>{command}\nthrew an exception'
        if extra_dir:
            reply += f' (standing in directory {extra_dir})'
        reply += f':\n\n'
        reply += f'type:  {type(e)}\n'
        reply += f'text:  {e}\n'
        reply += '\n-end of exception-\n'
        reply += f'stdout: {e.stdout}\n'
        reply += f'stderr: {e.stderr}\n'
        exit_code = 3

    return reply, exit_code

#-------------------------------------------------------------------------------
def main():
    inputs = parse_arguments()
    src_file, arguments = make_llvm_command_line(inputs)

#    print(f'{src_file = }\n{arguments = }')
    if not os.path.exists(src_file):
        print(f'Cannot open file "{src_file}"')
        sys.exit(3)

    llvm_root = 'C:/LLVM/18.1.7/bin'

    the_config = do_the_setup(arguments)

    config_file = os.path.basename(src_file)
    config_file += '.clang-tidy'
    save_as_yaml(config_file, the_config)

    command = [
        f'{llvm_root}/clang-tidy',
        f'--header-filter=.*',
        f'--config-file={config_file}',
        f'{src_file}',
        ]

    print(_to_cmdline(command))
    reply, exit_code = run_process(command, False)

    save_file_name = inputs.output_file
    with open(save_file_name, 'w') as fp:
        fp.write(reply)
    print(f'Output saved as {save_file_name}')
    os.unlink(config_file)

    return 0

#-------------------------------------------------------------------------------
#
#-------------------------------------------------------------------------------
sys.exit(main())
