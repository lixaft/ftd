# ftd

## About

`ftd` is a package I wrote for my own use. It contains many different things like utility functions, api's or simple tools. Each of them was not written with the goal to use them in a production in mind and can be modified with braking changes without any warning.

That being said, feel free to use and/or copy any code of this repository in your own project!

## Structure

Ther is some package in this repository:

| Path          | Description                                                              |
| :------------ | :----------------------------------------------------------------------- |
| `ftd`         | It contains utility functions or classes organised in different modules. |
| `ftd.api`     | API to handle some of the annoying module or package.                    |
| `ftd.configs` | Contains only serialized files that will be used in this repository.     |
| `ftd.tools`   | Some simple and basic tools that do not require their own depot.         |
| `ftd.ui`      | All utilities that involve the user interface such as widgets or layout. |

## Documentation

The documentation can be locally build using the following command:

```
sphinx-build docs/ docs/_build/ -vE
```

This will build a website locally that can be openned using the `docs/_build/index.html` file.

To be able to build the documentation properly, we need to have some package install in your environment:

```
PyYaml
six
Sphinx
furo
myst_parser
sphinx_copybutton
sphinx_inline_tabs
```
