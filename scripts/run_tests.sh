#!/bin/bash

for python_version in 3.10 3.11 3.12 3.13; do
    echo "Teting on Python version $python_version"
    venv="py$python_version"
    deactivate
    if [ ! -d "$venv" ]; then
        uv venv $venv --python=$python_version
    fi
    source $venv/bin/activate
    uv pip install -e ".[tests]"
    pytest
done
