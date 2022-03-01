# <!-- leav the header empty for the root page -->

<br>

_ftd_ is a python package designed for [Autodesk Maya](https://help.autodesk.com/view/MAYAUL/2022/ENU/) that provides some utilities and tools.

<br>

## Install

### Basic

1. [Download](https://github.com/FabienTaxil/ftd/archive/refs/heads/main.zip) the package and unzip it wherever you want.
2. Inside the `ftd` directory, run a file called `install.py`.
3. Restart maya.

Now you should be able to import the `ftd` package inside maya:

```python
import ftd
```

````{note}
If the `install.py` file is run from the terminal, it is possible to pass the `--maya-version` argument to specify the version of maya on which the installation should be performed.

**Example:**
```bash
python install.py --maya-version 2022
```
````

<br>

### Manual

_ftd_ is distributed as a [maya module](https://help.autodesk.com/view/MAYAUL/2022/ENU//?guid=Maya_SDK_Distributing_Maya_Plug_ins_DistributingUsingModules_html). This mean that once the package is [downloaded](https://github.com/FabienTaxil/ftd/archive/refs/heads/main.zip), the only thing to do is to add the root directory to the `MAYA_MODULE_PATH` environment variable. Then, in the package, a file called `ftd.mod` takes care of everything else when a maya session starts.

There are different possibilities to do this:

- Create the variable within the system or user environment variables.
- Use the [`Maya.env`](https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2020/ENU/Maya-EnvVar/files/GUID-8EFB1AC1-ED7D-4099-9EEE-624097872C04-htm.html) file provided by maya.

  This file can be found at differents location following the current operating system (If it does not exist, it can be created. Make sure to capitalize `Maya.env`)

  ````{admonition} Windows
  ---
  class: windows
  ---
  ```
  ~\Documents\maya\Maya.env
  ~\Documents\maya\<VERSION>\Maya.env
  ```
  ````

  ````{admonition} MacOS
  ---
  class: apple
  ---
  ```
  ~/Library/Preferences/Autodesk/maya/Maya.env
  ~/Library/Preferences/Autodesk/maya/<VERSION>/Maya.env
  ```
  ````

  ````{admonition} Linux
  ---
  class: linux
  ---
  ```
  ~/maya/Maya.env
  ~/maya/<VERSION>/Maya.env
  ```
  ````

  Now simply add the following line to the file, replacing `<...>` with the absolute path to the root directory of the package:

  ```
  MAYA_MODULE_PATH=<...>/ftd
  ```

<br>

````{admonition} Something wrong?
---
class: error
---
If an error of the following form appears

```python
ModuleNotFoundError: No module named 'ftd'
```

This is because Maya does not have access to the module. This can be checked by using the `cmds.moduleInfo` command. It will return a list of strings representing the different modules known by Maya. `ftd` should appear in the list.

```python
from maya import cmds
modules = cmds.moduleInfo(listModules=True)
print("ftd" in modules)
```

Do not hesitate to <a href="mailto:fabien.taxil@gmail.com">contact me</a> if you have any difficulties or if you encounter an unknown problem.
````

<br>

## Overview

| Module        | Description                                                  |
| :------------ | :----------------------------------------------------------- |
| `ftd`         | A very cool description of what you can find in this moudle. |
| `ftd.api`     | A very cool description of what you can find in this moudle. |
| `ftd.solvers` | A very cool description of what you can find in this moudle. |
| `ftd.tools`   | A very cool description of what you can find in this moudle. |
| `ftd.ui`      | A very cool description of what you can find in this moudle. |

<br>

## Documentation

It's possible to localy build this documentation using [sphinx](https://www.sphinx-doc.org/en/master/index.html):

```bash
sphinx-build docs/ docs/_build/
```

The root page will be found at `docs/_build/index.html`.

<br>

## Limitations

Some functions/tools require a minimum version of maya to work. They will be indicated as follows:

```{function} foo

The best  docstring ever written! :D

_Require Maya 2020._
```

```{toctree}
---
hidden:
caption: API Reference
---
apigen/ftd/ftd
```

```{toctree}
---
hidden:
caption: Sphinx Extensions
---
pages/apigen
```

```{toctree}
---
hidden:
caption: Project Links
---
GitHub <https://github.com/lixaft/ftd>
```
