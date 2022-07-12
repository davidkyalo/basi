# Basi


[![PyPi version][pypi-image]][pypi-link]
[![Supported Python versions][pyversions-image]][pyversions-link]
[![Build status][ci-image]][ci-link]
[![Coverage status][codecov-image]][codecov-link]


`Basi` is a [dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) framework for Python.

## Install

Install from [PyPi](https://pypi.org/project/basi/)

```
pip install basi
```

## Features

- Async support: `basi` will `await` for you.
- Lots of Providers to choose from. E.g. [Value](basic/providers/value.md), 
[Alias](basic/providers/alias.md).
- Extensibility through `Container` inheritance.
- Multi scope support.
- Fast: minus the cost of an additional stack frame, `basi` resolves dependencies 
nearly as efficiently as resolving them by hand.


## Links

- __[Documentation][docs-link]__
- __[API Reference][api-docs-link]__
- __[Installation][install-link]__
- __[Get Started][why-link]__
- __[Contributing][contributing-link]__



## Production

This package is currently under active development and is not recommended for production use.

Will be production ready from version `v1.0.0` onwards.



[docs-link]: https://davidkyalo.github.io/basi/
[api-docs-link]: https://davidkyalo.github.io/basi/api/
[install-link]: https://davidkyalo.github.io/basi/install.html
[why-link]: https://davidkyalo.github.io/basi/why.html
[contributing-link]: https://davidkyalo.github.io/basi/0.5.x/contributing.html
[pypi-image]: https://img.shields.io/pypi/v/basi.svg?color=%233d85c6
[pypi-link]: https://pypi.python.org/pypi/basi
[pyversions-image]: https://img.shields.io/pypi/pyversions/basi.svg
[pyversions-link]: https://pypi.python.org/pypi/basi
[ci-image]: https://github.com/davidkyalo/basi/actions/workflows/workflow.yaml/badge.svg?event=push&branch=master
[ci-link]: https://github.com/davidkyalo/basi/actions?query=workflow%3ACI%2FCD+event%3Apush+branch%3Amaster
[codecov-image]: https://codecov.io/gh/davidkyalo/basi/branch/master/graph/badge.svg
[codecov-link]: https://codecov.io/gh/davidkyalo/basi

