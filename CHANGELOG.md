# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

* Nothing

## [1.0.0] 2020-07-15

### Added

* Method `expose()` implements a way to expose the metrics by adding an 
    endpoint to a given Flask app. Compatible with multiprocess mode.

### Changed

* Switch to SemVer versioning.
* Split instrumentation and exposition into two parts.
* Moved pass of Flask object from constructor to `instrument()` method.
* Extended testing.

## [20.7.5] [YANKED]

## ... [YANKED]