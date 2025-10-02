# Assignment Template

## Initial Setup

- uv is recommended for managing virtual environments.

```
uv sync --all-groups

uv run manage.py migrate
```

### Run tests

```
uv run poe test
```

### Run server

```
uv run manage.py runserver
```


### Lint and format code

```
uv run poe lint
uv run poe format
```
