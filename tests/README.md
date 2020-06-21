# Testing

To test locally, first run `python setup.py develop` in the root of this repo. 
This will make sure that the dependencies pinned in `requirements-dev.txt` are 
installed. Usage of virtual environment is recommended.

Then use `pytest` as usual.

Make sure that you don't have other (permanent) versions of this package 
installed.

## Commonly used commands

Install package with an link to this repository:

    python setup.py develop

Uninstall package:
    
    python setup.py develop --uninstall

Check what version of the package is used:

    pip show prometheus-flask-instrumentator

Run pytest for explicit version with all output:

    pytest -v -s -k <method_name>
