"""
Auto-generate the top-level RST index for the animedex API documentation.

This module scans a project directory for Python modules and packages and
emits a single English ``api_doc.rst`` file containing a toctree directive
that lists every public sub-package and module.

Packages are detected by the presence of an ``__init__.py``; standalone
modules are ``*.py`` files whose name does not start with ``__``.

The generator is single-language by design; ``animedex`` is an
English-only repository (see ``AGENTS.md`` section 1).
"""

import argparse
import os

from natsort import natsorted


def generate_rst_index(input_dir, output_file, title):
    """
    Generate a single RST index file with a titled toctree.

    :param input_dir: Input Python project directory to scan
    :type input_dir: str
    :param output_file: Output RST documentation index file path
    :type output_file: str
    :param title: Section title shown before the toctree
    :type title: str
    """
    rel_names = []
    for name in os.listdir(input_dir):
        item_path = os.path.join(input_dir, name)
        # Check if it's a package (directory with __init__.py) or a standalone module
        if (os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, '__init__.py'))) or \
                (os.path.isfile(item_path) and name.endswith('.py') and not name.startswith('__')):
            if name.endswith('.py'):
                # Remove .py extension for modules
                rel_names.append(os.path.splitext(name)[0])
            else:
                # Keep directory name for packages
                rel_names.append(name)

    # Sort names naturally (e.g., module1, module2, module10)
    rel_names = natsorted(rel_names)

    # Write the titled RST toctree to output file
    with open(output_file, 'w') as f:
        print(f'{title}', file=f)
        print(f'-------------------------', file=f)
        print(f'', file=f)
        print(f'.. toctree::', file=f)
        print(f'    :maxdepth: 2', file=f)
        print(f'    :caption: {title}', file=f)
        print(f'    :hidden:', file=f)
        print(f'', file=f)
        for name in rel_names:
            # Packages get /index suffix, modules don't
            if os.path.exists(os.path.join(input_dir, name, '__init__.py')):
                print(f'    api_doc/{name}/index', file=f)
            else:
                print(f'    api_doc/{name}', file=f)
        print(f'', file=f)
        for name in rel_names:
            if os.path.exists(os.path.join(input_dir, name, '__init__.py')):
                print(f'* :doc:`api_doc/{name}/index`', file=f)
            else:
                print(f'* :doc:`api_doc/{name}`', file=f)
        print(f'', file=f)


def main():
    """
    Main entry point for the RST documentation index generator.

    This function parses command-line arguments, scans the input directory for
    Python modules and packages, and generates RST files with toctree directives
    containing all discovered items in natural sorted order.

    The function identifies:
    - Python packages: directories containing __init__.py
    - Python modules: .py files that don't start with '__'

    Command-line arguments:
        -i, --input_dir: Input Python project directory to scan.
        -o, --output_dir: Output directory for the generated RST file.

    Example::

        $ python auto_rst_top_index.py -i ./animedex -o ./docs/source
        # Generates ./docs/source/api_doc.rst
    """
    parser = argparse.ArgumentParser(description='Auto create rst docs top index for project')
    parser.add_argument('-i', '--input_dir', required=True, help='Input python project directory')
    parser.add_argument('-o', '--output_dir', required=True, help='Output directory for rst doc index files')
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate the single English top-level toctree.
    output = os.path.join(args.output_dir, 'api_doc.rst')
    generate_rst_index(args.input_dir, output, 'API Documentation')
    print(f'Generated: {output}')


if __name__ == '__main__':
    main()
