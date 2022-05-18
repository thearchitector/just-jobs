# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2022-05-18

### Changed

- Replaced `aioredis` with asyncio `redis-py` and `hiredis`.
- Replaced `pdoc3` with `pdoc`.

### Removed

- Extraneous `anyio` dependency.
- Support for Python <3.7.

## [1.0.0] - 2021-08-27

### Added

- Manager for handling graceful application and worker startups and shutdowns.
- Ability to specify separate queues, each of which is monitoried by a separate worker process.
- Enqueueing jobs via Python pickling serialization.
- Worker processes spawn 20 working coroutines by default, but can be configured via the broker's `coroutines_per_worker` arg.
- Generic Broker interface to allow for custom brokers and logic.
- Redis broker implementation for handling job queueing and running (based on the generic).
- Documentation via `pdoc3` and in-code markdown docstrings.

[unreleased]: https://github.com/thearchitector/just-jobs/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/thearchitector/just-jobs/tree/v1.0.0
