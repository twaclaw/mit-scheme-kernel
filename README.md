# mit-scheme-kernel



A MIT/GNU Scheme Jupyter kernel based on [metakernel](https://github.com/Calysto/metakernel).

## Features

-

## Installation

### Pre-requisites

Requires [MIT/GNU Scheme](https://www.gnu.org/software/mit-scheme/) to be installed. The installation defaults to the `mit-scheme` executable, but can be configured if the executable has a different name or if a derivative installation is used (e.g., an installation with the [scmutils library](https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html)). See the [Configuration](#configuration) section below for more information.

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

# Configuration

A few configuration options are available to customize the kernel's behavior. See the [default configuration file](./src/mit_scheme_kernel/config.yaml) for a description of the available options.

To change the default configuration, create a YAML file with a subset of the options that you want to override, and then point the `MIT_SCHEME_KERNEL_CONFIG` environment variable to the absolute path of that file.

For example, to change the `mit-scheme` executable to `mechanics` (see [how to install the scmutils library](https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html)):

```bash
cat << EOF > /tmp/my_config.yaml
executable: mechanics
output_value_regex: ^\#\|\s*([^\s]+)\s*\|\#$
EOF

export MIT_SCHEME_KERNEL_CONFIG=/tmp/my_config.yaml
# start Jupyter Notebook
```

# Contributing

Contributions are more than welcome. If you have any suggestions, ideas, or improvements, please feel free to open an issue or a pull request. If you have any questions or want to start a discussion, please feel free to reach out.

Have a look at the [contributing guidelines](./CONTRIBUTING.md) for more information.
