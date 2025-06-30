# PRs and other forms of contributing are welcome!

**Thanks a lot for you interest!!!**

## Steps to submit a pull request

1. Fork https://github.com/twaclaw/mit-scheme-kernel
2. Clone your forked repository to your local machine
3. `git remote add upstream https://github.com/twaclaw/mit-scheme-kernel.git`
4. Create a new branch for your changes
5. Set up your development environment. There are many ways to accomplish this task; here is one example that requires [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uv venv venv --python 3.13
. venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
```

6. Make your changes or additions to the codebase.
7. Run the tests:

```bash
# Run tests in all supported Python versions
hatch tests --cover --all

# For specific Python versions
hatch tests --cover --python 3.11
```

8. Push your changes and create a pull request
