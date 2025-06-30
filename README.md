# mit-scheme-kernel



A MIT/GNU Scheme Jupyter kernel based on [metakernel](https://github.com/Calysto/metakernel).

## Features

- Interactive execution of MIT/GNU Scheme code in Jupyter notebooks.
- The kernel  can be configured to use a different Scheme installation, such as the one provided by the [Scmutils library](https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html). See the [Configuration](#configuration) section below for more information.
- Implements a cell magic command `%%show_expression` to render the output of a cell into LaTeX, in the same way as the `show-expression` function in the `Smcutils`. See the [mechanics notebook](./examples/mechanics.ipynb) for an example.
- Plus all the features provided by [metakernel](https://github.com/Calysto/metakernel).

## Installation

### Pre-requisites

It requires [MIT/GNU Scheme](https://www.gnu.org/software/mit-scheme/) to be installed (it expects the `mit-scheme` executable to be on the `PATH`).

Depending on the [configuration](#configuration), [Scmutils](https://github.com/slavad/scmutils) may be required. See the [installation instructions](https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html).


### Installation

```bash
pip install mit-scheme-kernel
```


### Post-installation

Run one of the following commands provided by [metakernel](https://github.com/Calysto/metakernel):

```bash
# Install the kernel for the current Python environment
python -m mit_scheme_kernel install --sys-prefix

# Install the kernel for the current user
python -m mit_scheme_kernel install --user

# Global installation, might require root privileges
python -m mit_scheme_kernel install

# To find additional installation options, run:
python -m mit_scheme_kernel install --help
```

## Configuration

There are a few configuration options available to customize the kernel's behavior. See the [default configuration file](./src/mit_scheme_kernel/config.yaml) for a description of these options.

To override the default configuration, create a YAML file containing the options you want to change and set the `MIT_SCHEME_KERNEL_CONFIG` environment variable to the file's absolute path.

For example, to change the `mit-scheme` executable to `mechanics` (the executable created when installing the [Scmutils library](https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html)):

```bash
cat > /tmp/my_config.yaml << EOF
executable: mechanics
filter_output: true
output_value_regex: ^\#\|\s*(.+)\s*\|\#$
EOF

export MIT_SCHEME_KERNEL_CONFIG=/tmp/my_config.yaml
# start Jupyter Notebook
```

## Contributing

Contributions are more than welcome! If you have any suggestions, ideas, or improvements, please feel free to open an issue or a pull request. If you have any questions or would like to start a discussion, please feel free to reach out.

Take a look at the [contributing guidelines](./CONTRIBUTING.md) for more information.

## Credits

- This kernel is built on top of [Calysto/Metakernel](https://github.com/Calysto/metakernel).
- This kernel relies on [GNU/MIT Scheme](https://www.gnu.org/software/mit-scheme/) as its Scheme implementation and was originally inspired by the excellent book [The Structure and Interpretation of Classical Mechanics](https://mitpress.mit.edu/9780262028967/structure-and-interpretation-of-classical-mechanics/) (MIT Press, 2015, second edition) by Gerald Jay Sussman and Jack Wisdom.
- This kernel uses the impressive functionality provided by the [Jupyter Project](https://jupyter.org/).
