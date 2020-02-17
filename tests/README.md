## Running all tests (except slow ones)

To run all tests from this folder (except "slow" ones, see below), run following command:

```
python -m unittest -v
```

## Running all tests (including slow ones)

Some tests like `test_qaoa.py` are "slow" tests and are turned off by default.

To run these tests the environment variable `SLOW` needs to be set to 1, like following:

```
SLOW=1 python -m unittest -v
```

## Running individual tests

Just run it like regulat python file (but add `-v` file for more verbosity)

```
SLOW=1 python test_qaoa.py -v
```

## Specifying LOGLEVEL (for tests that use logging)

Example:
```
LOGLEVEL=DEBUG SLOW=1 python test_qaoa.py -v
```