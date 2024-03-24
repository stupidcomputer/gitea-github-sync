{ pkgs ? import <nixpkgs> {} }:
let
  my-python-packages = ps: with ps; [
    requests
    gitpython
    github3_py
  ];
  my-python = pkgs.python3.withPackages my-python-packages;
in my-python.env
